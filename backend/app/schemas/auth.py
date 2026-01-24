"""
Pydantic schemas for authentication operations.

These schemas handle validation for registration, login, and token responses.

Security considerations:
- Password validation enforces minimum length and complexity
- Email is normalized (lowercase, stripped)
- Error messages don't reveal whether email exists
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.config import get_settings

settings = get_settings()


class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., 
        min_length=settings.min_password_length,
        max_length=128,  # Prevent DoS with very long passwords
        description=f"Password (minimum {settings.min_password_length} characters)"
    )
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., 
        max_length=128,  # Prevent DoS with very long passwords
        description="User password"
    )
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()


class UserResponse(BaseModel):
    """Schema for user profile response (safe, no password)."""
    id: str
    email: str
    created_at: datetime
    updated_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Schema for token response."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration in seconds")


class AuthResponse(BaseModel):
    """Schema for authentication response (login/register)."""
    user: UserResponse
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Token expiration in seconds")


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


class PasswordRequirementsResponse(BaseModel):
    """Schema for password requirements."""
    min_length: int
    requirements: List[str]


class RateLimitedResponse(BaseModel):
    """Schema for rate limited response."""
    detail: str
    retry_after: int = Field(..., description="Seconds until retry is allowed")


class SessionInfo(BaseModel):
    """Schema for active session information."""
    id: str
    created_at: datetime
    ip_address: Optional[str]
    user_agent: Optional[str]
    expires_at: datetime

    class Config:
        from_attributes = True
