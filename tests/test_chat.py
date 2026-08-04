from backend.services import ollama_client, persona_service, skill_loader


def test_chat_with_persona(client, persona, monkeypatch):
    async def fake_chat(model, messages, options=None):
        return f"[{model}] saw {len(messages)} messages, last: {messages[-1]['content']}"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    resp = client.post(
        "/chat", json={"persona_id": persona["id"], "message": "hello there"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["persona_id"] == persona["id"]
    assert "hello there" in body["reply"]


def test_chat_includes_system_prompt_as_first_message(client, monkeypatch):
    resp = client.post(
        "/personas",
        json={"name": "Prompt Checker", "system_prompt": "You are terse."},
    )
    persona_id = resp.json()["id"]

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    client.post("/chat", json={"persona_id": persona_id, "message": "hi"})

    assert captured["messages"][0] == {
        "role": "system",
        "content": "You are terse.",
    }


def test_chat_with_missing_persona_404s(client):
    resp = client.post("/chat", json={"persona_id": 999999, "message": "hi"})
    assert resp.status_code == 404


def test_chat_surfaces_ollama_failure_as_502(client, persona, monkeypatch):
    async def failing_chat(model, messages, options=None):
        raise ollama_client.OllamaError("simulated failure")

    monkeypatch.setattr(ollama_client, "chat", failing_chat)

    resp = client.post("/chat", json={"persona_id": persona["id"], "message": "hi"})
    assert resp.status_code == 502


def test_chat_surfaces_missing_skill_as_422(client, persona, monkeypatch):
    async def failing_run_chat(db, persona_id, message, history):
        raise skill_loader.SkillNotFoundError("No skill file found for 'ghost-skill'")
 
    monkeypatch.setattr(persona_service, "run_chat", failing_run_chat)
 
    resp = client.post("/chat", json={"persona_id": persona["id"], "message": "hi"})
    assert resp.status_code == 422
    assert "ghost-skill" in resp.json()["detail"]
 
 
def test_chat_surfaces_invalid_skill_name_as_422(client, persona, monkeypatch):
    async def failing_run_chat(db, persona_id, message, history):
        raise skill_loader.InvalidSkillNameError("'../etc' isn't a valid skill name.")
 
    monkeypatch.setattr(persona_service, "run_chat", failing_run_chat)
 
    resp = client.post("/chat", json={"persona_id": persona["id"], "message": "hi"})
    assert resp.status_code == 422