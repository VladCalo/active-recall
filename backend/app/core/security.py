"""
Security utilities for authentication.

This module provides:
- Password hashing with Argon2 (memory-hard, GPU-resistant)
- JWT token creation and validation with rotation support
- CSRF token generation and validation
- Secure token handling

Security considerations:
- Argon2 is the winner of the Password Hashing Competition
- Tokens are signed with HS256 algorithm
- Short-lived access tokens minimize impact of token theft
- Refresh tokens support rotation with reuse detection
"""

import uuid
import hmac
import hashlib
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
        "jti": str(uuid.uuid4()),  # Unique token ID
    })
    
    return jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )


def create_refresh_token(
    data: dict[str, Any],
    token_id: Optional[str] = None,
    family_id: Optional[str] = None,
    expires_delta: Optional[timedelta] = None
) -> tuple[str, str, str]:
    """
    Create a JWT refresh token with rotation support.
    
    Refresh tokens are longer-lived (default 7 days) and support:
    - Token rotation (new token on each refresh)
    - Reuse detection (via token ID tracking)
    - Family-based revocation
    
    Args:
        data: Payload data to encode in the token
        token_id: Optional specific token ID (for testing)
        family_id: Token family ID (new tokens inherit this)
        expires_delta: Optional custom expiration time
        
    Returns:
        Tuple of (encoded_jwt, token_id, family_id)
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.refresh_token_expire_days
        )
    
    # Generate or use provided IDs
    jti = token_id or str(uuid.uuid4())
    fid = family_id or str(uuid.uuid4())
    
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "jti": jti,      # Token ID for tracking
        "fid": fid,      # Family ID for rotation
    })
    
    token = jwt.encode(
        to_encode, 
        settings.jwt_secret_key, 
        algorithm=settings.jwt_algorithm
    )
    
    return token, jti, fid


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


# =============================================================================
# CSRF Token Functions
# =============================================================================

def generate_csrf_token(session_id: str) -> str:
    """
    Generate a CSRF token tied to a session.
    
    Uses HMAC to create a token that can be validated without storage.
    
    Args:
        session_id: User's session identifier
        
    Returns:
        CSRF token string
    """
    message = f"{session_id}:{datetime.now(timezone.utc).date().isoformat()}"
    signature = hmac.new(
        settings.csrf_secret_key.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return f"{session_id}:{signature[:32]}"


def validate_csrf_token(token: str, session_id: str) -> bool:
    """
    Validate a CSRF token.
    
    Args:
        token: CSRF token to validate
        session_id: Expected session identifier
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Token format: "session_id:signature"
        parts = token.split(":")
        if len(parts) != 2:
            return False
        
        token_session_id, provided_sig = parts
        
        # Verify session ID matches
        if token_session_id != session_id:
            return False
        
        # Generate expected signature
        expected = generate_csrf_token(session_id)
        expected_sig = expected.split(":")[1]
        
        # Constant-time comparison
        return hmac.compare_digest(provided_sig, expected_sig)
    except Exception:
        return False


# =============================================================================
# Utility Functions
# =============================================================================

def constant_time_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing attacks.
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        True if strings are equal
    """
    return hmac.compare_digest(a.encode(), b.encode())
