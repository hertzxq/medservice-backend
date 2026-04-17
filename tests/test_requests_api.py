"""
Tests for requests API: filters, creation (superuser-only), edge cases.
"""


# ── Basic fetch ──────────────────────────────────────────────────────────────


def test_get_requests_returns_all_for_branch(client, auth_headers):
    response = client.get("/api/v1/requests?branchId=1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "requests" in data
    assert "total" in data
    assert data["total"] >= 1


def test_get_requests_supports_filters(client, auth_headers):
    response = client.get(
        "/api/v1/requests?branchId=2&status=published&limit=10&offset=0",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    request_item = data["requests"][0]
    assert request_item["branchId"] == 2
    assert request_item["status"] == "published"
    assert "branchName" in request_item


# ── Status filters ───────────────────────────────────────────────────────────


def test_get_requests_filter_status_sent(client, auth_headers):
    response = client.get(
        "/api/v1/requests?branchId=1&status=sent",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for req in data["requests"]:
        assert req["status"] == "sent"


def test_get_requests_filter_status_opened(client, auth_headers):
    response = client.get(
        "/api/v1/requests?branchId=1&status=opened",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for req in data["requests"]:
        assert req["status"] == "opened"


def test_get_requests_filter_nonexistent_status_returns_empty(client, auth_headers):
    response = client.get(
        "/api/v1/requests?branchId=1&status=complaint",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


# ── Create request ───────────────────────────────────────────────────────────


def test_create_request_creates_new_entry(client, auth_headers):
    response = client.post(
        "/api/v1/requests",
        headers=auth_headers,
        json={
            "branchId": 1,
            "clientName": "Новый клиент",
            "clientPhone": "+79991111111",
            "clientEmail": "new.client@example.com",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["branchId"] == 1
    assert data["clientName"] == "Новый клиент"
    assert data["status"] == "sent"
    assert data["requestLink"] is not None


def test_create_request_generates_unique_links(client, auth_headers):
    resp1 = client.post(
        "/api/v1/requests",
        headers=auth_headers,
        json={
            "branchId": 1,
            "clientName": "Клиент А",
            "clientPhone": "+79990000001",
        },
    )
    resp2 = client.post(
        "/api/v1/requests",
        headers=auth_headers,
        json={
            "branchId": 1,
            "clientName": "Клиент Б",
            "clientPhone": "+79990000002",
        },
    )

    assert resp1.status_code == 201
    assert resp2.status_code == 201
    assert resp1.json()["requestLink"] != resp2.json()["requestLink"]


def test_create_request_for_nonexistent_branch_returns_404(client, auth_headers):
    response = client.post(
        "/api/v1/requests",
        headers=auth_headers,
        json={
            "branchId": 9999,
            "clientName": "Ghost",
            "clientPhone": "+79990000000",
        },
    )

    assert response.status_code == 404


# ── Pagination ───────────────────────────────────────────────────────────────


def test_get_requests_pagination(client, auth_headers):
    response = client.get(
        "/api/v1/requests?branchId=1&limit=1&offset=0",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["requests"]) <= 1


# ── Response shape ───────────────────────────────────────────────────────────


def test_request_response_contains_required_fields(client, auth_headers):
    response = client.get("/api/v1/requests?branchId=1", headers=auth_headers)
    data = response.json()

    if data["total"] > 0:
        req = data["requests"][0]
        expected = {"id", "branchId", "clientName", "clientPhone", "status", "sentAt"}
        assert expected.issubset(set(req.keys()))


# ── Branch isolation ─────────────────────────────────────────────────────────


def test_get_requests_nonexistent_branch_returns_empty(client, auth_headers):
    response = client.get("/api/v1/requests?branchId=9999", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["total"] == 0
