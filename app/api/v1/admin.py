"""
Admin endpoints: user management (superuser only).
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import EmailStr, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_superuser
from app.core.security import create_access_token, get_password_hash
from app.models.branch import Branch
from app.models.user import User
from app.schemas.auth import LoginResponse, UserResponse
from app.schemas.common import APIModel

router = APIRouter(prefix="/admin")


class AdminUserCreate(APIModel):
    username: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    full_name: str | None = None
    phone: str | None = None
    role: str | None = None
    is_superuser: bool = False
    # Branches this (non-superuser) user may access. Superusers ignore it.
    branch_ids: list[int] = []


class AdminUserUpdate(APIModel):
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    # When provided, REPLACES the user's branch assignments.
    branch_ids: list[int] | None = None


def _resolve_branches(db: Session, branch_ids: list[int]) -> list[Branch]:
    """Validate that every id exists; return the Branch rows."""
    if not branch_ids:
        return []
    branches = db.query(Branch).filter(Branch.id.in_(branch_ids)).all()
    found = {b.id for b in branches}
    missing = [bid for bid in branch_ids if bid not in found]
    if missing:
        raise HTTPException(status_code=400, detail=f"Филиалы не найдены: {missing}")
    return branches


def _admin_user_response(user: User) -> UserResponse:
    """UserResponse with the user's assigned branch ids attached."""
    resp = UserResponse.model_validate(user)
    resp.branch_ids = [b.id for b in user.branches]
    return resp


@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_superuser),
):
    """List all users (superuser only)."""
    return [_admin_user_response(u) for u in db.query(User).all()]


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
    user.branches = _resolve_branches(db, payload.branch_ids)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _admin_user_response(user)


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

    data = payload.model_dump(exclude_unset=True)
    branch_ids = data.pop("branch_ids", None)  # relationship, not a column
    for key, value in data.items():
        setattr(user, key, value)
    if branch_ids is not None:
        user.branches = _resolve_branches(db, branch_ids)

    db.commit()
    db.refresh(user)
    return _admin_user_response(user)


IMPERSONATION_TTL = timedelta(minutes=30)


@router.post("/users/{user_id}/impersonate", response_model=LoginResponse)
async def impersonate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superuser),
):
    """Issue a short-lived, restricted access token for another user (superuser only).

    Lets the admin open the regular cabinet as that user. The token is marked
    `typ=impersonation` and carries `imp` (the admin's id) for traceability; it
    is rejected on superuser-gated routes (see get_current_superuser) so it
    cannot be used to re-impersonate or reach the admin panel, and it expires
    after a short window instead of inheriting the full login lifetime.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Пользователь неактивен")
    # Don't let impersonation be used to step into ANOTHER superuser's account.
    if user.is_superuser and user.id != current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Нельзя войти в аккаунт другого администратора",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "imp": current_user.id, "typ": "impersonation"},
        expires_delta=IMPERSONATION_TTL,
    )
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


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
