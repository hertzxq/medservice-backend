"""
Pydantic schemas for branches.
"""

import datetime

from pydantic import ConfigDict

from app.schemas.common import APIModel


class BranchResponse(APIModel):
    """Schema for branch response."""

    id: int
    name: str
    address: str | None
    city: str | None
    phone: str | None
    timezone: str
    specialization: str
    request_frequency_days: int
    complaint_emails: list[str]
    reminder_emails: list[str]
    platform_urls: dict[str, str] = {}
    is_active: bool
    paid_until: datetime.date | None
    employees_count: int = 0
    avg_rating: float
    nps_score: int

    model_config = ConfigDict(from_attributes=True)


class BranchUpdate(APIModel):
    """Schema for updating branch settings"""

    name: str | None = None
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    timezone: str | None = None
    specialization: str | None = None
    request_frequency_days: int | None = None
    complaint_emails: list[str] | None = None
    reminder_emails: list[str] | None = None
    platform_urls: dict[str, str] | None = None
    is_active: bool | None = None
    paid_until: datetime.date | None = None


class BranchCreate(APIModel):
    """Schema for creating a new branch."""

    name: str
    address: str | None = None
    city: str | None = None
    phone: str | None = None
    timezone: str = "Московское время - UTC +3"
    specialization: str = "Офтальмология"
    request_frequency_days: int = 14
    paid_until: datetime.date | None = None


class BranchesListResponse(APIModel):
    """Schema for branches list response."""

    branches: list[BranchResponse]
    total: int
