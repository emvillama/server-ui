"""
Request/response shapes for the /personas/{persona_id}/favorites
endpoint. Separate from the SQLAlchemy Favorite model, same reasoning
as schemas/persona.py.
"""

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class FavoriteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    ingredients: list[str] = Field(..., min_length=1)
    steps: list[str] = Field(..., min_length=1)


class FavoriteOut(BaseModel):
    id: int
    persona_id: int
    title: str
    ingredients: list[str]
    steps: list[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)