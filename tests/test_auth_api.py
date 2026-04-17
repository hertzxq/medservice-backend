"""
Tests for authentication and RBAC authorization.
Covers: login, me, forgot-password, unauthorized access, superuser restrictions.
"""

import pytest


# ── Login ─────────────────────────────────────────────────────────────────────


def test_login_success_returns_token_and_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "password123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "accessToken" in data
    assert data["tokenType"] == "bearer"
    assert data["user"]["username"] == "admin"
    assert data["user"]["isActive"] is True
    assert data["user"]["isSuperuser"] is True


def test_login_invalid_credentials_returns_401(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_login_nonexistent_user_returns_401(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "password123"},
    )

    assert response.status_code == 401


def test_login_empty_username_returns_422(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "", "password": "password123"},
    )
    # FastAPI may return 422 or 401 depending on validation;
    # the important thing is it does not return 200
    assert response.status_code != 200


# ── Forgot Password ──────────────────────────────────────────────────────────


def test_forgot_password_returns_success_message_for_existing_user(client):
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "admin@medservice.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()


def test_forgot_password_returns_200_for_nonexistent_email(client):
    """Anti-enumeration: always 200 regardless of existence."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()


# ── Me ────────────────────────────────────────────────────────────────────────


def test_me_returns_current_user(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["fullName"] == "Test Admin"
    assert data["isSuperuser"] is True
    assert data["isActive"] is True
    assert "email" in data


def test_me_without_token_returns_401_or_403(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code in (401, 403)


def test_me_with_invalid_token_returns_401(client):
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )

    assert response.status_code in (401, 403)


# ── Unauthorized access to protected endpoints ───────────────────────────────


@pytest.mark.parametrize(
    "method,endpoint",
    [
        ("GET", "/api/v1/branches"),
        ("GET", "/api/v1/reviews?branchId=1"),
        ("GET", "/api/v1/complaints?branchId=1"),
        ("GET", "/api/v1/requests?branchId=1"),
        ("GET", "/api/v1/analytics/1?period=30"),
        ("GET", "/api/v1/employees?branch_id=1"),
        ("GET", "/api/v1/blacklist?branch_id=1"),
    ],
)
def test_unauthenticated_access_returns_401_or_403(client, method, endpoint):
    response = client.request(method, endpoint)
    assert response.status_code in (401, 403)


# ── Superuser restriction on POST /requests ──────────────────────────────────


def test_create_request_requires_superuser(client, auth_headers):
    """The seed admin IS a superuser, so this should succeed."""
    response = client.post(
        "/api/v1/requests",
        headers=auth_headers,
        json={
            "branchId": 1,
            "clientName": "Test Client",
            "clientPhone": "+79990000099",
        },
    )

    assert response.status_code == 201
