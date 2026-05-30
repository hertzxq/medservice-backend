"""Tests for the public patient review flow (H4).

The SERVER, not the client, decides complaint-vs-publish based on the rating,
and a low rating is persisted as an intercepted Complaint linked to the Request.
"""

import datetime

from app.models.branch import Branch
from app.models.complaint import Complaint
from app.models.request import Request, RequestStatusEnum


def _make_request(session_factory, *, token: str, branch_id: int = 1, platform_urls=None):
    db = session_factory()
    try:
        if platform_urls is not None:
            branch = db.query(Branch).filter(Branch.id == branch_id).first()
            branch.platform_urls = platform_urls
        req = Request(
            branch_id=branch_id,
            client_name="Тестовый Пациент",
            client_phone="+79990001122",
            client_email=None,
            status=RequestStatusEnum.SENT,
            public_token=token,
            sent_at=datetime.datetime.now(datetime.timezone.utc),
        )
        db.add(req)
        db.commit()
    finally:
        db.close()


def test_high_rating_returns_publish_with_platforms(client, session_factory):
    _make_request(
        session_factory,
        token="tok-high",
        platform_urls={"yandex_maps": "https://yandex.ru/maps/org/1", "2gis": ""},
    )
    r = client.post("/api/v1/public/requests/tok-high/rating", json={"rating": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"] == "publish"
    # only the non-empty platform url is returned
    assert body["platforms"] == [
        {"platform": "yandex_maps", "url": "https://yandex.ru/maps/org/1"}
    ]


def test_low_rating_returns_complaint_without_platforms(client, session_factory):
    _make_request(
        session_factory,
        token="tok-low",
        platform_urls={"yandex_maps": "https://yandex.ru/maps/org/1"},
    )
    r = client.post("/api/v1/public/requests/tok-low/rating", json={"rating": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"] == "complaint"
    assert body["platforms"] == []


def test_rating_persisted_and_status_advanced(client, session_factory):
    _make_request(session_factory, token="tok-rate")
    client.post("/api/v1/public/requests/tok-rate/rating", json={"rating": 3})

    db = session_factory()
    try:
        req = db.query(Request).filter(Request.public_token == "tok-rate").first()
        assert req.rating == 3
        assert req.status == RequestStatusEnum.RATED
    finally:
        db.close()


def test_submit_complaint_creates_intercepted_complaint(client, session_factory):
    _make_request(session_factory, token="tok-cmp")
    client.post("/api/v1/public/requests/tok-cmp/rating", json={"rating": 1})

    r = client.post(
        "/api/v1/public/requests/tok-cmp/complaint",
        json={"message": "Долго ждал приёма"},
    )
    assert r.status_code == 201

    db = session_factory()
    try:
        req = db.query(Request).filter(Request.public_token == "tok-cmp").first()
        assert req.status == RequestStatusEnum.COMPLAINT
        assert req.complaint_id is not None
        complaint = db.query(Complaint).filter(Complaint.id == req.complaint_id).first()
        assert complaint is not None
        assert complaint.rating == 1
        assert complaint.text == "Долго ждал приёма"
        assert complaint.intercepted is True
    finally:
        db.close()


def test_complaint_rejected_for_high_rating(client, session_factory):
    _make_request(session_factory, token="tok-cmp-high")
    client.post("/api/v1/public/requests/tok-cmp-high/rating", json={"rating": 5})
    r = client.post(
        "/api/v1/public/requests/tok-cmp-high/complaint",
        json={"message": "не должно пройти"},
    )
    assert r.status_code == 409


def test_complaint_empty_message_rejected(client, session_factory):
    _make_request(session_factory, token="tok-empty")
    client.post("/api/v1/public/requests/tok-empty/rating", json={"rating": 2})
    r = client.post(
        "/api/v1/public/requests/tok-empty/complaint", json={"message": "   "}
    )
    assert r.status_code == 422


def test_rating_out_of_range_rejected(client, session_factory):
    _make_request(session_factory, token="tok-bad")
    assert (
        client.post(
            "/api/v1/public/requests/tok-bad/rating", json={"rating": 0}
        ).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/public/requests/tok-bad/rating", json={"rating": 6}
        ).status_code
        == 422
    )


def test_unknown_token_returns_404(client):
    assert (
        client.post(
            "/api/v1/public/requests/nope/rating", json={"rating": 5}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/public/requests/nope/complaint", json={"message": "x"}
        ).status_code
        == 404
    )


def test_publish_confirm_sets_status(client, session_factory):
    _make_request(session_factory, token="tok-pub")
    client.post("/api/v1/public/requests/tok-pub/rating", json={"rating": 5})
    r = client.post("/api/v1/public/requests/tok-pub/published")
    assert r.status_code == 200

    db = session_factory()
    try:
        req = db.query(Request).filter(Request.public_token == "tok-pub").first()
        assert req.status == RequestStatusEnum.PUBLISHED
        assert req.published_at is not None
    finally:
        db.close()
