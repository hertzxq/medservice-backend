"""
Main API router for v1 endpoints.
Collects all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1 import auth, analytics, branches, reviews, complaints, requests

# Create main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, tags=["Auth"])
api_router.include_router(analytics.router, tags=["Analytics"])
api_router.include_router(branches.router, tags=["Branches"])
api_router.include_router(reviews.router, tags=["Reviews"])
api_router.include_router(complaints.router, tags=["Complaints"])
api_router.include_router(requests.router, tags=["Requests"])
