def _favorite_payload(title="Banana Bread"):
    return {
        "title": title,
        "ingredients": ["2 ripe bananas", "1.5 cups flour", "1 egg"],
        "steps": ["Preheat oven to 350F.", "Mix wet and dry separately.", "Bake 60 minutes."],
    }


# --- create ---


def test_create_favorite(client, persona):
    resp = client.post(
        f"/personas/{persona['id']}/favorites", json=_favorite_payload()
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Banana Bread"
    assert body["persona_id"] == persona["id"]
    assert body["ingredients"] == ["2 ripe bananas", "1.5 cups flour", "1 egg"]
    assert body["steps"] == [
        "Preheat oven to 350F.",
        "Mix wet and dry separately.",
        "Bake 60 minutes.",
    ]
    assert "created_at" in body


def test_create_favorite_missing_persona_404s(client):
    resp = client.post("/personas/999999/favorites", json=_favorite_payload())
    assert resp.status_code == 404


def test_create_favorite_empty_title_returns_422(client, persona):
    payload = _favorite_payload()
    payload["title"] = ""
    resp = client.post(f"/personas/{persona['id']}/favorites", json=payload)
    assert resp.status_code == 422


def test_create_favorite_empty_ingredients_returns_422(client, persona):
    payload = _favorite_payload()
    payload["ingredients"] = []
    resp = client.post(f"/personas/{persona['id']}/favorites", json=payload)
    assert resp.status_code == 422


def test_create_favorite_empty_steps_returns_422(client, persona):
    payload = _favorite_payload()
    payload["steps"] = []
    resp = client.post(f"/personas/{persona['id']}/favorites", json=payload)
    assert resp.status_code == 422


def test_create_favorite_allows_duplicate_titles(client, persona):
    # No uniqueness constraint on title -- saving the same recipe name
    # twice is allowed (e.g. two variations), per the Phase 5.5 handoff
    # notes on Favorite's design.
    resp1 = client.post(f"/personas/{persona['id']}/favorites", json=_favorite_payload())
    resp2 = client.post(f"/personas/{persona['id']}/favorites", json=_favorite_payload())
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["id"] != resp2.json()["id"]


# --- list ---


def test_list_favorites_empty_persona_returns_empty_list(client, persona):
    resp = client.get(f"/personas/{persona['id']}/favorites")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_favorites_returns_created_ones(client, persona):
    client.post(
        f"/personas/{persona['id']}/favorites", json=_favorite_payload("Banana Bread")
    )
    client.post(
        f"/personas/{persona['id']}/favorites", json=_favorite_payload("Omelette")
    )

    resp = client.get(f"/personas/{persona['id']}/favorites")
    assert resp.status_code == 200
    titles = {f["title"] for f in resp.json()}
    assert titles == {"Banana Bread", "Omelette"}


def test_list_favorites_missing_persona_404s(client):
    resp = client.get("/personas/999999/favorites")
    assert resp.status_code == 404


def test_list_favorites_only_returns_this_personas_favorites(client, persona):
    other = client.post("/personas", json={"name": "Other Persona"}).json()

    client.post(f"/personas/{persona['id']}/favorites", json=_favorite_payload("Mine"))
    client.post(f"/personas/{other['id']}/favorites", json=_favorite_payload("Theirs"))

    resp = client.get(f"/personas/{persona['id']}/favorites")
    titles = [f["title"] for f in resp.json()]
    assert titles == ["Mine"]


# --- delete ---


def test_delete_favorite(client, persona):
    create_resp = client.post(
        f"/personas/{persona['id']}/favorites", json=_favorite_payload()
    )
    favorite_id = create_resp.json()["id"]

    resp = client.delete(f"/personas/{persona['id']}/favorites/{favorite_id}")
    assert resp.status_code == 204

    resp = client.get(f"/personas/{persona['id']}/favorites")
    assert resp.json() == []


def test_delete_favorite_missing_persona_404s(client):
    resp = client.delete("/personas/999999/favorites/1")
    assert resp.status_code == 404


def test_delete_nonexistent_favorite_404s(client, persona):
    resp = client.delete(f"/personas/{persona['id']}/favorites/999999")
    assert resp.status_code == 404


def test_delete_only_affects_the_named_favorite(client, persona):
    keep = client.post(
        f"/personas/{persona['id']}/favorites", json=_favorite_payload("Keep")
    ).json()
    remove = client.post(
        f"/personas/{persona['id']}/favorites", json=_favorite_payload("Remove")
    ).json()

    resp = client.delete(f"/personas/{persona['id']}/favorites/{remove['id']}")
    assert resp.status_code == 204

    remaining = client.get(f"/personas/{persona['id']}/favorites").json()
    assert len(remaining) == 1
    assert remaining[0]["id"] == keep["id"]