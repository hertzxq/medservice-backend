"""
Branches endpoints: get list of branches.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.branch import Branch
from app.schemas.branch import BranchesListResponse, BranchResponse

router = APIRouter(prefix="/branches")


@router.get("", response_model=BranchesListResponse)
async def get_branches(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of all branches.

    Endpoint: GET /api/v1/branches

    Returns:
        BranchesListResponse with branches list and total count
    """
    branches = db.query(Branch).all()

    return BranchesListResponse(
        branches=[BranchResponse.model_validate(b) for b in branches],
        total=len(branches),
    )
