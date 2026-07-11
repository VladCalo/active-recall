"""
API routes package.

This package contains all FastAPI route handlers organized by resource.
"""

from app.api.subjects import router as subjects_router
from app.api.reviews import router as reviews_router
from app.api.reference_mode import router as reference_mode_router
from app.api.health import router as health_router
from app.api.auth import router as auth_router

__all__ = [
    "subjects_router",
    "reviews_router",
    "reference_mode_router",
    "health_router",
    "auth_router",
]
