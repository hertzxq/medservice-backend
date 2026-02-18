"""
Pydantic schemas for complaints.
"""

from datetime import datetime
from pydantic import BaseModel


class ComplaintResponse(BaseModel):
    """Schema for complaint response."""

    id: int
    branch_id: int
    branch_name: str | None = None  # Joined from Branch
    client_name: str | None
    client_phone: str | None
    rating: float
    text: str
    intercepted: bool
    resolved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ComplaintsListResponse(BaseModel):
    """Schema for complaints list response."""

    complaints: list[ComplaintResponse]
    total: int


class ComplaintUpdateRequest(BaseModel):
    """Schema for updating complaint (mark as resolved)."""

    resolved: bool
