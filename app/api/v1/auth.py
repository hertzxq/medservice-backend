"""
Authentication endpoints: login, forgot-password, me.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import verify_password, create_access_token
from app.core.dependencies import get_current_user, get_current_superuser
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    ForgotPasswordRequest,
    UserResponse,
    UserUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")


@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate user and return JWT access token.

    Args:
        request: FastAPI Request (required by slowapi for rate limiting)
        payload: LoginRequest with username and password
        db: Database session

    Returns:
        LoginResponse with access_token and user data

    Raises:
        HTTPException 401: Invalid credentials or inactive user
    """
    client_ip = request.client.host if request.client else "unknown"
    user = db.query(User).filter(User.username == payload.username).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        logger.warning(
            "Login failed: username=%s ip=%s", payload.username, client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
        )

    if not user.is_active:
        logger.warning(
            "Login blocked (inactive): username=%s ip=%s",
            payload.username,
            client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Пользователь неактивен",
        )

    # jose/jwt expects "sub" claim as string; int subject breaks decode validation.
    access_token = create_access_token(data={"sub": str(user.id)})

    logger.info(
        "Login success: user_id=%s username=%s ip=%s",
        user.id,
        user.username,
        client_ip,
    )

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Send password reset link to user's email.

    ⚠️ ЗАГЛУШКА: Email НЕ отправляется реально, только mock ответ.
    Всегда возвращает 200 OK, чтобы предотвратить перечисление пользователей.

    Args:
        request: FastAPI Request (required by slowapi for rate limiting)
        payload: ForgotPasswordRequest with email
        db: Database session

    Returns:
        Success message (always 200 OK)
    """
    client_ip = request.client.host if request.client else "unknown"
    # Проверяем пользователя, но НЕ раскрываем существование email
    user = db.query(User).filter(User.email == payload.email).first()

    logger.info(
        "Password reset requested: email=%s exists=%s ip=%s",
        payload.email,
        bool(user),
        client_ip,
    )

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
    """Update current user profile (full_name, email, phone, role)."""
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)
