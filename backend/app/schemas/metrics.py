"""Pydantic schema for the Metrics page."""

from pydantic import BaseModel


class CategoryDistribution(BaseModel):
    HARD: int
    MEDIUM: int
    EASY: int


class MetricsResponse(BaseModel):
    total_chapters: int
    category_distribution: CategoryDistribution
    overdue_count: int
    average_sessions_per_chapter: float
    total_sessions: int
    final_recall_reached_count: int
    reread_completed_count: int
