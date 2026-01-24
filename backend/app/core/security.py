"""
Security utilities for authentication.

This module provides:
- Password hashing with Argon2 (memory-hard, GPU-resistant)
- JWT token creation and validation
- Secure token handling

Security considerations:
- Argon2 is the winner of the Password Hashing Competition
- Tokens are signed with HS256 algorithm
- Short-lived access tokens minimize impact of token theft
- Refresh tokens enable secure session extension
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import get_settings

settings = get_settings()

# =============================================================================
# Password Hashing Configuration
# =============================================================================

# Use Argon2 as primary, bcrypt as fallback
# Argon2 parameters are tuned for security while keeping reasonable performance
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    # Argon2 parameters (memory-hard to resist GPU attacks)
    argon2__memory_cost=65536,  # 64 MB
    argon2__time_cost=3,        # 3 iterations
    argon2__parallelism=4,      # 4 parallel threads
)


def hash_password(password: str) -> str:
    """
    Hash a password using Argon2.
    
    Args:
        password: Plain text password
        
    Returns:
        Argon2 hash string
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Uses constant-time comparison to prevent timing attacks.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Stored hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT Token Functions
# =============================================================================

def create_access_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Access tokens are short-lived (default 15 minutes) and contain
    the user's identity information.
    
    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc),
    })
    
    return jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Refresh tokens are longer-lived (default 7 days) and are used
    to obtain new access tokens without re-authentication.
    
    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
    
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
    })
    
    return jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT string to decode
        
    Returns:
        Decoded payload if valid, None if invalid or expired
    """
    try:
        payload = jwt.decode(
            token, 
            settings.jwt_secret_key, 
            algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None
