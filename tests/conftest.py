"""
Shared pytest fixtures. Spins up a throwaway SQLite file per test and
overrides the app's `get_db` dependency to use it, so tests never touch
your real data/persona_hub.db.
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    engine = create_engine(
        f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    engine.dispose()
    os.remove(db_path)


@pytest.fixture()
def persona(client):
    """Creates a basic persona and returns its JSON representation."""
    resp = client.post(
        "/personas",
        json={"name": "Test Persona", "system_prompt": "Be helpful."},
    )
    assert resp.status_code == 201
    return resp.json()