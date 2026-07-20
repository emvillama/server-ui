from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.persona import PersonaCreate, PersonaUpdate, PersonaOut
from backend.services import persona_service as svc

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("", response_model=list[PersonaOut])
def list_personas(db: Session = Depends(get_db)):
    return svc.list_personas(db)


@router.post("", response_model=PersonaOut, status_code=201)
def create_persona(data: PersonaCreate, db: Session = Depends(get_db)):
    try:
        return svc.create_persona(db, data)
    except svc.PersonaNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{persona_id}", response_model=PersonaOut)
def get_persona(persona_id: int, db: Session = Depends(get_db)):
    try:
        return svc.get_persona(db, persona_id)
    except svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{persona_id}", response_model=PersonaOut)
def update_persona(persona_id: int, data: PersonaUpdate, db: Session = Depends(get_db)):
    try:
        return svc.update_persona(db, persona_id, data)
    except svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except svc.PersonaNameConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except svc.PersonaValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/{persona_id}", status_code=204)
def delete_persona(persona_id: int, db: Session = Depends(get_db)):
    try:
        svc.delete_persona(db, persona_id)
    except svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))