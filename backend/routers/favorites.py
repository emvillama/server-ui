from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.favorite import FavoriteCreate, FavoriteOut
from backend.services import favorite_service
from backend.services import persona_service as persona_svc

# Nested under /personas/{persona_id}, same reasoning as knowledge.py --
# favorites are always scoped to a single persona, no standalone
# "favorites" resource independent of one.
router = APIRouter(prefix="/personas/{persona_id}/favorites", tags=["favorites"])


@router.post("", response_model=FavoriteOut, status_code=201)
def create_favorite(persona_id: int, data: FavoriteCreate, db: Session = Depends(get_db)):
    try:
        return favorite_service.create_favorite(db, persona_id, data)
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("", response_model=list[FavoriteOut])
def list_favorites(persona_id: int, db: Session = Depends(get_db)):
    try:
        return favorite_service.list_favorites(db, persona_id)
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{favorite_id}", status_code=204)
def delete_favorite(persona_id: int, favorite_id: int, db: Session = Depends(get_db)):
    try:
        favorite_service.delete_favorite(db, persona_id, favorite_id)
    except persona_svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except favorite_service.FavoriteNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))