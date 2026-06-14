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


# ── Monthly usage («X из Y» counter) ─────────────────────────────────────────


def test_request_usage_returns_limit_and_count(client, auth_headers):
    response = client.get("/api/v1/requests/usage?branchId=1", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "sentThisMonth" in data
    assert data["limit"] == 150  # default tariff (sms_monthly_limit)


def test_request_usage_increments_after_create(client, auth_headers):
    before = client.get(
        "/api/v1/requests/usage?branchId=1", headers=auth_headers
    ).json()["sentThisMonth"]

    created = client.post(
        "/api/v1/requests",
        headers=auth_headers,
        json={
            "branchId": 1,
            "clientName": "Счётчик Тест",
            "clientPhone": "+79993334444",
        },
    )
    assert created.status_code == 201

    after = client.get(
        "/api/v1/requests/usage?branchId=1", headers=auth_headers
    ).json()["sentThisMonth"]
    assert after == before + 1


def test_request_usage_forbidden_for_unassigned_branch(client, user_auth_headers):
    # A non-superuser may not read usage for a branch they don't have access to.
    response = client.get(
        "/api/v1/requests/usage?branchId=9999", headers=user_auth_headers
    )
    assert response.status_code == 404


# ── «Читать отзыв» появляется сразу после публикации (до парс-матча) ──────────


def test_published_claim_exposes_platform_and_read_link_before_match(
    client, auth_headers
):
    # Площадка для филиала настроена (это и есть цель кнопки «Читать отзыв»).
    client.patch(
        "/api/v1/branches/1",
        headers=auth_headers,
        json={"platformUrls": {"yandex_maps": "https://yandex.ru/maps/org/123"}},
    )

    created = client.post(
        "/api/v1/requests",
        headers=auth_headers,
        json={
            "branchId": 1,
            "clientName": "Публикатор",
            "clientPhone": "+79995556677",
        },
    )
    rid = created.json()["id"]
    token = created.json()["requestLink"].rstrip("/").split("/")[-1]

    client.post(f"/api/v1/public/requests/{token}/rating", json={"rating": 5})
    pub = client.post(
        f"/api/v1/public/requests/{token}/published",
        json={
            "platform": "yandex_maps",
            "reviewerName": "Публикатор",
            "reviewText": "Всё понравилось",
        },
    )
    assert pub.status_code == 200

    # В списке заявок строка уже отдаёт площадку и ссылку, хотя распарсенный
    # Review ещё не сматчен (verification pending).
    data = client.get(
        "/api/v1/requests?branchId=1&limit=100", headers=auth_headers
    ).json()
    row = next(r for r in data["requests"] if r["id"] == rid)
    assert row["status"] == "published"
    assert row["platform"] == "yandex_maps"
    assert row["reviewUrl"] == "https://yandex.ru/maps/org/123"
