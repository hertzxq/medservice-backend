"""Tests for /branches/{id}/branding (public brand header)."""


def test_get_branding_defaults_to_nulls(client, auth_headers):
    r = client.get("/api/v1/branches/1/branding", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "publicName": None,
        "publicCity": None,
        "logoUrl": None,
        "websiteUrl": None,
    }


def test_patch_branding_updates_fields(client, auth_headers):
    payload = {
        "publicName": "Клиника микрохирургии глаза",
        "publicCity": "Санкт-Петербург",
        "logoUrl": None,
    }
    r = client.patch("/api/v1/branches/1/branding", json=payload, headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["publicName"] == payload["publicName"]
    assert body["publicCity"] == payload["publicCity"]
    assert body["logoUrl"] is None


def test_patch_branding_accepts_base64_logo(client, auth_headers):
    payload = {"logoUrl": "data:image/png;base64,iVBORw0KGgoAAA=="}
    r = client.patch("/api/v1/branches/1/branding", json=payload, headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["logoUrl"] == payload["logoUrl"]


def test_patch_branding_rejects_non_png_data_url(client, auth_headers):
    payload = {"logoUrl": "data:image/jpeg;base64,xxxx"}
    r = client.patch("/api/v1/branches/1/branding", json=payload, headers=auth_headers)
    assert r.status_code == 422


def test_patch_branding_rejects_oversized_logo(client, auth_headers):
    big = "data:image/png;base64," + ("A" * (200 * 1024 + 1))
    r = client.patch(
        "/api/v1/branches/1/branding", json={"logoUrl": big}, headers=auth_headers
    )
    assert r.status_code == 422


def test_branding_requires_auth(client):
    r = client.get("/api/v1/branches/1/branding")
    assert r.status_code in (401, 403)


def test_branding_unknown_branch_returns_404(client, auth_headers):
    r = client.get("/api/v1/branches/9999/branding", headers=auth_headers)
    assert r.status_code == 404
