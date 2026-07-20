from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.persona import Persona
from backend.schemas.persona import PersonaCreate, PersonaUpdate
from backend.schemas.chat import ChatMessage
from backend.services import ollama_client


class PersonaNotFoundError(Exception):
    pass


class PersonaNameConflictError(Exception):
    pass


class PersonaValidationError(Exception):
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
    """
    PUT semantics: only fields actually present in the request body are
    touched. `data.model_fields_set` tells "field omitted" apart from
    "field explicitly sent as null" -- both would otherwise show up as
    `None` on the `data` object and be indistinguishable.

    `model` is the one field that's genuinely nullable in storage, so
    explicitly sending `"model": null` clears a persona's model override
    back to using the default. `name`, `system_prompt`, `params`, and
    `capabilities` are non-nullable columns, so explicitly sending null
    for those is a client error rather than silently ignored.
    """
    persona = get_persona(db, persona_id)
    provided = data.model_fields_set

    if "name" in provided:
        if data.name is None:
            raise PersonaValidationError("name cannot be set to null")
        if data.name != persona.name:
            existing = db.query(Persona).filter(Persona.name == data.name).first()
            if existing is not None:
                raise PersonaNameConflictError(f"Persona '{data.name}' already exists")
            persona.name = data.name

    if "system_prompt" in provided:
        if data.system_prompt is None:
            raise PersonaValidationError("system_prompt cannot be set to null")
        persona.system_prompt = data.system_prompt

    if "params" in provided:
        if data.params is None:
            raise PersonaValidationError("params cannot be set to null")
        persona.params = data.params.model_dump(exclude_none=True)

    if "capabilities" in provided:
        if data.capabilities is None:
            raise PersonaValidationError("capabilities cannot be set to null")
        persona.capabilities = data.capabilities.model_dump()

    if "model" in provided:
        persona.model = data.model

    db.commit()
    db.refresh(persona)
    return persona


def delete_persona(db: Session, persona_id: int) -> None:
    persona = get_persona(db, persona_id)
    db.delete(persona)
    db.commit()


async def run_chat(
    db: Session, persona_id: int, message: str, history: list[ChatMessage]
) -> tuple[str, str]:
    persona = get_persona(db, persona_id)

    messages: list[dict] = []
    if persona.system_prompt:
        messages.append({"role": "system", "content": persona.system_prompt})
    messages.extend({"role": m.role, "content": m.content} for m in history)
    messages.append({"role": "user", "content": message})

    model = persona.model or settings.default_model
    reply = await ollama_client.chat(model=model, messages=messages, options=persona.params)
    return reply, model