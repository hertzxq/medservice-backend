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


def test_non_superuser_can_create_request_for_own_branch(client, user_auth_headers):
    """Запрос на отзыв отправляет клиника со страницы «Запросить отзывы» —
    доступно обычному пользователю, но только для его филиалов."""
    response = client.post(
        "/api/v1/requests",
        json={
            "branchId": 1,
            "clientName": "Клиент",
            "clientPhone": "+79998887766",
        },
        headers=user_auth_headers,
    )
    assert response.status_code == 201
    body = response.json()
    # Результат SMS возвращается фронту, чтобы он не показывал ложный успех.
    assert "sms" in body


def test_non_superuser_cannot_create_request_for_foreign_branch(
    client, user_auth_headers, auth_headers
):
    created = client.post(
        "/api/v1/branches",
        json={"name": "Чужой филиал"},
        headers=auth_headers,
    )
    assert created.status_code == 201
    foreign_id = created.json()["id"]

    response = client.post(
        "/api/v1/requests",
        json={
            "branchId": foreign_id,
            "clientName": "Клиент",
            "clientPhone": "+79998887766",
        },
        headers=user_auth_headers,
    )
    # Чужой филиал не раскрываем — 404, как и остальные branch-scoped ручки.
    assert response.status_code == 404


def test_non_superuser_cannot_send_test_sms(client, user_auth_headers):
    response = client.post(
        "/api/v1/requests/test-sms?branchId=1",
        json={"phone": "+79998887766"},
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


# ── Роль в команде меняет только суперпользователь (PATCH /auth/me) ───────────

def test_non_superuser_cannot_change_own_role(client, user_auth_headers):
    """Обычный пользователь видит свою роль, но не может её изменить через профиль."""
    before = client.get("/api/v1/auth/me", headers=user_auth_headers).json()
    response = client.patch(
        "/api/v1/auth/me",
        json={"role": "Главный врач"},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    # Роль из payload игнорируется — остаётся прежней.
    assert response.json()["role"] == before["role"]


def test_non_superuser_can_still_edit_own_profile(client, user_auth_headers):
    """Запрет касается только роли — имя/телефон обычный юзер меняет сам."""
    response = client.patch(
        "/api/v1/auth/me",
        json={"fullName": "Новое Имя", "phone": "+79990001122"},
        headers=user_auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fullName"] == "Новое Имя"
    assert body["phone"] == "+79990001122"


def test_superuser_can_change_own_role(client, auth_headers):
    response = client.patch(
        "/api/v1/auth/me",
        json={"role": "Администратор"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "Администратор"
