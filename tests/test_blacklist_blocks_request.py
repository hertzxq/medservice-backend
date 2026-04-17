"""
Интеграционные тесты: чёрный список блокирует создание запроса.
"""


def test_request_blocked_when_phone_in_blacklist(client, auth_headers):
    add_resp = client.post(
        "/api/v1/blacklist?branch_id=1",
        json={
            "lastName": "Иванов",
            "firstName": "Иван",
            "phone": "+79990001122",
            "reason": "Некорректное поведение",
        },
        headers=auth_headers,
    )
    assert add_resp.status_code == 201

    create_resp = client.post(
        "/api/v1/requests",
        json={
            "branchId": 1,
            "clientName": "Иван Иванов",
            "clientPhone": "+79990001122",
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 409
    assert "Некорректное поведение" in create_resp.json()["detail"]


def test_phone_normalization_detects_blacklist(client, auth_headers):
    """Разные форматы телефона должны распознаваться как один номер."""
    client.post(
        "/api/v1/blacklist?branch_id=1",
        json={
            "lastName": "Петров",
            "firstName": "Пётр",
            "phone": "89990001133",
        },
        headers=auth_headers,
    )

    resp = client.post(
        "/api/v1/requests",
        json={
            "branchId": 1,
            "clientName": "Пётр Петров",
            "clientPhone": "+7 (999) 000-11-33",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 409


def test_blacklist_isolated_by_branch(client, auth_headers):
    """ЧС одного филиала не должен блокировать запросы в другом филиале."""
    client.post(
        "/api/v1/blacklist?branch_id=1",
        json={
            "lastName": "Сидоров",
            "firstName": "Сидор",
            "phone": "+79990001144",
        },
        headers=auth_headers,
    )

    resp = client.post(
        "/api/v1/requests",
        json={
            "branchId": 2,
            "clientName": "Сидор Сидоров",
            "clientPhone": "+79990001144",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201


def test_request_allowed_when_phone_not_in_blacklist(client, auth_headers):
    resp = client.post(
        "/api/v1/requests",
        json={
            "branchId": 1,
            "clientName": "Новый клиент",
            "clientPhone": "+79990009999",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
