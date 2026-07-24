"""
Business logic for ingesting documents into a persona's knowledge base:
chunk the text, embed each chunk via Ollama, and store the results.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.knowledge import Knowledge
from backend.services import ollama_client
from backend.services.chunking import chunk_text
from backend.services.similarity import cosine_similarity
from backend.services.persona_service import get_persona


class KnowledgeNotFoundError(Exception):
    """Raised when deleting a document that doesn't exist for this
    persona -- distinct from PersonaNotFoundError, since the persona
    might exist fine and just never had this filename ingested."""


async def ingest_document(
    db: Session, persona_id: int, source_filename: str, text: str
) -> list[Knowledge]:
    """
    Overwrite semantics: if this persona already has chunks under
    `source_filename` (e.g. re-ingesting an edited document), those old
    chunks are deleted first, so retrieval never mixes stale and current
    content for the same file. The delete and the new inserts happen in
    the same transaction as everything else here -- if embedding fails
    partway through, the rollback below restores the old chunks too,
    rather than leaving the document half-replaced.
    """
    get_persona(db, persona_id)

    chunks = chunk_text(text)

    knowledge_rows: list[Knowledge] = []
    try:
        db.query(Knowledge).filter(
            Knowledge.persona_id == persona_id,
            Knowledge.source_filename == source_filename,
        ).delete()

        for index, chunk in enumerate(chunks):
            vector = await ollama_client.embed(model=settings.embedding_model, text=chunk)
            row = Knowledge(
                persona_id=persona_id,
                source_filename=source_filename,
                chunk_index=index,
                chunk_text=chunk,
                embedding=vector,
            )
            db.add(row)
            knowledge_rows.append(row)

        db.commit()
    except Exception:
        db.rollback()
        raise

    for row in knowledge_rows:
        db.refresh(row)

    return knowledge_rows


async def search_knowledge(
    db: Session, persona_id: int, query: str, top_n: int = 5
) -> list[Knowledge]:
    """
    Embeds `query`, compares it against every stored Knowledge chunk for
    this persona via cosine similarity, and returns the top_n most similar
    chunks, best match first.

    Plain Python loop over rows -- fine at personal scale (see the Phase 2
    handoff notes). Returns fewer than top_n if the persona has fewer
    chunks than that.
    """
    get_persona(db, persona_id)  # PersonaNotFoundError if missing

    chunks = db.query(Knowledge).filter(Knowledge.persona_id == persona_id).all()
    if not chunks:
        return []

    query_vector = await ollama_client.embed(model=settings.embedding_model, text=query)

    scored = [
        (cosine_similarity(query_vector, chunk.embedding), chunk) for chunk in chunks
    ]
    scored.sort(key=lambda pair: pair[0], reverse=True)

    return [chunk for _, chunk in scored[:top_n]]


def list_documents(db: Session, persona_id: int) -> list[dict]:
    """
    Returns one summary entry per distinct source_filename attached to
    this persona -- chunk_count and the most recent created_at among that
    document's chunks -- rather than every raw chunk row. Matches how a
    person actually thinks about "what has this persona ingested."
    """
    get_persona(db, persona_id)

    rows = (
        db.query(
            Knowledge.source_filename,
            func.count(Knowledge.id).label("chunk_count"),
            func.max(Knowledge.created_at).label("ingested_at"),
        )
        .filter(Knowledge.persona_id == persona_id)
        .group_by(Knowledge.source_filename)
        .order_by(Knowledge.source_filename)
        .all()
    )

    return [
        {
            "source_filename": row.source_filename,
            "chunk_count": row.chunk_count,
            "ingested_at": row.ingested_at,
        }
        for row in rows
    ]


def delete_document(db: Session, persona_id: int, source_filename: str) -> None:
    """
    Deletes every chunk belonging to `source_filename` for this persona.
    Raises KnowledgeNotFoundError if no chunks matched (persona exists,
    but never had this filename ingested).
    """
    get_persona(db, persona_id)

    deleted_count = (
        db.query(Knowledge)
        .filter(
            Knowledge.persona_id == persona_id,
            Knowledge.source_filename == source_filename,
        )
        .delete()
    )
    if deleted_count == 0:
        db.rollback()
        raise KnowledgeNotFoundError(
            f"No knowledge found for persona {persona_id} with filename "
            f"'{source_filename}'"
        )

    db.commit()