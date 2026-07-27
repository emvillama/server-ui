import pytest

from backend.services.dice import DiceNotationError, parse_notation, roll_dice


# --- parse_notation() ---


@pytest.mark.parametrize(
    "notation, expected",
    [
        ("2d6", (2, 6, 0)),
        ("1d20", (1, 20, 0)),
        ("1d20+5", (1, 20, 5)),
        ("4d6-2", (4, 6, -2)),
        ("3d8 + 1", (3, 8, 1)),
        ("2D6", (2, 6, 0)),  # case-insensitive
        ("  2d6  ", (2, 6, 0)),  # surrounding whitespace tolerated
    ],
)
def test_parse_notation_valid(notation, expected):
    assert parse_notation(notation) == expected


@pytest.mark.parametrize(
    "notation",
    [
        "2d",  # missing sides
        "d6",  # missing dice count
        "2x6",  # wrong separator
        "2d6++3",  # malformed modifier
        "roll 2d6",  # extra words (guards against a chatty model wrapping the call)
        "",
        "2d6 extra",
    ],
)
def test_parse_notation_rejects_malformed_input(notation):
    with pytest.raises(DiceNotationError):
        parse_notation(notation)


def test_parse_notation_rejects_zero_dice():
    with pytest.raises(DiceNotationError):
        parse_notation("0d6")


def test_parse_notation_rejects_too_many_dice():
    with pytest.raises(DiceNotationError):
        parse_notation("101d6")


def test_parse_notation_accepts_max_dice_boundary():
    # Exactly at the cap should be fine, not rejected
    assert parse_notation("100d6") == (100, 6, 0)


def test_parse_notation_rejects_too_many_sides():
    with pytest.raises(DiceNotationError):
        parse_notation("1d1001")


def test_parse_notation_accepts_max_sides_boundary():
    assert parse_notation("1d1000") == (1, 1000, 0)


def test_parse_notation_rejects_single_sided_die():
    with pytest.raises(DiceNotationError):
        parse_notation("1d1")


# --- roll_dice() ---


def test_roll_dice_returns_expected_shape():
    result = roll_dice("2d6+3")
    assert set(result.keys()) == {"notation", "rolls", "modifier", "total"}
    assert result["notation"] == "2d6+3"
    assert result["modifier"] == 3
    assert len(result["rolls"]) == 2


def test_roll_dice_rolls_are_within_die_range():
    result = roll_dice("5d6")
    assert len(result["rolls"]) == 5
    assert all(1 <= r <= 6 for r in result["rolls"])


def test_roll_dice_total_matches_rolls_plus_modifier():
    result = roll_dice("4d6-2")
    assert result["total"] == sum(result["rolls"]) - 2


def test_roll_dice_single_die_no_modifier():
    result = roll_dice("1d20")
    assert 1 <= result["total"] <= 20
    assert result["modifier"] == 0


def test_roll_dice_strips_whitespace_in_notation_field():
    result = roll_dice("  1d6  ")
    assert result["notation"] == "1d6"


def test_roll_dice_raises_on_invalid_notation():
    with pytest.raises(DiceNotationError):
        roll_dice("not dice")


def test_roll_dice_is_randomized_across_many_rolls():
    # Statistically near-impossible for 30 rolls of 1d20 to all match --
    # guards against an accidental constant/hardcoded return.
    results = {roll_dice("1d20")["total"] for _ in range(30)}
    assert len(results) > 1