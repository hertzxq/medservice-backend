"""
Analytics endpoints: main feature of the application.
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.branch import Branch
from app.models.complaint import Complaint
from app.models.request import Request
from app.models.review import PlatformEnum, Review
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsDashboardResponse,
    AnalyticsResponse,
    AnalyticsReviewFeedItem,
    BranchAnalyticsRow,
    BranchesAnalyticsResponse,
    EmployeeScoreRow,
    NpsSeriesPoint,
    PlatformAnalyticsRow,
    SatisfactionRow,
)

router = APIRouter(prefix="/analytics")

PLATFORM_ORDER = [
    PlatformEnum.YANDEX_MAPS,
    PlatformEnum.GOOGLE_MAPS,
    PlatformEnum.TWO_GIS,
    PlatformEnum.PRODOCTOROV,
    PlatformEnum.NAPOPRAVKU,
]

PLATFORM_LABELS = {
    PlatformEnum.YANDEX_MAPS: "Яндекс.Карты",
    PlatformEnum.GOOGLE_MAPS: "Google Maps",
    PlatformEnum.TWO_GIS: "2GIS",
    PlatformEnum.PRODOCTOROV: "ПроДокторов",
    PlatformEnum.NAPOPRAVKU: "НаПоправку",
    PlatformEnum.OTHER: "Другое",
}

ENABLED_PLATFORMS = {
    PlatformEnum.YANDEX_MAPS,
    PlatformEnum.GOOGLE_MAPS,
    PlatformEnum.TWO_GIS,
}

EMPLOYEE_NAME_PATTERN = re.compile(
    r"\b[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+){1,2}\b"
)


def get_period_dates(period: str) -> tuple[datetime, datetime]:
    """
    Calculate start and end dates for period.

    Args:
        period: "week" | "30" | "90" | "year"

    Returns:
        (start_date, end_date) tuple
    """
    end_date = datetime.utcnow()

    if period == "week":
        start_date = end_date - timedelta(days=7)
    elif period == "30":
        start_date = end_date - timedelta(days=30)
    elif period == "90":
        start_date = end_date - timedelta(days=90)
    elif period == "year":
        start_date = end_date - timedelta(days=365)
    else:
        start_date = end_date - timedelta(days=30)  # Default: 30 days

    return start_date, end_date


def to_utc_naive(dt: datetime) -> datetime:
    """Normalize datetime to naive UTC for safe cross-source comparisons."""
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def clamp_star(rating: float) -> int:
    """Normalize rating into integer star bucket [1..5]."""
    return max(1, min(5, int(round(rating))))


def is_promoter(rating: float) -> bool:
    """Map 5-star rating to NPS promoter band."""
    return clamp_star(rating) == 5


def is_detractor(rating: float) -> bool:
    """Map 5-star rating to NPS detractor band."""
    return clamp_star(rating) <= 3


def build_satisfaction_rows(period_reviews: list[Review]) -> list[SatisfactionRow]:
    """Build rating distribution rows from 5 to 1 stars."""
    counts = {stars: 0 for stars in range(1, 6)}

    for review in period_reviews:
        counts[clamp_star(review.rating)] += 1

    total = len(period_reviews)
    rows: list[SatisfactionRow] = []
    for stars in range(5, 0, -1):
        count = counts[stars]
        percent = round((count / total) * 100, 1) if total else 0.0
        rows.append(SatisfactionRow(stars=stars, count=count, percent=percent))

    return rows


def build_nps_series(
    period_reviews: list[Review],
    start_date: datetime,
    end_date: datetime,
    points: int,
) -> list[NpsSeriesPoint]:
    """Build an NPS timeline with fixed number of buckets."""
    if points <= 0:
        return []

    start_date = to_utc_naive(start_date)
    end_date = to_utc_naive(end_date)
    total_seconds = max((end_date - start_date).total_seconds(), 1.0)
    bucket_size = total_seconds / points

    buckets = [{"total": 0, "promoters": 0, "detractors": 0} for _ in range(points)]

    for review in period_reviews:
        if not review.published_at:
            continue

        timestamp = to_utc_naive(review.published_at)
        position = (timestamp - start_date).total_seconds()
        if position < 0 or position > total_seconds:
            continue

        index = min(points - 1, int(position / bucket_size))
        bucket = buckets[index]
        bucket["total"] += 1
        if is_promoter(review.rating):
            bucket["promoters"] += 1
        if is_detractor(review.rating):
            bucket["detractors"] += 1

    result: list[NpsSeriesPoint] = []
    for index, bucket in enumerate(buckets):
        total = bucket["total"]
        if total == 0:
            nps_value = 0
        else:
            promoters_pct = bucket["promoters"] / total
            detractors_pct = bucket["detractors"] / total
            nps_value = int(round((promoters_pct - detractors_pct) * 100))
        result.append(NpsSeriesPoint(index=index, nps=nps_value))

    return result


def build_platform_rows(
    all_reviews: list[Review],
    period_start: datetime,
    period_end: datetime,
) -> list[PlatformAnalyticsRow]:
    """Build platform table rows (period + all-time metrics)."""
    period_start = to_utc_naive(period_start)
    period_end = to_utc_naive(period_end)
    grouped_all: dict[PlatformEnum, list[Review]] = defaultdict(list)
    grouped_period: dict[PlatformEnum, list[Review]] = defaultdict(list)

    for review in all_reviews:
        grouped_all[review.platform].append(review)
        if review.published_at:
            published_at = to_utc_naive(review.published_at)
            if period_start <= published_at <= period_end:
                grouped_period[review.platform].append(review)

    rows: list[PlatformAnalyticsRow] = []

    for platform in PLATFORM_ORDER:
        all_items = grouped_all.get(platform, [])
        period_items = grouped_period.get(platform, [])

        rating_source = period_items if period_items else all_items
        if rating_source:
            rating = round(sum(item.rating for item in rating_source) / len(rating_source), 1)
        else:
            rating = 0.0

        total_reviews = len(all_items)
        total_negative = sum(1 for item in all_items if clamp_star(item.rating) <= 3)
        negative_percent = (
            round((total_negative / total_reviews) * 100, 1) if total_reviews else 0.0
        )

        rows.append(
            PlatformAnalyticsRow(
                platform=platform,
                label=PLATFORM_LABELS[platform],
                enabled=platform in ENABLED_PLATFORMS,
                rating=rating,
                reviews=len(period_items),
                total_reviews=total_reviews,
                total_negative=total_negative,
                negative_percent=negative_percent,
            )
        )

    return rows


def extract_employee_mentions(text: str | None) -> list[str]:
    """Extract likely employee full names from review text."""
    if not text:
        return []

    names = []
    for match in EMPLOYEE_NAME_PATTERN.finditer(text):
        name = " ".join(match.group(0).split())
        if len(name.split()) >= 2:
            names.append(name)

    return names


def build_employee_rows(period_reviews: list[Review]) -> list[EmployeeScoreRow]:
    """Infer employee score table from names mentioned in review text."""
    stats: dict[str, dict[str, float | int | dict[int, int]]] = {}

    for review in period_reviews:
        names = extract_employee_mentions(review.text)
        if not names:
            continue

        stars = clamp_star(review.rating)
        unique_names = list(dict.fromkeys(names))

        for name in unique_names[:3]:
            if name not in stats:
                stats[name] = {
                    "count": 0,
                    "rating_sum": 0.0,
                    "buckets": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
                }

            item = stats[name]
            item["count"] = int(item["count"]) + 1
            item["rating_sum"] = float(item["rating_sum"]) + review.rating
            buckets = item["buckets"]
            if isinstance(buckets, dict):
                buckets[stars] += 1

    if not stats:
        return []

    sorted_items = sorted(
        stats.items(),
        key=lambda entry: (int(entry[1]["count"]), float(entry[1]["rating_sum"])),
        reverse=True,
    )

    rows: list[EmployeeScoreRow] = []
    for name, item in sorted_items[:5]:
        count = int(item["count"])
        rating_sum = float(item["rating_sum"])
        buckets = item["buckets"]
        if not isinstance(buckets, dict):
            continue

        def pct(stars: int) -> float:
            value = buckets.get(stars, 0)
            return round((value / count) * 100, 1) if count else 0.0

        rows.append(
            EmployeeScoreRow(
                name=name,
                ratings_count=count,
                five_star_percent=pct(5),
                four_star_percent=pct(4),
                three_star_percent=pct(3),
                two_star_percent=pct(2),
                one_star_percent=pct(1),
                avg_rating=round(rating_sum / count, 1) if count else 0.0,
            )
        )

    return rows


@router.get("/branches", response_model=BranchesAnalyticsResponse)
def get_branches_analytics(
    period: str = Query("30", pattern="^(week|30|90|year)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get analytics for all branches (table view).

    Endpoint: GET /api/v1/analytics/branches?period=30

    Args:
        period: "week" | "30" | "90" | "year"
        db: Database session
        current_user: Current authenticated user

    Returns:
        BranchesAnalyticsResponse with rows for each branch
    """
    start_date, _ = get_period_dates(period)

    # Оптимизированный запрос: один SQL вместо N+1
    from sqlalchemy import outerjoin, case, literal_column
    from sqlalchemy.sql import expression

    # Подзапросы для агрегации
    requests_sub = (
        db.query(
            Request.branch_id,
            func.count(Request.id).label("requests_count"),
        )
        .filter(Request.sent_at >= start_date)
        .group_by(Request.branch_id)
        .subquery()
    )

    reviews_sub = (
        db.query(
            Review.branch_id,
            func.count(Review.id).label("reviews_count"),
            func.avg(Review.rating).label("avg_rating"),
        )
        .filter(Review.published_at >= start_date)
        .group_by(Review.branch_id)
        .subquery()
    )

    complaints_sub = (
        db.query(
            Complaint.branch_id,
            func.count(Complaint.id).label("complaints_count"),
        )
        .filter(Complaint.created_at >= start_date)
        .group_by(Complaint.branch_id)
        .subquery()
    )

    results = (
        db.query(
            Branch.id,
            Branch.name,
            Branch.nps_score,
            func.coalesce(requests_sub.c.requests_count, 0).label("requests"),
            func.coalesce(reviews_sub.c.reviews_count, 0).label("new_reviews"),
            func.coalesce(complaints_sub.c.complaints_count, 0).label("intercepted_complaints"),
            func.coalesce(reviews_sub.c.avg_rating, 0.0).label("avg_rating"),
        )
        .outerjoin(requests_sub, Branch.id == requests_sub.c.branch_id)
        .outerjoin(reviews_sub, Branch.id == reviews_sub.c.branch_id)
        .outerjoin(complaints_sub, Branch.id == complaints_sub.c.branch_id)
        .all()
    )

    rows = [
        BranchAnalyticsRow(
            id=row.id,
            name=row.name,
            requests=row.requests,
            new_reviews=row.new_reviews,
            intercepted_complaints=row.intercepted_complaints,
            avg_rating=round(float(row.avg_rating), 1),
            nps=row.nps_score,
        )
        for row in results
    ]

    return BranchesAnalyticsResponse(rows=rows)


@router.get("/{branch_id}/dashboard", response_model=AnalyticsDashboardResponse)
def get_branch_analytics_dashboard(
    branch_id: int,
    period: str = Query("30", pattern="^(week|30|90|year)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get extended analytics payload for dashboard widgets."""
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    start_date, end_date = get_period_dates(period)

    sent = (
        db.query(func.count(Request.id))
        .filter(Request.branch_id == branch_id, Request.sent_at >= start_date)
        .scalar()
    )
    complaints = (
        db.query(func.count(Complaint.id))
        .filter(Complaint.branch_id == branch_id, Complaint.created_at >= start_date)
        .scalar()
    )

    all_reviews = (
        db.query(Review)
        .filter(Review.branch_id == branch_id)
        .order_by(Review.published_at.desc())
        .all()
    )

    period_reviews = []
    for review in all_reviews:
        if not review.published_at:
            continue
        published_at = to_utc_naive(review.published_at)
        if start_date <= published_at <= end_date:
            period_reviews.append(review)

    reviews_count = len(period_reviews)
    avg_rating = (
        round(sum(review.rating for review in period_reviews) / reviews_count, 1)
        if reviews_count
        else 0.0
    )

    platform_rows = build_platform_rows(all_reviews, start_date, end_date)
    satisfaction_rows = build_satisfaction_rows(period_reviews)
    nps_small = build_nps_series(period_reviews, start_date, end_date, points=12)
    nps_large = build_nps_series(period_reviews, start_date, end_date, points=30)
    employees = build_employee_rows(period_reviews)

    recent_reviews = [
        AnalyticsReviewFeedItem(
            id=review.id,
            reviewer_name=review.reviewer_name,
            rating=review.rating,
            text=review.text,
            platform=review.platform,
            platform_label=PLATFORM_LABELS.get(review.platform, "Другое"),
            published_at=review.published_at,
        )
        for review in period_reviews[:12]
    ]

    return AnalyticsDashboardResponse(
        sent=sent or 0,
        reviews=reviews_count,
        complaints=complaints or 0,
        avg_rating=avg_rating,
        period_start=start_date,
        period_end=end_date,
        platforms=platform_rows,
        satisfaction=satisfaction_rows,
        nps_small=nps_small,
        nps_large=nps_large,
        employees=employees,
        recent_reviews=recent_reviews,
    )


@router.get("/{branch_id}", response_model=AnalyticsResponse)
def get_branch_analytics(
    branch_id: int,
    period: str = Query("30", pattern="^(week|30|90|year)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get analytics for a specific branch.

    Endpoint: GET /api/v1/analytics/{branch_id}?period=30

    Args:
        branch_id: Branch ID
        period: "week" | "30" | "90" | "year"
        db: Database session
        current_user: Current authenticated user

    Returns:
        AnalyticsResponse with sent, reviews, complaints, avgRating
    """
    # Check if branch exists
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Филиал не найден")

    start_date, _ = get_period_dates(period)

    # Count sent requests
    sent = (
        db.query(func.count(Request.id))
        .filter(Request.branch_id == branch_id, Request.sent_at >= start_date)
        .scalar()
    )

    # Count reviews
    reviews = (
        db.query(func.count(Review.id))
        .filter(Review.branch_id == branch_id, Review.published_at >= start_date)
        .scalar()
    )

    # Count complaints
    complaints = (
        db.query(func.count(Complaint.id))
        .filter(Complaint.branch_id == branch_id, Complaint.created_at >= start_date)
        .scalar()
    )

    # Calculate average rating
    avg_rating = (
        db.query(func.avg(Review.rating))
        .filter(Review.branch_id == branch_id, Review.published_at >= start_date)
        .scalar()
    )

    return AnalyticsResponse(
        sent=sent or 0,
        reviews=reviews or 0,
        complaints=complaints or 0,
        avg_rating=round(float(avg_rating or 0), 1),
    )
