"""
Subject service - handles all subject (chapter)-related business logic.

Security: All operations are scoped to the authenticated user.
"""

from datetime import date
from typing import Optional
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models.subject import Subject
from app.models.user import User
from app.schemas.subject import SubjectCreate, SubjectUpdate
from app.config import get_settings
from app.core.timeutil import today_in_tz
from app.services.adaptive_engine import DEFAULT_CATEGORY, DEFAULT_STAGE, State, next_due_date


class SubjectService:
    """
    Service class for Subject operations.

    All operations are scoped to a specific user for security.
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.settings = get_settings()

    def _today(self) -> date:
        return today_in_tz(self.settings.default_timezone)

    def _is_reference_mode(self) -> bool:
        return self._today() >= self.settings.final_recall_cutoff_date

    def _apply_forced_cutover(self, subject: Subject) -> Subject:
        """
        If the global Reference Mode cutoff has arrived and this chapter
        hasn't naturally reached its Final Active Recall yet, force it in -
        using whatever category it's currently sitting on (defaults to
        Medium if it was never reviewed at all, since that's the starting
        category).
        """
        if not subject.is_final_recall_reached and self._is_reference_mode():
            subject.is_final_recall_reached = True
            subject.final_active_recall_date = subject.last_active_recall_date or subject.start_date
            subject.final_category = subject.category
            subject.next_due_date = None
            self.db.commit()
            self.db.refresh(subject)
        return subject

    def get_all(self) -> list[Subject]:
        """Get all subjects for the current user, ordered by name."""
        subjects = self.db.query(Subject).filter(
            Subject.user_id == self.user.id
        ).order_by(Subject.name).all()
        return [self._apply_forced_cutover(s) for s in subjects]

    def get_by_id(self, subject_id: str) -> Optional[Subject]:
        subject = self.db.query(Subject).filter(
            and_(
                Subject.id == subject_id,
                Subject.user_id == self.user.id
            )
        ).first()
        if not subject:
            return None
        return self._apply_forced_cutover(subject)

    def get_by_name(self, name: str) -> Optional[Subject]:
        return self.db.query(Subject).filter(
            and_(
                func.lower(Subject.name) == name.lower().strip(),
                Subject.user_id == self.user.id
            )
        ).first()

    def create(self, data: SubjectCreate) -> Subject:
        """
        Create a new chapter for the current user, starting on Medium/stage 0.

        Raises:
            ValueError: If a subject with the same name already exists, or
                if new chapters are blocked because Reference Mode has started.
        """
        if self._is_reference_mode():
            raise ValueError(
                "Cannot create new chapters during Reference Mode "
                "(new chapters have no Active Recall history to build a Final category from)"
            )

        existing = self.get_by_name(data.name)
        if existing:
            raise ValueError(f"A subject with name '{data.name}' already exists")

        subject = Subject(
            user_id=self.user.id,
            name=data.name.strip(),
            start_date=data.start_date,
            category=DEFAULT_CATEGORY,
            stage=DEFAULT_STAGE,
            next_due_date=next_due_date(data.start_date, State(DEFAULT_CATEGORY, DEFAULT_STAGE)),
        )

        self.db.add(subject)
        self.db.commit()
        self.db.refresh(subject)
        return subject

    def update(self, subject_id: str, data: SubjectUpdate) -> Optional[Subject]:
        subject = self.get_by_id(subject_id)
        if not subject:
            return None

        if data.name is not None and data.name.strip().lower() != subject.name.lower():
            existing = self.get_by_name(data.name)
            if existing:
                raise ValueError(f"A subject with name '{data.name}' already exists")
            subject.name = data.name.strip()

        if data.start_date is not None:
            subject.start_date = data.start_date

        self.db.commit()
        self.db.refresh(subject)
        return subject

    def delete(self, subject_id: str) -> bool:
        subject = self.get_by_id(subject_id)
        if not subject:
            return False

        self.db.delete(subject)
        self.db.commit()
        return True

    def total_active_recall_count(self, subject: Subject) -> int:
        from app.models.review_completion import ReviewCompletion
        return self.db.query(ReviewCompletion).filter(
            ReviewCompletion.subject_id == subject.id
        ).count()
