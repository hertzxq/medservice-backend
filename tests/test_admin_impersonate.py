"""
Tests for admin impersonation: POST /api/v1/admin/users/{id}/impersonate.
"""


def _user_id_by_username(client, auth_headers, username: str) -> int:
    response = client.get("/api/v1/admin/users", headers=auth_headers)
    assert response.status_code == 200
    return next(u["id"] for u in response.json() if u["username"] == username)


def test_superuser_can_impersonate_user(client, auth_headers):
    user_id = _user_id_by_username(client, auth_headers, "user")

    response = client.post(
        f"/api/v1/admin/users/{user_id}/impersonate", headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user"]["username"] == "user"

    # Выданный токен действительно открывает кабинет от имени пользователя.
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['accessToken']}"},
    )
    assert me.status_code == 200
    assert me.json()["username"] == "user"
    assert me.json()["isSuperuser"] is False


def test_non_superuser_cannot_impersonate(client, auth_headers, user_auth_headers):
    admin_id = _user_id_by_username(client, auth_headers, "admin")

    response = client.post(
        f"/api/v1/admin/users/{admin_id}/impersonate", headers=user_auth_headers
    )

    assert response.status_code == 403


def test_impersonate_unknown_user_returns_404(client, auth_headers):
    response = client.post(
        "/api/v1/admin/users/999999/impersonate", headers=auth_headers
    )

    assert response.status_code == 404


def test_cannot_impersonate_another_superuser(client, auth_headers):
    # The seeded admin can't step into a different admin's account.
    other_admin = client.post(
        "/api/v1/admin/users",
        json={
            "username": "admin2",
            "email": "admin2@medservice.com",
            "password": "password123",
            "is_superuser": True,
        },
        headers=auth_headers,
    )
    assert other_admin.status_code == 201
    other_id = other_admin.json()["id"]

    resp = client.post(
        f"/api/v1/admin/users/{other_id}/impersonate", headers=auth_headers
    )
    assert resp.status_code == 400


def test_impersonation_token_rejected_on_superuser_routes(client, auth_headers):
    # An impersonation token must not be usable to reach admin/superuser routes
    # (no re-impersonation, no user management).
    user_id = _user_id_by_username(client, auth_headers, "user")
    data = client.post(
        f"/api/v1/admin/users/{user_id}/impersonate", headers=auth_headers
    ).json()
    imp_headers = {"Authorization": f"Bearer {data['accessToken']}"}

    # /auth/me (normal route) works; /admin/users (superuser route) is forbidden.
    assert client.get("/api/v1/auth/me", headers=imp_headers).status_code == 200
    assert client.get("/api/v1/admin/users", headers=imp_headers).status_code == 403
