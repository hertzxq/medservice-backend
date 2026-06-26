"""
Pydantic schemas for authentication.
"""

from pydantic import EmailStr, Field

from app.schemas.common import APIModel


class LoginRequest(APIModel):
    """Schema for login request."""

    username: str
    password: str


class ForgotPasswordRequest(APIModel):
    """Schema for forgot password request."""

    email: EmailStr


class ResetPasswordRequest(APIModel):
    """Schema for password reset confirmation."""

    token: str
    password: str = Field(min_length=8, max_length=72)


class UserResponse(APIModel):
    """Schema for user response (excluding password)."""

    id: int
    username: str
    email: str
    full_name: str | None
    phone: str | None
    role: str | None
    is_active: bool
    is_superuser: bool
    # Assigned branch ids (multi-tenancy). Populated by the admin endpoints;
    # defaults to [] elsewhere (the dashboard gets branches via GET /branches).
    branch_ids: list[int] = []


class UserUpdate(APIModel):
    """Schema for updating current user profile."""

    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    role: str | None = None
    # Опционально: новый пароль (хэшируется в update_me, не присваивается setattr).
    password: str | None = Field(default=None, min_length=8, max_length=72)


class LoginResponse(APIModel):
    """Schema for login response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
