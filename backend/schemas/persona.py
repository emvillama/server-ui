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
    Phase 5 without breaking existing personas."""

    vision: bool = False
    tools: bool = False
    knowledge: bool = False
    web_search: bool = False

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