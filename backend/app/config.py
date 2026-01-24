"""
Application configuration settings.

This module handles all configuration via environment variables with sensible defaults.
Uses pydantic-settings for type-safe configuration management.

SECURITY NOTE: In production, ensure all sensitive values are set via environment
variables and never committed to version control.
"""

import secrets
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # ==========================================================================
    # Application
    # ==========================================================================
    app_name: str = "Active Recall Monitor"
    debug: bool = False
    environment: str = "development"  # development, staging, production
    
    # ==========================================================================
    # Database
    # ==========================================================================
    database_url: str = "sqlite:///./app.db"
    
    # ==========================================================================
    # CORS - Security: Lock down in production
    # ==========================================================================
    # In production, set to your actual frontend domain(s)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]
    
    # ==========================================================================
    # JWT Authentication
    # ==========================================================================
    # CRITICAL: In production, this MUST be set via environment variable
    # Generate with: python -c "import secrets; print(secrets.token_urlsafe(64))"
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    
    # Token expiration times (in minutes)
    access_token_expire_minutes: int = 15  # Short-lived for security
    refresh_token_expire_days: int = 7     # Longer-lived, stored in httpOnly cookie
    
    # ==========================================================================
    # Security Settings
    # ==========================================================================
    # Cookie settings
    cookie_secure: bool = False  # Set True in production (requires HTTPS)
    cookie_samesite: str = "lax"  # lax or strict
    cookie_domain: Optional[str] = None  # Set in production if needed
    
    # Rate limiting
    rate_limit_auth: str = "5/minute"  # Auth endpoints
    rate_limit_general: str = "100/minute"  # General API endpoints
    
    # Password policy
    min_password_length: int = 8
    
    # Brute force protection
    login_delay_seconds: float = 0.5  # Small delay after failed login
    
    # ==========================================================================
    # Application Settings
    # ==========================================================================
    default_timezone: str = "Europe/Bucharest"
    default_intervals: list[int] = [1, 3, 7, 14, 30, 60, 120, 180]
    
    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """
        Validate JWT secret key.
        
        In production, fail hard if not set.
        In development, generate a random key (with warning).
        """
        if not v:
            # Check if we're in production
            env = info.data.get('environment', 'development')
            if env == 'production':
                raise ValueError(
                    "JWT_SECRET_KEY must be set in production! "
                    "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            # Generate a random key for development (warning: sessions won't persist across restarts)
            import warnings
            warnings.warn(
                "JWT_SECRET_KEY not set - using random key. "
                "Sessions will not persist across restarts. "
                "Set JWT_SECRET_KEY environment variable for persistent sessions.",
                UserWarning
            )
            return secrets.token_urlsafe(64)
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # Allow environment variables to use different naming
        env_prefix = ""


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Using lru_cache ensures settings are only loaded once from environment.
    """
    return Settings()
