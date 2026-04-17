"""
Tests for complaints API: filters, pagination, resolve toggle, edge cases.
"""


# ── Basic fetch ──────────────────────────────────────────────────────────────


def test_get_complaints_returns_all_for_branch(client, auth_headers):
    response = client.get(
        "/api/v1/complaints?branchId=1",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "complaints" in data
    assert "total" in data
    assert data["total"] >= 1


def test_get_complaints_supports_branch_and_resolved_filters(client, auth_headers):
    response = client.get(
        "/api/v1/complaints?branchId=1&resolved=false&limit=10&offset=0",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    complaint = data["complaints"][0]
    assert complaint["branchId"] == 1
    assert complaint["resolved"] is False
    assert "branchName" in complaint


def test_get_complaints_filter_resolved_true(client, auth_headers):
    response = client.get(
        "/api/v1/complaints?branchId=1&resolved=true",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for complaint in data["complaints"]:
        assert complaint["resolved"] is True


def test_get_complaints_for_branch_2(client, auth_headers):
    response = client.get("/api/v1/complaints?branchId=2", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for complaint in data["complaints"]:
        assert complaint["branchId"] == 2


# ── Pagination ───────────────────────────────────────────────────────────────


def test_get_complaints_pagination_limit(client, auth_headers):
    response = client.get(
        "/api/v1/complaints?branchId=1&limit=1&offset=0",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["complaints"]) <= 1


def test_get_complaints_pagination_offset_beyond(client, auth_headers):
    response = client.get(
        "/api/v1/complaints?branchId=1&limit=10&offset=100",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.json()["complaints"]) == 0


# ── Resolve toggle ───────────────────────────────────────────────────────────


def test_update_complaint_marks_resolved(client, auth_headers):
    response = client.patch(
        "/api/v1/complaints/1",
        headers=auth_headers,
        json={"resolved": True},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["resolved"] is True


def test_update_complaint_marks_unresolved(client, auth_headers):
    # First resolve it
    client.patch(
        "/api/v1/complaints/1",
        headers=auth_headers,
        json={"resolved": True},
    )
    # Then unresolve
    response = client.patch(
        "/api/v1/complaints/1",
        headers=auth_headers,
        json={"resolved": False},
    )

    assert response.status_code == 200
    assert response.json()["resolved"] is False


# ── Edge cases ───────────────────────────────────────────────────────────────


def test_update_nonexistent_complaint_returns_404(client, auth_headers):
    response = client.patch(
        "/api/v1/complaints/9999",
        headers=auth_headers,
        json={"resolved": True},
    )

    assert response.status_code == 404


def test_get_complaints_nonexistent_branch(client, auth_headers):
    response = client.get(
        "/api/v1/complaints?branchId=9999",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0


def test_complaint_response_contains_required_fields(client, auth_headers):
    response = client.get("/api/v1/complaints?branchId=1", headers=auth_headers)
    data = response.json()

    if data["total"] > 0:
        complaint = data["complaints"][0]
        expected = {"id", "branchId", "clientName", "clientPhone", "rating", "text", "resolved", "createdAt"}
        assert expected.issubset(set(complaint.keys()))
