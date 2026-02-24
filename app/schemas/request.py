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
