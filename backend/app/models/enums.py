"""Shared enums for the adaptive Active Recall system."""

import enum


class Category(str, enum.Enum):
    HARD = "HARD"
    MEDIUM = "MEDIUM"
    EASY = "EASY"


class Rating(str, enum.Enum):
    MAJOR_GAPS = "MAJOR_GAPS"
    MANY_CONFUSIONS = "MANY_CONFUSIONS"
    GOOD_MINOR_HESITATION = "GOOD_MINOR_HESITATION"
    EXCELLENT = "EXCELLENT"
