"""
Pydantic schemas for users.
"""

from pydantic import BaseModel, EmailStr


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


class UserCreate(BaseModel):
    """Schema for creating new user."""

    username: str
    email: EmailStr
    password: str
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
