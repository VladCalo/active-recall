"""
Pydantic schemas for review-related operations.

These schemas handle the today's reviews and upcoming reviews responses.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class ReviewEvent(BaseModel):
    """Event info for a specific due date."""
    subject_id: str = Field(..., description="Subject UUID")
    subject_name: str = Field(..., description="Subject name")
    start_date: date = Field(..., description="Subject start date")
    schedule_type: str = Field(..., description="DEFAULT or CUSTOM")
    due_date: date = Field(..., description="Original scheduled due date")
    effective_date: date = Field(..., description="Displayed date (after missed/reschedule)")
    revision_number: int = Field(..., description="Which revision this is (1-based)")
    total_revisions: int = Field(..., description="Total number of revisions in schedule")
    is_completed: bool = Field(..., description="Whether this event is completed")
    is_missed: bool = Field(..., description="Whether this event was missed and moved")
    was_rescheduled: bool = Field(..., description="Whether this event was manually rescheduled")
    rescheduled_to: Optional[date] = Field(None, description="Manual reschedule target date")


class TodayReviewsResponse(BaseModel):
    """Response schema for today's reviews endpoint."""
    today: date = Field(..., description="Today's date in the requested timezone")
    timezone: str = Field(..., description="Timezone used for date calculation")
    events: list[ReviewEvent] = Field(
        ...,
        description="Review events effective today"
    )
    count: int = Field(..., description="Number of events due today")


class UpcomingReviewsResponse(BaseModel):
    """Response schema for upcoming reviews endpoint."""
    start_date: date = Field(..., description="Start of the date range")
    end_date: date = Field(..., description="End of the date range")
    timezone: str = Field(..., description="Timezone used for date calculation")
    reviews: dict[str, list[ReviewEvent]] = Field(
        ...,
        description="Map of date strings to events due on that date"
    )
    total_count: int = Field(..., description="Total number of reviews in the period")


class CalendarSubject(ReviewEvent):
    """Event info for calendar display (alias)."""
    pass


class RangeReviewsResponse(BaseModel):
    """Response schema for calendar range endpoint."""
    timezone: str = Field(..., description="Timezone used for date calculation")
    start: date = Field(..., description="Start of the requested range")
    end: date = Field(..., description="End of the requested range")
    items: dict[str, list[CalendarSubject]] = Field(
        ...,
        description="Map of date strings (YYYY-MM-DD) to events on that date"
    )
    total_count: int = Field(..., description="Total number of due items in the range")
