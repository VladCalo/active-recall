"""
Authentication API endpoints.

Handles user registration, login, logout, token refresh, and profile access.

Security features:
- Rate limiting per endpoint type
- Generic error messages (no user enumeration)
- Refresh tokens in httpOnly cookies
- Token rotation with reuse detection
- CSRF protection for state-changing operations
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request, Cookie, Header
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
    PasswordRequirementsResponse,
)
from app.core.deps import get_current_user
from app.core.security import decode_token
from app.core.password import get_password_requirements
from app.core.rate_limiter import limiter
from app.core.logging import auth_logger
from app.models.user import User
from app.config import get_settings

settings = get_settings()

router = APIRouter(prefix="/api/auth", tags=["auth"])


def get_client_ip(request: Request) -> str:
    """Extract client IP from request (handles proxies)."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_auth_service(db: Session = Depends(get_db)) -> AuthService:
    """Dependency to get AuthService instance."""
    return AuthService(db)


def set_refresh_cookie(response: Response, refresh_token: str, remember_me: bool = True) -> None:
    """
    Set refresh token as httpOnly cookie.
    
    Security settings:
    - httponly: Prevents JavaScript access (XSS protection)
    - secure: Only sent over HTTPS (in production)
    - samesite: Prevents CSRF attacks
    """
    days = (
        settings.refresh_token_expire_days_remember 
        if remember_me 
        else settings.refresh_token_expire_days
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=days * 24 * 60 * 60,
        path="/api/auth",  # Only sent to auth endpoints
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear all auth-related cookies."""
    response.delete_cookie(key="refresh_token", path="/api/auth")
    response.delete_cookie(key="access_token", path="/")


@router.get("/password-requirements", response_model=PasswordRequirementsResponse)
async def get_password_requirements_endpoint():
    """Get password requirements for registration."""
    return PasswordRequirementsResponse(
        min_length=settings.min_password_length,
        requirements=get_password_requirements()
    )


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.rate_limit_register)
async def register(
    request: Request,
    data: UserRegister,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Register a new user.

    New accounts start unapproved and cannot log in until an admin approves
    them - no tokens are issued here, unlike login.

    Rate limited: 3 registrations per 10 minutes per IP.
    """
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")[:500]

    try:
        auth_service.register(data, ip_address=ip, user_agent=user_agent)
    except ValueError as e:
        error_msg = str(e)
        # Check if it's a password strength issue (safe to show)
        if "Password requirements" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
        # Generic error for other issues (email exists, etc.)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Please check your input and try again."
        )

    return MessageResponse(
        message="Registration successful. An administrator needs to approve your account before you can log in."
    )


@router.post("/login", response_model=AuthResponse)
@limiter.limit(settings.rate_limit_login)
async def login(
    request: Request,
    data: UserLogin,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    """
    Authenticate a user.
    
    Rate limited: 5 attempts per 5 minutes per IP.
    """
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")[:500]
    
    result = await auth_service.login(
        data.email, data.password,
        remember_me=data.remember_me,
        ip_address=ip, user_agent=user_agent
    )
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user, access_token, refresh_token = result
    
    set_refresh_cookie(response, refresh_token, remember_me=data.remember_me)
    
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """
    Log out the current user.
    
    Clears cookies and revokes refresh token.
    """
    ip = get_client_ip(request)
    
    if refresh_token:
        payload = decode_token(refresh_token)
        if payload:
            user_id = payload.get("sub")
            token_id = payload.get("jti")
            if user_id:
                auth_service = AuthService(db)
                auth_service.logout(user_id, token_id)
                auth_logger.logout(user_id, ip)
    
    clear_auth_cookies(response)
    return MessageResponse(message="Successfully logged out")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current user profile.
    
    Requires authentication.
    """
    return UserResponse.model_validate(current_user)


@router.post("/refresh", response_model=AuthResponse)
@limiter.limit(settings.rate_limit_refresh)
async def refresh_tokens(
    request: Request,
    response: Response,
    refresh_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
):
    """
    Refresh authentication tokens.
    
    Implements token rotation - old token is invalidated.
    
    Rate limited: 30 refreshes per minute per IP.
    """
    ip = get_client_ip(request)
    user_agent = request.headers.get("User-Agent", "")[:500]
    
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Decode and validate refresh token
    payload = decode_token(refresh_token)
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
    
    # Perform token rotation
    auth_service = AuthService(db)
    result = auth_service.refresh_tokens(
        payload, ip_address=ip, user_agent=user_agent
    )
    
    if not result:
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not refresh tokens",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    new_access_token, new_refresh_token, user = result
    
    # Set new refresh token cookie
    set_refresh_cookie(response, new_refresh_token)
    
    return AuthResponse(
        user=UserResponse.model_validate(user),
        access_token=new_access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )
