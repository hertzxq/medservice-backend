"""
Blacklist endpoints: CRUD for users excluded from review requests.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.blacklist import BlacklistUser
from app.models.branch import Branch
from app.schemas.blacklist import BlacklistUserCreate, BlacklistUserUpdate, BlacklistUserResponse

router = APIRouter(prefix="/blacklist")


@router.get("", response_model=list[BlacklistUserResponse])
async def get_blacklist(
    branch_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of blacklisted users for a branch.
    """
    users = db.query(BlacklistUser).filter(BlacklistUser.branch_id == branch_id).all()
    return [BlacklistUserResponse.model_validate(u) for u in users]


@router.post("", response_model=BlacklistUserResponse, status_code=status.HTTP_201_CREATED)
async def create_blacklist_user(
    branch_id: int,
    user_in: BlacklistUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add a new user to the blacklist for a branch.
    Доступно любому авторизованному пользователю в рамках выбранного филиала.
    """
    branch = db.query(Branch).filter(Branch.id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    blacklist_user = BlacklistUser(
        branch_id=branch_id,
        last_name=user_in.last_name,
        first_name=user_in.first_name,
        phone=user_in.phone,
        reason=user_in.reason,
    )
    db.add(blacklist_user)
    db.commit()
    db.refresh(blacklist_user)
    return BlacklistUserResponse.model_validate(blacklist_user)


@router.patch("/{user_id}", response_model=BlacklistUserResponse)
async def update_blacklist_user(
    user_id: int,
    user_update: BlacklistUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update blacklisted user details.
    Доступно любому авторизованному пользователю.
    """
    user = db.query(BlacklistUser).filter(BlacklistUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in blacklist")

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return BlacklistUserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_blacklist_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Remove a user from the blacklist.
    Доступно любому авторизованному пользователю.
    """
    user = db.query(BlacklistUser).filter(BlacklistUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found in blacklist")

    db.delete(user)
    db.commit()
    return None
