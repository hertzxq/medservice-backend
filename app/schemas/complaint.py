"""
Pydantic schemas for complaints.
"""

from datetime import datetime

from app.schemas.common import APIModel


class ComplaintResponse(APIModel):
    """Schema for complaint response."""

    id: int
    branch_id: int
    branch_name: str | None = None  # Joined from Branch
    client_name: str | None
    client_phone: str | None
    rating: int
    text: str
    intercepted: bool
    resolved: bool
    created_at: datetime


class ComplaintsListResponse(APIModel):
    """Schema for complaints list response."""

    complaints: list[ComplaintResponse]
    total: int


class ComplaintUpdateRequest(APIModel):
    """Schema for updating complaint (mark as resolved)."""

    resolved: bool
