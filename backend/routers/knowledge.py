from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.knowledge import KnowledgeIngestRequest, KnowledgeOut
from backend.services import knowledge_service
from backend.services import persona_service as persona_svc
from backend.services.ollama_client import OllamaError

# Nested under /personas/{persona_id} since knowledge is always scoped to
# a single persona (see the Phase 2 handoff notes on single-persona
# ownership) -- there's no standalone "knowledge" resource independent
# of a persona.
router = APIRouter(prefix="/personas/{persona_id}/knowledge", tags=["knowledge"])


@router.post("", response_model=list[KnowledgeOut], status_code=201)
async def ingest_knowledge(
    persona_id: int, data: KnowledgeIngestRequest, db: Session = Depends(get_db)
):
    try:
        rows = await knowledge_service.ingest_document(
            db, persona_id, data.source_filename, data.text
        )
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return rows