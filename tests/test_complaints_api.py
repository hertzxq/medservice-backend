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
