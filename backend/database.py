"""
SQLite engine + session factory, plus the declarative Base that all ORM
models inherit from. Tables are created on startup in main.py via
`Base.metadata.create_all`, which is fine at this scale -- if the schema
gets more complex later, swap this for Alembic migrations.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.config import settings

# Ensure the directory for the SQLite file exists (e.g. ./data/)
db_dir = os.path.dirname(settings.db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

# check_same_thread=False is required for SQLite when accessed from
# FastAPI's threaded request handling.
engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency: yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()