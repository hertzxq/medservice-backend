"""
Pydantic schemas for analytics endpoints.
"""

from datetime import datetime

from app.models.review import PlatformEnum
from app.schemas.common import APIModel


class AnalyticsResponse(APIModel):
    """
    Schema for single branch analytics.
    Endpoint: GET /api/v1/analytics/{branch_id}
    """

    sent: int  # Кол-во отправленных запросов
    reviews: int  # Новые отзывы
    complaints: int  # Жалобы
    avg_rating: float  # Средний рейтинг (0.0 - 5.0)


class BranchAnalyticsRow(APIModel):
    """
    Schema for single row in branches analytics table.
    Endpoint: GET /api/v1/analytics/branches
    """

    id: int
    name: str
    requests: int  # Отправленные запросы
    new_reviews: int  # Новые отзывы
    intercepted_complaints: int  # Перехваченные жалобы
    avg_rating: float  # Средний рейтинг
    nps: int  # Net Promoter Score


class BranchesAnalyticsResponse(APIModel):
    """
    Schema for branches analytics response.
    Endpoint: GET /api/v1/analytics/branches
    """

    rows: list[BranchAnalyticsRow]


class PlatformAnalyticsRow(APIModel):
    """Platform-level metrics for analytics dashboard."""

    platform: PlatformEnum
    label: str
    enabled: bool
    rating: float
    reviews: int
    total_reviews: int
    total_negative: int
    negative_percent: float


class SatisfactionRow(APIModel):
    """Ratings distribution (1-5 stars)."""

    stars: int
    count: int
    percent: float


class NpsSeriesPoint(APIModel):
    """Single point in NPS chart."""

    index: int
    nps: int
    bucket_start: datetime
    bucket_end: datetime


class EmployeeScoreRow(APIModel):
    """Employee score card inferred from review mentions."""

    name: str
    ratings_count: int
    five_star_percent: float
    four_star_percent: float
    three_star_percent: float
    two_star_percent: float
    one_star_percent: float
    avg_rating: float


class AnalyticsReviewFeedItem(APIModel):
    """Compact review item for analytics right panel."""

    id: int
    reviewer_name: str | None
    rating: int
    text: str | None
    platform: PlatformEnum
    platform_label: str
    published_at: datetime | None


class AnalyticsDashboardResponse(APIModel):
    """Extended analytics payload for dashboard UI."""

    sent: int
    reviews: int
    complaints: int
    avg_rating: float
    period_start: datetime
    period_end: datetime
    platforms: list[PlatformAnalyticsRow]
    satisfaction: list[SatisfactionRow]
    nps_small: list[NpsSeriesPoint]
    nps_large: list[NpsSeriesPoint]
    employees: list[EmployeeScoreRow]
    recent_reviews: list[AnalyticsReviewFeedItem]
