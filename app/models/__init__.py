"""
SQLAlchemy models for the application.
All models must be imported here for Alembic to detect them.
"""

from app.models.user import User
from app.models.branch import Branch
from app.models.review import Review, PlatformEnum
from app.models.complaint import Complaint
from app.models.request import Request, RequestStatusEnum

__all__ = [
    "User",
    "Branch",
    "Review",
    "PlatformEnum",
    "Complaint",
    "Request",
    "RequestStatusEnum",
]
