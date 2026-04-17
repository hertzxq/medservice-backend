"""
Tests for employees API: full CRUD, toggle active, branch isolation.
"""


# ── GET employees ────────────────────────────────────────────────────────────


def test_get_employees_returns_list(client, auth_headers):
    response = client.get("/api/v1/employees?branch_id=1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_employees_empty_branch(client, auth_headers):
    response = client.get("/api/v1/employees?branch_id=2", headers=auth_headers)

    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ── POST employees ───────────────────────────────────────────────────────────


def test_create_employee(client, auth_headers):
    response = client.post(
        "/api/v1/employees?branch_id=1",
        headers=auth_headers,
        json={
            "name": "Иванов Иван Иванович",
            "active": True,
            "profiles": ["https://prodoctorov.ru/doctor/ivanov"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Иванов Иван Иванович"
    assert data["active"] is True
    assert data["branchId"] == 1
    assert len(data["profiles"]) == 1
    assert "id" in data


def test_create_employee_empty_profiles(client, auth_headers):
    response = client.post(
        "/api/v1/employees?branch_id=1",
        headers=auth_headers,
        json={
            "name": "Без профилей",
            "active": False,
            "profiles": [],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["profiles"] == []
    assert data["active"] is False


def test_create_employee_nonexistent_branch_returns_404(client, auth_headers):
    response = client.post(
        "/api/v1/employees?branch_id=9999",
        headers=auth_headers,
        json={
            "name": "Ghost",
            "active": True,
            "profiles": [],
        },
    )

    assert response.status_code == 404


def test_create_employee_appears_in_get(client, auth_headers):
    # Create
    create_resp = client.post(
        "/api/v1/employees?branch_id=1",
        headers=auth_headers,
        json={
            "name": "Появляюсь в списке",
            "active": True,
            "profiles": [],
        },
    )
    created_id = create_resp.json()["id"]

    # Verify
    list_resp = client.get("/api/v1/employees?branch_id=1", headers=auth_headers)
    ids = [e["id"] for e in list_resp.json()]
    assert created_id in ids


# ── PATCH employees ──────────────────────────────────────────────────────────


def test_update_employee_name(client, auth_headers):
    # Create
    create_resp = client.post(
        "/api/v1/employees?branch_id=1",
        headers=auth_headers,
        json={"name": "Старое имя", "active": True, "profiles": []},
    )
    emp_id = create_resp.json()["id"]

    # Update
    response = client.patch(
        f"/api/v1/employees/{emp_id}",
        headers=auth_headers,
        json={"name": "Новое имя"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Новое имя"
    assert response.json()["active"] is True  # preserved


def test_update_employee_toggle_active(client, auth_headers):
    create_resp = client.post(
        "/api/v1/employees?branch_id=1",
        headers=auth_headers,
        json={"name": "Toggle Test", "active": True, "profiles": []},
    )
    emp_id = create_resp.json()["id"]

    # Toggle off
    resp_off = client.patch(
        f"/api/v1/employees/{emp_id}",
        headers=auth_headers,
        json={"active": False},
    )
    assert resp_off.status_code == 200
    assert resp_off.json()["active"] is False

    # Toggle on
    resp_on = client.patch(
        f"/api/v1/employees/{emp_id}",
        headers=auth_headers,
        json={"active": True},
    )
    assert resp_on.status_code == 200
    assert resp_on.json()["active"] is True


def test_update_employee_profiles(client, auth_headers):
    create_resp = client.post(
        "/api/v1/employees?branch_id=1",
        headers=auth_headers,
        json={"name": "Profile Test", "active": True, "profiles": []},
    )
    emp_id = create_resp.json()["id"]

    new_profiles = [
        "https://yandex.ru/maps/doctor/1",
        "https://prodoctorov.ru/doctor/1",
    ]
    response = client.patch(
        f"/api/v1/employees/{emp_id}",
        headers=auth_headers,
        json={"profiles": new_profiles},
    )

    assert response.status_code == 200
    assert response.json()["profiles"] == new_profiles


def test_update_nonexistent_employee_returns_404(client, auth_headers):
    response = client.patch(
        "/api/v1/employees/9999",
        headers=auth_headers,
        json={"name": "Ghost"},
    )

    assert response.status_code == 404


# ── DELETE employees ─────────────────────────────────────────────────────────


def test_delete_employee(client, auth_headers):
    create_resp = client.post(
        "/api/v1/employees?branch_id=1",
        headers=auth_headers,
        json={"name": "Удалить меня", "active": True, "profiles": []},
    )
    emp_id = create_resp.json()["id"]

    response = client.delete(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert response.status_code == 204

    # Verify gone
    list_resp = client.get("/api/v1/employees?branch_id=1", headers=auth_headers)
    ids = [e["id"] for e in list_resp.json()]
    assert emp_id not in ids


def test_delete_nonexistent_employee_returns_404(client, auth_headers):
    response = client.delete("/api/v1/employees/9999", headers=auth_headers)
    assert response.status_code == 404


# ── Branch isolation ─────────────────────────────────────────────────────────


def test_employees_isolated_by_branch(client, auth_headers):
    # Create in branch 1
    client.post(
        "/api/v1/employees?branch_id=1",
        headers=auth_headers,
        json={"name": "Только в филиале 1", "active": True, "profiles": []},
    )

    # Should NOT appear in branch 2
    resp2 = client.get("/api/v1/employees?branch_id=2", headers=auth_headers)
    names = [e["name"] for e in resp2.json()]
    assert "Только в филиале 1" not in names


# ── Response shape ───────────────────────────────────────────────────────────


def test_employee_response_contains_required_fields(client, auth_headers):
    create_resp = client.post(
        "/api/v1/employees?branch_id=1",
        headers=auth_headers,
        json={"name": "Shape Test", "active": True, "profiles": ["https://test.com"]},
    )

    assert create_resp.status_code == 201
    data = create_resp.json()
    expected = {"id", "branchId", "name", "active", "profiles"}
    assert expected.issubset(set(data.keys()))
