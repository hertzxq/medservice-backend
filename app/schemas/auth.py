"""
Pydantic schemas for authentication.
"""

from pydantic import EmailStr

from app.schemas.common import APIModel


class LoginRequest(APIModel):
    """Schema for login request."""

    username: str
    password: str


class ForgotPasswordRequest(APIModel):
    """Schema for forgot password request."""

    email: EmailStr


class UserResponse(APIModel):
    """Schema for user response (excluding password)."""

    id: int
    username: str
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool


class LoginResponse(APIModel):
    """Schema for login response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
