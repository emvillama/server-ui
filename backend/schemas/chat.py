from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    persona_id: int
    message: str = Field(..., min_length=1)
    # Prior turns in the conversation, oldest first. The persona's system
    # prompt is prepended by the backend, so callers should NOT include a
    # system message here.
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    persona_id: int
    reply: str
    model: str
    # Populated only when the model's final action was a terminal tool
    # call (currently just return_recipe) -- carries that tool's raw
    # arguments so the frontend can render structured UI (e.g. the
    # Recipe tab) instead of parsing it back out of prose. None for
    # every other chat response, including ones that used non-terminal
    # tools like dice_roller. See the Phase 5.5 handoff notes.
    structured_output: dict | None = None