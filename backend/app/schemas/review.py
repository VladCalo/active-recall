"""
Pydantic schemas for review-related operations: today's due chapters,
completing a review, and calendar range data.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import Category, Rating


class DueItem(BaseModel):
    """A chapter due for Active Recall today (or overdue)."""
    subject_id: str
    subject_name: str
    category: Category
    stage: int
    due_date: date
    is_overdue: bool = Field(..., description="True if due_date is before today")


class TodayReviewsResponse(BaseModel):
    """Today's due chapters, sorted by overdue-priority (Hard, then Medium, then Easy)."""
    today: date
    timezone: str
    items: list[DueItem]
    count: int


class CompleteReviewRequest(BaseModel):
    subject_id: str = Field(..., description="Subject UUID")
    rating: Rating = Field(..., description="How the session went")
    completed_at: Optional[date] = Field(
        None, description="Date the session was actually completed (defaults to today)"
    )


class CompleteReviewResponse(BaseModel):
    subject_id: str
    category: Category
    stage: int
    next_due_date: Optional[date]
    is_final_recall: bool = Field(
        ..., description="True if this session was the chapter's Final Active Recall"
    )
    banner_message: Optional[str] = Field(
        None, description="Shown when is_final_recall is True"
    )


class CalendarItem(BaseModel):
    """A single calendar entry - either a completed session or the one upcoming date."""
    subject_id: str
    subject_name: str
    type: str = Field(..., description="'upcoming' or 'completed'")
    category: Category
    rating: Optional[Rating] = None


class RangeReviewsResponse(BaseModel):
    timezone: str
    start: date
    end: date
    items: dict[str, list[CalendarItem]] = Field(
        ..., description="Map of date strings (YYYY-MM-DD) to calendar entries on that date"
    )
    total_count: int
