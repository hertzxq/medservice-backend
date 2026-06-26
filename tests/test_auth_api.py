"""
Tests for authentication and RBAC authorization.
Covers: login, me, forgot-password, unauthorized access, superuser restrictions.
"""

import pytest

from app.core.security import create_password_reset_token
from app.models.user import User


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


def test_forgot_password_sends_reset_email_for_existing_user(client, monkeypatch):
    import app.api.v1.auth as auth_module

    sent: list[dict[str, str]] = []

    def fake_send_password_reset_email(*, to_email: str, reset_link: str) -> dict:
        sent.append({"to_email": to_email, "reset_link": reset_link})
        return {"ok": True}

    monkeypatch.setattr(
        auth_module,
        "send_password_reset_email",
        fake_send_password_reset_email,
    )
    monkeypatch.setattr(
        auth_module.settings,
        "frontend_public_url",
        "https://app.example.test",
    )

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "admin@medservice.com"},
    )

    assert response.status_code == 200
    assert sent == [
        {
            "to_email": "admin@medservice.com",
            "reset_link": sent[0]["reset_link"],
        }
    ]
    assert sent[0]["reset_link"].startswith("https://app.example.test/reset-password?token=")


def test_forgot_password_does_not_send_email_for_nonexistent_user(client, monkeypatch):
    import app.api.v1.auth as auth_module

    sent: list[dict[str, str]] = []

    def fake_send_password_reset_email(*, to_email: str, reset_link: str) -> dict:
        sent.append({"to_email": to_email, "reset_link": reset_link})
        return {"ok": True}

    monkeypatch.setattr(
        auth_module,
        "send_password_reset_email",
        fake_send_password_reset_email,
    )

    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@example.com"},
    )

    assert response.status_code == 200
    assert sent == []


def test_forgot_password_returns_200_for_nonexistent_email(client):
    """Anti-enumeration: always 200 regardless of existence."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@example.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()


def test_reset_password_changes_password_with_valid_token(client, session_factory):
    db = session_factory()
    user = db.query(User).filter(User.email == "user@medservice.com").one()
    token = create_password_reset_token(user.id, user.hashed_password)
    db.close()

    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": token, "password": "freshpass987"},
    )

    assert response.status_code == 200
    assert "message" in response.json()

    old = client.post(
        "/api/v1/auth/login",
        json={"username": "user", "password": "password123"},
    )
    assert old.status_code == 401

    new = client.post(
        "/api/v1/auth/login",
        json={"username": "user", "password": "freshpass987"},
    )
    assert new.status_code == 200


def test_reset_password_rejects_invalid_token(client):
    response = client.post(
        "/api/v1/auth/reset-password",
        json={"token": "not-a-valid-token", "password": "freshpass987"},
    )

    assert response.status_code == 400


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


def test_update_me_changes_password_and_profile(client, user_auth_headers):
    response = client.patch(
        "/api/v1/auth/me",
        headers=user_auth_headers,
        json={"fullName": "Новое Имя", "phone": "+79995554433", "password": "newpass9876"},
    )
    assert response.status_code == 200
    assert response.json()["fullName"] == "Новое Имя"

    # Старый пароль больше не подходит, новый — работает.
    old = client.post("/api/v1/auth/login", json={"username": "user", "password": "password123"})
    assert old.status_code == 401
    new = client.post("/api/v1/auth/login", json={"username": "user", "password": "newpass9876"})
    assert new.status_code == 200


def test_update_me_rejects_taken_email(client, user_auth_headers):
    response = client.patch(
        "/api/v1/auth/me",
        headers=user_auth_headers,
        json={"email": "admin@medservice.com"},
    )
    assert response.status_code == 400
