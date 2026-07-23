"""
SQLite engine + session factory, plus the declarative Base that all ORM
models inherit from. Tables are created on startup in main.py via
`Base.metadata.create_all`, which is fine at this scale -- if the schema
gets more complex later, swap this for Alembic migrations.
"""

import os
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, declarative_base

from backend.config import settings


# SQLite doesn't enforce foreign keys (including ON DELETE CASCADE) unless
# explicitly told to, per connection. Without this, Knowledge.persona_id's
# ondelete="CASCADE" is silently ignored and deleting a persona with
# attached knowledge raises an IntegrityError instead of cascading.
#
# Registered on the Engine *class*, not a specific engine instance, so
# this applies to any SQLite connection made anywhere in the process --
# including test engines that tests/conftest.py builds independently of
# the `engine` object below.
@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# Ensure the directory for the SQLite file exists (e.g. ./data/)
db_dir = os.path.dirname(settings.db_path)
if db_dir:
    os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    f"sqlite:///{settings.db_path}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()