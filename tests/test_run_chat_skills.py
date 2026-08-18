import pytest

from backend.services import ollama_client, persona_service, skill_loader
from backend.schemas.persona import PersonaCreate, Capabilities
from backend.config import settings


@pytest.fixture()
def skills_dir(tmp_path, monkeypatch):
    """Points settings.skills_dir at a throwaway directory per test, so
    tests never touch a real skills/ folder. Same fixture as
    test_skill_loader.py."""
    monkeypatch.setattr(settings, "skills_dir", str(tmp_path))
    return tmp_path


def _write_skill(skills_dir, name, content):
    (skills_dir / f"{name}.md").write_text(content, encoding="utf-8")


@pytest.mark.asyncio
async def test_run_chat_injects_skill_as_system_message(db, skills_dir, monkeypatch):
    _write_skill(skills_dir, "concise-answers", "Keep replies under 3 sentences.")

    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="Skill Bot",
            system_prompt="Be helpful.",
            capabilities=Capabilities(skills=["concise-answers"]),
        ),
    )

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await persona_service.run_chat(db, persona.id, "hello", [])

    messages = captured["messages"]
    # system prompt first
    assert messages[0] == {"role": "system", "content": "Be helpful."}
    # skill injected as its own system message, before the user message
    assert messages[1] == {
        "role": "system",
        "content": "Keep replies under 3 sentences.",
    }
    assert messages[-1] == {"role": "user", "content": "hello"}


@pytest.mark.asyncio
async def test_run_chat_injects_multiple_skills_in_order(db, skills_dir, monkeypatch):
    _write_skill(skills_dir, "first-skill", "First instruction.")
    _write_skill(skills_dir, "second-skill", "Second instruction.")

    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="Multi Skill Bot",
            capabilities=Capabilities(skills=["first-skill", "second-skill"]),
        ),
    )

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await persona_service.run_chat(db, persona.id, "hi", [])

    # Both skills joined into a single system message, in the order
    # given in capabilities["skills"] -- matches load_skills()'s
    # documented ordering guarantee.
    assert captured["messages"][0] == {
        "role": "system",
        "content": "First instruction.\n\nSecond instruction.",
    }


@pytest.mark.asyncio
async def test_run_chat_skips_skills_block_for_persona_with_no_skills(db, monkeypatch):
    persona = persona_service.create_persona(
        db, PersonaCreate(name="Plain Bot", system_prompt="Be terse.")
    )

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    await persona_service.run_chat(db, persona.id, "hello", [])

    # No skills attached -- messages go straight from system_prompt to
    # the user message, exactly as before Skills existed.
    assert captured["messages"] == [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "hello"},
    ]


@pytest.mark.asyncio
async def test_run_chat_skills_come_before_knowledge_block(db, skills_dir, monkeypatch):
    from backend.services import knowledge_service

    _write_skill(skills_dir, "concise-answers", "Keep replies short.")

    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="Skill And Knowledge Bot",
            capabilities=Capabilities(skills=["concise-answers"], knowledge=True),
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
    # skill system message comes before the knowledge system message
    assert messages[0] == {"role": "system", "content": "Keep replies short."}
    assert messages[1]["role"] == "system"
    assert "mitochondria" in messages[1]["content"]


@pytest.mark.asyncio
async def test_run_chat_raises_skill_not_found_for_missing_skill_file(
    db, skills_dir, monkeypatch
):
    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="Broken Skill Bot",
            capabilities=Capabilities(skills=["does-not-exist"]),
        ),
    )

    async def fake_chat(model, messages, options=None):
        raise AssertionError("chat() should not be reached -- skill load fails first")

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    with pytest.raises(skill_loader.SkillNotFoundError):
        await persona_service.run_chat(db, persona.id, "hello", [])


@pytest.mark.asyncio
async def test_run_chat_raises_invalid_skill_name_for_unsafe_name(
    db, skills_dir, monkeypatch
):
    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="Unsafe Skill Bot",
            capabilities=Capabilities(skills=["../../etc/passwd"]),
        ),
    )

    async def fake_chat(model, messages, options=None):
        raise AssertionError("chat() should not be reached -- skill load fails first")

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    with pytest.raises(skill_loader.InvalidSkillNameError):
        await persona_service.run_chat(db, persona.id, "hello", [])