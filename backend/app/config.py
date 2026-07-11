"""
Application configuration settings.

This module handles all configuration via environment variables with sensible defaults.
Uses pydantic-settings for type-safe configuration management.

SECURITY NOTE: In production, ensure all sensitive values are set via environment
variables and never committed to version control.
"""

import secrets
from datetime import date
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
    # Redis (for rate limiting and session storage)
    # ==========================================================================
    redis_url: Optional[str] = None  # e.g., redis://localhost:6379/0
    
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
    
    # Token expiration times
    access_token_expire_minutes: int = 15  # Short-lived for security
    refresh_token_expire_days: int = 7     # Default: 7 days
    refresh_token_expire_days_remember: int = 30  # "Remember me": 30 days
    
    # ==========================================================================
    # Security Settings
    # ==========================================================================
    # Cookie settings
    cookie_secure: bool = False  # Set True in production (requires HTTPS)
    cookie_samesite: str = "lax"  # lax or strict
    cookie_domain: Optional[str] = None  # Set in production if needed
    
    # CSRF token secret (for double-submit cookie pattern)
    csrf_secret_key: str = ""
    
    # ==========================================================================
    # Rate Limiting (configurable via env)
    # ==========================================================================
    # Auth endpoints
    rate_limit_login: str = "20/5minute"       # 20 attempts per 5 minutes (per client IP)
    rate_limit_register: str = "3/10minute"      # 3 registrations per 10 minutes
    rate_limit_refresh: str = "30/minute"        # 30 refreshes per minute
    
    # General API
    rate_limit_api_per_user: str = "120/minute"  # 120 requests per minute per user
    rate_limit_api_per_ip: str = "60/minute"     # 60 requests per minute per IP
    
    # ==========================================================================
    # Password Policy
    # ==========================================================================
    min_password_length: int = 10
    require_password_complexity: bool = True
    check_common_passwords: bool = True
    
    # ==========================================================================
    # Brute Force Protection
    # ==========================================================================
    login_delay_seconds: float = 0.5  # Small delay after failed login
    max_login_attempts: int = 5       # Before temporary lockout
    lockout_duration_minutes: int = 15
    
    # ==========================================================================
    # Request Limits
    # ==========================================================================
    max_request_body_size: int = 1_048_576  # 1MB
    max_subject_name_length: int = 255
    max_intervals_count: int = 50
    
    # ==========================================================================
    # Application Settings
    # ==========================================================================
    default_timezone: str = "Europe/Bucharest"

    # ==========================================================================
    # Final Active Recall / Reference Mode
    # ==========================================================================
    # On/after this date, a chapter's next computed interval pushes it into
    # Final Active Recall instead of scheduling another session.
    final_recall_cutoff_date: date = date(2026, 10, 13)
    # End of the Reference Mode / final rereading window.
    reference_mode_end_date: date = date(2026, 11, 12)
    # Used for the "days remaining" dashboard stat.
    exam_date: date = date(2026, 11, 13)

    # ==========================================================================
    # Admin Account Configuration
    # SECURITY: Change these defaults in production!
    # ==========================================================================
    admin_email: str = "adminvladcalo"
    admin_password: str = "Adminvladcalo123!"
    admin_allow_default: bool = False  # Must set True to allow defaults in production

    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """
        Validate JWT secret key.
        
        In production, fail hard if not set.
        In development, generate a random key (with warning).
        """
        if not v:
            env = info.data.get('environment', 'development')
            if env == 'production':
                raise ValueError(
                    "JWT_SECRET_KEY must be set in production! "
                    "Generate with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
                )
            import warnings
            warnings.warn(
                "JWT_SECRET_KEY not set - using random key. "
                "Sessions will not persist across restarts.",
                UserWarning
            )
            return secrets.token_urlsafe(64)
        return v

    @field_validator('csrf_secret_key')
    @classmethod
    def validate_csrf_secret(cls, v: str, info) -> str:
        """Generate CSRF secret if not provided."""
        if not v:
            env = info.data.get('environment', 'development')
            if env == 'production':
                raise ValueError("CSRF_SECRET_KEY must be set in production!")
            return secrets.token_urlsafe(32)
        return v

    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v: list[str], info) -> list[str]:
        """Validate CORS origins in production."""
        env = info.data.get('environment', 'development')
        if env == 'production':
            # Ensure no wildcard or localhost in production
            for origin in v:
                if '*' in origin:
                    raise ValueError("Wildcard CORS origins not allowed in production")
                if 'localhost' in origin or '127.0.0.1' in origin:
                    raise ValueError("localhost CORS origins not allowed in production")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        env_prefix = ""


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Using lru_cache ensures settings are only loaded once from environment.
    """
    return Settings()
