"""
Проверка разделения прав: обычный пользователь не может вызывать
мутирующие эндпоинты, которые требуют superuser.
"""


def test_non_superuser_cannot_patch_branch(client, user_auth_headers):
    response = client.patch(
        "/api/v1/branches/1",
        json={"name": "Новое имя"},
        headers=user_auth_headers,
    )
    assert response.status_code == 403


def test_non_superuser_cannot_create_employee(client, user_auth_headers):
    response = client.post(
        "/api/v1/employees?branch_id=1",
        json={"name": "Новый сотрудник", "active": True},
        headers=user_auth_headers,
    )
    assert response.status_code == 403


def test_non_superuser_cannot_update_employee(client, user_auth_headers, auth_headers):
    created = client.post(
        "/api/v1/employees?branch_id=1",
        json={"name": "Иванов", "active": True},
        headers=auth_headers,
    )
    assert created.status_code == 201
    employee_id = created.json()["id"]

    response = client.patch(
        f"/api/v1/employees/{employee_id}",
        json={"active": False},
        headers=user_auth_headers,
    )
    assert response.status_code == 403


def test_non_superuser_cannot_delete_employee(client, user_auth_headers, auth_headers):
    created = client.post(
        "/api/v1/employees?branch_id=1",
        json={"name": "Иванов", "active": True},
        headers=auth_headers,
    )
    employee_id = created.json()["id"]

    response = client.delete(
        f"/api/v1/employees/{employee_id}",
        headers=user_auth_headers,
    )
    assert response.status_code == 403


def test_non_superuser_can_add_blacklist(client, user_auth_headers):
    """Обычный пользователь может добавлять в чёрный список филиала.
    PATCH/DELETE по-прежнему остаются за superuser."""
    response = client.post(
        "/api/v1/blacklist?branch_id=1",
        json={
            "lastName": "Иванов",
            "firstName": "Иван",
            "phone": "+79990000000",
            "reason": "тест",
        },
        headers=user_auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["lastName"] == "Иванов"
    assert body["phone"] == "+79990000000"


def test_non_superuser_can_delete_blacklist(client, user_auth_headers, auth_headers):
    """Обычный пользователь может удалять записи из чёрного списка."""
    created = client.post(
        "/api/v1/blacklist?branch_id=1",
        json={
            "lastName": "Петров",
            "firstName": "Пётр",
            "phone": "+79990000077",
        },
        headers=auth_headers,
    )
    assert created.status_code == 201
    user_id = created.json()["id"]

    response = client.delete(
        f"/api/v1/blacklist/{user_id}",
        headers=user_auth_headers,
    )
    assert response.status_code == 204


def test_non_superuser_cannot_create_request(client, user_auth_headers):
    response = client.post(
        "/api/v1/requests",
        json={
            "branchId": 1,
            "clientName": "Клиент",
            "clientPhone": "+79998887766",
        },
        headers=user_auth_headers,
    )
    assert response.status_code == 403


def test_non_superuser_cannot_trigger_parsing(client, user_auth_headers):
    response = client.post(
        "/api/v1/parsing/trigger",
        json={"url": "https://yandex.ru/maps/org/1234567890", "branch_id": 1},
        headers=user_auth_headers,
    )
    assert response.status_code == 403


def test_non_superuser_can_read_data(client, user_auth_headers):
    """GET-эндпоинты остаются доступными для обычного пользователя."""
    assert client.get("/api/v1/branches", headers=user_auth_headers).status_code == 200
    assert client.get("/api/v1/reviews?branchId=1", headers=user_auth_headers).status_code == 200
    assert client.get("/api/v1/complaints?branchId=1", headers=user_auth_headers).status_code == 200
    assert client.get("/api/v1/requests?branchId=1", headers=user_auth_headers).status_code == 200
    assert client.get("/api/v1/blacklist?branch_id=1", headers=user_auth_headers).status_code == 200
