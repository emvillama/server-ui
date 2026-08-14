from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.pantry import PantryItemCreate, PantryItemUpdate, PantryItemOut
from backend.services import pantry_service
from backend.services import persona_service as persona_svc

router = APIRouter(prefix="/personas/{persona_id}/pantry", tags=["pantry"])


@router.post("", response_model=PantryItemOut, status_code=201)
def add_pantry_item(persona_id: int, data: PantryItemCreate, db: Session = Depends(get_db)):
    """Upsert-add: merges into an existing row with the same name if one
    exists, per upsert_pantry_item()'s merge rules. Always 201, even on
    a merge, since the response reflects the item's current state either
    way -- there's no meaningful distinction from the caller's side
    between "created" and "merged"."""
    try:
        return pantry_service.upsert_pantry_item(db, persona_id, data)
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("", response_model=list[PantryItemOut])
def list_pantry_items(persona_id: int, db: Session = Depends(get_db)):
    try:
        return pantry_service.list_pantry_items(db, persona_id)
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.put("/{item_id}", response_model=PantryItemOut)
def update_pantry_item(
    persona_id: int, item_id: int, data: PantryItemUpdate, db: Session = Depends(get_db)
):
    try:
        return pantry_service.update_pantry_item(db, persona_id, item_id, data)
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except pantry_service.PantryItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{item_id}", status_code=204)
def delete_pantry_item(persona_id: int, item_id: int, db: Session = Depends(get_db)):
    try:
        pantry_service.delete_pantry_item(db, persona_id, item_id)
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except pantry_service.PantryItemNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))