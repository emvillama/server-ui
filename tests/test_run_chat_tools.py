import json

import pytest

from backend.services import ollama_client, persona_service
from backend.schemas.persona import PersonaCreate, Capabilities


@pytest.mark.asyncio
async def test_run_chat_executes_tool_and_returns_final_reply(db, monkeypatch):
    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="D&D GM",
            system_prompt="You are a DM.",
            capabilities=Capabilities(tools=["dice_roller"]),
        ),
    )

    tool_call_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "dice_roller", "arguments": {"notation": "2d6+3"}}}
        ],
    }

    async def fake_chat_with_tools(model, messages, tools, options=None):
        return tool_call_message

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "You rolled well! The goblin flinches."

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)
    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    reply, model = await persona_service.run_chat(
        db, persona.id, "I attack the goblin, roll 2d6+3", []
    )

    assert reply == "You rolled well! The goblin flinches."

    messages = captured["messages"]
    # the assistant's own tool-call message should be present before the
    # tool result, since Ollama expects that ordering
    assert tool_call_message in messages

    # the tool result message should be a real, correctly-computed roll,
    # not a placeholder or an echo of the model's request
    tool_result_messages = [m for m in messages if m.get("role") == "tool"]
    assert len(tool_result_messages) == 1
    result = json.loads(tool_result_messages[0]["content"])
    assert result["notation"] == "2d6+3"
    assert result["modifier"] == 3
    assert result["total"] == sum(result["rolls"]) + 3

    # user message is present, followed by the assistant's tool-call
    # message and then the tool result -- in that order, since Ollama
    # expects the tool-call message before its corresponding result
    user_index = messages.index(
        {"role": "user", "content": "I attack the goblin, roll 2d6+3"}
    )
    assert messages[user_index + 1] == tool_call_message
    assert messages[user_index + 2]["role"] == "tool"


@pytest.mark.asyncio
async def test_run_chat_skips_tools_for_persona_with_no_tools_attached(db, monkeypatch):
    persona = persona_service.create_persona(
        db, PersonaCreate(name="Plain Bot", system_prompt="Be terse.")
    )

    chat_with_tools_called = {"n": 0}

    async def fake_chat_with_tools(model, messages, tools, options=None):
        chat_with_tools_called["n"] += 1
        raise AssertionError("chat_with_tools should never be called")

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "ok"

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)
    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    reply, model = await persona_service.run_chat(db, persona.id, "hello", [])

    # chat_with_tools() should never have been touched -- no tools
    # attached, so the cheap capabilities check should short-circuit
    # straight to the plain chat() path, exactly as it did before tools
    # existed at all.
    assert chat_with_tools_called["n"] == 0
    assert reply == "ok"
    assert captured["messages"] == [
        {"role": "system", "content": "Be terse."},
        {"role": "user", "content": "hello"},
    ]


@pytest.mark.asyncio
async def test_run_chat_returns_content_directly_when_model_declines_tool(db, monkeypatch):
    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="D&D GM 2", capabilities=Capabilities(tools=["dice_roller"])
        ),
    )

    plain_message = {
        "role": "assistant",
        "content": "Sure, what would you like to do next?",
    }

    async def fake_chat_with_tools(model, messages, tools, options=None):
        return plain_message

    async def fake_chat(model, messages, options=None):
        raise AssertionError(
            "chat() should not be called -- no tool_calls means no "
            "follow-up round trip is needed"
        )

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)
    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    reply, model = await persona_service.run_chat(
        db, persona.id, "what do I see in the room?", []
    )

    assert reply == "Sure, what would you like to do next?"


@pytest.mark.asyncio
async def test_run_chat_handles_unregistered_tool_name_gracefully(db, monkeypatch):
    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="D&D GM 3", capabilities=Capabilities(tools=["dice_roller"])
        ),
    )

    # Model hallucinates a tool name that was never actually offered to
    # it -- should not crash the request.
    hallucinated_tool_call = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "weather_lookup", "arguments": {}}}],
    }

    async def fake_chat_with_tools(model, messages, tools, options=None):
        return hallucinated_tool_call

    captured = {}

    async def fake_chat(model, messages, options=None):
        captured["messages"] = messages
        return "Sorry, I can't check the weather."

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)
    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    reply, model = await persona_service.run_chat(db, persona.id, "is it raining?", [])

    assert reply == "Sorry, I can't check the weather."

    tool_result_messages = [
        m for m in captured["messages"] if m.get("role") == "tool"
    ]
    assert len(tool_result_messages) == 1
    result = json.loads(tool_result_messages[0]["content"])
    assert "error" in result
    assert "weather_lookup" in result["error"]


@pytest.mark.asyncio
async def test_run_chat_passes_correct_tool_schemas_to_ollama(db, monkeypatch):
    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="D&D GM 4", capabilities=Capabilities(tools=["dice_roller"])
        ),
    )

    captured = {}

    async def fake_chat_with_tools(model, messages, tools, options=None):
        captured["tools"] = tools
        return {"role": "assistant", "content": "ok"}

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)

    await persona_service.run_chat(db, persona.id, "hi", [])

    assert len(captured["tools"]) == 1
    assert captured["tools"][0]["function"]["name"] == "dice_roller"