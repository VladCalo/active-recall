"""
Tests for the ReviewService.

Tests cover:
- Due date computation
- Next due date calculation
- Finding subjects due on specific dates
"""

import pytest
from datetime import date, timedelta
from unittest.mock import patch

from app.services.review_service import ReviewService
from app.models.subject import Subject, ScheduleType


class TestComputeDueDates:
    """Tests for compute_due_dates method."""

    def test_default_schedule_computes_correct_dates(self, db, sample_subject):
        """Default schedule should use [1, 3, 7, 14, 30, 60, 120, 180] intervals."""
        service = ReviewService(db)
        due_dates = service.compute_due_dates(sample_subject)
        
        # start_date = 2026-01-25
        expected = [
            date(2026, 1, 26),   # +1
            date(2026, 1, 28),   # +3
            date(2026, 2, 1),    # +7
            date(2026, 2, 8),    # +14
            date(2026, 2, 24),   # +30
            date(2026, 3, 26),   # +60
            date(2026, 5, 25),   # +120
            date(2026, 7, 24),   # +180
        ]
        
        assert due_dates == expected

    def test_custom_schedule_computes_correct_dates(self, db, sample_custom_subject):
        """Custom schedule should use provided intervals [2, 5, 10, 20]."""
        service = ReviewService(db)
        due_dates = service.compute_due_dates(sample_custom_subject)
        
        # start_date = 2026-01-25, intervals = [2, 5, 10, 20]
        expected = [
            date(2026, 1, 27),   # +2
            date(2026, 1, 30),   # +5
            date(2026, 2, 4),    # +10
            date(2026, 2, 14),   # +20
        ]
        
        assert due_dates == expected

    def test_due_dates_are_sorted(self, db):
        """Due dates should always be sorted ascending."""
        subject = Subject(
            name="Test",
            start_date=date(2026, 1, 1),
            schedule_type=ScheduleType.CUSTOM,
            custom_intervals_days=[30, 1, 15, 7],  # Unsorted input
        )
        db.add(subject)
        db.commit()
        
        service = ReviewService(db)
        due_dates = service.compute_due_dates(subject)
        
        # Should be sorted
        assert due_dates == sorted(due_dates)


class TestIsDueOnDate:
    """Tests for is_due_on_date method."""

    def test_returns_true_when_due(self, db, sample_subject):
        """Should return True when subject is due on the given date."""
        service = ReviewService(db)
        
        # Day 1 after start (2026-01-26) should be due
        assert service.is_due_on_date(sample_subject, date(2026, 1, 26)) is True

    def test_returns_false_when_not_due(self, db, sample_subject):
        """Should return False when subject is not due on the given date."""
        service = ReviewService(db)
        
        # Day 2 after start (2026-01-27) should NOT be due for default schedule
        assert service.is_due_on_date(sample_subject, date(2026, 1, 27)) is False

    def test_start_date_is_not_due(self, db, sample_subject):
        """Start date itself should not be a due date."""
        service = ReviewService(db)
        
        # Start date (2026-01-25) is not a review date
        assert service.is_due_on_date(sample_subject, date(2026, 1, 25)) is False


class TestGetNextDueDate:
    """Tests for get_next_due_date method."""

    def test_returns_first_due_date_from_today(self, db, sample_subject):
        """Should return the next upcoming due date."""
        service = ReviewService(db)
        
        # Mock today as 2026-01-25 (start date)
        with patch.object(service, 'get_today', return_value=date(2026, 1, 25)):
            next_due = service.get_next_due_date(sample_subject)
            assert next_due == date(2026, 1, 26)  # First interval is +1

    def test_returns_none_when_all_completed(self, db, sample_subject):
        """Should return None when all reviews are in the past."""
        service = ReviewService(db)
        
        # Mock today as far in the future
        with patch.object(service, 'get_today', return_value=date(2027, 1, 1)):
            next_due = service.get_next_due_date(sample_subject)
            assert next_due is None

    def test_skips_past_due_dates(self, db, sample_subject):
        """Should skip due dates that are in the past."""
        service = ReviewService(db)
        
        # Mock today as 2026-01-30 (after first two intervals)
        with patch.object(service, 'get_today', return_value=date(2026, 1, 30)):
            next_due = service.get_next_due_date(sample_subject)
            # Next due after Jan 30 is Feb 1 (+7 days from Jan 25)
            assert next_due == date(2026, 2, 1)


class TestGetSubjectsDueToday:
    """Tests for get_subjects_due_today method."""

    def test_returns_subjects_due_today(self, db, sample_subject):
        """Should return subjects that are due on today's date."""
        service = ReviewService(db)
        
        # Mock today as 2026-01-26 (first due date)
        with patch.object(service, 'get_today', return_value=date(2026, 1, 26)):
            due_subjects = service.get_subjects_due_today()
            assert len(due_subjects) == 1
            assert due_subjects[0].name == "Cardiology"

    def test_returns_empty_when_nothing_due(self, db, sample_subject):
        """Should return empty list when no subjects are due."""
        service = ReviewService(db)
        
        # Mock today as 2026-01-27 (not a due date for default schedule)
        with patch.object(service, 'get_today', return_value=date(2026, 1, 27)):
            due_subjects = service.get_subjects_due_today()
            assert len(due_subjects) == 0

    def test_returns_multiple_subjects(self, db, sample_subject, sample_custom_subject):
        """Should return all subjects due on the same day."""
        # Modify custom subject to also be due on Jan 26
        sample_custom_subject.custom_intervals_days = [1, 5, 10]
        db.commit()
        
        service = ReviewService(db)
        
        with patch.object(service, 'get_today', return_value=date(2026, 1, 26)):
            due_subjects = service.get_subjects_due_today()
            assert len(due_subjects) == 2


class TestGetToday:
    """Tests for get_today method with timezone handling."""

    def test_uses_default_timezone(self, db):
        """Should use Europe/Bucharest by default."""
        service = ReviewService(db)
        today = service.get_today()
        
        # Just verify it returns a date object
        assert isinstance(today, date)

    def test_uses_specified_timezone(self, db):
        """Should use the specified timezone."""
        service = ReviewService(db)
        
        # Test with different timezone
        today_utc = service.get_today("UTC")
        today_bucharest = service.get_today("Europe/Bucharest")
        
        # Both should be valid dates (may or may not be the same depending on time)
        assert isinstance(today_utc, date)
        assert isinstance(today_bucharest, date)
