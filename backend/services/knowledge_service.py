"""
Business logic for ingesting documents into a persona's knowledge base:
chunk the text, embed each chunk via Ollama, and store the results.
"""

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.knowledge import Knowledge
from backend.services import ollama_client
from backend.services.chunking import chunk_text
from backend.services.persona_service import get_persona  # also validates persona exists


async def ingest_document(
    db: Session, persona_id: int, source_filename: str, text: str
) -> list[Knowledge]:
    """
    Chunks `text`, embeds each chunk via Ollama, and stores one Knowledge
    row per chunk, attached to `persona_id`.

    Raises PersonaNotFoundError (via get_persona) if persona_id doesn't
    exist -- same failure mode as run_chat(), handled the same way at the
    router boundary.
    """
    # Confirms the persona exists before doing any embedding work --
    # fails fast rather than embedding chunks for a persona that isn't
    # there.
    get_persona(db, persona_id)

    chunks = chunk_text(text)

    knowledge_rows: list[Knowledge] = []
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
    for row in knowledge_rows:
        db.refresh(row)

    return knowledge_rows