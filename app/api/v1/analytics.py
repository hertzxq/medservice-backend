"""
Analytics endpoints: main feature of the application.
"""

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.branch import Branch
from app.models.review import Review
from app.models.complaint import Complaint
from app.models.request import Request
from app.schemas.analytics import (
    AnalyticsResponse,
    BranchesAnalyticsResponse,
    BranchAnalyticsRow,
)

router = APIRouter(prefix="/analytics")


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


@router.get("/{branch_id}", response_model=AnalyticsResponse)
async def get_branch_analytics(
    branch_id: int,
    period: str = Query("30", regex="^(week|30|90|year)$"),
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

    start_date, end_date = get_period_dates(period)

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


@router.get("/branches", response_model=BranchesAnalyticsResponse)
async def get_branches_analytics(
    period: str = Query("30", regex="^(week|30|90|year)$"),
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
    start_date, end_date = get_period_dates(period)

    branches = db.query(Branch).all()
    rows = []

    for branch in branches:
        # Count requests
        requests_count = (
            db.query(func.count(Request.id))
            .filter(Request.branch_id == branch.id, Request.sent_at >= start_date)
            .scalar()
        )

        # Count reviews
        new_reviews = (
            db.query(func.count(Review.id))
            .filter(Review.branch_id == branch.id, Review.published_at >= start_date)
            .scalar()
        )

        # Count complaints
        intercepted_complaints = (
            db.query(func.count(Complaint.id))
            .filter(Complaint.branch_id == branch.id, Complaint.created_at >= start_date)
            .scalar()
        )

        # Calculate average rating
        avg_rating = (
            db.query(func.avg(Review.rating))
            .filter(Review.branch_id == branch.id, Review.published_at >= start_date)
            .scalar()
        )

        rows.append(
            BranchAnalyticsRow(
                id=branch.id,
                name=branch.name,
                requests=requests_count or 0,
                new_reviews=new_reviews or 0,
                intercepted_complaints=intercepted_complaints or 0,
                avg_rating=round(float(avg_rating or 0), 1),
                nps=branch.nps_score,
            )
        )

    return BranchesAnalyticsResponse(rows=rows)
