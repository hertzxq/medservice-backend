"""Tests for the public mini-app endpoint."""

import datetime


def _today_iso() -> str:
    return datetime.date.today().isoformat()


def _future_iso(days: int) -> str:
    return (datetime.date.today() + datetime.timedelta(days=days)).isoformat()


def _past_iso(days: int) -> str:
    return (datetime.date.today() - datetime.timedelta(days=days)).isoformat()


def _branch_bonus(client, auth_headers, **overrides):
    payload = {
        "discountPercent": 20,
        "description": "Тест бонус филиала",
        "startDate": _today_iso(),
        "endDate": _future_iso(30),
    }
    payload.update(overrides)
    return client.post(
        "/api/v1/branches/1/bonuses", json=payload, headers=auth_headers
    ).json()


def _category(client, auth_headers, name="Аптеки"):
    return client.post(
        "/api/v1/admin/bonus-categories",
        json={"name": name},
        headers=auth_headers,
    ).json()


def _admin_bonus(client, auth_headers, category_id, **overrides):
    payload = {
        "companyName": "Аптека X",
        "city": "Санкт-Петербург",
        "discountPercent": 10,
        "description": "Тест бонус партнёра",
        "startDate": _today_iso(),
        "endDate": _future_iso(30),
    }
    payload.update(overrides)
    return client.post(
        f"/api/v1/admin/bonus-categories/{category_id}/bonuses",
        json=payload,
        headers=auth_headers,
    ).json()


def test_mini_no_auth_required(client):
    r = client.get("/api/v1/public/branches/1/mini")
    assert r.status_code == 200


def test_mini_returns_branch_and_empty_collections(client):
    r = client.get("/api/v1/public/branches/1/mini")
    body = r.json()
    assert body["branch"]["id"] == 1
    assert body["branch"]["publicName"] is None  # seed sets internal name only
    assert body["branchBonuses"] == []
    assert body["categories"] == []
    assert body["faq"] == []


def test_mini_includes_active_published_branch_bonus(client, auth_headers):
    _branch_bonus(client, auth_headers, promoCode="SuperSkidka")
    r = client.get("/api/v1/public/branches/1/mini")
    body = r.json()
    assert len(body["branchBonuses"]) == 1
    bonus = body["branchBonuses"][0]
    assert bonus["promoCode"] == "SuperSkidka"
    assert bonus["isPublished"] is True


def test_mini_filters_unpublished_branch_bonus(client, auth_headers):
    bonus = _branch_bonus(client, auth_headers)
    client.patch(
        f"/api/v1/branches/1/bonuses/{bonus['id']}",
        json={"isPublished": False},
        headers=auth_headers,
    )
    r = client.get("/api/v1/public/branches/1/mini")
    assert r.json()["branchBonuses"] == []


def test_mini_filters_past_branch_bonus(client, auth_headers):
    _branch_bonus(
        client,
        auth_headers,
        startDate=_past_iso(30),
        endDate=_past_iso(1),
    )
    r = client.get("/api/v1/public/branches/1/mini")
    assert r.json()["branchBonuses"] == []


def test_mini_filters_future_branch_bonus(client, auth_headers):
    _branch_bonus(
        client,
        auth_headers,
        startDate=_future_iso(1),
        endDate=_future_iso(30),
    )
    r = client.get("/api/v1/public/branches/1/mini")
    assert r.json()["branchBonuses"] == []


def test_mini_omits_empty_categories(client, auth_headers):
    cat = _category(client, auth_headers, name="Пустая")
    r = client.get("/api/v1/public/branches/1/mini")
    assert all(c["id"] != cat["id"] for c in r.json()["categories"])


def test_mini_includes_category_with_published_admin_bonus(client, auth_headers):
    cat = _category(client, auth_headers, name="Аптеки")
    _admin_bonus(
        client,
        auth_headers,
        cat["id"],
        companyName="Аптека 36,6",
        promoCode="SuperApteka",
        websiteUrl="https://366.ru",
    )
    r = client.get("/api/v1/public/branches/1/mini")
    cats = r.json()["categories"]
    assert len(cats) == 1
    assert cats[0]["name"] == "Аптеки"
    assert len(cats[0]["bonuses"]) == 1
    assert cats[0]["bonuses"][0]["promoCode"] == "SuperApteka"
    assert cats[0]["bonuses"][0]["websiteUrl"] == "https://366.ru"


def test_mini_filters_unpublished_admin_bonus(client, auth_headers):
    cat = _category(client, auth_headers, name="Аптеки")
    bonus = _admin_bonus(client, auth_headers, cat["id"])
    client.patch(
        f"/api/v1/admin/bonus-categories/{cat['id']}/bonuses/{bonus['id']}",
        json={"isPublished": False},
        headers=auth_headers,
    )
    r = client.get("/api/v1/public/branches/1/mini")
    assert r.json()["categories"] == []


def test_mini_sorts_faq_by_sort_order(client, auth_headers):
    client.post(
        "/api/v1/admin/faq",
        json={"question": "Q2", "answer": "A2", "sortOrder": 1},
        headers=auth_headers,
    )
    client.post(
        "/api/v1/admin/faq",
        json={"question": "Q1", "answer": "A1", "sortOrder": 0},
        headers=auth_headers,
    )
    r = client.get("/api/v1/public/branches/1/mini")
    faq = r.json()["faq"]
    assert [item["question"] for item in faq] == ["Q1", "Q2"]


def test_mini_404_for_unknown_branch(client):
    r = client.get("/api/v1/public/branches/9999/mini")
    assert r.status_code == 404


def test_mini_404_for_inactive_branch(client, auth_headers):
    client.patch(
        "/api/v1/branches/1", json={"isActive": False}, headers=auth_headers
    )
    r = client.get("/api/v1/public/branches/1/mini")
    assert r.status_code == 404
