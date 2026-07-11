"""
Tests for the adaptive Active Recall engine (app.services.adaptive_engine).

Covers every cell of the confirmed transition table, interval-ladder
capping, and Final Active Recall boundary detection. Pure unit tests -
no database involved.
"""

from datetime import date
import pytest

from app.services.adaptive_engine import (
    Category,
    Rating,
    State,
    apply_rating,
    get_interval,
    next_due_date,
    is_final_active_recall,
    DEFAULT_CATEGORY,
    DEFAULT_STAGE,
    shift_off_sunday,
    final_recall_cutoff_date,
    reference_mode_end_date,
)


class TestIntervalLadders:
    def test_hard_ladder(self):
        assert [get_interval(Category.HARD, s) for s in range(4)] == [2, 4, 6, 8]

    def test_medium_ladder(self):
        assert [get_interval(Category.MEDIUM, s) for s in range(4)] == [5, 8, 11, 14]

    def test_easy_ladder(self):
        assert [get_interval(Category.EASY, s) for s in range(4)] == [10, 14, 18, 21]

    @pytest.mark.parametrize("category,capped_interval", [
        (Category.HARD, 8),
        (Category.MEDIUM, 14),
        (Category.EASY, 21),
    ])
    def test_caps_at_max_stage(self, category, capped_interval):
        """Stage indices beyond 3 stay capped at the last ladder value."""
        assert get_interval(category, 3) == capped_interval
        assert get_interval(category, 4) == capped_interval
        assert get_interval(category, 99) == capped_interval

    def test_default_starting_state(self):
        assert DEFAULT_CATEGORY == Category.MEDIUM
        assert DEFAULT_STAGE == 0


class TestTransitionTable:
    """Every cell of the confirmed (current_category, rating) -> new_state table."""

    @pytest.mark.parametrize("current_category", [Category.HARD, Category.MEDIUM, Category.EASY])
    def test_major_gaps_always_resets_to_hard_stage_0(self, current_category):
        result = apply_rating(State(current_category, 2), Rating.MAJOR_GAPS)
        assert result == State(Category.HARD, 0)

    def test_many_confusions_hard_stays_hard_stage_1(self):
        # Flat reset to stage 1, regardless of current Hard stage.
        assert apply_rating(State(Category.HARD, 0), Rating.MANY_CONFUSIONS) == State(Category.HARD, 1)
        assert apply_rating(State(Category.HARD, 3), Rating.MANY_CONFUSIONS) == State(Category.HARD, 1)

    def test_many_confusions_medium_resets_to_medium_stage_0(self):
        assert apply_rating(State(Category.MEDIUM, 2), Rating.MANY_CONFUSIONS) == State(Category.MEDIUM, 0)

    def test_many_confusions_easy_demotes_to_medium_stage_0(self):
        assert apply_rating(State(Category.EASY, 2), Rating.MANY_CONFUSIONS) == State(Category.MEDIUM, 0)

    def test_good_hard_promotes_to_medium_stage_0(self):
        assert apply_rating(State(Category.HARD, 3), Rating.GOOD_MINOR_HESITATION) == State(Category.MEDIUM, 0)

    def test_good_medium_advances_one_stage_and_caps(self):
        s = State(Category.MEDIUM, 0)
        for expected_stage in [1, 2, 3, 3, 3]:
            s = apply_rating(s, Rating.GOOD_MINOR_HESITATION)
            assert s == State(Category.MEDIUM, expected_stage)

    def test_good_easy_resets_to_easy_stage_0(self):
        assert apply_rating(State(Category.EASY, 3), Rating.GOOD_MINOR_HESITATION) == State(Category.EASY, 0)

    def test_excellent_hard_promotes_to_medium_stage_1(self):
        assert apply_rating(State(Category.HARD, 0), Rating.EXCELLENT) == State(Category.MEDIUM, 1)

    def test_excellent_medium_promotes_to_easy_stage_0(self):
        assert apply_rating(State(Category.MEDIUM, 3), Rating.EXCELLENT) == State(Category.EASY, 0)

    def test_excellent_easy_advances_one_stage_and_caps(self):
        s = State(Category.EASY, 0)
        for expected_stage in [1, 2, 3, 3]:
            s = apply_rating(s, Rating.EXCELLENT)
            assert s == State(Category.EASY, expected_stage)

    def test_hard_chapters_never_jump_directly_to_easy(self):
        """Excellent from Hard can only reach Medium, never Easy, in one step."""
        result = apply_rating(State(Category.HARD, 0), Rating.EXCELLENT)
        assert result.category == Category.MEDIUM


