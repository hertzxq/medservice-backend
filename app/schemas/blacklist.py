"""
Pydantic schemas for blacklist users.
"""

from pydantic import ConfigDict

from app.schemas.common import APIModel


class BlacklistUserBase(APIModel):
    last_name: str
    first_name: str
    phone: str
    reason: str | None = None


class BlacklistUserCreate(BlacklistUserBase):
    pass


class BlacklistUserUpdate(APIModel):
    last_name: str | None = None
    first_name: str | None = None
    phone: str | None = None
    reason: str | None = None


class BlacklistUserResponse(BlacklistUserBase):
    id: int
    branch_id: int

    model_config = ConfigDict(from_attributes=True)
