"""
Pydantic schemas for authentication operations.

These schemas handle validation for registration, login, and token responses.

Security considerations:
- Password validation enforces minimum length
- Email is normalized (lowercase, stripped)
- Error messages don't reveal whether email exists
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.config import get_settings

settings = get_settings()


class UserRegister(BaseModel):
    """Schema for user registration."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(
        ..., 
        min_length=settings.min_password_length,
        description=f"Password (minimum {settings.min_password_length} characters)"
    )
    
    @field_validator('email')
    @classmethod
    def normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Validate password strength.
        
        Currently just enforces minimum length.
        Can be extended with complexity requirements.
        """
        if len(v) < settings.min_password_length:
            raise ValueError(
                f"Password must be at least {settings.min_password_length} characters"
            )
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")
    
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
