from fastapi import APIRouter

from backend.services import ollama_client

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    ollama_up = await ollama_client.is_reachable()
    return {
        "status": "ok",
        "ollama_reachable": ollama_up,
    }