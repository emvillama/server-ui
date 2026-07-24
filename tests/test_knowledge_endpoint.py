import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base, get_db
from backend.main import app
from backend.services import ollama_client


@pytest.fixture()
def client():
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
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
    resp = client.post("/personas", json={"name": "Study Bot"})
    assert resp.status_code == 201
    return resp.json()


def test_ingest_knowledge_endpoint(client, persona, monkeypatch):
    async def fake_embed(model, text):
        return [1.0, 0.0]

    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    resp = client.post(
        f"/personas/{persona['id']}/knowledge",
        json={
            "source_filename": "notes.txt",
            "text": "The mitochondria is the powerhouse of the cell.",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert len(body) == 1
    assert body[0]["source_filename"] == "notes.txt"
    assert body[0]["persona_id"] == persona["id"]
    assert "mitochondria" in body[0]["chunk_text"]
    # embedding vector should NOT be in the response
    assert "embedding" not in body[0]


def test_ingest_knowledge_missing_persona_404s(client, monkeypatch):
    async def fake_embed(model, text):
        return [1.0]

    monkeypatch.setattr(ollama_client, "embed", fake_embed)

    resp = client.post(
        "/personas/999999/knowledge",
        json={"source_filename": "notes.txt", "text": "some text"},
    )
    assert resp.status_code == 404


def test_ingest_knowledge_ollama_failure_surfaces_as_502(client, persona, monkeypatch):
    async def failing_embed(model, text):
        raise ollama_client.OllamaError("simulated failure")

    monkeypatch.setattr(ollama_client, "embed", failing_embed)

    resp = client.post(
        f"/personas/{persona['id']}/knowledge",
        json={"source_filename": "notes.txt", "text": "some text"},
    )
    assert resp.status_code == 502


def test_ingest_knowledge_empty_text_returns_422(client, persona):
    resp = client.post(
        f"/personas/{persona['id']}/knowledge",
        json={"source_filename": "notes.txt", "text": ""},
    )
    assert resp.status_code == 422