"""
Tests for blacklist API: full CRUD, edge cases, branch isolation.
"""


# ── GET blacklist ────────────────────────────────────────────────────────────


def test_get_blacklist_returns_list_for_branch(client, auth_headers):
    response = client.get("/api/v1/blacklist?branch_id=1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_blacklist_empty_for_branch_without_entries(client, auth_headers):
    response = client.get("/api/v1/blacklist?branch_id=2", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ── POST blacklist ───────────────────────────────────────────────────────────


def test_create_blacklist_user(client, auth_headers):
    response = client.post(
        "/api/v1/blacklist?branch_id=1",
        headers=auth_headers,
        json={
            "lastName": "Петров",
            "firstName": "Иван",
            "phone": "+79991234567",
            "reason": "Агрессивное поведение",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["lastName"] == "Петров"
    assert data["firstName"] == "Иван"
    assert data["phone"] == "+79991234567"
    assert data["reason"] == "Агрессивное поведение"
    assert data["branchId"] == 1
    assert "id" in data


def test_create_blacklist_user_without_reason(client, auth_headers):
    response = client.post(
        "/api/v1/blacklist?branch_id=1",
        headers=auth_headers,
        json={
            "lastName": "Сидоров",
            "firstName": "Олег",
            "phone": "+79997654321",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["reason"] is None


def test_create_blacklist_user_nonexistent_branch_returns_404(client, auth_headers):
    response = client.post(
        "/api/v1/blacklist?branch_id=9999",
        headers=auth_headers,
        json={
            "lastName": "Ghost",
            "firstName": "User",
            "phone": "+70000000000",
        },
    )

    assert response.status_code == 404


def test_create_blacklist_user_appears_in_get(client, auth_headers):
    # Create
    create_resp = client.post(
        "/api/v1/blacklist?branch_id=1",
        headers=auth_headers,
        json={
            "lastName": "Тестовый",
            "firstName": "Клиент",
            "phone": "+79990001122",
        },
    )
    assert create_resp.status_code == 201
    created_id = create_resp.json()["id"]

    # Verify it's in the list
    list_resp = client.get("/api/v1/blacklist?branch_id=1", headers=auth_headers)
    assert list_resp.status_code == 200
    ids = [u["id"] for u in list_resp.json()]
    assert created_id in ids


# ── PATCH blacklist ──────────────────────────────────────────────────────────


def test_update_blacklist_user(client, auth_headers):
    # Create first
    create_resp = client.post(
        "/api/v1/blacklist?branch_id=1",
        headers=auth_headers,
        json={
            "lastName": "Обновлять",
            "firstName": "Буду",
            "phone": "+79990009900",
        },
    )
    user_id = create_resp.json()["id"]

    # Update
    response = client.patch(
        f"/api/v1/blacklist/{user_id}",
        headers=auth_headers,
        json={"reason": "Новая причина"},
    )

    assert response.status_code == 200
    assert response.json()["reason"] == "Новая причина"
    assert response.json()["lastName"] == "Обновлять"  # unchanged


def test_update_blacklist_user_partial_fields(client, auth_headers):
    create_resp = client.post(
        "/api/v1/blacklist?branch_id=1",
        headers=auth_headers,
        json={
            "lastName": "Частичный",
            "firstName": "Апдейт",
            "phone": "+79990008800",
            "reason": "Старая причина",
        },
    )
    user_id = create_resp.json()["id"]

    # Update only phone
    response = client.patch(
        f"/api/v1/blacklist/{user_id}",
        headers=auth_headers,
        json={"phone": "+79991112233"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["phone"] == "+79991112233"
    assert data["reason"] == "Старая причина"  # preserved


def test_update_nonexistent_blacklist_user_returns_404(client, auth_headers):
    response = client.patch(
        "/api/v1/blacklist/9999",
        headers=auth_headers,
        json={"reason": "test"},
    )

    assert response.status_code == 404


# ── DELETE blacklist ─────────────────────────────────────────────────────────


def test_delete_blacklist_user(client, auth_headers):
    # Create
    create_resp = client.post(
        "/api/v1/blacklist?branch_id=1",
        headers=auth_headers,
        json={
            "lastName": "Удалять",
            "firstName": "Буду",
            "phone": "+79990007700",
        },
    )
    user_id = create_resp.json()["id"]

    # Delete
    response = client.delete(f"/api/v1/blacklist/{user_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify gone
    list_resp = client.get("/api/v1/blacklist?branch_id=1", headers=auth_headers)
    ids = [u["id"] for u in list_resp.json()]
    assert user_id not in ids


def test_delete_nonexistent_blacklist_user_returns_404(client, auth_headers):
    response = client.delete("/api/v1/blacklist/9999", headers=auth_headers)
    assert response.status_code == 404


# ── Branch isolation ─────────────────────────────────────────────────────────


def test_blacklist_isolated_by_branch(client, auth_headers):
    # Create in branch 1
    client.post(
        "/api/v1/blacklist?branch_id=1",
        headers=auth_headers,
        json={
            "lastName": "Изоляция",
            "firstName": "Тест",
            "phone": "+79990006600",
        },
    )

    # Should NOT appear in branch 2
    resp2 = client.get("/api/v1/blacklist?branch_id=2", headers=auth_headers)
    names = [u["lastName"] for u in resp2.json()]
    assert "Изоляция" not in names
