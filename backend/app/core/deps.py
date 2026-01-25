"""
FastAPI dependencies for authentication and authorization.

This module provides dependency injection for:
- Current user extraction from JWT tokens
- Optional authentication (for public endpoints)
- Required authentication (for protected endpoints)
- Admin-only access control

Security considerations:
- Tokens can be passed via Authorization header or httpOnly cookie
- Invalid tokens result in 401 Unauthorized
- User existence is verified on every request
- Disabled users are rejected
- Admin endpoints require is_admin=True
"""

from typing import Optional
from fastapi import Depends, HTTPException, status, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.core.security import decode_token

# HTTP Bearer scheme for Authorization header
security = HTTPBearer(auto_error=False)


async def get_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    refresh_token: Optional[str] = Cookie(default=None, alias="refresh_token"),
) -> Optional[str]:
    """
    Extract JWT token from request.
    
    Checks in order:
    1. Authorization header (Bearer token)
    2. Cookie (for refresh token operations)
    
    Args:
        request: FastAPI request object
        credentials: Optional Bearer token from header
        refresh_token: Optional token from cookie
        
    Returns:
        JWT token string or None
    """
    # First, check Authorization header
    if credentials:
        return credentials.credentials
    
    # Fall back to access_token cookie
    access_token = request.cookies.get("access_token")
    if access_token:
        return access_token
    
    return None


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> User:
    """
    Get the current authenticated user.
    
    This is a required dependency - raises 401 if not authenticated.
    Also checks if user is disabled.
    
    Args:
        token: JWT token from request
        db: Database session
        
    Returns:
        Authenticated User object
        
    Raises:
        HTTPException: 401 if not authenticated or invalid token
        HTTPException: 403 if user is disabled
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not token:
        raise credentials_exception
    
    payload = decode_token(token)
    if not payload:
        raise credentials_exception
    
    # Verify this is an access token
    token_type = payload.get("type")
    if token_type != "access":
        raise credentials_exception
    
    user_id: str = payload.get("sub")
    if not user_id:
        raise credentials_exception
    
    # Verify user exists
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exception
    
    # Check if user is disabled
    if user.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact administrator."
        )
    
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """
    Get the current user and verify they are an admin.
    
    Args:
        current_user: The authenticated user
        
    Returns:
        Admin User object
        
    Raises:
        HTTPException: 403 if user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_current_user_optional(
    token: Optional[str] = Depends(get_token_from_request),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, or None if not.
    
    This is an optional dependency - doesn't raise if not authenticated.
    Useful for endpoints that have different behavior for authenticated
    vs anonymous users.
    
    Args:
        token: JWT token from request
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    if not token:
        return None
    
    payload = decode_token(token)
    if not payload:
        return None
    
    token_type = payload.get("type")
    if token_type != "access":
        return None
    
    user_id: str = payload.get("sub")
    if not user_id:
        return None
    
    user = db.query(User).filter(User.id == user_id).first()
    
    # Return None for disabled users in optional auth
    if user and user.is_disabled:
        return None
    
    return user
