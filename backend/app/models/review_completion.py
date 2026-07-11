"""
ReviewCompletion model - a permanent log entry for each completed Active
Recall session.

Unlike the old ReviewEvent (one row per subject x scheduled due_date, toggled
completed/not), a ReviewCompletion row is only ever created once a session
is actually completed - there is no "not completed" state, since due dates
are no longer precomputed. Also records the (category, stage) transition
that session caused, giving a full audit trail and a trivial way to compute
a chapter's total Active Recall count.
"""

import uuid
from datetime import datetime, date
from typing import TYPE_CHECKING
from sqlalchemy import String, Date, DateTime, Enum, Integer, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import Category, Rating

if TYPE_CHECKING:
    from app.models.subject import Subject
    from app.models.user import User


class ReviewCompletion(Base):
    """One completed Active Recall session for a subject."""
    __tablename__ = "review_completions"

    __table_args__ = (
        Index("ix_review_completions_user_id", "user_id"),
        Index("ix_review_completions_subject_id", "subject_id"),
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

    completed_at: Mapped[date] = mapped_column(Date, nullable=False)
    rating: Mapped[Rating] = mapped_column(Enum(Rating), nullable=False)

    category_before: Mapped[Category] = mapped_column(Enum(Category), nullable=False)
    stage_before: Mapped[int] = mapped_column(Integer, nullable=False)
    category_after: Mapped[Category] = mapped_column(Enum(Category), nullable=False)
    stage_after: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )

    user: Mapped["User"] = relationship("User")
    subject: Mapped["Subject"] = relationship("Subject")
