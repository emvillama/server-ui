"""
Pure logic for parsing and rolling standard dice notation (e.g. "2d6+3").
No I/O, no dependencies on Ollama or the database -- keeps this trivially
unit-testable in isolation, same pattern as chunking.py / similarity.py.
"""

import random
import re

# Matches things like "2d6", "1d20", "4d6+2", "3d8-1", with optional
# whitespace around the modifier sign.
_DICE_PATTERN = re.compile(
    r"^\s*(\d+)\s*d\s*(\d+)\s*(?:([+-])\s*(\d+))?\s*$",
    re.IGNORECASE,
)

MAX_DICE = 100  # sanity cap so "999999d6" can't be used to hang the process
MAX_SIDES = 1000


class DiceNotationError(ValueError):
    """Raised when input doesn't parse as valid dice notation."""


def parse_notation(notation: str) -> tuple[int, int, int]:
    """
    Parses a dice notation string into (num_dice, sides, modifier).

    Examples:
        "2d6"    -> (2, 6, 0)
        "1d20+5" -> (1, 20, 5)
        "4d6-2"  -> (4, 6, -2)

    Raises DiceNotationError for anything that doesn't match, or that
    exceeds the sanity caps.
    """
    match = _DICE_PATTERN.match(notation)
    if not match:
        raise DiceNotationError(
            f"'{notation}' isn't valid dice notation. Expected format like "
            f"'2d6' or '1d20+3'."
        )

    num_dice = int(match.group(1))
    sides = int(match.group(2))
    sign = match.group(3)
    magnitude = int(match.group(4)) if match.group(4) else 0
    modifier = magnitude if sign in (None, "+") else -magnitude

    if num_dice < 1:
        raise DiceNotationError("Must roll at least 1 die.")
    if num_dice > MAX_DICE:
        raise DiceNotationError(f"Too many dice (max {MAX_DICE}).")
    if sides < 2:
        raise DiceNotationError("Dice must have at least 2 sides.")
    if sides > MAX_SIDES:
        raise DiceNotationError(f"Too many sides (max {MAX_SIDES}).")

    return num_dice, sides, modifier


def roll_dice(notation: str) -> dict:
    """
    Parses and rolls dice notation, returning a breakdown dict:

        {
            "notation": "2d6+3",
            "rolls": [4, 6],
            "modifier": 3,
            "total": 13,
        }

    Raises DiceNotationError for invalid input (caller decides how to
    surface that -- e.g. as a tool-call error back to the model).
    """
    num_dice, sides, modifier = parse_notation(notation)
    rolls = [random.randint(1, sides) for _ in range(num_dice)]
    total = sum(rolls) + modifier

    return {
        "notation": notation.strip(),
        "rolls": rolls,
        "modifier": modifier,
        "total": total,
    }