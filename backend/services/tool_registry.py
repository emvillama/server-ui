"""
Maps a tool name (as used in persona.capabilities["tools"]) to (a) the
JSON schema Ollama needs to expose the tool to the model, and (b) the
Python function that actually executes it when the model requests a
call.

Deliberately a plain dict, not a database table -- there's no
tool-specific data that needs to persist or be queried, so a registry
table would just duplicate what's already expressed here in code. See
the Phase 3 handoff notes for the reasoning against a heavier
attachment mechanism.

Each execute function takes the raw `arguments` dict Ollama hands back
from the model's tool call and returns a plain dict -- either the tool's
real result, or {"error": "..."} if the arguments were bad. Errors are
returned rather than raised so the caller can feed them back to the
model as the tool result (letting the model see its own mistake and
retry), rather than the request failing outright.
"""

from typing import Callable

from backend.services.dice import DiceNotationError, roll_dice


def _execute_dice_roller(arguments: dict) -> dict:
    notation = arguments.get("notation", "")
    try:
        return roll_dice(notation)
    except DiceNotationError as exc:
        return {"error": str(exc)}


TOOL_REGISTRY: dict[str, dict] = {
    "dice_roller": {
        "schema": {
            "type": "function",
            "function": {
                "name": "dice_roller",
                "description": (
                    "Rolls dice using standard tabletop notation, e.g. "
                    "'2d6+3' or '1d20'. Always use this for any dice roll, "
                    "ability check, attack roll, or other random tabletop "
                    "outcome -- never invent or estimate a result yourself."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "notation": {
                            "type": "string",
                            "description": (
                                "Dice notation such as '2d6+3', '1d20', or "
                                "'4d6-2'."
                            ),
                        }
                    },
                    "required": ["notation"],
                },
            },
        },
        "execute": _execute_dice_roller,
    }
}


def get_tool_schemas(tool_names: list[str]) -> list[dict]:
    """
    Returns the Ollama-facing schema for each name in `tool_names` that's
    actually registered, silently skipping unknown names rather than
    raising -- a persona with a stale/typo'd tool name in its
    capabilities shouldn't break chat entirely, just not get that tool.
    """
    return [
        TOOL_REGISTRY[name]["schema"]
        for name in tool_names
        if name in TOOL_REGISTRY
    ]


def get_tool_executor(tool_name: str) -> Callable[[dict], dict] | None:
    """Returns the execute function for `tool_name`, or None if it isn't
    a registered tool (e.g. the model hallucinated a tool name that was
    never offered to it)."""
    entry = TOOL_REGISTRY.get(tool_name)
    return entry["execute"] if entry else None