class TestNextDueDate:
    def test_counts_from_completion_date_not_original_due_date(self):
        """Missed days: next interval always counts from actual completion."""
        completion = date(2026, 3, 9)  # Monday, so +5 days doesn't collide with Sunday
        state = State(Category.MEDIUM, 0)
        assert next_due_date(completion, state) == date(2026, 3, 14)  # +5 days


class TestFinalActiveRecallDetection:
    def test_detects_final_when_next_interval_crosses_cutoff(self):
        cutoff = date(2026, 10, 13)
        completion = date(2026, 10, 5)
        state = State(Category.EASY, 3)  # +21 days -> Oct 26
        assert is_final_active_recall(completion, state, cutoff) is True

    def test_not_final_when_next_interval_before_cutoff(self):
        cutoff = date(2026, 10, 13)
        completion = date(2026, 9, 1)
        state = State(Category.HARD, 0)  # +2 days -> Sep 3
        assert is_final_active_recall(completion, state, cutoff) is False

    def test_boundary_exact_cutoff_date_is_final(self):
        """Landing exactly on the cutoff date counts as final ('on or after')."""
        cutoff = date(2026, 10, 13)
        completion = date(2026, 10, 8)
        state = State(Category.HARD, 1)  # +4 days lands exactly on Oct 12... adjust to hit exactly
        # Use Medium stage 0 (+5 days) from Oct 8 -> Oct 13 exactly.
        state = State(Category.MEDIUM, 0)
        assert next_due_date(completion, state) == cutoff
        assert is_final_active_recall(completion, state, cutoff) is True

    def test_day_before_cutoff_is_not_final(self):
        cutoff = date(2026, 10, 13)
        completion = date(2026, 10, 7)
        state = State(Category.MEDIUM, 0)  # +5 days -> Oct 12
        assert next_due_date(completion, state) == date(2026, 10, 12)
        assert is_final_active_recall(completion, state, cutoff) is False


class TestSundayShift:
    def test_sunday_shifts_to_monday(self):
        assert shift_off_sunday(date(2026, 1, 25)) == date(2026, 1, 26)  # Sun -> Mon

    def test_non_sunday_unchanged(self):
        assert shift_off_sunday(date(2026, 1, 26)) == date(2026, 1, 26)  # Mon stays Mon

    def test_next_due_date_shifts_off_sunday(self):
        """Medium stage0 (+5 days) from 2026-01-20 (Tue) lands on 2026-01-25 (Sun) -> Mon 26."""
        completion = date(2026, 1, 20)
        assert completion.strftime("%A") == "Tuesday"
        result = next_due_date(completion, State(Category.MEDIUM, 0))
        assert result == date(2026, 1, 26)

    def test_final_recall_detection_uses_shifted_date(self):
        """The cutoff check must use the post-shift date, not the raw pre-shift Sunday."""
        cutoff = date(2026, 1, 26)  # exactly the shifted Monday
        completion = date(2026, 1, 20)
        state = State(Category.MEDIUM, 0)  # raw target is Sunday 1/25, shifted to Mon 1/26
        assert is_final_active_recall(completion, state, cutoff) is True


class TestExamDateDerivedDates:
    def test_final_recall_cutoff_is_31_days_before_exam(self):
        assert final_recall_cutoff_date(date(2026, 11, 13)) == date(2026, 10, 13)

    def test_reference_mode_end_is_1_day_before_exam(self):
        assert reference_mode_end_date(date(2026, 11, 13)) == date(2026, 11, 12)
