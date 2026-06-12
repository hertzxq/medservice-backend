from datetime import datetime, timedelta, timezone

from app.api.v1.analytics import to_utc_naive


def test_get_branch_analytics_respects_period_filter(client, auth_headers):
    response = client.get("/api/v1/analytics/1?period=30", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["sent"] == 1
    assert data["reviews"] == 1
    assert data["complaints"] == 1
    assert data["avgRating"] == 5.0


def test_get_branches_analytics_returns_rows(client, auth_headers):
    response = client.get("/api/v1/analytics/branches?period=30", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data["rows"]) == 2
    first_row = data["rows"][0]
    assert "newReviews" in first_row
    assert "interceptedComplaints" in first_row
    assert "avgRating" in first_row


def test_get_branch_dashboard_returns_extended_metrics(client, auth_headers):
    response = client.get("/api/v1/analytics/1/dashboard?period=30", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    assert data["sent"] == 1
    assert data["reviews"] == 1
    assert data["complaints"] == 1
    assert data["avgRating"] == 5.0

    assert len(data["platforms"]) == 5
    assert data["platforms"][0]["platform"] == "yandex_maps"
    assert data["platforms"][0]["reviews"] == 1
    assert data["platforms"][0]["totalReviews"] == 1

    assert data["platforms"][1]["platform"] == "google_maps"
    assert data["platforms"][1]["reviews"] == 0
    assert data["platforms"][1]["totalReviews"] == 1
    assert data["platforms"][1]["totalNegative"] == 1
    assert data["platforms"][1]["negativePercent"] == 100.0

    assert len(data["satisfaction"]) == 5
    assert data["satisfaction"][0]["stars"] == 5
    assert data["satisfaction"][0]["count"] == 1
    assert data["satisfaction"][0]["percent"] == 100.0

    assert len(data["npsSmall"]) == 12
    assert len(data["npsLarge"]) == 30
    assert data["employees"] == []

    # Лента отзывов показывает только негатив (оценка <= 3); в 30-дневном
    # периоде у филиала 1 есть лишь 5-звёздочный отзыв — лента пуста.
    assert data["recentReviews"] == []


def test_get_branch_dashboard_recent_reviews_only_negative(client, auth_headers):
    response = client.get("/api/v1/analytics/1/dashboard?period=90", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()

    # За 90 дней у филиала 1 два отзыва (5★ и 3★) — в ленту попадает только 3★.
    assert data["reviews"] == 2
    assert len(data["recentReviews"]) == 1
    assert data["recentReviews"][0]["rating"] == 3
    assert data["recentReviews"][0]["platformLabel"] == "Google Maps"


def test_to_utc_naive_converts_offset_aware_datetime():
    source = datetime(2026, 1, 15, 13, 30, tzinfo=timezone(timedelta(hours=3)))
    result = to_utc_naive(source)
    assert result == datetime(2026, 1, 15, 10, 30)
    assert result.tzinfo is None


def test_to_utc_naive_keeps_naive_datetime():
    source = datetime(2026, 1, 15, 10, 30)
    result = to_utc_naive(source)
    assert result == source
