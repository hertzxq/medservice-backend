"""
Pydantic schemas for authentication.
"""

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Schema for login request."""

    username: str
    password: str


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request."""

    email: EmailStr


class UserResponse(BaseModel):
    """Schema for user response (excluding password)."""

    id: int
    username: str
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
