"""
Request/response shapes for the /personas/{persona_id}/knowledge
endpoint. Separate from the SQLAlchemy Knowledge model, same reasoning
as schemas/persona.py.
"""

from datetime import datetime

from pydantic import BaseModel, Field, ConfigDict


class KnowledgeIngestRequest(BaseModel):
    source_filename: str = Field(..., min_length=1, max_length=255)
    text: str = Field(..., min_length=1)


class DocumentSummaryOut(BaseModel):
    source_filename: str
    chunk_count: int
    ingested_at: datetime


class KnowledgeOut(BaseModel):
    id: int
    persona_id: int
    source_filename: str
    chunk_index: int
    chunk_text: str
    created_at: datetime

    # Deliberately excludes `embedding` -- the raw vector has no use to
    # a client and would bloat the response for no reason.
    model_config = ConfigDict(from_attributes=True)