"""
Tests for reviews API: filters, pagination, edge cases.
"""


# ── Basic fetch ──────────────────────────────────────────────────────────────


def test_get_reviews_returns_all_for_branch(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "reviews" in data
    assert "total" in data
    assert data["total"] >= 1
    for review in data["reviews"]:
        assert review["branchId"] == 1


def test_get_reviews_for_branch_2(client, auth_headers):
    response = client.get("/api/v1/reviews?branchId=2", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    for review in data["reviews"]:
        assert review["branchId"] == 2


# ── Platform filter ──────────────────────────────────────────────────────────


def test_get_reviews_filter_by_platform(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&platform=yandex_maps",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for review in data["reviews"]:
        assert review["platform"] == "yandex_maps"


def test_get_reviews_filter_platform_no_results(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&platform=napopravku",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["reviews"] == []


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


# ── Rating filters ───────────────────────────────────────────────────────────


def test_get_reviews_filter_rating_min(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&ratingMin=4",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for review in data["reviews"]:
        assert review["rating"] >= 4


def test_get_reviews_filter_rating_max(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&ratingMax=3",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for review in data["reviews"]:
        assert review["rating"] <= 3


def test_get_reviews_filter_rating_range(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&ratingMin=3&ratingMax=5",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    for review in data["reviews"]:
        assert 3 <= review["rating"] <= 5


def test_get_reviews_rating_min_greater_than_max_returns_422(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&ratingMin=5&ratingMax=1",
        headers=auth_headers,
    )

    assert response.status_code == 422


# ── Period filter ────────────────────────────────────────────────────────────


def test_get_reviews_filter_period_week(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&period=week",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # Review at day -3 should be within a week
    assert data["total"] >= 1


def test_get_reviews_filter_period_year(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&period=year",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    # All seeded reviews are within a year
    assert data["total"] >= 2


# ── Pagination ───────────────────────────────────────────────────────────────


def test_get_reviews_pagination_limit(client, auth_headers):
    response = client.get(
        "/api/v1/reviews?branchId=1&limit=1&offset=0",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["reviews"]) <= 1


def test_get_reviews_pagination_offset(client, auth_headers):
    # First get total
    response_all = client.get("/api/v1/reviews?branchId=1", headers=auth_headers)
    total = response_all.json()["total"]

    # Offset beyond total → no results
    response = client.get(
        f"/api/v1/reviews?branchId=1&limit=10&offset={total + 10}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["reviews"]) == 0


# ── Response shape ───────────────────────────────────────────────────────────


def test_review_response_contains_required_fields(client, auth_headers):
    response = client.get("/api/v1/reviews?branchId=1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    if data["total"] > 0:
        review = data["reviews"][0]
        expected = {"id", "branchId", "reviewerName", "rating", "text", "platform", "publishedAt", "branchName"}
        assert expected.issubset(set(review.keys()))


# ── Nonexistent branch ──────────────────────────────────────────────────────


def test_get_reviews_nonexistent_branch(client, auth_headers):
    response = client.get("/api/v1/reviews?branchId=9999", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["reviews"] == []
