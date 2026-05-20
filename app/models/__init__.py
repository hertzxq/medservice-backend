"""
SQLAlchemy models for the application.
All models must be imported here for Alembic to detect them.
"""

from app.models.user import User
from app.models.branch import Branch
from app.models.review import Review, PlatformEnum
from app.models.complaint import Complaint
from app.models.request import Request, RequestStatusEnum
from app.models.employee import Employee
from app.models.blacklist import BlacklistUser
from app.models.bonus import BranchBonus, BonusCategory, AdminBonus

__all__ = [
    "User",
    "Branch",
    "Review",
    "PlatformEnum",
    "Complaint",
    "Request",
    "RequestStatusEnum",
    "Employee",
    "BlacklistUser",
    "BranchBonus",
    "BonusCategory",
    "AdminBonus",
]
