import tempfile
import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.services import ollama_client, persona_service, knowledge_service
from backend.schemas.persona import PersonaCreate
from backend.models.knowledge import Knowledge


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


@pytest.mark.asyncio
async def test_ingest_document_creates_knowledge_rows(db, monkeypatch):
    persona = persona_service.create_persona(
        db, PersonaCreate(name="Study Bot", system_prompt="Be terse.")
    )

    async def fake_embed(model, text):
        # Deterministic fake vector -- length depends on text so we can
        # confirm different chunks actually get different vectors.
        return [float(len(text))]

    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    text = "The mitochondria is the powerhouse of the cell. " * 20
    rows = await knowledge_service.ingest_document(db, persona.id, "notes.txt", text)

    assert len(rows) > 1
    for i, row in enumerate(rows):
        assert row.persona_id == persona.id
        assert row.source_filename == "notes.txt"
        assert row.chunk_index == i
        assert row.embedding == [float(len(row.chunk_text))]
        assert row.id is not None


@pytest.mark.asyncio
async def test_ingest_document_missing_persona_raises(db, monkeypatch):
    async def fake_embed(model, text):
        return [1.0]

    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    with pytest.raises(persona_service.PersonaNotFoundError):
        await knowledge_service.ingest_document(db, 999999, "notes.txt", "some text")


@pytest.mark.asyncio
async def test_ingest_document_failure_rolls_back(db, monkeypatch):
    persona = persona_service.create_persona(db, PersonaCreate(name="Fragile Bot"))

    call_count = {"n": 0}

    async def flaky_embed(model, text):
        call_count["n"] += 1
        if call_count["n"] == 3:
            raise ollama_client.OllamaError("simulated failure mid-ingestion")
        return [1.0]

    monkeypatch.setattr(ollama_client, "embed", flaky_embed)

    # target_size default is 500 -- need enough repeats to guarantee at
    # least 3 chunks so the flaky_embed failure on call 3 actually fires.
    text = "The mitochondria is the powerhouse of the cell. " * 60

    with pytest.raises(ollama_client.OllamaError):
        await knowledge_service.ingest_document(db, persona.id, "notes.txt", text)

    # Nothing should have been committed -- atomic ingestion.
    remaining = db.query(Knowledge).filter(Knowledge.persona_id == persona.id).all()
    assert remaining == []


@pytest.mark.asyncio
async def test_knowledge_chunks_relationship(db, monkeypatch):
    persona = persona_service.create_persona(db, PersonaCreate(name="Cascade Bot"))

    async def fake_embed(model, text):
        return [1.0]

    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    await knowledge_service.ingest_document(db, persona.id, "notes.txt", "Short note here.")

    db.refresh(persona)
    assert len(persona.knowledge_chunks) == 1


@pytest.mark.asyncio
async def test_deleting_persona_cascades_to_knowledge(db, monkeypatch):
    # Deliberately does NOT access persona.knowledge_chunks before
    # deleting -- matches how delete_persona() is actually called from
    # the router, so this exercises the real code path. (passive_deletes
    # only defers to the DB's ON DELETE CASCADE for an *unloaded*
    # collection -- see the note on the relationship in models/knowledge.py.)
    persona = persona_service.create_persona(db, PersonaCreate(name="Cascade Bot 2"))

    async def fake_embed(model, text):
        return [1.0]

    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    await knowledge_service.ingest_document(db, persona.id, "notes.txt", "Short note here.")

    persona_service.delete_persona(db, persona.id)

    remaining = db.query(Knowledge).all()
    assert remaining == []