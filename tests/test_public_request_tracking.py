"""
Tests for the mini's request-status tracking events:
POST /public/requests/{token}/opened and /visited.

Statuses must only move FORWARD (sent → opened → rated → visited →
published/complaint) — re-opening a link never downgrades a later status.
"""


def _create_request(client, auth_headers) -> tuple[int, str]:
    """Create a real request (like the UI does) and return (id, bare token)."""
    response = client.post(
        "/api/v1/requests",
        headers=auth_headers,
        json={
            "branchId": 1,
            "clientName": "Трекинг Тест",
            "clientPhone": "+79991112233",
        },
    )
    assert response.status_code == 201
    body = response.json()
    token = body["requestLink"].rstrip("/").split("/")[-1]
    return body["id"], token


def _status(client, auth_headers, request_id: int) -> str:
    response = client.get("/api/v1/requests?limit=100", headers=auth_headers)
    assert response.status_code == 200
    for r in response.json()["requests"]:
        if r["id"] == request_id:
            return r["status"]
    raise AssertionError(f"request {request_id} not found")


def test_opened_moves_sent_forward(client, auth_headers):
    req_id, token = _create_request(client, auth_headers)
    assert _status(client, auth_headers, req_id) == "sent"

    response = client.post(f"/api/v1/public/requests/{token}/opened")
    assert response.status_code == 200
    assert _status(client, auth_headers, req_id) == "opened"


def test_visited_after_rating(client, auth_headers):
    req_id, token = _create_request(client, auth_headers)
    client.post(f"/api/v1/public/requests/{token}/opened")
    client.post(f"/api/v1/public/requests/{token}/rating", json={"rating": 5})
    assert _status(client, auth_headers, req_id) == "rated"

    response = client.post(f"/api/v1/public/requests/{token}/visited")
    assert response.status_code == 200
    assert _status(client, auth_headers, req_id) == "visited"


def test_tracking_never_downgrades_published(client, auth_headers):
    req_id, token = _create_request(client, auth_headers)
    client.post(f"/api/v1/public/requests/{token}/rating", json={"rating": 5})
    client.post(f"/api/v1/public/requests/{token}/published", json={})
    assert _status(client, auth_headers, req_id) == "published"

    client.post(f"/api/v1/public/requests/{token}/opened")
    client.post(f"/api/v1/public/requests/{token}/visited")
    assert _status(client, auth_headers, req_id) == "published"


def test_opened_unknown_token_returns_404(client):
    response = client.post("/api/v1/public/requests/nope/opened")
    assert response.status_code == 404
