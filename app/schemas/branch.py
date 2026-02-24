"""
Pydantic schemas for branches.
"""

from app.schemas.common import APIModel


class BranchResponse(APIModel):
    """Schema for branch response."""

    id: int
    name: str
    address: str | None
    city: str | None
    phone: str | None
    avg_rating: float
    nps_score: int


class BranchesListResponse(APIModel):
    """Schema for branches list response."""

    branches: list[BranchResponse]
    total: int
