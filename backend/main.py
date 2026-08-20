"""
FastAPI app entrypoint. Run with:

    uvicorn backend.main:app --reload

Creates database tables on startup (fine at this scale -- switch to
Alembic migrations if the schema outgrows `create_all`).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.database import Base, engine
from backend.routers import health, personas, chat, knowledge, favorites, pantry
import backend.models  # noqa: F401 -- ensures models are registered before create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Persona AI Hub", version="0.1.0", lifespan=lifespan)

# Allows the Vite dev server (a different origin from the browser's
# perspective, since it's a different port) to actually read responses
# from this API. Origins come from settings.cors_origins rather than
# being hardcoded here, same reasoning as ollama_host/db_path -- nothing
# machine- or environment-specific belongs baked into the code itself.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(personas.router)
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(favorites.router)
app.include_router(pantry.router)