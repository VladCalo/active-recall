"""
User model - represents an authenticated user.

Security considerations:
- Passwords are hashed using Argon2 (memory-hard, resistant to GPU attacks)
- Email is stored case-insensitively (normalized to lowercase)
- No sensitive data exposed in repr
- Failed login tracking for brute force protection
- Admin and disabled flags for access control
"""

import uuid
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Date, DateTime, Integer, Boolean, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.refresh_token import RefreshToken


class User(Base):
    """
    User ORM model.
    
    Represents an authenticated user who can create and manage their own subjects.
    
    Attributes:
        id: UUID primary key (stored as string for SQLite compatibility)
        email: Unique email address (stored lowercase for case-insensitive matching)
        password_hash: Argon2 hash of the user's password
        is_admin: Whether this user has admin privileges
        is_disabled: Whether this account is disabled (cannot login)
        failed_login_attempts: Count of consecutive failed logins
        locked_until: Timestamp until account is unlocked
        created_at: Timestamp when account was created
        updated_at: Timestamp when account was last modified
        last_login_at: Timestamp of last successful login
    """
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Authentication fields
    email: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        unique=True,
        index=True
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), 
        nullable=False
    )
    
    # Admin and access control
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        index=True
    )
    is_disabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False
    )
    # New self-registrations start unapproved and can't log in until an
    # admin approves them (see AuthService.register/login). Column defaults
    # to True so existing accounts aren't retroactively locked out.
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True
    )
    
    # Brute force protection
    failed_login_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0
    )
    locked_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        nullable=False, 
        server_default=func.now(),
        onupdate=func.now()
    )
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )

    # Exam-cycle setting: when null, app.config.default_exam_date is used.
    # Final Active Recall cutoff and Reference Mode end are both derived
    # from this (see app.services.adaptive_engine).
    exam_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Customizable adaptive-engine rules. When custom_ladders is null, the
    # built-in defaults (app.services.adaptive_engine.LADDERS) are used - a
    # user only ever overrides all three categories at once, never partially.
    custom_ladders: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    no_revision_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    no_revision_weekday: Mapped[int] = mapped_column(Integer, nullable=False, default=6)

    # Relationships
    subjects: Mapped[list["Subject"]] = relationship(
        "Subject",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        """Safe repr that doesn't expose sensitive data."""
        return f"<User(id={self.id}, email={self.email[:3]}***{'[ADMIN]' if self.is_admin else ''})>"
