"""
Tests for POST /api/v1/public/branches/{id}/complaint — negative feedback from
the mini opened without an SMS request token.
"""


def test_branch_complaint_lands_in_clinic_feed(client, auth_headers):
    response = client.post(
        "/api/v1/public/branches/1/complaint",
        json={"message": "Очень долго ждал приёма", "rating": 1},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    # Жалоба видна клинике в «Отзывы и запросы → Перехваченные жалобы».
    feed = client.get("/api/v1/complaints?branchId=1", headers=auth_headers)
    assert feed.status_code == 200
    complaints = feed.json()["complaints"]
    newest = complaints[0]
    assert newest["text"] == "Очень долго ждал приёма"
    assert newest["rating"] == 1
    assert newest["resolved"] is False


def test_branch_complaint_without_rating_uses_fallback(client, auth_headers):
    response = client.post(
        "/api/v1/public/branches/1/complaint",
        json={"message": "Не понравилось"},
    )

    assert response.status_code == 200

    feed = client.get("/api/v1/complaints?branchId=1", headers=auth_headers)
    newest = feed.json()["complaints"][0]
    assert newest["rating"] == 2


def test_branch_complaint_unknown_branch_returns_404(client):
    response = client.post(
        "/api/v1/public/branches/999999/complaint",
        json={"message": "test"},
    )

    assert response.status_code == 404


def test_branch_complaint_invalid_rating_returns_422(client):
    response = client.post(
        "/api/v1/public/branches/1/complaint",
        json={"message": "test", "rating": 9},
    )

    assert response.status_code == 422
