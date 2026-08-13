"""
Business logic for a persona's saved Favorites. Deliberately thin --
favorites are just structured data handed over by the frontend (already
shaped by the return_recipe tool during chat), not something this layer
computes or validates beyond existence checks. Mirrors knowledge_service.py's
shape, minus anything Ollama-related.
"""

from sqlalchemy.orm import Session

from backend.models.favorite import Favorite
from backend.schemas.favorite import FavoriteCreate
from backend.services.persona_service import get_persona


class FavoriteNotFoundError(Exception):
    """Raised when deleting a favorite that doesn't exist for this
    persona -- distinct from PersonaNotFoundError, since the persona
    might exist fine and just never have had this favorite saved."""


def create_favorite(db: Session, persona_id: int, data: FavoriteCreate) -> Favorite:
    get_persona(db, persona_id)  # PersonaNotFoundError if missing

    favorite = Favorite(
        persona_id=persona_id,
        title=data.title,
        ingredients=data.ingredients,
        steps=data.steps,
    )
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


def list_favorites(db: Session, persona_id: int) -> list[Favorite]:
    get_persona(db, persona_id)

    return (
        db.query(Favorite)
        .filter(Favorite.persona_id == persona_id)
        .order_by(Favorite.created_at.desc())
        .all()
    )


def delete_favorite(db: Session, persona_id: int, favorite_id: int) -> None:
    get_persona(db, persona_id)

    favorite = (
        db.query(Favorite)
        .filter(Favorite.persona_id == persona_id, Favorite.id == favorite_id)
        .first()
    )
    if favorite is None:
        raise FavoriteNotFoundError(
            f"No favorite with id {favorite_id} for persona {persona_id}"
        )

    db.delete(favorite)
    db.commit()