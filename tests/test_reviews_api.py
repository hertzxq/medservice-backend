def test_get_reviews_supports_frontend_filters(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&platform=yandex_maps&ratingMin=4&period=30&limit=10&offset=0",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    review = data["reviews"][0]
    assert review["branchId"] == 1
    assert review["platform"] == "yandex_maps"
    assert review["rating"] >= 4
    assert "branchName" in review
