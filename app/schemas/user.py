"""
Pydantic schemas for users.
"""

from pydantic import EmailStr

from app.schemas.common import APIModel


class UserResponse(APIModel):
    """Schema for user response (excluding password)."""

    id: int
    username: str
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool


class UserCreate(APIModel):
    """Schema for creating new user."""

    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
