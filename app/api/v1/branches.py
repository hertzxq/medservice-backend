"""
Branches endpoints: get list of branches.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_superuser
from app.models.employee import Employee
from app.models.user import User
from app.models.branch import Branch
from app.schemas.branch import BranchCreate, BranchesListResponse, BranchResponse, BranchUpdate

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

    counts = dict(
        db.query(Employee.branch_id, func.count(Employee.id))
        .group_by(Employee.branch_id)
        .all()
    )

    result = []
    for b in branches:
        data = BranchResponse.model_validate(b)
        data.employees_count = counts.get(b.id, 0)
        result.append(data)

    return BranchesListResponse(branches=result, total=len(result))


@router.post("", response_model=BranchResponse, status_code=status.HTTP_201_CREATED)
async def create_branch(
    payload: BranchCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Create a new branch (superuser only). Endpoint: POST /api/v1/branches"""
    branch = Branch(
        name=payload.name,
        address=payload.address,
        city=payload.city,
        phone=payload.phone,
        timezone=payload.timezone,
        specialization=payload.specialization,
        request_frequency_days=payload.request_frequency_days,
        paid_until=payload.paid_until,
        complaint_emails=[],
        reminder_emails=[],
        platform_urls={},
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)
    data = BranchResponse.model_validate(branch)
    data.employees_count = 0
    return data


@router.patch("/{branch_id}", response_model=BranchResponse)
async def update_branch(
    branch_id: int,
    branch_update: BranchUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
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


@router.delete("/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_branch(
    branch_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Delete a branch and all related data (superuser only).

    Endpoint: DELETE /api/v1/branches/{branch_id}

    Каскадно удаляет отзывы, жалобы, запросы, сотрудников и чёрный список
    благодаря `cascade='all, delete-orphan'` на модели `Branch`.
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Филиал не найден",
        )
    db.delete(branch)
    db.commit()
