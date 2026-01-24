"""
RefreshToken model - stores refresh token identifiers for revocation.

This enables:
- Token rotation (new token on each refresh)
- Revocation on logout
- Detection of token reuse (potential theft)
- Session management across devices
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RefreshToken(Base):
    """
    RefreshToken ORM model.
    
    Stores refresh token identifiers (not the actual tokens) for:
    - Token revocation on logout
    - Token rotation with reuse detection
    - Session listing and management
    
    Attributes:
        id: Token identifier (jti claim in JWT)
        user_id: Foreign key to the owning user
        family_id: Token family for rotation tracking
        is_revoked: Whether token has been revoked
        revoked_at: When token was revoked
        used_at: When token was last used (for rotation)
        expires_at: When token expires
        created_at: When token was created
        ip_address: IP that created the token
        user_agent: User agent that created the token
    """
    __tablename__ = "refresh_tokens"
    
    __table_args__ = (
        Index('ix_refresh_tokens_user_id', 'user_id'),
        Index('ix_refresh_tokens_family_id', 'family_id'),
        Index('ix_refresh_tokens_expires_at', 'expires_at'),
    )

    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Token family for rotation tracking
    family_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        default=lambda: str(uuid.uuid4())
    )
    
    # Revocation status
    is_revoked: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # Usage tracking
    used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=func.now()
    )
    
    # Metadata for security auditing
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),  # IPv6 max length
        nullable=True
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    
    # Relationship
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<RefreshToken(id={self.id[:8]}..., user_id={self.user_id}, revoked={self.is_revoked})>"
