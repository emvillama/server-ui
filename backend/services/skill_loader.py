"""
Loads skill content from markdown files on disk. A "skill" is a named
behavioral instruction set (e.g. "always roll initiative before combat")
attached to a persona via capabilities["skills"]: list[str] and injected
into the chat context as-is -- no embedding, no retrieval, no DB row.

Deliberately filesystem-based rather than DB-backed: skills are edited by
hand often, and a .md file you can open and change directly is a better
fit for that than round-tripping through an API. Mirrors dice.py /
chunking.py / similarity.py in staying free of I/O side effects beyond
the filesystem read itself -- no Ollama, no database.

Fail-loud on a missing file: a persona's capabilities["skills"] entry
that no longer resolves to a real file is a configuration error, not
something to silently skip (same reasoning as EmptyExtractionError in
file_extraction.py -- surface it rather than quietly proceeding with a
persona that "should" have an instruction it doesn't actually have).
"""

import re
from pathlib import Path

from backend.config import settings

# Skill names are used to build a filesystem path (skills_dir/<name>.md),
# so they're restricted to a safe character set -- this also blocks path
# traversal via a name like "../../etc/passwd".
_VALID_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")


class SkillNotFoundError(Exception):
    """Raised when a skill name doesn't resolve to an existing .md file."""


class InvalidSkillNameError(ValueError):
    """Raised when a skill name contains characters outside the safe set
    (letters, digits, hyphen, underscore) -- most likely a path traversal
    attempt or a typo'd name with stray punctuation."""


def _skill_path(name: str) -> Path:
    if not _VALID_NAME.match(name):
        raise InvalidSkillNameError(
            f"'{name}' isn't a valid skill name. Use only letters, digits, "
            f"hyphens, and underscores."
        )
    return Path(settings.skills_dir) / f"{name}.md"


def load_skill(name: str) -> str:
    """
    Reads and returns the content of skills/<name>.md, stripped of
    leading/trailing whitespace.

    Raises InvalidSkillNameError for unsafe names, SkillNotFoundError if
    the file doesn't exist.
    """
    path = _skill_path(name)
    if not path.is_file():
        raise SkillNotFoundError(
            f"No skill file found for '{name}' (expected {path})"
        )
    return path.read_text(encoding="utf-8").strip()


def load_skills(names: list[str]) -> list[tuple[str, str]]:
    """
    Loads multiple skills in order, returning a list of (name, content)
    pairs. Order matches `names` -- callers that care about precedence
    (e.g. injecting skills into messages in a specific sequence) can rely
    on this rather than re-sorting.

    Raises on the first missing/invalid skill rather than partially
    loading the rest, for the same fail-loud reasoning as load_skill().
    """
    return [(name, load_skill(name)) for name in names]