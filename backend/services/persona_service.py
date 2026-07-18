"""
Business logic for personas. Routers stay thin (parse request, call a
function here, return the result) -- all the actual database work lives in
this file.
"""

from sqlalchemy.orm import Session

from backend.models.persona import Persona
from backend.schemas.persona import PersonaCreate, PersonaUpdate


class PersonaNotFoundError(Exception):
    pass


class PersonaNameConflictError(Exception):
    pass


def list_personas(db: Session) -> list[Persona]:
    return db.query(Persona).order_by(Persona.name).all()


def get_persona(db: Session, persona_id: int) -> Persona:
    persona = db.get(Persona, persona_id)
    if persona is None:
        raise PersonaNotFoundError(f"No persona with id {persona_id}")
    return persona


def create_persona(db: Session, data: PersonaCreate) -> Persona:
    existing = db.query(Persona).filter(Persona.name == data.name).first()
    if existing is not None:
        raise PersonaNameConflictError(f"Persona '{data.name}' already exists")

    persona = Persona(
        name=data.name,
        system_prompt=data.system_prompt,
        params=data.params.model_dump(exclude_none=True),
        capabilities=data.capabilities.model_dump(),
        model=data.model,
    )
    db.add(persona)
    db.commit()
    db.refresh(persona)
    return persona


def update_persona(db: Session, persona_id: int, data: PersonaUpdate) -> Persona:
    persona = get_persona(db, persona_id)

    if data.name is not None and data.name != persona.name:
        existing = db.query(Persona).filter(Persona.name == data.name).first()
        if existing is not None:
            raise PersonaNameConflictError(f"Persona '{data.name}' already exists")
        persona.name = data.name

    if data.system_prompt is not None:
        persona.system_prompt = data.system_prompt
    if data.params is not None:
        persona.params = data.params.model_dump(exclude_none=True)
    if data.capabilities is not None:
        persona.capabilities = data.capabilities.model_dump()
    if data.model is not None:
        persona.model = data.model

    db.commit()
    db.refresh(persona)
    return persona


def delete_persona(db: Session, persona_id: int) -> None:
    persona = get_persona(db, persona_id)
    db.delete(persona)
    db.commit()