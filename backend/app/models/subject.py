"""
Subject model - represents a study subject for active recall tracking.

A Subject has:
- A unique name per user (case-insensitive)
- A start date (when studying began)
- A schedule type (DEFAULT or CUSTOM)
- Optional custom intervals for CUSTOM schedule type
- An owner (user_id foreign key)
"""

import uuid
import enum
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Date, DateTime, Enum, JSON, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class ScheduleType(str, enum.Enum):
    """
    Schedule type for active recall.
    
    DEFAULT: Uses the standard intervals [1, 3, 7, 14, 30, 60, 120, 180] days
    CUSTOM: Uses user-defined intervals
    """
    DEFAULT = "DEFAULT"
    CUSTOM = "CUSTOM"


class Subject(Base):
    """
    Subject ORM model.
    
    Represents a study subject that needs periodic review based on
    spaced repetition / active recall principles.
    
    Attributes:
        id: UUID primary key (stored as string for SQLite compatibility)
        user_id: Foreign key to the owning user
        name: Subject name (unique per user, case-insensitive enforced at app level)
        start_date: The date when studying this subject began
        schedule_type: Either DEFAULT or CUSTOM
        custom_intervals_days: JSON array of integers (only used when schedule_type=CUSTOM)
        created_at: Timestamp when record was created
        updated_at: Timestamp when record was last updated
    """
    __tablename__ = "subjects"
    
    # Table-level constraints
    __table_args__ = (
        # Index for efficient user-scoped queries
        Index('ix_subjects_user_id', 'user_id'),
        # Composite index for user+name lookups (uniqueness enforced at app level)
        Index('ix_subjects_user_id_name', 'user_id', 'name'),
    )

    id: Mapped[str] = mapped_column(
        String(36), 
        primary_key=True, 
        default=lambda: str(uuid.uuid4())
    )
    
    # Foreign key to user - every subject belongs to exactly one user
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType), 
        nullable=False, 
        default=ScheduleType.DEFAULT
    )
    custom_intervals_days: Mapped[Optional[list]] = mapped_column(
        JSON, 
        nullable=True,
        default=None
    )
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
    
    # Relationship to user
    user: Mapped["User"] = relationship("User", back_populates="subjects")

    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, name={self.name}, user_id={self.user_id})>"
