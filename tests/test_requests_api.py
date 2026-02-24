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
