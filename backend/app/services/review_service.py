"""
Review service - the adaptive Active Recall scheduling engine's DB-facing
layer: today's due chapters, completing a review, and calendar data.

Security: All operations are scoped to the authenticated user.
"""

from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session

from app.models.subject import Subject
from app.models.review_completion import ReviewCompletion
from app.models.enums import Category, Rating
from app.models.user import User
from app.services.subject_service import SubjectService
from app.services.adaptive_engine import (
    State,
    apply_rating,
    next_due_date as engine_next_due_date,
    is_final_active_recall,
    REREAD_INTENSITY,
)
from app.config import get_settings
from app.core.timeutil import today_in_tz

# Overdue-priority sort order for the "today" list.
_CATEGORY_PRIORITY = {Category.HARD: 0, Category.MEDIUM: 1, Category.EASY: 2}


class ReviewService:
    """
    Handles completing reviews and querying due/calendar/reference-mode data.

    All operations are scoped to a specific user for security.
    """

    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.settings = get_settings()
        self.subject_service = SubjectService(db, user)

    def get_today(self, timezone: str = None) -> date:
        return today_in_tz(timezone or self.settings.default_timezone)

    def is_reference_mode(self, timezone: str = None) -> bool:
        return self.get_today(timezone) >= self.settings.final_recall_cutoff_date

    # ------------------------------------------------------------------
    # Phase 1: Adaptive Active Recall
    # ------------------------------------------------------------------

    def get_due_today(self, timezone: str = None) -> list[dict]:
        """
        Chapters due today or overdue, sorted:
        Overdue Hard, Today's Hard, Overdue Medium, Today's Medium,
        Overdue Easy, Today's Easy.
        """
        today = self.get_today(timezone)
        subjects = self.subject_service.get_all()

        due = [
            s for s in subjects
            if not s.is_final_recall_reached and s.next_due_date is not None and s.next_due_date <= today
        ]

        def sort_key(s: Subject):
            is_overdue = s.next_due_date < today
            return (_CATEGORY_PRIORITY[s.category], 0 if is_overdue else 1, s.name)

        due.sort(key=sort_key)

        return [
            {
                "subject_id": s.id,
                "subject_name": s.name,
                "category": s.category,
                "stage": s.stage,
                "due_date": s.next_due_date,
                "is_overdue": s.next_due_date < today,
            }
            for s in due
        ]

    def complete_review(
        self,
        subject_id: str,
        rating: Rating,
        completed_at: Optional[date] = None,
        timezone: str = None,
    ) -> dict:
        """
        Complete an Active Recall session: apply the rating, update the
        chapter's (category, stage), and detect whether this was its Final
        Active Recall.
        """
        subject = self.subject_service.get_by_id(subject_id)
        if not subject:
            raise ValueError("Subject not found")

        if subject.is_final_recall_reached:
            raise ValueError("This chapter has already reached its Final Active Recall")

        completed_at = completed_at or self.get_today(timezone)

        current_state = State(subject.category, subject.stage)
        new_state = apply_rating(current_state, rating)
        final = is_final_active_recall(completed_at, new_state, self.settings.final_recall_cutoff_date)

        completion = ReviewCompletion(
            user_id=self.user.id,
            subject_id=subject.id,
            completed_at=completed_at,
            rating=rating,
            category_before=current_state.category,
            stage_before=current_state.stage,
            category_after=new_state.category,
            stage_after=new_state.stage,
        )
        self.db.add(completion)

        subject.last_active_recall_date = completed_at
        subject.category = new_state.category
        subject.stage = new_state.stage

        banner_message = None
        if final:
            subject.is_final_recall_reached = True
            subject.final_active_recall_date = completed_at
            subject.final_category = new_state.category
            subject.next_due_date = None
            banner_message = (
                "This is the final Active Recall for this chapter before Final Rereading begins."
            )
        else:
            subject.next_due_date = engine_next_due_date(completed_at, new_state)

        self.db.commit()
        self.db.refresh(subject)

        return {
            "subject_id": subject.id,
            "category": subject.category,
            "stage": subject.stage,
            "next_due_date": subject.next_due_date,
            "is_final_recall": final,
            "banner_message": banner_message,
        }

    def get_calendar_range(self, start: date, end: date, timezone: str = None) -> dict[date, list[dict]]:
        """
        Calendar data for a date range: each chapter's single upcoming
        next_due_date (if it falls in range) plus historical completed
        sessions in range. Unlike the old static schedule, future dates
        beyond the immediate next_due_date can't be shown - they depend on
        a rating that hasn't happened yet.
        """
        subjects = self.subject_service.get_all()
        subject_ids = [s.id for s in subjects]
        subjects_by_id = {s.id: s for s in subjects}

        result: dict[date, list[dict]] = {}

        for s in subjects:
            if not s.is_final_recall_reached and s.next_due_date is not None and start <= s.next_due_date <= end:
                result.setdefault(s.next_due_date, []).append({
                    "subject_id": s.id,
                    "subject_name": s.name,
                    "type": "upcoming",
                    "category": s.category,
                    "rating": None,
                })

        if subject_ids:
            completions = self.db.query(ReviewCompletion).filter(
                ReviewCompletion.subject_id.in_(subject_ids),
                ReviewCompletion.completed_at >= start,
                ReviewCompletion.completed_at <= end,
            ).all()
            for c in completions:
                subject = subjects_by_id.get(c.subject_id)
                if not subject:
                    continue
                result.setdefault(c.completed_at, []).append({
                    "subject_id": c.subject_id,
                    "subject_name": subject.name,
                    "type": "completed",
                    "category": c.category_after,
                    "rating": c.rating,
                })

        return result

    # ------------------------------------------------------------------
    # Phase 2: Reference Mode / Final Rereading
    # ------------------------------------------------------------------

    def get_reference_mode_chapters(self) -> list[dict]:
        """All chapters that have reached their Final Active Recall."""
        subjects = self.subject_service.get_all()
        chapters = []
        for s in subjects:
            if not s.is_final_recall_reached:
                continue
            intensity = REREAD_INTENSITY[s.final_category]
            chapters.append({
                "subject_id": s.id,
                "subject_name": s.name,
                "last_active_recall_date": s.last_active_recall_date,
                "final_category": s.final_category,
                "total_active_recall_count": self.subject_service.total_active_recall_count(s),
                "recommended_intensity_label": intensity["label"],
                "recommended_focus": intensity["focus"],
                "reread_completed": s.reread_completed_at is not None,
                "reread_completed_at": s.reread_completed_at,
            })
        return chapters

    def complete_reread(self, subject_id: str, timezone: str = None) -> Subject:
        subject = self.subject_service.get_by_id(subject_id)
        if not subject:
            raise ValueError("Subject not found")
        if not subject.is_final_recall_reached:
            raise ValueError("This chapter hasn't reached its Final Active Recall yet")
        if subject.reread_completed_at is not None:
            raise ValueError("Final Reread already completed for this chapter")

        subject.reread_completed_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(subject)
        return subject

    def get_reference_mode_summary(self, timezone: str = None) -> dict:
        subjects = self.subject_service.get_all()
        total = len(subjects)
        completed = sum(1 for s in subjects if s.reread_completed_at is not None)
        remaining = total - completed
        percentage = (completed / total * 100) if total > 0 else 0.0
        today = self.get_today(timezone)
        days_remaining = (self.settings.exam_date - today).days

        return {
            "is_reference_mode": self.is_reference_mode(timezone),
            "chapters_completed": completed,
            "chapters_remaining": remaining,
            "percentage_completed": round(percentage, 1),
            "days_remaining_until_exam": days_remaining,
            "exam_date": self.settings.exam_date,
        }
