"""
Pydantic schemas for feedback requests.
"""

from datetime import datetime
from typing import Literal

from pydantic import EmailStr, Field, field_validator

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


class RequestCreateResponse(APIModel):
    """Schema for created request response."""

    id: int
    branch_id: int
    client_name: str
    client_phone: str
    status: RequestStatusEnum
    request_link: str | None
    sent_at: datetime


# --- Public mini-app review flow (H4) ---------------------------------------


class MiniRatingRequest(APIModel):
    """Patient submits a star rating from the SMS mini-app."""

    rating: int = Field(ge=1, le=5)


class MiniPlatformLink(APIModel):
    """A real review platform link for the patient's branch."""

    platform: str
    url: str


class MiniRatingResponse(APIModel):
    """Server decides complaint-vs-publish; the client must not."""

    outcome: Literal["complaint", "publish"]
    # Populated only for the publish path (rating > 3); empty for complaints.
    platforms: list[MiniPlatformLink] = []


class MiniComplaintRequest(APIModel):
    """Patient's free-text complaint for a low rating."""

    message: str

    @field_validator("message")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("message must not be empty")
        return stripped


class MiniComplaintResponse(APIModel):
    ok: bool = True
