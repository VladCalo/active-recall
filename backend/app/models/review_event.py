"""
ReviewEvent model - per-subject per-due-date completion tracking.

Tracks:
- Completion status for a specific due date
- Optional reschedule date for missed events
"""

import uuid
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Date, DateTime, Boolean, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.user import User


class ReviewEvent(Base):
    """
    ReviewEvent ORM model.

    Represents a single scheduled review occurrence (subject + due_date).
    """
    __tablename__ = "review_events"

    __table_args__ = (
        Index("ix_review_events_user_id", "user_id"),
        Index("ix_review_events_subject_due_date", "subject_id", "due_date", unique=True),
        Index("ix_review_events_rescheduled_to", "rescheduled_to"),
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
    subject_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False
    )

    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rescheduled_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

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

    user: Mapped["User"] = relationship("User")
    subject: Mapped["Subject"] = relationship("Subject")

