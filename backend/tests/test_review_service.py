"""
Tests for ReviewService: completing reviews, today's due list ordering,
Reference Mode summary/list, and forced cutover.
"""

from datetime import date, datetime
from unittest.mock import patch

import pytest

from app.models.enums import Category, Rating
from app.services.review_service import ReviewService
from app.services.subject_service import SubjectService


class TestCompleteReview:
    def test_updates_category_stage_and_next_due_date(self, db, test_user, sample_subject):
        service = ReviewService(db, test_user)
        result = service.complete_review(
            sample_subject.id, Rating.EXCELLENT, completed_at=date(2026, 1, 25)
        )
        # Medium + Excellent -> Easy, stage 0 (+10 days)
        assert result["category"] == Category.EASY
        assert result["stage"] == 0
        assert result["next_due_date"] == date(2026, 2, 4)
        assert result["is_final_recall"] is False
        assert result["banner_message"] is None

    def test_creates_completion_log_entry(self, db, test_user, sample_subject):
        service = ReviewService(db, test_user)
        service.complete_review(sample_subject.id, Rating.GOOD_MINOR_HESITATION, completed_at=date(2026, 1, 25))
        assert SubjectService(db, test_user).total_active_recall_count(sample_subject) == 1

    def test_next_interval_counts_from_completion_date_not_scheduled_date(self, db, test_user, sample_subject):
        """Even if completed late, the next interval counts from the real completion date."""
        service = ReviewService(db, test_user)
        # sample_subject was due 2026-01-30 (Medium, +5 from start 2026-01-25),
        # completed 3 days late on 2026-02-02
        result = service.complete_review(
            sample_subject.id, Rating.GOOD_MINOR_HESITATION, completed_at=date(2026, 2, 2)
        )
        # Medium + Good -> Medium stage 1 (+8 days) from Feb 2, not from the original due date
        assert result["next_due_date"] == date(2026, 2, 10)

    def test_detects_final_active_recall(self, db, test_user, sample_subject):
        service = ReviewService(db, test_user)
        # Force close to the cutoff: Easy stage 3 (+21 days) from Oct 5 lands Oct 26, past Oct 13 cutoff.
        # Push the subject to Easy stage 3 first via repeated excellent ratings, then complete near cutoff.
        db_subject = SubjectService(db, test_user).get_by_id(sample_subject.id)
        db_subject.category = Category.EASY
        db_subject.stage = 3
        db.commit()

        result = service.complete_review(
            sample_subject.id, Rating.EXCELLENT, completed_at=date(2026, 10, 5)
        )
        assert result["is_final_recall"] is True
        assert result["next_due_date"] is None
        assert "final Active Recall" in result["banner_message"]

        updated = SubjectService(db, test_user).get_by_id(sample_subject.id)
        assert updated.is_final_recall_reached is True
        assert updated.final_active_recall_date == date(2026, 10, 5)
        assert updated.final_category == Category.EASY

    def test_cannot_complete_already_final_subject(self, db, test_user, sample_subject):
        service = ReviewService(db, test_user)
        subject = SubjectService(db, test_user).get_by_id(sample_subject.id)
        subject.is_final_recall_reached = True
        db.commit()

        with pytest.raises(ValueError, match="already reached its Final Active Recall"):
            service.complete_review(sample_subject.id, Rating.EXCELLENT)

    def test_raises_for_unknown_subject(self, db, test_user):
        service = ReviewService(db, test_user)
        with pytest.raises(ValueError, match="not found"):
            service.complete_review("unknown-id", Rating.EXCELLENT)


class TestGetDueToday:
    def test_overdue_priority_ordering(self, db, test_user, sample_subject, sample_hard_subject):
        """Overdue Hard, Today's Hard, Overdue Medium, Today's Medium order."""
        service = ReviewService(db, test_user)
        subject_service = SubjectService(db, test_user)

        medium = subject_service.get_by_id(sample_subject.id)
        hard = subject_service.get_by_id(sample_hard_subject.id)

        with patch.object(ReviewService, "get_today", return_value=date(2026, 2, 1)):
            medium.next_due_date = date(2026, 1, 20)  # overdue medium
            hard.next_due_date = date(2026, 2, 1)      # today's hard
            db.commit()

            due = service.get_due_today()
            assert [d["category"] for d in due] == [Category.HARD, Category.MEDIUM]
            assert due[0]["is_overdue"] is False
            assert due[1]["is_overdue"] is True

    def test_excludes_final_recall_reached_subjects(self, db, test_user, sample_subject):
        service = ReviewService(db, test_user)
        subject = SubjectService(db, test_user).get_by_id(sample_subject.id)
        subject.is_final_recall_reached = True
        db.commit()

        with patch.object(ReviewService, "get_today", return_value=date(2026, 2, 1)):
            assert service.get_due_today() == []


class TestReferenceModeForcedCutover:
    def test_forces_cutover_when_cutoff_reached(self, db, test_user, sample_subject):
        subject_service = SubjectService(db, test_user)
        with patch.object(SubjectService, "_today", return_value=date(2026, 10, 20)):
            fetched = subject_service.get_by_id(sample_subject.id)
            assert fetched.is_final_recall_reached is True
            assert fetched.final_category == Category.MEDIUM  # default, never reviewed
            assert fetched.next_due_date is None

    def test_no_cutover_before_cutoff(self, db, test_user, sample_subject):
        subject_service = SubjectService(db, test_user)
        with patch.object(SubjectService, "_today", return_value=date(2026, 6, 1)):
            fetched = subject_service.get_by_id(sample_subject.id)
            assert fetched.is_final_recall_reached is False


class TestReferenceModeSummary:
    def test_summary_counts(self, db, test_user, sample_subject, sample_hard_subject):
        service = ReviewService(db, test_user)
        subject_service = SubjectService(db, test_user)

        subject = subject_service.get_by_id(sample_subject.id)
        subject.is_final_recall_reached = True
        subject.final_category = Category.MEDIUM
        subject.reread_completed_at = datetime.utcnow()
        db.commit()

        with patch.object(ReviewService, "get_today", return_value=date(2026, 10, 20)):
            summary = service.get_reference_mode_summary()

        assert summary["chapters_completed"] == 1
        assert summary["chapters_remaining"] == 1
        assert summary["percentage_completed"] == 50.0
        assert summary["is_reference_mode"] is True

