"""
The `pantry_items` table. Each row is one ingredient a user has on hand,
attached to a single persona (the Recipe Recommender, in practice, but
nothing here enforces that -- same reasoning as Favorite).

Upsert-by-name is enforced at the DB level via a unique constraint on
(persona_id, name), not just in the service layer -- so a race between
two concurrent "add eggs" requests can't slip past the service's
check-then-merge logic and create a duplicate row. The service still
does the actual merge (see the Phase 5.5 handoff notes on unit
mismatches), this constraint just guarantees it can't be bypassed.
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, backref

from backend.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class PantryItem(Base):
    __tablename__ = "pantry_items"
    __table_args__ = (
        UniqueConstraint("persona_id", "name", name="uq_pantry_persona_name"),
    )

    id = Column(Integer, primary_key=True, index=True)

    persona_id = Column(
        Integer, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    name = Column(String(255), nullable=False)

    # Nullable rather than defaulting to 0/"" -- a user might add "salt"
    # to their pantry with no meaningful quantity to track, and NULL
    # says "unspecified" more honestly than a fake zero would.
    quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)

    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )

    persona = relationship("Persona", backref=backref("pantry_items", passive_deletes=True))