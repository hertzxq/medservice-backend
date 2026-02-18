"""
Pydantic schemas for branches.
"""

from pydantic import BaseModel


class BranchResponse(BaseModel):
    """Schema for branch response."""

    id: int
    name: str
    address: str | None
    city: str | None
    phone: str | None
    avg_rating: float
    nps_score: int

    class Config:
        from_attributes = True


class BranchesListResponse(BaseModel):
    """Schema for branches list response."""

    branches: list[BranchResponse]
    total: int
