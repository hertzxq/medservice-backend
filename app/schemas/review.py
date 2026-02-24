"""
Pydantic schemas for reviews.
"""

from datetime import datetime

from app.models.review import PlatformEnum
from app.schemas.common import APIModel


class ReviewResponse(APIModel):
    """Schema for review response."""

    id: int
    branch_id: int
    branch_name: str | None = None  # Joined from Branch
    reviewer_name: str | None
    rating: int
    text: str | None
    platform: PlatformEnum
    published_at: datetime | None


class ReviewsListResponse(APIModel):
    """Schema for reviews list response."""

    reviews: list[ReviewResponse]
    total: int
