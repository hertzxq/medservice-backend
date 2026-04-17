"""
Admin endpoints: user management (superuser only).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_superuser
from app.core.security import get_password_hash
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.common import APIModel

router = APIRouter(prefix="/admin")


class AdminUserCreate(APIModel):
    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    phone: str | None = None
    role: str | None = None
    is_superuser: bool = False


class AdminUserUpdate(APIModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """List all users (superuser only)."""
    return [UserResponse.model_validate(u) for u in db.query(User).all()]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Create a new user (superuser only)."""
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким логином уже существует")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
        is_superuser=payload.is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """Update a user (superuser only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Delete a user (superuser only). Cannot delete yourself."""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить свой аккаунт")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    db.delete(user)
    db.commit()
