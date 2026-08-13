"""
Request/response shapes for the /personas/{persona_id}/pantry endpoint.
Separate from the SQLAlchemy PantryItem model, same reasoning as
schemas/persona.py.

Two write shapes, matching the two distinct operations the router
exposes: PantryItemCreate for the upsert-add endpoint (POST), where
quantity/unit describe what's being *added*; PantryItemUpdate for direct
edits (PUT) to an existing row, where every field is optional so a
caller can patch just the unit without re-specifying quantity, same
omitted-vs-null reasoning as PersonaUpdate.
"""

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class PantryItemCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    quantity: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=50)


class PantryItemUpdate(BaseModel):
    quantity: Optional[float] = None
    unit: Optional[str] = Field(None, max_length=50)


class PantryItemOut(BaseModel):
    id: int
    persona_id: int
    name: str
    quantity: Optional[float] = None
    unit: Optional[str] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)