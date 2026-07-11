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
)
from app.schemas.review import TodayReviewsResponse
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
    "TodayReviewsResponse",
    "UserRegister",
    "UserLogin",
    "UserResponse",
    "TokenResponse",
    "AuthResponse",
    "MessageResponse",
]
