import json

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.persona import Persona
from backend.schemas.persona import PersonaCreate, PersonaUpdate
from backend.schemas.chat import ChatMessage
from backend.services import ollama_client
from backend.models.knowledge import Knowledge


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
) -> tuple[str, str, dict | None]:
    """
    Returns (reply, model, structured_output).

    structured_output is None for every ordinary chat response, including
    ones that used a non-terminal tool like dice_roller. It's only
    populated when the model's final action was a terminal tool call
    (currently just return_recipe) -- see the Phase 5.5 handoff notes on
    why that tool short-circuits the normal round trip instead of
    flowing through it.
    """
    persona = get_persona(db, persona_id)

    messages: list[dict] = []
    if persona.system_prompt:
        messages.append({"role": "system", "content": persona.system_prompt})

    # Skills: markdown instruction sets attached by name via
    # capabilities["skills"], always injected (not retrieved) -- see the
    # Phase 4 handoff notes on why always-injected was chosen over a
    # Knowledge-style similarity search for this. Placed before the
    # Knowledge block: skills are closer to "how you behave" (same
    # family as system_prompt) than "what you currently know."
    skill_names = (persona.capabilities or {}).get("skills") or []
    if skill_names:
        from backend.services import skill_loader

        loaded_skills = skill_loader.load_skills(skill_names)
        skills_content = "\n\n".join(content for _, content in loaded_skills)
        messages.append({"role": "system", "content": skills_content})

    # Phase 5: capabilities.knowledge is a necessary gate, not just the
    # row-existence check -- a persona can have real Knowledge rows
    # attached (e.g. from before this flag existed) and still have
    # retrieval skipped if the flag itself is off. Existence check still
    # matters on top of the flag: it's what avoids a wasted embedding
    # call for a persona that has the capability enabled but nothing
    # ingested yet.
    knowledge_enabled = (persona.capabilities or {}).get("knowledge", False)
    if knowledge_enabled:
        has_knowledge = (
            db.query(Knowledge).filter(Knowledge.persona_id == persona.id).first()
            is not None
        )
        if has_knowledge:
            # Deferred import, not at module top: knowledge_service imports
            # get_persona from this module, so importing knowledge_service at
            # the top of this file would create a circular import. By the
            # time run_chat() actually executes, both modules are already
            # fully loaded, so importing here avoids the cycle entirely.
            from backend.services import knowledge_service

            retrieved = await knowledge_service.search_knowledge(
                db, persona.id, message, top_n=5
            )
            if retrieved:
                context = "\n\n".join(
                    f"[{chunk.source_filename}] {chunk.chunk_text}" for chunk in retrieved
                )
                messages.append(
                    {
                        "role": "system",
                        "content": f"Relevant context from your knowledge base:\n\n{context}",
                    }
                )

    messages.extend({"role": m.role, "content": m.content} for m in history)
    messages.append({"role": "user", "content": message})

    model = persona.model or settings.default_model

    # Only pass `tools` to Ollama if this persona actually has any
    # attached (persona.capabilities["tools"], a list of tool names --
    # see the Phase 3 handoff notes on why this is a plain list rather
    # than a separate attachment table). Personas with no tools attached
    # go through the plain chat() path unchanged, exactly as before this
    # was added.
    tool_names = (persona.capabilities or {}).get("tools") or []
    if tool_names:
        from backend.services import tool_registry

        tools = tool_registry.get_tool_schemas(tool_names)
    else:
        tools = None

    if tools:
        assistant_message = await ollama_client.chat_with_tools(
            model=model, messages=messages, tools=tools, options=persona.params
        )
        tool_calls = assistant_message.get("tool_calls")

        if not tool_calls:
            # Model chose not to use a tool for this message -- its
            # content is the final reply, no follow-up call needed.
            return assistant_message.get("content", ""), model, None

        # Model wants to invoke one or more tools. Append its own
        # message (including the tool_calls) back into history first --
        # Ollama expects the assistant's tool-call message to be present
        # before the corresponding "tool" role result messages that
        # follow it.
        messages.append(assistant_message)

        # Terminal shortcut: return_recipe's arguments ARE the final
        # answer, not an intermediate result to hand back to the model
        # for prose-ification. If the model called it, short-circuit
        # here -- no follow-up chat() call, and any other tool_calls in
        # this same response are ignored (a model returning a recipe
        # plus something else in one turn isn't a case worth
        # supporting). See the Phase 5.5 handoff notes on why this
        # differs from dice_roller's round-trip flow.
        for call in tool_calls:
            function = call.get("function", {})
            if function.get("name") == "return_recipe":
                arguments = function.get("arguments", {}) or {}
                title = arguments.get("title", "Recipe")
                # reply is a short human-readable string, not the raw
                # dict -- ChatResponse.reply is typed as str. The full
                # structured data goes out separately via
                # structured_output.
                return f"Here's your recipe: {title}", model, arguments

        for call in tool_calls:
            function = call.get("function", {})
            tool_name = function.get("name")
            arguments = function.get("arguments", {}) or {}

            executor = tool_registry.get_tool_executor(tool_name)
            if executor:
                result = executor(arguments)
            else:
                # Model requested a tool name that isn't registered (or
                # wasn't offered to it) -- fed back as an error result
                # rather than raised, so the model can see its own
                # mistake and recover in its final reply.
                result = {"error": f"Unknown tool '{tool_name}'"}

            messages.append({"role": "tool", "content": json.dumps(result)})

        # Single follow-up call to get the model's final natural-language
        # reply now that it has the tool result(s). Deliberately not
        # passed `tools` again and not looped -- one round trip only, to
        # keep this narrow given llama3.1:8b's documented tool-calling
        # fragility. A model requesting a second tool call here would
        # just have that request's content returned as plain text.
        reply = await ollama_client.chat(model=model, messages=messages, options=persona.params)
        return reply, model, None

    reply = await ollama_client.chat(model=model, messages=messages, options=persona.params)
    return reply, model, None