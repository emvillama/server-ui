# --- add (upsert) ---


def test_add_new_pantry_item_returns_201(client, persona):
    resp = client.post(
        f"/personas/{persona['id']}/pantry",
        json={"name": "eggs", "quantity": 6, "unit": "count"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "eggs"
    assert body["quantity"] == 6
    assert body["unit"] == "count"
    assert body["persona_id"] == persona["id"]


def test_add_pantry_item_with_no_quantity_or_unit(client, persona):
    resp = client.post(f"/personas/{persona['id']}/pantry", json={"name": "salt"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["quantity"] is None
    assert body["unit"] is None


def test_add_duplicate_name_same_unit_merges_and_returns_200(client, persona):
    resp1 = client.post(
        f"/personas/{persona['id']}/pantry",
        json={"name": "eggs", "quantity": 3, "unit": "count"},
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        f"/personas/{persona['id']}/pantry",
        json={"name": "eggs", "quantity": 2, "unit": "count"},
    )
    assert resp2.status_code == 200
    body = resp2.json()
    assert body["quantity"] == 5
    assert body["unit"] == "count"
    assert body["id"] == resp1.json()["id"]  # same row, not a new one


def test_add_duplicate_name_no_unit_both_times_merges(client, persona):
    # None == None counts as "same unit" per upsert_pantry_item()'s
    # merge rules -- the common case of adding more of an unspecified
    # quantity item.
    client.post(f"/personas/{persona['id']}/pantry", json={"name": "flour", "quantity": 2})
    resp = client.post(
        f"/personas/{persona['id']}/pantry", json={"name": "flour", "quantity": 3}
    )
    assert resp.status_code == 200
    assert resp.json()["quantity"] == 5


def test_add_duplicate_name_different_unit_overwrites_and_returns_200(client, persona):
    client.post(
        f"/personas/{persona['id']}/pantry",
        json={"name": "flour", "quantity": 2, "unit": "cups"},
    )
    resp = client.post(
        f"/personas/{persona['id']}/pantry",
        json={"name": "flour", "quantity": 500, "unit": "g"},
    )
    assert resp.status_code == 200
    body = resp.json()
    # overwritten, not summed -- mismatched units aren't converted
    assert body["quantity"] == 500
    assert body["unit"] == "g"


def test_add_duplicate_name_case_sensitive_creates_separate_row(client, persona):
    # Documents the current exact-match behavior -- "Eggs" and "eggs"
    # are treated as different pantry items, per the Phase 5.5 handoff
    # notes on name matching.
    client.post(f"/personas/{persona['id']}/pantry", json={"name": "eggs", "quantity": 1})
    resp = client.post(
        f"/personas/{persona['id']}/pantry", json={"name": "Eggs", "quantity": 1}
    )
    assert resp.status_code == 201  # new row, not a merge

    items = client.get(f"/personas/{persona['id']}/pantry").json()
    assert len(items) == 2


def test_add_pantry_item_missing_persona_404s(client):
    resp = client.post("/personas/999999/pantry", json={"name": "eggs"})
    assert resp.status_code == 404


# --- list ---


def test_list_pantry_items_empty_persona_returns_empty_list(client, persona):
    resp = client.get(f"/personas/{persona['id']}/pantry")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_pantry_items_returns_added_ones_sorted_by_name(client, persona):
    client.post(f"/personas/{persona['id']}/pantry", json={"name": "salt"})
    client.post(f"/personas/{persona['id']}/pantry", json={"name": "eggs"})

    resp = client.get(f"/personas/{persona['id']}/pantry")
    names = [item["name"] for item in resp.json()]
    assert names == ["eggs", "salt"]  # alphabetical


def test_list_pantry_items_missing_persona_404s(client):
    resp = client.get("/personas/999999/pantry")
    assert resp.status_code == 404


def test_list_pantry_items_only_returns_this_personas_items(client, persona):
    other = client.post("/personas", json={"name": "Other Persona"}).json()

    client.post(f"/personas/{persona['id']}/pantry", json={"name": "mine"})
    client.post(f"/personas/{other['id']}/pantry", json={"name": "theirs"})

    resp = client.get(f"/personas/{persona['id']}/pantry")
    names = [item["name"] for item in resp.json()]
    assert names == ["mine"]


# --- update ---


def test_update_pantry_item(client, persona):
    create_resp = client.post(
        f"/personas/{persona['id']}/pantry", json={"name": "eggs", "quantity": 6}
    )
    item_id = create_resp.json()["id"]

    resp = client.put(
        f"/personas/{persona['id']}/pantry/{item_id}",
        json={"quantity": 12, "unit": "count"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quantity"] == 12
    assert body["unit"] == "count"


def test_update_pantry_item_omitting_a_field_leaves_it_unchanged(client, persona):
    create_resp = client.post(
        f"/personas/{persona['id']}/pantry",
        json={"name": "flour", "quantity": 2, "unit": "cups"},
    )
    item_id = create_resp.json()["id"]

    resp = client.put(
        f"/personas/{persona['id']}/pantry/{item_id}", json={"quantity": 5}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["quantity"] == 5
    assert body["unit"] == "cups"  # untouched, not wiped out


def test_update_pantry_item_explicit_null_clears_field(client, persona):
    create_resp = client.post(
        f"/personas/{persona['id']}/pantry",
        json={"name": "flour", "quantity": 2, "unit": "cups"},
    )
    item_id = create_resp.json()["id"]

    resp = client.put(
        f"/personas/{persona['id']}/pantry/{item_id}", json={"unit": None}
    )
    assert resp.status_code == 200
    assert resp.json()["unit"] is None
    assert resp.json()["quantity"] == 2  # untouched


def test_update_nonexistent_pantry_item_404s(client, persona):
    resp = client.put(
        f"/personas/{persona['id']}/pantry/999999", json={"quantity": 1}
    )
    assert resp.status_code == 404


def test_update_pantry_item_missing_persona_404s(client):
    resp = client.put("/personas/999999/pantry/1", json={"quantity": 1})
    assert resp.status_code == 404


# --- delete ---


def test_delete_pantry_item(client, persona):
    create_resp = client.post(f"/personas/{persona['id']}/pantry", json={"name": "eggs"})
    item_id = create_resp.json()["id"]

    resp = client.delete(f"/personas/{persona['id']}/pantry/{item_id}")
    assert resp.status_code == 204

    remaining = client.get(f"/personas/{persona['id']}/pantry").json()
    assert remaining == []


def test_delete_nonexistent_pantry_item_404s(client, persona):
    resp = client.delete(f"/personas/{persona['id']}/pantry/999999")
    assert resp.status_code == 404


def test_delete_pantry_item_missing_persona_404s(client):
    resp = client.delete("/personas/999999/pantry/1")
    assert resp.status_code == 404


def test_delete_only_affects_the_named_item(client, persona):
    keep = client.post(f"/personas/{persona['id']}/pantry", json={"name": "keep"}).json()
    remove = client.post(f"/personas/{persona['id']}/pantry", json={"name": "remove"}).json()

    resp = client.delete(f"/personas/{persona['id']}/pantry/{remove['id']}")
    assert resp.status_code == 204

    remaining = client.get(f"/personas/{persona['id']}/pantry").json()
    assert len(remaining) == 1
    assert remaining[0]["id"] == keep["id"]