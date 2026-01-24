"""
Pydantic schemas for request/response validation.

This package contains all Pydantic models used for:
- API request validation
- API response serialization
- Data transfer objects (DTOs)
"""

from app.schemas.subject import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    SubjectWithNextDue,
)
from app.schemas.review import TodayReviewsResponse, UpcomingReviewsResponse
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
    AuthResponse,
    MessageResponse,
)

__all__ = [
    "SubjectCreate",
    "SubjectUpdate", 
    "SubjectResponse",
    "SubjectWithNextDue",
    "TodayReviewsResponse",
    "UpcomingReviewsResponse",
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "AuthResponse",
    "MessageResponse",
]
