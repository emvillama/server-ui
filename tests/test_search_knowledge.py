import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.services import ollama_client, persona_service, knowledge_service
from backend.schemas.persona import PersonaCreate


@pytest.fixture()
def db():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()
    os.remove(db_path)


# Fake embeddings: map specific known substrings to specific vectors, so
# we can control exactly which chunks should be "similar" to which query,
# rather than relying on real Ollama output.
FAKE_VECTORS = {
    "mitochondria": [1.0, 0.0, 0.0],
    "powerhouse": [0.9, 0.1, 0.0],   # close to mitochondria
    "volcano": [0.0, 0.0, 1.0],       # unrelated
    "query:cell biology": [0.95, 0.05, 0.0],  # should match mitochondria/powerhouse
}


async def fake_embed(model, text):
    for key, vector in FAKE_VECTORS.items():
        if key in text:
            return vector
    return [0.0, 1.0, 0.0]  # fallback, distinct from everything above


@pytest.mark.asyncio
async def test_search_returns_most_similar_chunks_first(db, monkeypatch):
    persona = persona_service.create_persona(db, PersonaCreate(name="Bio Bot"))
    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    await knowledge_service.ingest_document(db, persona.id, "a.txt", "mitochondria facts")
    await knowledge_service.ingest_document(db, persona.id, "b.txt", "powerhouse of the cell")
    await knowledge_service.ingest_document(db, persona.id, "c.txt", "volcano eruption history")

    results = await knowledge_service.search_knowledge(
        db, persona.id, "query:cell biology", top_n=2
    )

    assert len(results) == 2
    texts = [r.chunk_text for r in results]
    assert "mitochondria facts" in texts
    assert "powerhouse of the cell" in texts
    assert "volcano eruption history" not in texts


@pytest.mark.asyncio
async def test_search_respects_top_n(db, monkeypatch):
    persona = persona_service.create_persona(db, PersonaCreate(name="Bio Bot 2"))
    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    await knowledge_service.ingest_document(db, persona.id, "a.txt", "mitochondria facts")
    await knowledge_service.ingest_document(db, persona.id, "b.txt", "powerhouse of the cell")
    await knowledge_service.ingest_document(db, persona.id, "c.txt", "volcano eruption history")

    results = await knowledge_service.search_knowledge(
        db, persona.id, "query:cell biology", top_n=1
    )
    assert len(results) == 1
    assert results[0].chunk_text == "mitochondria facts"


@pytest.mark.asyncio
async def test_search_returns_fewer_than_top_n_if_not_enough_chunks(db, monkeypatch):
    persona = persona_service.create_persona(db, PersonaCreate(name="Sparse Bot"))
    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    await knowledge_service.ingest_document(db, persona.id, "a.txt", "mitochondria facts")

    results = await knowledge_service.search_knowledge(
        db, persona.id, "query:cell biology", top_n=5
    )
    assert len(results) == 1


@pytest.mark.asyncio
async def test_search_with_no_knowledge_returns_empty_list(db, monkeypatch):
    persona = persona_service.create_persona(db, PersonaCreate(name="Empty Bot"))
    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    results = await knowledge_service.search_knowledge(db, persona.id, "anything", top_n=5)
    assert results == []


@pytest.mark.asyncio
async def test_search_missing_persona_raises(db, monkeypatch):
    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    with pytest.raises(persona_service.PersonaNotFoundError):
        await knowledge_service.search_knowledge(db, 999999, "anything")


@pytest.mark.asyncio
async def test_search_only_returns_chunks_for_the_given_persona(db, monkeypatch):
    persona_a = persona_service.create_persona(db, PersonaCreate(name="Persona A"))
    persona_b = persona_service.create_persona(db, PersonaCreate(name="Persona B"))
    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    await knowledge_service.ingest_document(db, persona_a.id, "a.txt", "mitochondria facts")
    await knowledge_service.ingest_document(db, persona_b.id, "b.txt", "powerhouse of the cell")

    results = await knowledge_service.search_knowledge(
        db, persona_a.id, "query:cell biology", top_n=5
    )
    assert len(results) == 1
    assert results[0].persona_id == persona_a.id