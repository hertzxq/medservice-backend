"""
Tests for branches API: GET list, PATCH settings, partial update, 404.
"""


# ── GET branches ─────────────────────────────────────────────────────────────


def test_get_branches_returns_all_branches(client, auth_headers):
    response = client.get("/api/v1/branches", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["branches"]) == 2
    assert "avgRating" in data["branches"][0]
    assert "npsScore" in data["branches"][0]


def test_get_branches_response_contains_settings_fields(client, auth_headers):
    response = client.get("/api/v1/branches", headers=auth_headers)

    assert response.status_code == 200
    branch = response.json()["branches"][0]
    expected_fields = {
        "id", "name", "timezone", "specialization",
        "requestFrequencyDays", "complaintEmails", "reminderEmails",
    }
    assert expected_fields.issubset(set(branch.keys()))


def test_get_branches_default_settings(client, auth_headers):
    response = client.get("/api/v1/branches", headers=auth_headers)
    branch = response.json()["branches"][0]

    assert isinstance(branch["complaintEmails"], list)
    assert isinstance(branch["reminderEmails"], list)
    assert isinstance(branch["requestFrequencyDays"], int)


# ── PATCH branch (full update) ───────────────────────────────────────────────


def test_patch_branch_updates_name(client, auth_headers):
    response = client.patch(
        "/api/v1/branches/1",
        headers=auth_headers,
        json={"name": "Новое название филиала"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Новое название филиала"


def test_patch_branch_updates_timezone(client, auth_headers):
    response = client.patch(
        "/api/v1/branches/1",
        headers=auth_headers,
        json={"timezone": "Asia/Novosibirsk"},
    )

    assert response.status_code == 200
    assert response.json()["timezone"] == "Asia/Novosibirsk"


def test_patch_branch_updates_specialization(client, auth_headers):
    response = client.patch(
        "/api/v1/branches/1",
        headers=auth_headers,
        json={"specialization": "Стоматология"},
    )

    assert response.status_code == 200
    assert response.json()["specialization"] == "Стоматология"


def test_patch_branch_updates_request_frequency(client, auth_headers):
    response = client.patch(
        "/api/v1/branches/1",
        headers=auth_headers,
        json={"requestFrequencyDays": 30},
    )

    assert response.status_code == 200
    assert response.json()["requestFrequencyDays"] == 30


def test_patch_branch_updates_complaint_emails(client, auth_headers):
    emails = ["doctor@clinic.ru", "admin@clinic.ru"]
    response = client.patch(
        "/api/v1/branches/1",
        headers=auth_headers,
        json={"complaintEmails": emails},
    )

    assert response.status_code == 200
    assert response.json()["complaintEmails"] == emails


def test_patch_branch_updates_reminder_emails(client, auth_headers):
    emails = ["reminder@clinic.ru"]
    response = client.patch(
        "/api/v1/branches/1",
        headers=auth_headers,
        json={"reminderEmails": emails},
    )

    assert response.status_code == 200
    assert response.json()["reminderEmails"] == emails


# ── PATCH branch (partial) ───────────────────────────────────────────────────


def test_patch_branch_partial_update_preserves_other_fields(client, auth_headers):
    # Get original state
    original = client.get("/api/v1/branches", headers=auth_headers).json()["branches"][0]

    # Update only name
    response = client.patch(
        f"/api/v1/branches/{original['id']}",
        headers=auth_headers,
        json={"name": "Только название"},
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Только название"
    # Other fields should remain unchanged
    assert updated["city"] == original["city"]


# ── PATCH nonexistent ────────────────────────────────────────────────────────


def test_patch_nonexistent_branch_returns_404(client, auth_headers):
    response = client.patch(
        "/api/v1/branches/9999",
        headers=auth_headers,
        json={"name": "Ghost"},
    )

    assert response.status_code == 404
