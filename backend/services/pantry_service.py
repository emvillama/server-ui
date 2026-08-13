"""
Business logic for a persona's Pantry. The one non-trivial piece is
upsert_pantry_item()'s merge behavior -- see the Phase 5.5 handoff notes
on why a unit mismatch falls back to overwrite rather than attempting
unit conversion.
"""

from sqlalchemy.orm import Session

from backend.models.pantry import PantryItem
from backend.schemas.pantry import PantryItemCreate, PantryItemUpdate
from backend.services.persona_service import get_persona


class PantryItemNotFoundError(Exception):
    """Raised when updating/deleting a pantry item that doesn't exist
    for this persona."""


def upsert_pantry_item(db: Session, persona_id: int, data: PantryItemCreate) -> PantryItem:
    """
    Looks up an existing row by (persona_id, name) -- exact, case-
    sensitive match, per the Phase 5.5 handoff notes. If found:

      - same unit (including both None) and both quantities present:
        quantities are summed (this is the actual "add more of what I
        already have" case)
      - anything else (unit mismatch, or either quantity is None):
        the existing row's quantity/unit are overwritten with the
        incoming values, last-write-wins -- rather than silently adding
        mismatched units together (e.g. "2 cups" + "500 g")

    If not found, a new row is created as-is.
    """
    get_persona(db, persona_id)

    existing = (
        db.query(PantryItem)
        .filter(PantryItem.persona_id == persona_id, PantryItem.name == data.name)
        .first()
    )

    if existing is None:
        item = PantryItem(
            persona_id=persona_id,
            name=data.name,
            quantity=data.quantity,
            unit=data.unit,
        )
        db.add(item)
    else:
        can_sum = (
            existing.unit == data.unit
            and existing.quantity is not None
            and data.quantity is not None
        )
        if can_sum:
            existing.quantity += data.quantity
        else:
            existing.quantity = data.quantity
            existing.unit = data.unit
        item = existing

    db.commit()
    db.refresh(item)
    return item


def list_pantry_items(db: Session, persona_id: int) -> list[PantryItem]:
    get_persona(db, persona_id)

    return (
        db.query(PantryItem)
        .filter(PantryItem.persona_id == persona_id)
        .order_by(PantryItem.name)
        .all()
    )


def update_pantry_item(
    db: Session, persona_id: int, item_id: int, data: PantryItemUpdate
) -> PantryItem:
    """
    Direct edit, not an upsert-merge -- a PUT to a known row ID always
    sets quantity/unit to exactly what's provided, matching PersonaUpdate's
    omitted-vs-null semantics: only fields actually present in the
    request body are touched.
    """
    get_persona(db, persona_id)

    item = (
        db.query(PantryItem)
        .filter(PantryItem.persona_id == persona_id, PantryItem.id == item_id)
        .first()
    )
    if item is None:
        raise PantryItemNotFoundError(
            f"No pantry item with id {item_id} for persona {persona_id}"
        )

    provided = data.model_fields_set
    if "quantity" in provided:
        item.quantity = data.quantity
    if "unit" in provided:
        item.unit = data.unit

    db.commit()
    db.refresh(item)
    return item


def delete_pantry_item(db: Session, persona_id: int, item_id: int) -> None:
    get_persona(db, persona_id)

    item = (
        db.query(PantryItem)
        .filter(PantryItem.persona_id == persona_id, PantryItem.id == item_id)
        .first()
    )
    if item is None:
        raise PantryItemNotFoundError(
            f"No pantry item with id {item_id} for persona {persona_id}"
        )

    db.delete(item)
    db.commit()