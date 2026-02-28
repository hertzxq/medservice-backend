"""
Branches endpoints: get list of branches.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.branch import Branch
from app.schemas.branch import BranchesListResponse, BranchResponse, BranchUpdate

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


@router.patch("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: int,
    branch_update: BranchUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update branch settings.

    Endpoint: PATCH /api/v1/branches/{branch_id}

    Returns:
        BranchResponse
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found",
        )

    update_data = branch_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(branch, key, value)

    db.commit()
    db.refresh(branch)

    return BranchResponse.model_validate(branch)
