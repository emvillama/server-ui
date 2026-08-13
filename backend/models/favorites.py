"""
The `favorites` table. Each row is one recipe a user explicitly saved
from the Recipe Recommender persona's chat -- populated via the
return_recipe tool's structured output, POSTed here by the frontend on
an explicit "save" action (not auto-saved during chat; see the Phase
5.5 handoff notes on why saving is a separate, deliberate step).
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref

from backend.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)

    # Which persona this favorite belongs to. Same single-owner pattern
    # as Knowledge.persona_id -- no sharing across personas.
    persona_id = Column(
        Integer, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title = Column(String(255), nullable=False)

    # Both stored as plain JSON lists of strings (e.g. ["2 eggs", "1 cup
    # flour"] / ["Preheat oven to 350F.", "Whisk eggs and flour."]) --
    # matches the shape the return_recipe tool hands back, no separate
    # normalization into their own tables needed at this scale.
    ingredients = Column(JSON, nullable=False)
    steps = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # passive_deletes=True: same reasoning as Knowledge.persona -- let
    # SQLite's ON DELETE CASCADE handle removing a persona's favorites
    # rather than the ORM nulling out persona_id on loaded children.
    persona = relationship("Persona", backref=backref("favorites", passive_deletes=True))