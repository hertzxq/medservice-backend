"""
FastAPI application entry point.
MedService Feedback API - Backend for medical clinic review management.
"""

import logging
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn

if __package__ in (None, ""):
    # Allows running `python /path/to/app/main.py` from any working directory.
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.api.v1.router import api_router

setup_logging()
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    debug=settings.debug,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    description="REST API для управления отзывами медицинских клиник",
)

# Rate limiting (slowapi) — requires state attribute and 429 handler.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware для Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router with /api/v1 prefix
app.include_router(api_router, prefix="/api/v1")

logger.info(
    "Application started: name=%s debug=%s env=%s",
    settings.app_name,
    settings.debug,
    settings.environment,
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "MedService Feedback API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
