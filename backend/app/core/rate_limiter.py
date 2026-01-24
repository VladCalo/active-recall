"""
Rate limiting with Redis support and in-memory fallback.

This module provides production-ready rate limiting:
- Redis-backed for distributed deployments
- In-memory fallback for development/single-instance
- Per-IP and per-user limiting
- Configurable limits via environment variables
- Standard headers (X-RateLimit-*, Retry-After)
"""

import time
from typing import Optional, Callable
from functools import wraps

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import get_settings

settings = get_settings()


def get_redis_storage():
    """Get Redis storage if available, else return None for in-memory."""
    if settings.redis_url:
        try:
            from limits.storage import RedisStorage
            return RedisStorage(settings.redis_url)
        except Exception as e:
            import warnings
            warnings.warn(f"Redis connection failed, using in-memory storage: {e}")
            return None
    return None


# Create limiter with Redis or in-memory storage
_storage = get_redis_storage()
if _storage:
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url,
    )
else:
    limiter = Limiter(key_func=get_remote_address)


def get_user_identifier(request: Request) -> str:
    """
    Get user identifier for rate limiting.
    
    Uses user ID if authenticated, else IP address.
    """
    # Check for user in request state (set by auth middleware)
    if hasattr(request.state, 'user') and request.state.user:
        return f"user:{request.state.user.id}"
    return f"ip:{get_remote_address(request)}"


def get_email_key(request: Request) -> str:
    """Get key for per-email rate limiting (login attempts)."""
    try:
        import json
        body = request._body.decode() if hasattr(request, '_body') else '{}'
        data = json.loads(body)
        email = data.get('email', '')
        if email:
            return f"email:{email.lower()}"
    except:
        pass
    return f"ip:{get_remote_address(request)}"


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """
    Handle rate limit exceeded errors with proper headers.
    """
    # Parse retry-after from the exception message
    retry_after = 60  # Default
    try:
        # Extract from message like "5 per 5 minute"
        parts = str(exc.detail).split()
        if 'minute' in parts:
            idx = parts.index('minute')
            if idx > 0:
                retry_after = int(parts[idx - 1]) * 60
        elif 'second' in parts:
            idx = parts.index('second')
            if idx > 0:
                retry_after = int(parts[idx - 1])
    except:
        pass
    
    response = JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Too many requests. Please try again later.",
            "retry_after": retry_after,
        }
    )
    response.headers["Retry-After"] = str(retry_after)
    response.headers["X-RateLimit-Remaining"] = "0"
    return response


# Pre-configured rate limit decorators
def limit_login(func):
    """Rate limit for login endpoint."""
    return limiter.limit(settings.rate_limit_login)(func)


def limit_register(func):
    """Rate limit for registration endpoint."""
    return limiter.limit(settings.rate_limit_register)(func)


def limit_refresh(func):
    """Rate limit for token refresh endpoint."""
    return limiter.limit(settings.rate_limit_refresh)(func)


def limit_api(func):
    """Rate limit for general API endpoints."""
    return limiter.limit(settings.rate_limit_api_per_ip)(func)
