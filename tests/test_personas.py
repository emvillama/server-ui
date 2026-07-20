def test_create_persona_minimal(client):
    resp = client.post("/personas", json={"name": "Minimal Bot"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Minimal Bot"
    assert body["system_prompt"] == ""
    assert body["params"] == {}
    assert body["model"] is None


def test_create_persona_duplicate_name_conflicts(client, persona):
    resp = client.post("/personas", json={"name": persona["name"]})
    assert resp.status_code == 409


def test_list_personas_includes_created(client, persona):
    resp = client.get("/personas")
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert persona["id"] in ids


def test_get_persona_by_id(client, persona):
    resp = client.get(f"/personas/{persona['id']}")
    assert resp.status_code == 200
    assert resp.json()["name"] == persona["name"]


def test_get_missing_persona_404s(client):
    resp = client.get("/personas/999999")
    assert resp.status_code == 404


def test_delete_persona(client, persona):
    resp = client.delete(f"/personas/{persona['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/personas/{persona['id']}")
    assert resp.status_code == 404


def test_delete_missing_persona_404s(client):
    resp = client.delete("/personas/999999")
    assert resp.status_code == 404


# --- PUT semantics: omitted vs. explicit null (the bug we just fixed) ---


def test_put_omitting_a_field_leaves_it_unchanged(client, persona):
    resp = client.put(f"/personas/{persona['id']}", json={"model": "llama3.1:8b"})
    assert resp.status_code == 200
    assert resp.json()["model"] == "llama3.1:8b"

    # Update a different field, omitting "model" entirely.
    resp = client.put(
        f"/personas/{persona['id']}", json={"system_prompt": "New prompt."}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["system_prompt"] == "New prompt."
    assert body["model"] == "llama3.1:8b"  # untouched, not wiped out


def test_put_explicit_null_clears_nullable_model_field(client, persona):
    resp = client.put(f"/personas/{persona['id']}", json={"model": "llama3.1:8b"})
    assert resp.status_code == 200

    resp = client.put(f"/personas/{persona['id']}", json={"model": None})
    assert resp.status_code == 200
    assert resp.json()["model"] is None


def test_put_explicit_null_on_non_nullable_field_returns_422(client, persona):
    resp = client.put(f"/personas/{persona['id']}", json={"system_prompt": None})
    assert resp.status_code == 422


def test_put_rename_to_existing_name_conflicts(client, persona):
    other = client.post("/personas", json={"name": "Other Bot"}).json()
    resp = client.put(f"/personas/{other['id']}", json={"name": persona["name"]})
    assert resp.status_code == 409