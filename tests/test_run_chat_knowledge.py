import pytest

from backend.services import ollama_client, persona_service, knowledge_service
from backend.schemas.persona import PersonaCreate, Capabilities


@pytest.mark.asyncio
async def test_run_chat_injects_retrieved_knowledge_as_system_message(db, monkeypatch):
    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="Study Bot",
            system_prompt="Be terse.",
            capabilities=Capabilities(knowledge=True),
        ),
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


@pytest.mark.asyncio
async def test_run_chat_skips_retrieval_when_flag_off_even_with_knowledge_rows(
    db, monkeypatch
):
    """Phase 5: capabilities.knowledge is a necessary gate, not just the
    existence check. A persona can have real Knowledge rows attached and
    still have retrieval skipped if the flag itself is off -- e.g. an
    existing persona from before Phase 5 that hasn't had the flag
    explicitly turned on yet (see the Phase 5 handoff's no-migration
    decision)."""
    persona = persona_service.create_persona(
        db,
        PersonaCreate(name="Flag Off Bot", system_prompt="Be terse."),
        # capabilities.knowledge defaults to False -- left unset deliberately
    )

    async def fake_embed(model, text):
        return [1.0, 0.0]

    monkeypatch.setattr(ollama_client, "embed", fake_embed)
    await knowledge_service.ingest_document(
        db, persona.id, "notes.txt", "The mitochondria is the powerhouse of the cell."
    )

    embed_called = {"n": 0}

    async def fake_embed_during_chat(model, text):
        embed_called["n"] += 1
        return [1.0, 0.0]

    monkeypatch.setattr(ollama_client, "embed", fake_embed_during_chat)

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await persona_service.run_chat(db, persona.id, "tell me about cells", [])

    # Rows exist, but the flag is off -- retrieval should never fire, so
    # no query-time embed call and no retrieved-context system message.
    assert embed_called["n"] == 0
    assert captured["messages"] == [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "tell me about cells"},
    ]


@pytest.mark.asyncio
async def test_run_chat_skips_retrieval_when_flag_on_but_no_knowledge_rows(
    db, monkeypatch
):
    """The flip side: flag on, but nothing ingested yet. The existence
    check still matters here -- it's what avoids a wasted embedding call
    for a persona that has the capability enabled but no documents yet."""
    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="Flag On Empty Bot",
            system_prompt="Be terse.",
            capabilities=Capabilities(knowledge=True),
        ),
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

    assert embed_called["n"] == 0
    assert captured["messages"] == [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "hello"},
    ]