"""
Pydantic schemas for employees.
"""

from pydantic import ConfigDict

from app.schemas.common import APIModel


class EmployeeBase(APIModel):
    name: str
    active: bool = True
    profiles: list[str] = []


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(APIModel):
    name: str | None = None
    active: bool | None = None
    profiles: list[str] | None = None


class EmployeeResponse(EmployeeBase):
    id: int
    branch_id: int

    model_config = ConfigDict(from_attributes=True)
