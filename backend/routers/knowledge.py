from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.knowledge import (
    KnowledgeIngestRequest,
    KnowledgeOut,
    DocumentSummaryOut,
)
from backend.services import knowledge_service, file_extraction
from backend.services import persona_service as persona_svc
from backend.services.ollama_client import OllamaError

# Nested under /personas/{persona_id} since knowledge is always scoped to
# a single persona (see the Phase 2 handoff notes on single-persona
# ownership) -- there's no standalone "knowledge" resource independent
# of a persona.
router = APIRouter(prefix="/personas/{persona_id}/knowledge", tags=["knowledge"])


@router.post("", response_model=list[KnowledgeOut], status_code=201)
async def ingest_knowledge_text(
    persona_id: int, data: KnowledgeIngestRequest, db: Session = Depends(get_db)
):
    """Ingest raw pasted text -- useful for quick testing without a file."""
    try:
        rows = await knowledge_service.ingest_document(
            db, persona_id, data.source_filename, data.text
        )
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return rows


@router.post("/upload", response_model=list[KnowledgeOut], status_code=201)
async def upload_knowledge_file(
    persona_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
):
    """Ingest an actual uploaded file (.txt, .md, .pdf, .docx, .pptx)."""
    content = await file.read()

    try:
        text = file_extraction.extract_text(file.filename, content)
    except file_extraction.UnsupportedFileTypeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except file_extraction.EmptyExtractionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    try:
        rows = await knowledge_service.ingest_document(
            db, persona_id, file.filename, text
        )
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return rows


@router.get("", response_model=list[DocumentSummaryOut])
def list_knowledge(persona_id: int, db: Session = Depends(get_db)):
    try:
        return knowledge_service.list_documents(db, persona_id)
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{source_filename}", status_code=204)
def delete_knowledge(persona_id: int, source_filename: str, db: Session = Depends(get_db)):
    try:
        knowledge_service.delete_document(db, persona_id, source_filename)
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except knowledge_service.KnowledgeNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))