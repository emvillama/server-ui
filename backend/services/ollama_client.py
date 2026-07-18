"""
The only file in this codebase that makes HTTP calls to Ollama.
"""

import httpx

from backend.config import settings


class OllamaError(Exception):
    """Raised when Ollama is unreachable or returns an error response."""


async def chat(model: str, messages: list[dict], options: dict | None = None) -> str:
    """
    Calls Ollama's /api/chat with a non-streaming request and returns the
    assistant's reply text.

    messages: list of {"role": ..., "content": ...} dicts, system prompt
              first if present.
    options:  Ollama's native generation params (temperature, top_p, etc.),
              passed through as-is. None/empty means "use Ollama's defaults".
    """
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if options:
        cleaned = {k: v for k, v in options.items() if v is not None}
        if cleaned:
            payload["options"] = cleaned

    url = f"{settings.ollama_host}/api/chat"
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
    except httpx.RequestError as exc:
        raise OllamaError(f"Could not reach Ollama at {url}: {exc}") from exc
    except httpx.HTTPStatusError as exc:
        raise OllamaError(
            f"Ollama returned an error ({exc.response.status_code}): "
            f"{exc.response.text}"
        ) from exc

    data = response.json()
    try:
        return data["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise OllamaError(f"Unexpected response shape from Ollama: {data}") from exc


async def is_reachable() -> bool:
    """Used by the /health endpoint to confirm Ollama is up."""
    url = f"{settings.ollama_host}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url)
            return response.status_code == 200
    except httpx.RequestError:
        return False