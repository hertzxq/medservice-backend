"""
Main API router for v1 endpoints.
Collects all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_bonuses,
    auth,
    analytics,
    blacklist,
    bonuses,
    branches,
    complaints,
    employees,
    parsing,
    requests,
    reviews,
)

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, tags=["Auth"])
api_router.include_router(admin.router, tags=["Admin"])
api_router.include_router(admin_bonuses.router, tags=["AdminBonuses"])
api_router.include_router(analytics.router, tags=["Analytics"])
api_router.include_router(branches.router, tags=["Branches"])
api_router.include_router(bonuses.router, tags=["Bonuses"])
api_router.include_router(reviews.router, tags=["Reviews"])
api_router.include_router(complaints.router, tags=["Complaints"])
api_router.include_router(requests.router, tags=["Requests"])
api_router.include_router(employees.router, tags=["Employees"])
api_router.include_router(blacklist.router, tags=["Blacklist"])
api_router.include_router(parsing.router, tags=["Parsing"])
