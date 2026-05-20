"""Tests for /admin/faq CRUD."""


def test_list_faq_initially_empty(client, auth_headers):
    r = client.get("/api/v1/admin/faq", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_create_faq(client, auth_headers):
    r = client.post(
        "/api/v1/admin/faq",
        json={"question": "Что такое промокод?", "answer": "Это код для скидки.", "sortOrder": 1},
        headers=auth_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["question"] == "Что такое промокод?"
    assert body["answer"] == "Это код для скидки."
    assert body["sortOrder"] == 1


def test_create_faq_rejects_empty_question(client, auth_headers):
    r = client.post(
        "/api/v1/admin/faq",
        json={"question": "   ", "answer": "Ответ"},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_create_faq_rejects_empty_answer(client, auth_headers):
    r = client.post(
        "/api/v1/admin/faq",
        json={"question": "Вопрос", "answer": "  "},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_patch_faq(client, auth_headers):
    item = client.post(
        "/api/v1/admin/faq",
        json={"question": "Q", "answer": "A"},
        headers=auth_headers,
    ).json()
    r = client.patch(
        f"/api/v1/admin/faq/{item['id']}",
        json={"answer": "Новый ответ"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["answer"] == "Новый ответ"


def test_patch_faq_404(client, auth_headers):
    r = client.patch(
        "/api/v1/admin/faq/9999", json={"answer": "x"}, headers=auth_headers
    )
    assert r.status_code == 404


def test_delete_faq(client, auth_headers):
    item = client.post(
        "/api/v1/admin/faq",
        json={"question": "Q", "answer": "A"},
        headers=auth_headers,
    ).json()
    r = client.delete(f"/api/v1/admin/faq/{item['id']}", headers=auth_headers)
    assert r.status_code == 204

    listing = client.get("/api/v1/admin/faq", headers=auth_headers).json()
    assert listing == []


def test_list_faq_sorted_by_sort_order(client, auth_headers):
    client.post(
        "/api/v1/admin/faq",
        json={"question": "Q-B", "answer": "A-B", "sortOrder": 2},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/admin/faq",
        json={"question": "Q-A", "answer": "A-A", "sortOrder": 1},
        headers=auth_headers,
    )
    r = client.get("/api/v1/admin/faq", headers=auth_headers)
    assert [item["question"] for item in r.json()] == ["Q-A", "Q-B"]


def test_faq_forbidden_for_regular_user(client, user_auth_headers):
    r = client.get("/api/v1/admin/faq", headers=user_auth_headers)
    assert r.status_code == 403

    r = client.post(
        "/api/v1/admin/faq",
        json={"question": "Q", "answer": "A"},
        headers=user_auth_headers,
    )
    assert r.status_code == 403


def test_faq_requires_auth(client):
    r = client.get("/api/v1/admin/faq")
    assert r.status_code in (401, 403)
