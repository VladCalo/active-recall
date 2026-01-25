"""
Authentication service - handles user registration, login, and token management.

Security features:
- Argon2 password hashing
- Account lockout after failed attempts
- Refresh token rotation with reuse detection
- Server-side token tracking for revocation
- Timing-safe operations
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.schemas.auth import UserRegister
from app.core.security import (
    hash_password, verify_password, 
    create_access_token, create_refresh_token
)
from app.core.password import check_password_strength
from app.core.logging import auth_logger
from app.config import get_settings

settings = get_settings()


class AuthService:
    """
    Service class for authentication operations.
    
    Handles user registration, login, token management, and security measures.
    """

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email (case-insensitive)."""
        return self.db.query(User).filter(
            func.lower(User.email) == email.lower().strip()
        ).first()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID."""
        return self.db.query(User).filter(User.id == user_id).first()

    def _is_account_locked(self, user: User) -> bool:
        """Check if account is currently locked."""
        if user.locked_until:
            if datetime.now(timezone.utc) < user.locked_until.replace(tzinfo=timezone.utc):
                return True
            # Lockout expired, reset
            user.locked_until = None
            user.failed_login_attempts = 0
            self.db.commit()
        return False

    def _increment_failed_attempts(self, user: User) -> None:
        """Increment failed login attempts and lock if threshold reached."""
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= settings.max_login_attempts:
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.lockout_duration_minutes
            )
        
        self.db.commit()

    def _reset_failed_attempts(self, user: User) -> None:
        """Reset failed login counter on successful login."""
        user.failed_login_attempts = 0
        user.locked_until = None
        self.db.commit()

    def _create_refresh_token_record(
        self, 
        user_id: str, 
        token_id: str, 
        family_id: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_days: Optional[int] = None
    ) -> RefreshToken:
        """Create a refresh token record in database."""
        days = expires_days or settings.refresh_token_expire_days
        expires_at = datetime.now(timezone.utc) + timedelta(days=days)
        
        token_record = RefreshToken(
            id=token_id,
            user_id=user_id,
            family_id=family_id,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self.db.add(token_record)
        self.db.commit()
        return token_record

    def _revoke_token_family(self, family_id: str) -> None:
        """Revoke all tokens in a family (for reuse detection)."""
        self.db.query(RefreshToken).filter(
            RefreshToken.family_id == family_id,
            RefreshToken.is_revoked == False
        ).update({
            "is_revoked": True,
            "revoked_at": datetime.now(timezone.utc)
        })
        self.db.commit()

    def _get_token_record(self, token_id: str) -> Optional[RefreshToken]:
        """Get a refresh token record by ID."""
        return self.db.query(RefreshToken).filter(
            RefreshToken.id == token_id
        ).first()

    def _cleanup_expired_tokens(self, user_id: str) -> None:
        """Remove expired tokens for a user."""
        self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.expires_at < datetime.now(timezone.utc)
        ).delete()
        self.db.commit()

    def register(
        self, 
        data: UserRegister,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Tuple[User, str, str]:
        """
        Register a new user.
        
        Args:
            data: Registration data (email, password)
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            
        Returns:
            Tuple of (User, access_token, refresh_token_jwt)
            
        Raises:
            ValueError: If email exists or password too weak
        """
        # Check password strength
        is_strong, issues = check_password_strength(data.password)
        if not is_strong:
            auth_logger.register_failure(data.email, ip_address or "unknown", "weak_password")
            raise ValueError(f"Password requirements not met: {'; '.join(issues)}")

        # Check if email already exists (case-insensitive)
        existing = self.get_user_by_email(data.email)
        if existing:
            auth_logger.register_failure(data.email, ip_address or "unknown", "email_exists")
            # Generic error to prevent user enumeration
            raise ValueError("Registration failed. Please try again.")

        # Hash password
        password_hash = hash_password(data.password)
        
        # Create user
        user = User(
            email=data.email.lower().strip(),
            password_hash=password_hash,
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        # Generate tokens
        access_token = create_access_token({"sub": user.id})
        refresh_jwt, token_id, family_id = create_refresh_token({"sub": user.id})
        
        # Store refresh token record
        self._create_refresh_token_record(
            user.id, token_id, family_id, ip_address, user_agent
        )
        
        auth_logger.register_success(user.id, user.email, ip_address or "unknown")
        
        return user, access_token, refresh_jwt

    async def login(
        self, 
        email: str, 
        password: str,
        remember_me: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Tuple[User, str, str]]:
        """
        Authenticate a user.
        
        Includes:
        - Account lockout check
        - Small delay after failed attempts
        - Timing-safe password verification
        
        Args:
            email: User email
            password: Plain text password
            ip_address: Client IP for logging
            user_agent: Client user agent for logging
            
        Returns:
            Tuple of (User, access_token, refresh_token_jwt) if successful, None otherwise
        """
        user = self.get_user_by_email(email)
        
        # Always verify against something to prevent timing attacks
        if not user:
            verify_password(password, hash_password("dummy_password"))
            await asyncio.sleep(settings.login_delay_seconds)
            auth_logger.login_failure(email, ip_address or "unknown", "user_not_found")
            return None
        
        # Check if account is disabled
        if user.is_disabled:
            await asyncio.sleep(settings.login_delay_seconds)
            auth_logger.login_failure(email, ip_address or "unknown", "account_disabled")
            return None
        
        # Check if account is locked
        if self._is_account_locked(user):
            await asyncio.sleep(settings.login_delay_seconds)
            auth_logger.login_failure(email, ip_address or "unknown", "account_locked")
            return None
        
        # Verify password
        if not verify_password(password, user.password_hash):
            self._increment_failed_attempts(user)
            await asyncio.sleep(settings.login_delay_seconds)
            auth_logger.login_failure(email, ip_address or "unknown", "invalid_password")
            return None
        
        # Successful login - reset counters
        self._reset_failed_attempts(user)
        
        # Update last login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # Clean up expired tokens
        self._cleanup_expired_tokens(user.id)
        
        # Generate tokens (longer expiry if remember_me)
        access_token = create_access_token({"sub": user.id})
        
        token_days = (
            settings.refresh_token_expire_days_remember 
            if remember_me 
            else settings.refresh_token_expire_days
        )
        refresh_jwt, token_id, family_id = create_refresh_token(
            {"sub": user.id},
            expires_delta=timedelta(days=token_days)
        )
        
        # Store refresh token record with appropriate expiry
        self._create_refresh_token_record(
            user.id, token_id, family_id, ip_address, user_agent,
            expires_days=token_days
        )
        
        auth_logger.login_success(user.id, user.email, ip_address or "unknown")
        
        return user, access_token, refresh_jwt

    def refresh_tokens(
        self, 
        refresh_token_payload: dict,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Tuple[str, str, User]]:
        """
        Rotate refresh tokens and generate new access token.
        
        Implements:
        - Token rotation (new token on each refresh)
        - Reuse detection (revokes family if old token used)
        
        Args:
            refresh_token_payload: Decoded refresh token payload
            ip_address: Client IP for logging
            user_agent: Client user agent
            
        Returns:
            Tuple of (new_access_token, new_refresh_token_jwt, user) if valid, None otherwise
        """
        # Verify token type
        if refresh_token_payload.get("type") != "refresh":
            return None
        
        user_id = refresh_token_payload.get("sub")
        token_id = refresh_token_payload.get("jti")
        family_id = refresh_token_payload.get("fid")
        
        if not all([user_id, token_id, family_id]):
            return None
        
        # Get token record
        token_record = self._get_token_record(token_id)
        
        if not token_record:
            # Token not found - might be an old/invalid token
            return None
        
        # Check if token was already used (reuse detection)
        if token_record.used_at is not None:
            # SECURITY: Token reuse detected - possible theft!
            # Revoke entire token family
            auth_logger.token_reuse_detected(user_id, token_id, ip_address or "unknown")
            self._revoke_token_family(family_id)
            return None
        
        # Check if token is revoked
        if token_record.is_revoked:
            return None
        
        # Mark token as used
        token_record.used_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # Verify user still exists and is not disabled
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        if user.is_disabled:
            # User was disabled - revoke their tokens
            self._revoke_token_family(family_id)
            return None
        
        # Generate new tokens (same family for tracking)
        access_token = create_access_token({"sub": user.id})
        new_refresh_jwt, new_token_id, _ = create_refresh_token(
            {"sub": user.id},
            family_id=family_id  # Inherit family
        )
        
        # Store new refresh token record
        self._create_refresh_token_record(
            user.id, new_token_id, family_id, ip_address, user_agent
        )
        
        auth_logger.token_refresh(user.id, ip_address or "unknown")
        
        return access_token, new_refresh_jwt, user

    def logout(self, user_id: str, token_id: Optional[str] = None) -> None:
        """
        Log out user by revoking refresh tokens.
        
        Args:
            user_id: User to logout
            token_id: Specific token to revoke (or all if None)
        """
        if token_id:
            # Revoke specific token and its family
            token = self._get_token_record(token_id)
            if token:
                self._revoke_token_family(token.family_id)
        else:
            # Revoke all tokens for user
            self.db.query(RefreshToken).filter(
                RefreshToken.user_id == user_id,
                RefreshToken.is_revoked == False
            ).update({
                "is_revoked": True,
                "revoked_at": datetime.now(timezone.utc)
            })
            self.db.commit()

    def get_active_sessions(self, user_id: str) -> list[RefreshToken]:
        """Get all active sessions for a user."""
        return self.db.query(RefreshToken).filter(
            RefreshToken.user_id == user_id,
            RefreshToken.is_revoked == False,
            RefreshToken.expires_at > datetime.now(timezone.utc)
        ).all()
