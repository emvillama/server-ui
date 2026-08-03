import pytest

from backend.services.skill_loader import (
    load_skill,
    load_skills,
    SkillNotFoundError,
    InvalidSkillNameError,
)
from backend.config import settings


@pytest.fixture()
def skills_dir(tmp_path, monkeypatch):
    """Points settings.skills_dir at a throwaway directory per test, so
    tests never touch a real skills/ folder."""
    monkeypatch.setattr(settings, "skills_dir", str(tmp_path))
    return tmp_path


def _write_skill(skills_dir, name, content):
    (skills_dir / f"{name}.md").write_text(content, encoding="utf-8")


# --- load_skill() ---


def test_load_skill_returns_file_content(skills_dir):
    _write_skill(skills_dir, "concise-answers", "Keep replies under 3 sentences.")
    assert load_skill("concise-answers") == "Keep replies under 3 sentences."


def test_load_skill_strips_surrounding_whitespace(skills_dir):
    _write_skill(skills_dir, "terse", "\n\n  Be terse.  \n\n")
    assert load_skill("terse") == "Be terse."


def test_load_skill_missing_file_raises(skills_dir):
    with pytest.raises(SkillNotFoundError):
        load_skill("does-not-exist")


@pytest.mark.parametrize(
    "bad_name",
    [
        "../../etc/passwd",
        "../secrets",
        "skills/nested",
        "name with spaces",
        "name.md",
        "",
    ],
)
def test_load_skill_rejects_unsafe_names(skills_dir, bad_name):
    with pytest.raises(InvalidSkillNameError):
        load_skill(bad_name)


def test_load_skill_accepts_hyphen_and_underscore(skills_dir):
    _write_skill(skills_dir, "dnd_combat-rules", "Roll initiative first.")
    assert load_skill("dnd_combat-rules") == "Roll initiative first."


# --- load_skills() ---


def test_load_skills_returns_ordered_pairs(skills_dir):
    _write_skill(skills_dir, "first", "First content.")
    _write_skill(skills_dir, "second", "Second content.")

    result = load_skills(["second", "first"])
    assert result == [("second", "Second content."), ("first", "First content.")]


def test_load_skills_empty_list_returns_empty_list(skills_dir):
    assert load_skills([]) == []


def test_load_skills_raises_on_first_missing_without_partial_results(skills_dir):
    _write_skill(skills_dir, "exists", "Real content.")

    with pytest.raises(SkillNotFoundError):
        load_skills(["exists", "missing"])