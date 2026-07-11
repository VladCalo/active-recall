"""
Adaptive Active Recall engine.

Pure, side-effect-free scheduling logic for the Hard/Medium/Easy category
system. Each category has its own interval ladder (days until next review);
a rating given after completing a review moves the chapter to a new
(category, stage) pair, which determines the next interval.

Kept separate from the DB/service layer so the full rule table can be
unit-tested without a database.
"""

from datetime import date, timedelta
from typing import NamedTuple, Optional

from app.models.enums import Category, Rating


# Interval ladder per category: index = stage (0-based). Once the last stage
# is reached, the interval stays capped there indefinitely. This is the
# built-in default - a user may override it entirely (see RulesConfig below),
# but never partially: an override always supplies all three categories.
LADDERS: dict[Category, list[int]] = {
    Category.HARD: [2, 4, 6, 8],
    Category.MEDIUM: [5, 8, 11, 14],
    Category.EASY: [10, 14, 18, 21],
}

MAX_STAGE = 3  # every ladder has 4 stages, indices 0-3

# Default starting state for a brand-new chapter (before its first review).
DEFAULT_CATEGORY = Category.MEDIUM
DEFAULT_STAGE = 0

# Default "no revisions on this day" rule (Sunday, Python's date.weekday()
# where Monday=0 ... Sunday=6).
DEFAULT_NO_REVISION_ENABLED = True
DEFAULT_NO_REVISION_WEEKDAY = 6


class State(NamedTuple):
    category: Category
    stage: int


class RulesConfig(NamedTuple):
    """
    A user's customizable scheduling rules. Defaults reproduce the built-in
    behavior exactly - only ladders and the no-revision-day rule are
    user-editable; the rating transition table itself is fixed.
    """
    ladders: dict[Category, list[int]] = LADDERS
    no_revision_enabled: bool = DEFAULT_NO_REVISION_ENABLED
    no_revision_weekday: int = DEFAULT_NO_REVISION_WEEKDAY


DEFAULT_RULES = RulesConfig()


def validate_ladders(ladders: dict[str, list[int]]) -> None:
    """
    Raise ValueError if a custom ladder set isn't exactly 3 categories x 4
    strictly-ascending positive-integer stages.
    """
    expected_categories = {c.value for c in Category}
    if set(ladders.keys()) != expected_categories:
        raise ValueError(f"Ladders must supply exactly these categories: {sorted(expected_categories)}")

    for category_name, days in ladders.items():
        if len(days) != 4:
            raise ValueError(f"{category_name}: must have exactly 4 stages, got {len(days)}")
        if not all(isinstance(d, int) and d > 0 for d in days):
            raise ValueError(f"{category_name}: all stage intervals must be positive integers")
        if list(days) != sorted(days) or len(set(days)) != len(days):
            raise ValueError(f"{category_name}: stage intervals must be strictly ascending")


def ladders_from_dict(data: dict[str, list[int]]) -> dict[Category, list[int]]:
    return {Category(k): v for k, v in data.items()}


def ladders_to_dict(ladders: dict[Category, list[int]]) -> dict[str, list[int]]:
    return {k.value: v for k, v in ladders.items()}


def get_interval(category: Category, stage: int, rules: RulesConfig = DEFAULT_RULES) -> int:
    """Days until next review for a given (category, stage)."""
    ladder = rules.ladders[category]
    return ladder[min(stage, MAX_STAGE)]


def _advance(state: State) -> State:
    """Move one step forward in the current category's own ladder, capped at MAX_STAGE."""
    return State(state.category, min(state.stage + 1, MAX_STAGE))


