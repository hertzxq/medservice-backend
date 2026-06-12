"""
Authentication endpoints: login, forgot-password, me.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.dependencies import get_current_user
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/auth")

# Precomputed hash to verify against when the username doesn't exist, so the
# response time of a missing user matches that of a wrong password — closing
# the username-enumeration timing oracle.
_DUMMY_PASSWORD_HASH = get_password_hash("constant-time-dummy-password")


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT access token.

    Args:
        request: LoginRequest with username and password
        db: Database session

    Returns:
        LoginResponse with access_token and user data

    Raises:
        HTTPException 401: Invalid credentials or inactive user
    """
    user = db.query(User).filter(User.username == request.username).first()

    # Always run a bcrypt verify (against a dummy hash when the user is missing)
    # so timing doesn't reveal whether the username exists.
    password_ok = verify_password(
        request.password, user.hashed_password if user else _DUMMY_PASSWORD_HASH
    )
    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    # jose/jwt expects "sub" claim as string; int subject breaks decode validation.
    access_token = create_access_token(data={"sub": str(user.id)})

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest, db: Session = Depends(get_db)
):
    """
    Send password reset link to user's email.

    ⚠️ ЗАГЛУШКА: Email НЕ отправляется реально, только mock ответ.
    Всегда возвращает 200 OK, чтобы предотвратить перечисление пользователей.

    Args:
        request: ForgotPasswordRequest with email
        db: Database session

    Returns:
        Success message (always 200 OK)
    """
    # Проверяем пользователя, но НЕ раскрываем существование email
    user = db.query(User).filter(User.email == request.email).first()

    if user:
        # TODO: Отправить email с ссылкой для восстановления
        pass

    # Всегда возвращаем одинаковый ответ (предотвращение user enumeration)
    return {"message": "Если указанный email зарегистрирован, на него отправлена ссылка для восстановления пароля"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user.

    Args:
        current_user: Current user from JWT token

    Returns:
        UserResponse with current user data
    """
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update current user profile (full_name, email, phone, role, password)."""
    update_data = payload.model_dump(exclude_unset=True)

    new_password = update_data.pop("password", None)

    new_email = update_data.get("email")
    if new_email and new_email != current_user.email:
        taken = (
            db.query(User)
            .filter(User.email == new_email, User.id != current_user.id)
            .first()
        )
        if taken:
            raise HTTPException(
                status_code=400,
                detail="Пользователь с таким email уже существует",
            )

    for key, value in update_data.items():
        setattr(current_user, key, value)

    if new_password:
        current_user.hashed_password = get_password_hash(new_password)

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)
