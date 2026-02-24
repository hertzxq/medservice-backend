def test_get_branches_returns_all_branches(client, auth_headers):
    response = client.get("/api/v1/branches", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["branches"]) == 2
    assert "avgRating" in data["branches"][0]
    assert "npsScore" in data["branches"][0]
