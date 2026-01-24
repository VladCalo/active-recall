"""
Structured logging configuration.

This module sets up structured logging for the application:
- JSON format in production for log aggregation
- Human-readable format in development
- No sensitive data in logs
- Auth event logging (success/failure/logout)
"""

import logging
import sys
from typing import Optional

import structlog
from structlog.types import EventDict

from app.config import get_settings

settings = get_settings()


def filter_sensitive_data(logger, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Remove sensitive data from logs.
    
    Filters out passwords, tokens, and other secrets.
    """
    sensitive_keys = {
        'password', 'password_hash', 'token', 'access_token', 
        'refresh_token', 'secret', 'api_key', 'authorization',
        'cookie', 'csrf_token'
    }
    
    for key in list(event_dict.keys()):
        if key.lower() in sensitive_keys:
            event_dict[key] = '[REDACTED]'
        elif isinstance(event_dict[key], dict):
            for nested_key in list(event_dict[key].keys()):
                if nested_key.lower() in sensitive_keys:
                    event_dict[key][nested_key] = '[REDACTED]'
    
    # Also mask email partially for privacy
    if 'email' in event_dict and event_dict['email']:
        email = str(event_dict['email'])
        if '@' in email:
            local, domain = email.split('@', 1)
            masked = f"{local[:2]}***@{domain}"
            event_dict['email'] = masked
    
    return event_dict


def setup_logging():
    """Configure structured logging based on environment."""
    
    # Shared processors for all environments
    shared_processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        filter_sensitive_data,
    ]
    
    if settings.environment == "production":
        # JSON output for production (easier to parse by log aggregators)
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
        ]
    else:
        # Human-readable output for development
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer()
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configure standard library logging
    log_level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str = __name__):
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Auth-specific logging functions
class AuthLogger:
    """Logger for authentication events."""
    
    def __init__(self):
        self.logger = get_logger("auth")
    
    def login_success(self, user_id: str, email: str, ip: str):
        """Log successful login."""
        self.logger.info(
            "login_success",
            user_id=user_id,
            email=email,
            ip=ip,
            event_type="auth"
        )
    
    def login_failure(self, email: str, ip: str, reason: str = "invalid_credentials"):
        """Log failed login attempt."""
        self.logger.warning(
            "login_failure",
            email=email,
            ip=ip,
            reason=reason,
            event_type="auth"
        )
    
    def logout(self, user_id: str, ip: str):
        """Log logout."""
        self.logger.info(
            "logout",
            user_id=user_id,
            ip=ip,
            event_type="auth"
        )
    
    def register_success(self, user_id: str, email: str, ip: str):
        """Log successful registration."""
        self.logger.info(
            "register_success",
            user_id=user_id,
            email=email,
            ip=ip,
            event_type="auth"
        )
    
    def register_failure(self, email: str, ip: str, reason: str):
        """Log failed registration."""
        self.logger.warning(
            "register_failure",
            email=email,
            ip=ip,
            reason=reason,
            event_type="auth"
        )
    
    def token_refresh(self, user_id: str, ip: str):
        """Log token refresh."""
        self.logger.info(
            "token_refresh",
            user_id=user_id,
            ip=ip,
            event_type="auth"
        )
    
    def token_reuse_detected(self, user_id: str, token_id: str, ip: str):
        """Log potential refresh token reuse (security incident)."""
        self.logger.error(
            "token_reuse_detected",
            user_id=user_id,
            token_id=token_id,
            ip=ip,
            event_type="security",
            severity="high"
        )
    
    def rate_limit_exceeded(self, ip: str, endpoint: str):
        """Log rate limit exceeded."""
        self.logger.warning(
            "rate_limit_exceeded",
            ip=ip,
            endpoint=endpoint,
            event_type="security"
        )


auth_logger = AuthLogger()
