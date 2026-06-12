"""
Reviews endpoints: get published reviews with filters.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import (
    accessible_branch_ids,
    get_current_user,
    require_branch_access,
)
from app.models.user import User
from app.models.review import PlatformEnum, Review
from app.schemas.review import ReviewsListResponse, ReviewResponse

router = APIRouter(prefix="/reviews")


def get_period_start(period: str) -> datetime:
    """Calculate the start datetime for supported filters."""
    now = datetime.utcnow()
    if period == "week":
        return now - timedelta(days=7)
    if period == "30":
        return now - timedelta(days=30)
    if period == "90":
        return now - timedelta(days=90)
    return now - timedelta(days=365)


@router.get("", response_model=ReviewsListResponse)
def get_reviews(
    branch_id: int | None = Query(None, alias="branchId"),
    branch_id_legacy: int | None = Query(None, alias="branch_id", include_in_schema=False),
    platform: PlatformEnum | None = Query(None),
    rating_min: float | None = Query(None, alias="ratingMin", ge=1.0, le=5.0),
    rating_min_legacy: float | None = Query(None, alias="rating_min", ge=1.0, le=5.0, include_in_schema=False),
    rating_max: float | None = Query(None, alias="ratingMax", ge=1.0, le=5.0),
    rating_max_legacy: float | None = Query(None, alias="rating_max", ge=1.0, le=5.0, include_in_schema=False),
    period: str | None = Query(None, pattern="^(week|30|90|year)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of published reviews with filters."""
    branch_filter = branch_id if branch_id is not None else branch_id_legacy
    min_rating_filter = rating_min if rating_min is not None else rating_min_legacy
    max_rating_filter = rating_max if rating_max is not None else rating_max_legacy

    if (
        min_rating_filter is not None
        and max_rating_filter is not None
        and min_rating_filter > max_rating_filter
    ):
        raise HTTPException(status_code=422, detail="rating_min не может быть больше rating_max")

    query = db.query(Review).options(joinedload(Review.branch))

    # Multi-tenancy: a specific branch must be accessible; without one, a
    # non-superuser is implicitly scoped to their assigned branches.
    if branch_filter is not None:
        require_branch_access(branch_filter, current_user, db)
        query = query.filter(Review.branch_id == branch_filter)
    else:
        allowed = accessible_branch_ids(current_user)
        if allowed is not None:
            query = query.filter(Review.branch_id.in_(allowed))
    if platform:
        query = query.filter(Review.platform == platform)
    if min_rating_filter is not None:
        query = query.filter(Review.rating >= min_rating_filter)
    if max_rating_filter is not None:
        query = query.filter(Review.rating <= max_rating_filter)
    if period:
        query = query.filter(Review.published_at >= get_period_start(period))

    total = query.count()
    reviews = query.order_by(Review.published_at.desc()).offset(offset).limit(limit).all()

    # Add branch name to response
    response_reviews = []
    for review in reviews:
        review_dict = ReviewResponse.model_validate(review).model_dump()
        review_dict["branch_name"] = review.branch.name if review.branch else None
        response_reviews.append(ReviewResponse(**review_dict))

    return ReviewsListResponse(reviews=response_reviews, total=total)
