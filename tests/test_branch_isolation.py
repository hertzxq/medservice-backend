"""
Multi-tenancy / BOLA tests: a non-superuser may only access branches assigned
to them. The seeded `user` has branches 1 & 2; a freshly created branch is NOT
assigned to them, so every branch-scoped read/write must 404 for that user
while the superuser still has full access.
"""


def _create_unassigned_branch(client, auth_headers) -> int:
    """Superuser creates a branch the non-superuser is NOT a member of."""
    resp = client.post(
        "/api/v1/branches",
        json={"name": "Изолированный филиал"},
        headers=auth_headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_user_cannot_read_unassigned_branch(client, auth_headers, user_auth_headers):
    bid = _create_unassigned_branch(client, auth_headers)

    # Every branch-scoped read returns 404 (existence not disclosed) for the user.
    assert client.get(f"/api/v1/analytics/{bid}", headers=user_auth_headers).status_code == 404
    assert client.get(f"/api/v1/analytics/{bid}/dashboard", headers=user_auth_headers).status_code == 404
    assert client.get(f"/api/v1/reviews?branchId={bid}", headers=user_auth_headers).status_code == 404
    assert client.get(f"/api/v1/complaints?branchId={bid}", headers=user_auth_headers).status_code == 404
    assert client.get(f"/api/v1/requests?branchId={bid}", headers=user_auth_headers).status_code == 404
    assert client.get(f"/api/v1/employees?branch_id={bid}", headers=user_auth_headers).status_code == 404
    assert client.get(f"/api/v1/blacklist?branch_id={bid}", headers=user_auth_headers).status_code == 404


def test_user_cannot_write_unassigned_branch(client, auth_headers, user_auth_headers):
    bid = _create_unassigned_branch(client, auth_headers)

    # Blacklist add is open to non-superusers, but only for THEIR branches.
    resp = client.post(
        f"/api/v1/blacklist?branch_id={bid}",
        json={"lastName": "Иванов", "firstName": "Иван", "phone": "+79990000000"},
        headers=user_auth_headers,
    )
    assert resp.status_code == 404


def test_branches_list_is_scoped_for_user(client, auth_headers, user_auth_headers):
    bid = _create_unassigned_branch(client, auth_headers)

    user_branches = client.get("/api/v1/branches", headers=user_auth_headers).json()["branches"]
    ids = {b["id"] for b in user_branches}
    assert bid not in ids          # the unassigned branch is hidden
    assert {1, 2} <= ids           # the assigned branches are visible

    # Superuser sees everything, including the new branch.
    admin_branches = client.get("/api/v1/branches", headers=auth_headers).json()["branches"]
    assert bid in {b["id"] for b in admin_branches}


def test_superuser_can_access_any_branch(client, auth_headers):
    bid = _create_unassigned_branch(client, auth_headers)
    assert client.get(f"/api/v1/analytics/{bid}", headers=auth_headers).status_code == 200


def test_user_can_still_access_assigned_branch(client, user_auth_headers):
    # Sanity: scoping didn't lock the user out of their own branches.
    assert client.get("/api/v1/reviews?branchId=1", headers=user_auth_headers).status_code == 200
    assert client.get("/api/v1/analytics/1", headers=user_auth_headers).status_code == 200


def test_manager_can_update_own_branch_identity(client, user_auth_headers):
    # Витрину своего филиала (название/город/логотип для пациентов) менеджер
    # может редактировать — в отличие от полного PATCH /branches/{id}.
    logo = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg=="
    resp = client.patch(
        "/api/v1/branches/1/identity",
        json={"city": "Москва", "logoUrl": logo},
        headers=user_auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["city"] == "Москва"
    assert body["logoUrl"] == logo

    # И логотип теперь виден пациенту в mini (публичный эндпоинт, без авторизации).
    mini = client.get("/api/v1/public/branches/1/mini").json()
    assert mini["branch"]["logoUrl"] == logo


def test_manager_cannot_update_foreign_branch_identity(client, auth_headers, user_auth_headers):
    bid = _create_unassigned_branch(client, auth_headers)
    resp = client.patch(
        f"/api/v1/branches/{bid}/identity",
        json={"city": "Москва"},
        headers=user_auth_headers,
    )
    assert resp.status_code == 404  # чужой филиал не раскрываем


def test_full_branch_patch_stays_superuser_only(client, user_auth_headers):
    # Узкий identity-эндпоинт не должен открыть служебные поля: полный PATCH
    # (платёжка/активность/настройки) остаётся за суперадмином.
    resp = client.patch(
        "/api/v1/branches/1",
        json={"is_active": False},
        headers=user_auth_headers,
    )
    assert resp.status_code == 403


def test_admin_can_assign_branches_to_new_user(client, auth_headers):
    # Create a manager with access to ONLY branch 1, then confirm scoping.
    created = client.post(
        "/api/v1/admin/users",
        json={
            "username": "manager1",
            "email": "manager1@medservice.com",
            "password": "managerpass1",
            "branchIds": [1],
        },
        headers=auth_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["branchIds"] == [1]

    token = client.post(
        "/api/v1/auth/login",
        json={"username": "manager1", "password": "managerpass1"},
    ).json()["accessToken"]
    mgr = {"Authorization": f"Bearer {token}"}

    # Sees only branch 1 in the list, can read it, and is 404'd on branch 2.
    branches = client.get("/api/v1/branches", headers=mgr).json()["branches"]
    assert {b["id"] for b in branches} == {1}
    assert client.get("/api/v1/analytics/1", headers=mgr).status_code == 200
    assert client.get("/api/v1/analytics/2", headers=mgr).status_code == 404


def test_admin_can_update_user_branches(client, auth_headers):
    created = client.post(
        "/api/v1/admin/users",
        json={
            "username": "manager2",
            "email": "manager2@medservice.com",
            "password": "managerpass2",
            "branchIds": [1],
        },
        headers=auth_headers,
    ).json()

    # Re-assign to branch 2 only.
    updated = client.patch(
        f"/api/v1/admin/users/{created['id']}",
        json={"branchIds": [2]},
        headers=auth_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["branchIds"] == [2]


def test_assign_nonexistent_branch_rejected(client, auth_headers):
    resp = client.post(
        "/api/v1/admin/users",
        json={
            "username": "manager3",
            "email": "manager3@medservice.com",
            "password": "managerpass3",
            "branchIds": [99999],
        },
        headers=auth_headers,
    )
    assert resp.status_code == 400
