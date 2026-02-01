"""
Review service - handles review scheduling logic.

This service computes due dates based on spaced repetition intervals
and determines which subjects need review on specific dates.

Security: All operations are scoped to the authenticated user.
"""

from datetime import date, timedelta
from zoneinfo import ZoneInfo
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.subject import Subject, ScheduleType
from app.models.review_event import ReviewEvent
from app.models.user import User
from app.services.subject_service import SubjectService
from app.config import get_settings


class ReviewService:
    """
    Service class for review scheduling operations.
    
    Handles all logic related to computing due dates and finding
    subjects that need review.
    
    All operations are scoped to a specific user for security.
    """

    def __init__(self, db: Session, user: User):
        """
        Initialize with database session and authenticated user.
        
        Args:
            db: Database session
            user: Authenticated user (all operations scoped to this user)
        """
        self.db = db
        self.user = user
        self.settings = get_settings()
        self.subject_service = SubjectService(db, user)

    def get_today(self, timezone: str = None) -> date:
        """
        Get today's date in the specified timezone.
        
        Args:
            timezone: IANA timezone string (e.g., 'Europe/Bucharest')
                     Defaults to settings.default_timezone
                     
        Returns:
            Today's date in the specified timezone
        """
        tz_str = timezone or self.settings.default_timezone
        tz = ZoneInfo(tz_str)
        from datetime import datetime
        return datetime.now(tz).date()

    def get_intervals(self, subject: Subject) -> list[int]:
        """
        Get the active intervals for a subject.
        
        Args:
            subject: Subject to get intervals for
            
        Returns:
            List of interval days
        """
        return self.subject_service.get_intervals(subject)

    def get_tracking_start_date(self, timezone: str = None) -> date:
        """
        Get the tracking start date for missed/completed logic.

        If not set, initialize to today.
        """
        if self.user.review_tracking_start_date:
            return self.user.review_tracking_start_date

        today = self.get_today(timezone)
        self.user.review_tracking_start_date = today
        self.db.commit()
        return today

    def compute_due_dates(self, subject: Subject) -> list[date]:
        """
        Compute all due dates for a subject based on its schedule.
        
        Each due date is: start_date + interval_days
        
        Args:
            subject: Subject to compute due dates for
            
        Returns:
            List of due dates, sorted ascending
            
        Example:
            If start_date = 2026-01-25 and intervals = [1, 3, 7]
            Due dates are: [2026-01-26, 2026-01-28, 2026-02-01]
        """
        intervals = self.get_intervals(subject)
        due_dates = []
        
        for interval in intervals:
            due_date = subject.start_date + timedelta(days=interval)
            due_dates.append(due_date)
        
        return sorted(due_dates)

    def get_next_due_date(
        self, 
        subject: Subject, 
        after_date: Optional[date] = None,
        timezone: str = None
    ) -> Optional[date]:
        """
        Get the next due date for a subject.
        
        Args:
            subject: Subject to check
            after_date: Only return dates after this date (exclusive)
                       Defaults to yesterday (so today is included)
            timezone: Timezone for computing 'today'
            
        Returns:
            Next due date, or None if all reviews are completed
        """
        if after_date is None:
            today = self.get_today(timezone)
            after_date = today - timedelta(days=1)  # Include today
        
        due_dates = self.compute_due_dates(subject)
        
        for due_date in due_dates:
            if due_date > after_date:
                return due_date
        
        return None

    def _get_review_event_map(
        self,
        subject_ids: list[str],
        start_date: date,
        end_date: date
    ) -> dict[tuple[str, date], ReviewEvent]:
        """
        Fetch review events for subjects in a date range.
        """
        if not subject_ids:
            return {}

        events = self.db.query(ReviewEvent).filter(
            ReviewEvent.subject_id.in_(subject_ids),
            ReviewEvent.due_date >= start_date,
            ReviewEvent.due_date <= end_date,
        ).all()

        return {(e.subject_id, e.due_date): e for e in events}

    def _build_event(
        self,
        subject: Subject,
        due_date: date,
        event: Optional[ReviewEvent],
        today: date,
        tracking_start_date: date
    ) -> dict:
        """
        Build event dict with completion/missed/reschedule status.
        """
        intervals = self.get_intervals(subject)
        total_revisions = len(intervals)
        revision_number = self.compute_due_dates(subject).index(due_date) + 1

        if due_date < tracking_start_date:
            return {}

        is_completed = event.is_completed if event else False
        rescheduled_to = event.rescheduled_to if event else None

        if is_completed:
            effective_date = rescheduled_to or due_date
            is_missed = False
        else:
            if rescheduled_to:
                # If rescheduled to a past date, treat as missed again
                if rescheduled_to < today:
                    effective_date = today
                    is_missed = True
                else:
                    effective_date = rescheduled_to
                    is_missed = due_date < today
            else:
                if due_date < today:
                    effective_date = today
                    is_missed = True
                else:
                    effective_date = due_date
                    is_missed = False

        return {
            "subject_id": str(subject.id),
            "subject_name": subject.name,
            "start_date": subject.start_date,
            "schedule_type": subject.schedule_type.value,
            "due_date": due_date,
            "effective_date": effective_date,
            "revision_number": revision_number,
            "total_revisions": total_revisions,
            "is_completed": is_completed,
            "is_missed": is_missed,
            "was_rescheduled": rescheduled_to is not None,
            "rescheduled_to": rescheduled_to,
        }

    def get_review_events_in_range(
        self,
        start_date: date,
        end_date: date,
        timezone: str = None
    ) -> dict[date, list[dict]]:
        """
        Get review events in a date range with missed/rescheduled logic applied.
        """
        today = self.get_today(timezone)
        tracking_start_date = self.get_tracking_start_date(timezone)
        subjects = self.subject_service.get_all()

        subject_ids = [s.id for s in subjects]
        event_map = self._get_review_event_map(subject_ids, tracking_start_date, end_date)

        result: dict[date, list[dict]] = {}

        for subject in subjects:
            due_dates = self.compute_due_dates(subject)
            for due_date in due_dates:
                if due_date < tracking_start_date or due_date > end_date:
                    continue

                event_record = event_map.get((subject.id, due_date))
                event = self._build_event(subject, due_date, event_record, today, tracking_start_date)
                if not event:
                    continue

                effective_date = event["effective_date"]
                if start_date <= effective_date <= end_date:
                    result.setdefault(effective_date, []).append(event)

        return result

    def set_event_completion(self, subject_id: str, due_date: date, is_completed: bool) -> ReviewEvent:
        """
        Mark a review event as completed or not completed.
        """
        subject = self.subject_service.get_by_id(subject_id)
        if not subject:
            raise ValueError("Subject not found")

        if due_date not in self.compute_due_dates(subject):
            raise ValueError("Due date is not part of this subject's schedule")

        event = self.db.query(ReviewEvent).filter(
            ReviewEvent.subject_id == subject_id,
            ReviewEvent.due_date == due_date,
            ReviewEvent.user_id == self.user.id
        ).first()

        if not event:
            event = ReviewEvent(
                user_id=self.user.id,
                subject_id=subject_id,
                due_date=due_date,
            )
            self.db.add(event)

        event.is_completed = is_completed
        event.completed_at = datetime.utcnow() if is_completed else None
        if is_completed:
            event.rescheduled_to = event.rescheduled_to  # keep reschedule info

        self.db.commit()
        self.db.refresh(event)
        return event

    def reschedule_event(self, subject_id: str, due_date: date, new_date: date, timezone: str = None) -> ReviewEvent:
        """
        Reschedule a missed event to a new date.
        """
        subject = self.subject_service.get_by_id(subject_id)
        if not subject:
            raise ValueError("Subject not found")

        if due_date not in self.compute_due_dates(subject):
            raise ValueError("Due date is not part of this subject's schedule")

        today = self.get_today(timezone)
        tracking_start_date = self.get_tracking_start_date(timezone)

        if due_date < tracking_start_date:
            raise ValueError("Cannot reschedule events before tracking start date")

        if due_date >= today:
            raise ValueError("Only missed events can be rescheduled")

        event = self.db.query(ReviewEvent).filter(
            ReviewEvent.subject_id == subject_id,
            ReviewEvent.due_date == due_date,
            ReviewEvent.user_id == self.user.id
        ).first()

        if not event:
            event = ReviewEvent(
                user_id=self.user.id,
                subject_id=subject_id,
                due_date=due_date,
            )
            self.db.add(event)

        event.is_completed = False
        event.completed_at = None
        event.rescheduled_to = new_date

        self.db.commit()
        self.db.refresh(event)
        return event
    def is_due_on_date(self, subject: Subject, target_date: date) -> bool:
        """
        Check if a subject is due for review on a specific date.
        
        Args:
            subject: Subject to check
            target_date: Date to check against
            
        Returns:
            True if subject has a review scheduled on target_date
        """
        due_dates = self.compute_due_dates(subject)
        return target_date in due_dates

    def get_revision_number(self, subject: Subject, target_date: date) -> Optional[int]:
        """
        Get the revision number (1-based) for a subject on a specific date.
        
        Args:
            subject: Subject to check
            target_date: Date to check
            
        Returns:
            Revision number (1-based) if due on that date, None otherwise
            
        Example:
            With intervals [1, 3, 7, 14]:
            - Day 1: revision 1
            - Day 3: revision 2
            - Day 7: revision 3
            - Day 14: revision 4
        """
        due_dates = self.compute_due_dates(subject)
        if target_date in due_dates:
            return due_dates.index(target_date) + 1  # 1-based
        return None

    def get_total_revisions(self, subject: Subject) -> int:
        """
        Get the total number of revisions for a subject.
        
        Args:
            subject: Subject to check
            
        Returns:
            Total number of revisions (length of intervals array)
        """
        return len(self.get_intervals(subject))

    def is_completed(self, subject: Subject, as_of_date: date = None, timezone: str = None) -> bool:
        """
        Check if all revisions for a subject are completed.
        
        Args:
            subject: Subject to check
            as_of_date: Check as of this date (defaults to today)
            timezone: Timezone for determining 'today'
            
        Returns:
            True if all due dates are in the past
        """
        if as_of_date is None:
            as_of_date = self.get_today(timezone)
        
        due_dates = self.compute_due_dates(subject)
        if not due_dates:
            return True
        
        # Completed if today is after the last due date
        return as_of_date > due_dates[-1]

    def get_subjects_due_today(self, timezone: str = None) -> list[Subject]:
        """
        Get all subjects due for review today for the current user.
        
        Args:
            timezone: Timezone for determining 'today'
            
        Returns:
            List of subjects due today
        """
        today = self.get_today(timezone)
        all_subjects = self.subject_service.get_all()
        
        return [
            subject for subject in all_subjects 
            if self.is_due_on_date(subject, today)
        ]

    def get_subjects_due_in_range(
        self, 
        start_date: date, 
        end_date: date
    ) -> dict[date, list[Subject]]:
        """
        Get all subjects due for review in a date range for the current user.
        
        Args:
            start_date: Start of range (inclusive)
            end_date: End of range (inclusive)
            
        Returns:
            Dict mapping dates to lists of subjects due on that date
        """
        all_subjects = self.subject_service.get_all()
        result: dict[date, list[Subject]] = {}
        
        current = start_date
        while current <= end_date:
            due_subjects = [
                subject for subject in all_subjects 
                if self.is_due_on_date(subject, current)
            ]
            if due_subjects:
                result[current] = due_subjects
            current += timedelta(days=1)
        
        return result
