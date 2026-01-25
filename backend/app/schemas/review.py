"""
Pydantic schemas for review-related operations.

These schemas handle the today's reviews and upcoming reviews responses.
"""

from datetime import date
from pydantic import BaseModel, Field
from app.schemas.subject import SubjectWithNextDue


class TodayReviewsResponse(BaseModel):
    """Response schema for today's reviews endpoint."""
    today: date = Field(..., description="Today's date in the requested timezone")
    timezone: str = Field(..., description="Timezone used for date calculation")
    subjects: list[SubjectWithNextDue] = Field(
        ..., 
        description="Subjects due for review today"
    )
    count: int = Field(..., description="Number of subjects due today")


class UpcomingReviewsResponse(BaseModel):
    """Response schema for upcoming reviews endpoint."""
    start_date: date = Field(..., description="Start of the date range")
    end_date: date = Field(..., description="End of the date range")
    timezone: str = Field(..., description="Timezone used for date calculation")
    reviews: dict[str, list[SubjectWithNextDue]] = Field(
        ...,
        description="Map of date strings to subjects due on that date"
    )
    total_count: int = Field(..., description="Total number of reviews in the period")


class CalendarSubject(BaseModel):
    """Simplified subject info for calendar display."""
    subject_id: str = Field(..., description="Subject UUID")
    subject_name: str = Field(..., description="Subject name")
    start_date: date = Field(..., description="Subject start date")
    schedule_type: str = Field(..., description="DEFAULT or CUSTOM")
    revision_number: int = Field(..., description="Which revision this is (1-based)")
    total_revisions: int = Field(..., description="Total number of revisions in schedule")


class RangeReviewsResponse(BaseModel):
    """Response schema for calendar range endpoint."""
    timezone: str = Field(..., description="Timezone used for date calculation")
    start: date = Field(..., description="Start of the requested range")
    end: date = Field(..., description="End of the requested range")
    items: dict[str, list[CalendarSubject]] = Field(
        ...,
        description="Map of date strings (YYYY-MM-DD) to subjects due on that date"
    )
    total_count: int = Field(..., description="Total number of due items in the range")
