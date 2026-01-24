"""
Authentication service - handles user registration, login, and token management.

Security considerations:
- Passwords are hashed with Argon2 before storage
- Failed logins have a small delay (brute force mitigation)
- Generic error messages prevent user enumeration
- Email uniqueness is case-insensitive
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import UserRegister
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token
from app.config import get_settings

settings = get_settings()


class AuthService:
    """
    Service class for authentication operations.
    
    Handles user registration, login, and password management.
    """

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db

    def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get a user by email (case-insensitive).
        
        Args:
            email: Email to search for
            
        Returns:
            User if found, None otherwise
        """
        return self.db.query(User).filter(
            func.lower(User.email) == email.lower().strip()
        ).first()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            User if found, None otherwise
        """
        return self.db.query(User).filter(User.id == user_id).first()

    def register(self, data: UserRegister) -> Tuple[User, str, str]:
        """
        Register a new user.
        
        Args:
            data: Registration data (email, password)
            
        Returns:
            Tuple of (User, access_token, refresh_token)
            
        Raises:
            ValueError: If email already exists
        """
        # Check if email already exists (case-insensitive)
        existing = self.get_user_by_email(data.email)
        if existing:
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
        refresh_token = create_refresh_token({"sub": user.id})
        
        return user, access_token, refresh_token

    async def login(self, email: str, password: str) -> Optional[Tuple[User, str, str]]:
        """
        Authenticate a user.
        
        Includes a small delay after failed attempts to mitigate brute force.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            Tuple of (User, access_token, refresh_token) if successful, None otherwise
        """
        user = self.get_user_by_email(email)
        
        # Always verify against something to prevent timing attacks
        if not user:
            # Verify against dummy hash to maintain constant time
            verify_password(password, hash_password("dummy_password"))
            # Add delay for brute force protection
            await asyncio.sleep(settings.login_delay_seconds)
            return None
        
        # Verify password
        if not verify_password(password, user.password_hash):
            # Add delay for brute force protection
            await asyncio.sleep(settings.login_delay_seconds)
            return None
        
        # Update last login timestamp
        user.last_login_at = datetime.now(timezone.utc)
        self.db.commit()
        
        # Generate tokens
        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})
        
        return user, access_token, refresh_token

    def refresh_tokens(self, refresh_token_payload: dict) -> Optional[Tuple[str, str]]:
        """
        Generate new access and refresh tokens from a valid refresh token.
        
        Args:
            refresh_token_payload: Decoded refresh token payload
            
        Returns:
            Tuple of (new_access_token, new_refresh_token) if valid, None otherwise
        """
        # Verify token type
        if refresh_token_payload.get("type") != "refresh":
            return None
        
        user_id = refresh_token_payload.get("sub")
        if not user_id:
            return None
        
        # Verify user still exists
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        
        # Generate new tokens
        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})
        
        return access_token, refresh_token
