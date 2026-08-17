import pytest

from backend.services import ollama_client, persona_service
from backend.schemas.persona import PersonaCreate, Capabilities


def _persona(db, name="Recipe Bot"):
    return persona_service.create_persona(
        db,
        PersonaCreate(
            name=name,
            system_prompt="You are a recipe recommender.",
            capabilities=Capabilities(tools=["return_recipe"]),
        ),
    )


@pytest.mark.asyncio
async def test_run_chat_return_recipe_short_circuits_without_follow_up_chat_call(
    db, monkeypatch
):
    persona = _persona(db)

    recipe_args = {
        "title": "Banana Bread",
        "ingredients": ["2 ripe bananas", "1.5 cups flour"],
        "steps": ["Preheat oven to 350F.", "Mix and bake for 60 minutes."],
    }
    tool_call_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "return_recipe", "arguments": recipe_args}}],
    }

    async def fake_chat_with_tools(model, messages, tools, options=None):
        return tool_call_message

    async def fake_chat(model, messages, options=None):
        raise AssertionError(
            "chat() should never be called for return_recipe -- it's a "
            "terminal tool, not a round-trip one"
        )

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)
    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    reply, model, structured_output = await persona_service.run_chat(
        db, persona.id, "give me a banana bread recipe", []
    )

    assert structured_output == recipe_args
    assert "Banana Bread" in reply


@pytest.mark.asyncio
async def test_run_chat_return_recipe_structured_output_matches_arguments_exactly(
    db, monkeypatch
):
    persona = _persona(db)

    recipe_args = {
        "title": "Simple Omelette",
        "ingredients": ["3 eggs", "1 tbsp butter", "salt"],
        "steps": ["Whisk eggs with salt.", "Melt butter in pan.", "Cook eggs 2-3 minutes."],
    }
    tool_call_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "return_recipe", "arguments": recipe_args}}],
    }

    async def fake_chat_with_tools(model, messages, tools, options=None):
        return tool_call_message

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)

    _, _, structured_output = await persona_service.run_chat(
        db, persona.id, "quick breakfast idea?", []
    )

    # exact pass-through -- no reshaping, dropped fields, or renaming
    assert structured_output["title"] == "Simple Omelette"
    assert structured_output["ingredients"] == recipe_args["ingredients"]
    assert structured_output["steps"] == recipe_args["steps"]


@pytest.mark.asyncio
async def test_run_chat_return_recipe_ignores_other_tool_calls_in_same_response(
    db, monkeypatch
):
    persona = _persona(db)

    recipe_args = {"title": "Toast", "ingredients": ["bread"], "steps": ["Toast it."]}
    mixed_tool_call_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "dice_roller", "arguments": {"notation": "1d6"}}},
            {"function": {"name": "return_recipe", "arguments": recipe_args}},
        ],
    }

    async def fake_chat_with_tools(model, messages, tools, options=None):
        return mixed_tool_call_message

    async def fake_chat(model, messages, options=None):
        raise AssertionError("chat() should not be called -- return_recipe is terminal")

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)
    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    reply, model, structured_output = await persona_service.run_chat(
        db, persona.id, "roll for it then give me toast", []
    )

    # return_recipe wins regardless of position or other tool_calls
    # present in the same response -- dice_roller's result is simply
    # never executed or surfaced
    assert structured_output == recipe_args


@pytest.mark.asyncio
async def test_run_chat_return_recipe_missing_title_falls_back_to_default(db, monkeypatch):
    persona = _persona(db)

    recipe_args = {"ingredients": ["mystery ingredient"], "steps": ["Cook it."]}
    tool_call_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [{"function": {"name": "return_recipe", "arguments": recipe_args}}],
    }

    async def fake_chat_with_tools(model, messages, tools, options=None):
        return tool_call_message

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)

    reply, model, structured_output = await persona_service.run_chat(
        db, persona.id, "surprise me", []
    )

    assert "Recipe" in reply  # falls back to the generic "Recipe" title
    assert structured_output == recipe_args


@pytest.mark.asyncio
async def test_run_chat_non_recipe_tools_still_take_the_round_trip_path(db, monkeypatch):
    """Sanity check that adding return_recipe's shortcut didn't
    accidentally change dice_roller's existing round-trip behavior for
    a persona that has both tools attached."""
    persona = persona_service.create_persona(
        db,
        PersonaCreate(
            name="D&D GM with recipes?",
            capabilities=Capabilities(tools=["dice_roller", "return_recipe"]),
        ),
    )

    tool_call_message = {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {"function": {"name": "dice_roller", "arguments": {"notation": "1d20"}}}
        ],
    }

    async def fake_chat_with_tools(model, messages, tools, options=None):
        return tool_call_message

    async def fake_chat(model, messages, options=None):
        return "You rolled a natural 20!"

    monkeypatch.setattr(ollama_client, "chat_with_tools", fake_chat_with_tools)
    monkeypatch.setattr(ollama_client, "chat", fake_chat)

    reply, model, structured_output = await persona_service.run_chat(
        db, persona.id, "roll initiative", []
    )

    assert reply == "You rolled a natural 20!"
    assert structured_output is None