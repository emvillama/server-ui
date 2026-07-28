from backend.services.tool_registry import (
    TOOL_REGISTRY,
    get_tool_schemas,
    get_tool_executor,
)


# --- get_tool_schemas() ---


def test_get_tool_schemas_returns_schema_for_known_tool():
    schemas = get_tool_schemas(["dice_roller"])
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "dice_roller"


def test_get_tool_schemas_returns_empty_list_for_no_tools():
    assert get_tool_schemas([]) == []


def test_get_tool_schemas_silently_skips_unknown_tool_names():
    # A stale/typo'd tool name in a persona's capabilities shouldn't
    # break the whole lookup -- just quietly not include it.
    schemas = get_tool_schemas(["dice_roller", "not_a_real_tool"])
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "dice_roller"


def test_get_tool_schemas_all_unknown_returns_empty_list():
    assert get_tool_schemas(["fake_one", "fake_two"]) == []


def test_dice_roller_schema_has_required_ollama_shape():
    schema = get_tool_schemas(["dice_roller"])[0]
    assert schema["type"] == "function"
    function = schema["function"]
    assert "description" in function
    assert function["parameters"]["type"] == "object"
    assert "notation" in function["parameters"]["properties"]
    assert function["parameters"]["required"] == ["notation"]


# --- get_tool_executor() ---


def test_get_tool_executor_returns_callable_for_known_tool():
    executor = get_tool_executor("dice_roller")
    assert callable(executor)


def test_get_tool_executor_returns_none_for_unknown_tool():
    assert get_tool_executor("not_a_real_tool") is None


def test_dice_roller_executor_returns_valid_roll():
    executor = get_tool_executor("dice_roller")
    result = executor({"notation": "2d6+3"})
    assert result["notation"] == "2d6+3"
    assert result["modifier"] == 3
    assert result["total"] == sum(result["rolls"]) + 3


def test_dice_roller_executor_returns_error_dict_for_bad_notation():
    # Errors come back as a dict, not raised -- so a malformed model-
    # generated argument can be fed back to the model as a tool result
    # rather than blowing up the whole chat request.
    executor = get_tool_executor("dice_roller")
    result = executor({"notation": "not dice"})
    assert "error" in result


def test_dice_roller_executor_handles_missing_notation_key():
    executor = get_tool_executor("dice_roller")
    result = executor({})
    assert "error" in result


def test_registry_contains_dice_roller():
    assert "dice_roller" in TOOL_REGISTRY