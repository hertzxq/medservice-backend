"""Tests for /branches/{id}/bonuses (clinic bonuses)."""


def _make_payload(**overrides):
    base = {
        "discountPercent": 20,
        "description": "Скидка 20% на вторичный прием",
        "startDate": "2026-05-01",
        "endDate": "2026-05-30",
    }
    base.update(overrides)
    return base


def test_list_bonuses_initially_empty(client, auth_headers):
    r = client.get("/api/v1/branches/1/bonuses", headers=auth_headers)
    assert r.status_code == 200
    assert r.json() == []


def test_create_bonus_returns_201(client, auth_headers):
    r = client.post(
        "/api/v1/branches/1/bonuses", json=_make_payload(), headers=auth_headers
    )
    assert r.status_code == 201
    body = r.json()
    assert body["branchId"] == 1
    assert body["discountPercent"] == 20
    assert body["isPublished"] is True


def test_list_returns_created_bonus(client, auth_headers):
    client.post(
        "/api/v1/branches/1/bonuses", json=_make_payload(), headers=auth_headers
    )
    r = client.get("/api/v1/branches/1/bonuses", headers=auth_headers)
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 1
    assert items[0]["description"] == "Скидка 20% на вторичный прием"


def test_patch_bonus_toggles_published(client, auth_headers):
    created = client.post(
        "/api/v1/branches/1/bonuses", json=_make_payload(), headers=auth_headers
    ).json()
    bonus_id = created["id"]

    r = client.patch(
        f"/api/v1/branches/1/bonuses/{bonus_id}",
        json={"isPublished": False},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["isPublished"] is False


def test_delete_bonus_removes_it(client, auth_headers):
    created = client.post(
        "/api/v1/branches/1/bonuses", json=_make_payload(), headers=auth_headers
    ).json()
    bonus_id = created["id"]

    r = client.delete(
        f"/api/v1/branches/1/bonuses/{bonus_id}", headers=auth_headers
    )
    assert r.status_code == 204

    listing = client.get("/api/v1/branches/1/bonuses", headers=auth_headers).json()
    assert listing == []


def test_create_rejects_end_before_start(client, auth_headers):
    payload = _make_payload(startDate="2026-05-30", endDate="2026-05-01")
    r = client.post("/api/v1/branches/1/bonuses", json=payload, headers=auth_headers)
    assert r.status_code == 422


def test_create_rejects_discount_out_of_range(client, auth_headers):
    payload = _make_payload(discountPercent=0)
    r = client.post("/api/v1/branches/1/bonuses", json=payload, headers=auth_headers)
    assert r.status_code == 422

    payload = _make_payload(discountPercent=101)
    r = client.post("/api/v1/branches/1/bonuses", json=payload, headers=auth_headers)
    assert r.status_code == 422


def test_bonuses_unknown_branch_returns_404(client, auth_headers):
    r = client.post(
        "/api/v1/branches/9999/bonuses", json=_make_payload(), headers=auth_headers
    )
    assert r.status_code == 404


def test_bonuses_require_auth(client):
    r = client.get("/api/v1/branches/1/bonuses")
    assert r.status_code in (401, 403)


def test_deleting_branch_cascades_bonuses(client, auth_headers, session_factory):
    """Deleting a branch should remove its bonuses through CASCADE."""
    client.post(
        "/api/v1/branches/1/bonuses", json=_make_payload(), headers=auth_headers
    )
    r = client.delete("/api/v1/branches/1", headers=auth_headers)
    assert r.status_code == 204

    from app.models.bonus import BranchBonus

    session = session_factory()
    try:
        remaining = session.query(BranchBonus).filter_by(branch_id=1).all()
        assert remaining == []
    finally:
        session.close()
