"""
FastAPI app entrypoint. Run with:

    uvicorn backend.main:app --reload

Creates database tables on startup (fine at this scale -- switch to
Alembic migrations if the schema outgrows `create_all`).
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.database import Base, engine
from backend.routers import health, personas
import backend.models  # noqa: F401 -- ensures models are registered before create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Persona AI Hub", version="0.1.0", lifespan=lifespan)

app.include_router(health.router)
app.include_router(personas.router)