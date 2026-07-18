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