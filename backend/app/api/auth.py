"""
Authentication API endpoints.

Handles user registration, login, logout, token refresh, and profile access.

Security considerations:
- Rate limited to prevent brute force
- Generic error messages prevent user enumeration
- Refresh tokens stored in httpOnly cookies
- Access tokens returned in response body
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.services.auth_service import AuthService
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    UserResponse,
    AuthResponse,
    MessageResponse,
)
from app.core.deps import get_current_user
from app.core.security import decode_token
from app.models.user import User
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency to get AuthService instance."""
    return AuthService(db)


def set_refresh_cookie(response: Response, refresh_token: str) -> None:
    """
    Set refresh token as httpOnly cookie.
    
    Security settings:
    - httponly: Prevents JavaScript access (XSS protection)
    - secure: Only sent over HTTPS (in production)
    - samesite: Prevents CSRF attacks
    """
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/auth",  # Only sent to auth endpoints
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear all auth-related cookies."""
    response.delete_cookie(
        key="refresh_token",
        path="/api/auth",
    )
    response.delete_cookie(
        key="access_token",
        path="/",
    )


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserRegister,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.
    
    Creates a new user account and returns authentication tokens.
    
    Args:
        data: Registration data (email, password)
        
    Returns:
        User profile and access token
        
    Raises:
        400: If registration fails (e.g., email exists)
        422: If validation fails
    """
    try:
        user, access_token, refresh_token = auth_service.register(data)
    except ValueError as e:
        # Generic error to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your input and try again."
        )
    
    # Set refresh token in httpOnly cookie
    set_refresh_cookie(response, refresh_token)
    
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    data: UserLogin,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate a user.
    
    Validates credentials and returns authentication tokens.
    
    Args:
        data: Login credentials (email, password)
        
    Returns:
        User profile and access token
        
    Raises:
        401: If credentials are invalid
    """
    result = await auth_service.login(data.email, data.password)
    
    if not result:
        # Generic error to prevent user enumeration
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user, access_token, refresh_token = result
    
    # Set refresh token in httpOnly cookie
    set_refresh_cookie(response, refresh_token)
    
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(response: Response):
    """
    Log out the current user.
    
    Clears all authentication cookies.
    
    Note: Client should also discard the access token from memory.
    
    Returns:
        Success message
    """
    clear_auth_cookies(response)
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user profile.
    
    Requires authentication.
    
    Returns:
        Current user's profile
    """
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=AuthResponse)
async def refresh_tokens(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """
    Refresh authentication tokens.
    
    Uses the refresh token from httpOnly cookie to generate new tokens.
    
    Returns:
        New access token and updated refresh token
        
    Raises:
        401: If refresh token is invalid or expired
    """
    # Try to get refresh token from cookie or request body
    token = refresh_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode and validate refresh token
    payload = decode_token(token)
    if not payload:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify it's a refresh token
    if payload.get("type") != "refresh":
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user
    auth_service = AuthService(db)
    user_id = payload.get("sub")
    user = auth_service.get_user_by_id(user_id) if user_id else None
    
    if not user:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate new tokens
    result = auth_service.refresh_tokens(payload)
    if not result:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh tokens",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    new_access_token, new_refresh_token = result
    
    # Update refresh token cookie
    set_refresh_cookie(response, new_refresh_token)
    
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=new_access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
