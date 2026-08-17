"""
Request/response shapes for the /personas endpoints. Kept separate from the
SQLAlchemy model in backend/models/persona.py because the API contract and
the storage layout are allowed to diverge.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class OllamaParams(BaseModel):
    """Mirrors Ollama's native `options` dict. All fields optional -- omit
    a field to let Ollama use its own default."""

    temperature: Optional[float] = None
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    num_ctx: Optional[int] = None
    repeat_penalty: Optional[float] = None
    seed: Optional[int] = None
    stop: Optional[list[str]] = None

    model_config = ConfigDict(extra="allow")


class Capabilities(BaseModel):
    """Per-persona feature flags. Extra keys allowed so this can grow in
    Phase 5 without breaking existing personas.

    `tools` changed from a bool to a list of tool names in Phase 3, so a
    persona can be attached to zero or more tools by name (e.g.
    ["dice_roller"]). Existing DB rows with the old `tools: false` shape
    are untouched by this change unless/until that persona is next
    updated via PUT with capabilities explicitly provided -- PersonaOut
    returns capabilities as a plain dict, not re-validated against this
    schema on read.

    `skills` follows the identical shape (Phase 4): a list of skill names
    (e.g. ["dnd-combat", "concise-answers"]), each resolved to a markdown
    file on disk via services/skill_loader.py at chat time. Not stored in
    the DB itself -- just referenced by name here, same relationship
    `tools` has to tool_registry.py.

    `features` (Phase 5.5) is the frontend-facing counterpart to `tools`/
    `skills`: a list of sub-resource tab names this persona exposes (e.g.
    ["chat", "favorites", "pantry", "options"]). Unlike `tools` and
    `skills`, this has no backend enforcement mechanism of its own --
    the Favorites/Pantry endpoints work regardless of what's listed here,
    since a persona_id is a persona_id. `features` exists purely so
    GET /personas can tell the frontend which tabs to render for a given
    persona, same role `ui_theme` plays for top-level tab-to-persona
    routing (see the Phase 6 handoff notes). A persona with "pantry" in
    `tools` or `skills` wouldn't mean anything; a persona with "pantry"
    in `features` means "show the Pantry tab for this persona."
    """

    vision: bool = False
    tools: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    knowledge: bool = False
    web_search: bool = False
    features: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="allow")


class PersonaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    system_prompt: str = ""
    params: OllamaParams = Field(default_factory=OllamaParams)
    capabilities: Capabilities = Field(default_factory=Capabilities)
    model: Optional[str] = None


class PersonaUpdate(BaseModel):
    """All fields optional -- PUT only touches what's provided."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    system_prompt: Optional[str] = None
    params: Optional[OllamaParams] = None
    capabilities: Optional[Capabilities] = None
    model: Optional[str] = None


class PersonaOut(BaseModel):
    id: int
    name: str
    system_prompt: str
    params: dict
    capabilities: dict
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)