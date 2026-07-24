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


@pytest.mark.asyncio
async def test_run_chat_injects_retrieved_knowledge_as_system_message(db, monkeypatch):
    persona = persona_service.create_persona(
        db, PersonaCreate(name="Study Bot", system_prompt="Be terse.")
    )

    async def fake_embed(model, text):
        return [1.0, 0.0]

    monkeypatch.setattr(ollama_client, "embed", fake_embed)
    await knowledge_service.ingest_document(
        db, persona.id, "notes.txt", "The mitochondria is the powerhouse of the cell."
    )

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await persona_service.run_chat(db, persona.id, "tell me about cells", [])

    messages = captured["messages"]
    # system prompt first
    assert messages[0] == {"role": "system", "content": "Be terse."}
    # retrieved context injected as a second system message, before the
    # user's actual message
    assert messages[1]["role"] == "system"
    assert "mitochondria" in messages[1]["content"]
    assert "notes.txt" in messages[1]["content"]
    # user message still present, last
    assert messages[-1] == {"role": "user", "content": "tell me about cells"}


@pytest.mark.asyncio
async def test_run_chat_skips_retrieval_for_persona_with_no_knowledge(db, monkeypatch):
    persona = persona_service.create_persona(
        db, PersonaCreate(name="Plain Bot", system_prompt="Be terse.")
    )

    embed_called = {"n": 0}

    async def fake_embed(model, text):
        embed_called["n"] += 1
        return [1.0]

    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await persona_service.run_chat(db, persona.id, "hello", [])

    # embed() should never have been called -- no knowledge attached,
    # so the cheap existence check should have short-circuited retrieval.
    assert embed_called["n"] == 0
    messages = captured["messages"]
    assert messages == [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "hello"},
    ]