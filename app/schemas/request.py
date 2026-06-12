"""
Pydantic schemas for feedback requests.
"""

from datetime import datetime
from pydantic import EmailStr

from app.models.request import RequestStatusEnum
from app.schemas.common import APIModel


class RequestResponse(APIModel):
    """Schema for request response."""

    id: int
    branch_id: int
    branch_name: str | None = None  # Joined from Branch
    client_name: str
    client_phone: str
    status: RequestStatusEnum
    sent_at: datetime
    opened_at: datetime | None
    rated_at: datetime | None
    published_at: datetime | None
    
    # Retrieved from related entities
    rating: int | None = None
    platform: str | None = None
    review_url: str | None = None

    # Review-publish verification (publish path)
    verification_status: str | None = None  # pending | verified | not_found
    verified_at: datetime | None = None
    review_claim_name: str | None = None


class RequestsListResponse(APIModel):
    """Schema for requests list response."""

    requests: list[RequestResponse]
    total: int


class RequestCreateRequest(APIModel):
    """Schema for creating new feedback request."""

    branch_id: int
    client_name: str
    client_phone: str
    client_email: EmailStr | None = None


class SmsResult(APIModel):
    """Outcome of an sms.ru send attempt (test or live)."""

    ok: bool
    test: bool = False
    sms_id: str | None = None
    cost: float | None = None
    balance: float | None = None
    error: str | None = None
    skipped_reason: str | None = None  # set when SMS was intentionally not sent


class RequestCreateResponse(APIModel):
    """Schema for created request response."""

    id: int
    branch_id: int
    client_name: str
    client_phone: str
    status: RequestStatusEnum
    request_link: str | None  # full review URL sent to the patient
    sent_at: datetime
    sms: SmsResult | None = None


class TestSmsRequest(APIModel):
    """Schema for the 'send test SMS' action from branch settings.

    `template` lets the UI test an unsaved draft; falls back to the branch's
    saved template when omitted.
    """

    phone: str
    template: str | None = None