# Explicit transition table: (current_category, rating) -> new State.
# Entries using "progress" are resolved at call time via _advance() so they
# correctly account for the *current* stage; all other entries are fixed
# (category, stage) targets exactly as specified, not relative movement.
_FIXED_TRANSITIONS: dict[tuple[Category, Rating], State] = {
    # Major gaps: always resets straight to Hard, stage 0, regardless of
    # current category.
    (Category.HARD, Rating.MAJOR_GAPS): State(Category.HARD, 0),
    (Category.MEDIUM, Rating.MAJOR_GAPS): State(Category.HARD, 0),
    (Category.EASY, Rating.MAJOR_GAPS): State(Category.HARD, 0),

    # Many confusions
    (Category.HARD, Rating.MANY_CONFUSIONS): State(Category.HARD, 1),
    (Category.MEDIUM, Rating.MANY_CONFUSIONS): State(Category.MEDIUM, 0),
    (Category.EASY, Rating.MANY_CONFUSIONS): State(Category.MEDIUM, 0),

    # Good, minor hesitation
    (Category.HARD, Rating.GOOD_MINOR_HESITATION): State(Category.MEDIUM, 0),
    # Medium + Good -> progress through the Medium ladder (resolved dynamically)
    (Category.EASY, Rating.GOOD_MINOR_HESITATION): State(Category.EASY, 0),

    # Excellent
    (Category.HARD, Rating.EXCELLENT): State(Category.MEDIUM, 1),
    (Category.MEDIUM, Rating.EXCELLENT): State(Category.EASY, 0),
    # Easy + Excellent -> progress through the Easy ladder (resolved dynamically)
}

# (category, rating) pairs that mean "advance one stage within the same
# category" instead of a fixed target - depends on current stage.
_PROGRESS_TRANSITIONS: set[tuple[Category, Rating]] = {
    (Category.MEDIUM, Rating.GOOD_MINOR_HESITATION),
    (Category.EASY, Rating.EXCELLENT),
}


def apply_rating(current: State, rating: Rating) -> State:
    """
    Apply a review rating to the current (category, stage) state and return
    the new state, per the confirmed transition table.
    """
    key = (current.category, rating)
    if key in _PROGRESS_TRANSITIONS:
        return _advance(current)
    return _FIXED_TRANSITIONS[key]


def shift_off_no_revision_day(d: date, rules: RulesConfig = DEFAULT_RULES) -> date:
    """Push a date one day later if it lands on the configured no-revision weekday."""
    if rules.no_revision_enabled and d.weekday() == rules.no_revision_weekday:
        return d + timedelta(days=1)
    return d


def shift_off_sunday(d: date) -> date:
    """No revisions on Sunday - push it to Monday. (Built-in default rule.)"""
    return shift_off_no_revision_day(d, DEFAULT_RULES)


def next_due_date(completion_date: date, new_state: State, rules: RulesConfig = DEFAULT_RULES) -> date:
    """
    The next review date, always counted from the actual completion date,
    shifted off the no-revision day if it would land on one.
    """
    raw = completion_date + timedelta(days=get_interval(new_state.category, new_state.stage, rules))
    return shift_off_no_revision_day(raw, rules)


def is_final_active_recall(
    completion_date: date, new_state: State, cutoff_date: date, rules: RulesConfig = DEFAULT_RULES
) -> bool:
    """
    True if the next scheduled review (given the state that resulted from
    this completion) would fall on or after the cutoff date - meaning the
    review just completed is this chapter's Final Active Recall.
    """
    return next_due_date(completion_date, new_state, rules) >= cutoff_date


# Fixed offsets from the exam date (Oct 13 -> Nov 13 is 31 days; Reference
# Mode ends the day before the exam).
FINAL_RECALL_CUTOFF_DAYS_BEFORE_EXAM = 31
REFERENCE_MODE_END_DAYS_BEFORE_EXAM = 1


def final_recall_cutoff_date(exam_date: date) -> date:
    return exam_date - timedelta(days=FINAL_RECALL_CUTOFF_DAYS_BEFORE_EXAM)


def reference_mode_end_date(exam_date: date) -> date:
    return exam_date - timedelta(days=REFERENCE_MODE_END_DAYS_BEFORE_EXAM)


REREAD_INTENSITY: dict[Category, dict[str, object]] = {
    Category.HARD: {
        "label": "Deep Reread",
        "focus": ["careful reading", "weak concepts", "difficult sections", "tables", "algorithms", "treatment details"],
    },
    Category.MEDIUM: {
        "label": "Focused Reread",
        "focus": ["normal reading pace", "previously difficult paragraphs", "previous weak points"],
    },
    Category.EASY: {
        "label": "Quick Reread",
        "focus": ["rapid chapter overview", "titles", "diagrams", "tables", "key values"],
    },
}
