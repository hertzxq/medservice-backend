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


def test_forgot_password_returns_success_message_for_existing_user(client):
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "admin@medservice.com"},
    )

    assert response.status_code == 200
    assert "message" in response.json()


def test_me_returns_current_user(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["fullName"] == "Test Admin"
