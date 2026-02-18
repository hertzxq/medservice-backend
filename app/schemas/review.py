"""
Pydantic schemas for reviews.
"""

from datetime import datetime
from pydantic import BaseModel

from app.models.review import PlatformEnum


class ReviewResponse(BaseModel):
    """Schema for review response."""

    id: int
    branch_id: int
    branch_name: str | None = None  # Joined from Branch
    reviewer_name: str | None
    rating: float
    text: str | None
    platform: PlatformEnum
    published_at: datetime | None

    class Config:
        from_attributes = True


class ReviewsListResponse(BaseModel):
    """Schema for reviews list response."""

    reviews: list[ReviewResponse]
    total: int
