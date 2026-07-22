"""
The `knowledge` table. Each row is one chunk of text from a source
document, embedded and attached to a single persona. Retrieval in
run_chat() will do a plain Python similarity search over these rows --
fine at personal scale, per the Phase 2 handoff notes.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Knowledge(Base):
    __tablename__ = "knowledge"

    id = Column(Integer, primary_key=True, index=True)

    # Which persona this chunk belongs to. Single-persona ownership --
    # no sharing across personas for now (see Phase 2 handoff notes).
    persona_id = Column(
        Integer, ForeignKey("personas.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Original filename the chunk came from, e.g. "linear_algebra_notes.txt".
    # Useful for showing the user where a retrieved chunk originated.
    source_filename = Column(String(255), nullable=False)

    # Which chunk this is within its source document, 0-indexed. Not used
    # for retrieval logic yet, but useful for debugging/ordering/display.
    chunk_index = Column(Integer, nullable=False)

    # The actual chunk text that gets embedded and, later, injected into
    # the system prompt / context when retrieved.
    chunk_text = Column(Text, nullable=False)

    # The embedding vector for chunk_text, as a plain JSON list of floats.
    # Stored this way (rather than a dedicated vector-search extension)
    # because a Python loop over rows is fine at personal scale.
    embedding = Column(JSON, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    persona = relationship("Persona", backref="knowledge_chunks")