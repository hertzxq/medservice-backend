"""
Reviews endpoints: get published reviews with filters.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.review import Review
from app.schemas.review import ReviewsListResponse, ReviewResponse

router = APIRouter(prefix="/reviews")


@router.get("", response_model=ReviewsListResponse)
async def get_reviews(
    branch_id: int | None = Query(None),
    platform: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get list of published reviews with filters."""
    query = db.query(Review).options(joinedload(Review.branch))

    if branch_id:
        query = query.filter(Review.branch_id == branch_id)
    if platform:
        query = query.filter(Review.platform == platform)

    total = query.count()
    reviews = query.order_by(Review.published_at.desc()).offset(offset).limit(limit).all()

    # Add branch name to response
    response_reviews = []
    for review in reviews:
        review_dict = ReviewResponse.model_validate(review).model_dump()
        review_dict["branch_name"] = review.branch.name if review.branch else None
        response_reviews.append(ReviewResponse(**review_dict))

    return ReviewsListResponse(reviews=response_reviews, total=total)
