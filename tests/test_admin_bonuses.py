"""Tests for /admin/bonus-categories admin catalog."""


def _bonus_payload(**overrides):
    base = {
        "companyName": "Клиника микрохирургии глаза",
        "city": "Санкт-Петербург",
        "discountPercent": 20,
        "description": "Скидка 20% на вторичный прием",
        "startDate": "2026-05-01",
        "endDate": "2026-05-30",
    }
    base.update(overrides)
    return base


def test_list_categories_initially_empty(client, auth_headers):
    r = client.get("/api/v1/admin/bonus-categories", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_create_category(client, auth_headers):
    r = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "Аптеки"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Аптеки"
    assert body["bonuses"] == []


def test_create_category_rejects_empty_name(client, auth_headers):
    r = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "   "},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_patch_category_renames(client, auth_headers):
    cat = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "Аптеки"},
        headers=auth_headers,
    ).json()
    r = client.patch(
        f"/api/v1/admin/bonus-categories/{cat['id']}",
        json={"name": "Фарма"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Фарма"


def test_delete_category_cascades_bonuses(client, auth_headers):
    cat = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "Аптеки"},
        headers=auth_headers,
    ).json()
    client.post(
        f"/api/v1/admin/bonus-categories/{cat['id']}/bonuses",
        json=_bonus_payload(),
        headers=auth_headers,
    )

    r = client.delete(
        f"/api/v1/admin/bonus-categories/{cat['id']}", headers=auth_headers
    )
    assert r.status_code == 204

    listing = client.get(
        "/api/v1/admin/bonus-categories", headers=auth_headers
    ).json()
    assert listing == []


def test_create_admin_bonus(client, auth_headers):
    cat = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "Аптеки"},
        headers=auth_headers,
    ).json()

    r = client.post(
        f"/api/v1/admin/bonus-categories/{cat['id']}/bonuses",
        json=_bonus_payload(),
        headers=auth_headers,
    )
    assert r.status_code == 201
    bonus = r.json()
    assert bonus["companyName"] == "Клиника микрохирургии глаза"
    assert bonus["categoryId"] == cat["id"]
    assert bonus["isPublished"] is True


def test_get_returns_categories_with_bonuses(client, auth_headers):
    cat = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "Аптеки"},
        headers=auth_headers,
    ).json()
    client.post(
        f"/api/v1/admin/bonus-categories/{cat['id']}/bonuses",
        json=_bonus_payload(),
        headers=auth_headers,
    )

    r = client.get("/api/v1/admin/bonus-categories", headers=auth_headers)
    body = r.json()
    assert len(body) == 1
    assert body[0]["name"] == "Аптеки"
    assert len(body[0]["bonuses"]) == 1
    assert body[0]["bonuses"][0]["city"] == "Санкт-Петербург"


def test_patch_admin_bonus_toggles_published(client, auth_headers):
    cat = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "Аптеки"},
        headers=auth_headers,
    ).json()
    bonus = client.post(
        f"/api/v1/admin/bonus-categories/{cat['id']}/bonuses",
        json=_bonus_payload(),
        headers=auth_headers,
    ).json()

    r = client.patch(
        f"/api/v1/admin/bonus-categories/{cat['id']}/bonuses/{bonus['id']}",
        json={"isPublished": False},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["isPublished"] is False


def test_delete_admin_bonus(client, auth_headers):
    cat = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "Аптеки"},
        headers=auth_headers,
    ).json()
    bonus = client.post(
        f"/api/v1/admin/bonus-categories/{cat['id']}/bonuses",
        json=_bonus_payload(),
        headers=auth_headers,
    ).json()

    r = client.delete(
        f"/api/v1/admin/bonus-categories/{cat['id']}/bonuses/{bonus['id']}",
        headers=auth_headers,
    )
    assert r.status_code == 204


def test_admin_bonus_rejects_oversized_logo(client, auth_headers):
    cat = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "Аптеки"},
        headers=auth_headers,
    ).json()
    big = "data:image/png;base64," + ("A" * (200 * 1024 + 1))
    r = client.post(
        f"/api/v1/admin/bonus-categories/{cat['id']}/bonuses",
        json=_bonus_payload(logoUrl=big),
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_admin_endpoints_forbidden_for_regular_user(client, user_auth_headers):
    r = client.get("/api/v1/admin/bonus-categories", headers=user_auth_headers)
    assert r.status_code == 403

    r = client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": "Аптеки"},
        headers=user_auth_headers,
    )
    assert r.status_code == 403


def test_admin_endpoints_require_auth(client):
    r = client.get("/api/v1/admin/bonus-categories")
    assert r.status_code in (401, 403)
