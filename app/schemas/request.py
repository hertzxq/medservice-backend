"""
Pydantic schemas for feedback requests.
"""

from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.models.request import RequestStatusEnum


class RequestResponse(BaseModel):
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

    class Config:
        from_attributes = True


class RequestsListResponse(BaseModel):
    """Schema for requests list response."""

    requests: list[RequestResponse]
    total: int


class RequestCreateRequest(BaseModel):
    """Schema for creating new feedback request."""

    branch_id: int
    client_name: str
    client_phone: str
    client_email: EmailStr | None = None


class RequestCreateResponse(BaseModel):
    """Schema for created request response."""

    id: int
    branch_id: int
    client_name: str
    client_phone: str
    status: RequestStatusEnum
    request_link: str | None
    sent_at: datetime

    class Config:
        from_attributes = True
