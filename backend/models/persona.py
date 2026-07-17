"""
The `personas` table. Each row is one "honed" persona: a name, a system
prompt, Ollama generation params, and a capabilities flag set.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, JSON, DateTime

from backend.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Persona(Base):
    __tablename__ = "personas"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    system_prompt = Column(Text, nullable=False, default="")

    # Ollama's `options` dict: temperature, top_p, top_k, num_ctx,
    # repeat_penalty, seed, stop, etc. Stored as-is and passed straight
    # through to Ollama's /api/chat call.
    params = Column(JSON, nullable=False, default=dict)

    # Feature flags, e.g. {"vision": false, "tools": false,
    # "knowledge": false, "web_search": false}. Phase 5 gives these real
    # meaning; for now they're just stored and returned.
    capabilities = Column(JSON, nullable=False, default=dict)

    # Optional override of the default model (falls back to
    # settings.default_model if null)
    model = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )