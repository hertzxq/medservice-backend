"""
Service layer: saves parsed reviews into the backend PostgreSQL database.

Maps ParseResult → Review (SQLAlchemy) and handles deduplication.
"""

import logging
from datetime import datetime, timezone

from dateutil import parser as dateutil_parser
from sqlalchemy.orm import Session

from app.models.review import PlatformEnum, Review

from .models import ParseResult, ParsedReview

logger = logging.getLogger(__name__)

PLATFORM_MAP: dict[str, PlatformEnum] = {
    "yandex_maps": PlatformEnum.YANDEX_MAPS,
    "google_maps": PlatformEnum.GOOGLE_MAPS,
    "2gis": PlatformEnum.TWO_GIS,
    "prodoctorov": PlatformEnum.PRODOCTOROV,
}


def _parse_date(raw: str) -> datetime | None:
    """Best-effort conversion of a free-form date string → datetime."""
    if not raw:
        return None
    try:
        return dateutil_parser.parse(raw)
    except (ValueError, OverflowError):
        return None


def _build_review_text(r: ParsedReview) -> str:
    """Merge text + pros + cons into a single review text."""
    parts: list[str] = []
    if r.text:
        parts.append(r.text)
    if r.pros:
        parts.append(f"Понравилось: {r.pros}")
    if r.cons:
        parts.append(f"Не понравилось: {r.cons}")
    return "\n".join(parts) or ""


def save_parse_result(
    db: Session,
    result: ParseResult,
    branch_id: int,
) -> dict:
    """Persist parsed reviews for the given branch.

    Returns a summary dict with counts.
    """
    platform_enum = PLATFORM_MAP.get(result.platform, PlatformEnum.OTHER)

    inserted = 0
    skipped = 0

    for r in result.reviews:
        published_at = _parse_date(r.date)
        text = _build_review_text(r)

        # Clamp rating to backend-allowed range
        rating = max(1, min(5, r.rating))

        # Deduplication: same branch + platform + reviewer + date
        existing = (
            db.query(Review)
            .filter(
                Review.branch_id == branch_id,
                Review.platform == platform_enum,
                Review.reviewer_name == (r.author or None),
            )
        )
        if published_at:
            existing = existing.filter(Review.published_at == published_at)
        existing = existing.first()

        if existing:
            skipped += 1
            continue

        review = Review(
            branch_id=branch_id,
            reviewer_name=r.author or None,
            rating=rating,
            text=text or None,
            platform=platform_enum,
            published_at=published_at,
            response_text=r.response,
        )
        db.add(review)
        inserted += 1

    db.commit()

    summary = {
        "branch_id": branch_id,
        "platform": result.platform,
        "total_parsed": result.total_parsed,
        "inserted": inserted,
        "skipped_duplicates": skipped,
        "business_name": result.business_info.name,
    }
    logger.info(
        "Сохранение завершено: branch=%d, platform=%s, parsed=%d, inserted=%d, skipped=%d",
        branch_id, result.platform, result.total_parsed, inserted, skipped,
    )
    return summary
