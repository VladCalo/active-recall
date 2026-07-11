"""
Subject model - represents a study chapter tracked by the adaptive
Active Recall engine (see app.services.adaptive_engine).

A Subject has:
- A unique name per user (case-insensitive)
- A start date (when studying began)
- A current (category, stage) state driving its next review interval
- Optional Final Active Recall / Reference Mode fields, populated once the
  chapter's next computed interval crosses the exam-cycle cutoff date
"""

import uuid
from datetime import datetime, date
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Date, DateTime, Enum, Integer, Boolean, ForeignKey, func, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base
from app.models.enums import Category

if TYPE_CHECKING:
    from app.models.user import User


class Subject(Base):
    """
    Subject ORM model - a chapter tracked through the two learning phases:

    Phase 1 (Adaptive Active Recall): category/stage/next_due_date drive
    when the chapter comes up for review, updated by the adaptive engine
    after every completed session.

    Phase 2 (Final Rereading / Reference Mode): once is_final_recall_reached
    is set, next_due_date is cleared and no more sessions are scheduled -
    final_category drives the recommended reread intensity, and
    reread_completed_at tracks progress through the final month.
    """
    __tablename__ = "subjects"

    __table_args__ = (
        Index('ix_subjects_user_id', 'user_id'),
        Index('ix_subjects_user_id_name', 'user_id', 'name'),
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

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)

    # --- Phase 1: Adaptive Active Recall state ---
    category: Mapped[Category] = mapped_column(
        Enum(Category), nullable=False, default=Category.MEDIUM
    )
    stage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_active_recall_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # --- Phase 2: Final Active Recall / Reference Mode ---
    is_final_recall_reached: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    final_active_recall_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    final_category: Mapped[Optional[Category]] = mapped_column(
        Enum(Category), nullable=True
    )
    reread_completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

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

    user: Mapped["User"] = relationship("User", back_populates="subjects")

    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, name={self.name}, category={self.category}, stage={self.stage})>"
