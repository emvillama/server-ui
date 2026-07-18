from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.chat import ChatRequest, ChatResponse
from backend.services import persona_service as svc
from backend.services.ollama_client import OllamaError

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(data: ChatRequest, db: Session = Depends(get_db)):
    try:
        reply, model = await svc.run_chat(
            db, data.persona_id, data.message, data.history
        )
    except svc.PersonaNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except OllamaError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return ChatResponse(persona_id=data.persona_id, reply=reply, model=model)