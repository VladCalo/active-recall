"""
Review API endpoints.

Handles review scheduling queries - what's due today, upcoming reviews, etc.

Security: All endpoints require authentication and are scoped to the current user.
"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.review_service import ReviewService
from app.schemas.review import (
    TodayReviewsResponse, 
    UpcomingReviewsResponse,
    RangeReviewsResponse,
    CalendarSubject,
    ReviewEvent,
)
from app.config import get_settings

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

settings = get_settings()

# Maximum allowed range in days for the /range endpoint
MAX_RANGE_DAYS = 370


class ReviewEventCompleteRequest(BaseModel):
    subject_id: str = Field(..., description="Subject UUID")
    due_date: date = Field(..., description="Original due date (YYYY-MM-DD)")
    is_completed: bool = Field(True, description="Completion status")


class ReviewEventRescheduleRequest(BaseModel):
    subject_id: str = Field(..., description="Subject UUID")
    due_date: date = Field(..., description="Original due date (YYYY-MM-DD)")
    new_date: date = Field(..., description="New date to reschedule to (YYYY-MM-DD)")


def get_review_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewService:
    """Dependency to get ReviewService instance scoped to current user."""
    return ReviewService(db, current_user)


@router.get("/today", response_model=TodayReviewsResponse)
def get_today_reviews(
    tz: str = Query(
        default=settings.default_timezone,
        description="Timezone for determining 'today' (IANA format)",
        alias="tz"
    ),
    review_service: ReviewService = Depends(get_review_service),
):
    """
    Get subjects due for review today for the current user.
    
    Args:
        tz: Timezone string (e.g., 'Europe/Bucharest')
        
    Returns:
        Today's date, timezone, and list of subjects due
    """
    today = review_service.get_today(tz)
    items = review_service.get_review_events_in_range(today, today, tz)
    events = items.get(today, [])

    return TodayReviewsResponse(
        today=today,
        timezone=tz,
        events=[ReviewEvent(**event) for event in events],
        count=len(events),
    )


@router.get("/upcoming", response_model=UpcomingReviewsResponse)
def get_upcoming_reviews(
    days: int = Query(
        default=7,
        ge=1,
        le=365,
        description="Number of days to look ahead"
    ),
    tz: str = Query(
        default=settings.default_timezone,
        description="Timezone for date calculations",
        alias="tz"
    ),
    review_service: ReviewService = Depends(get_review_service),
):
    """
    Get subjects due for review in the upcoming N days for the current user.
    
    Args:
        days: Number of days to look ahead (1-365)
        tz: Timezone string
        
    Returns:
        Date range, timezone, and map of dates to subjects
    """
    today = review_service.get_today(tz)
    end_date = today + timedelta(days=days - 1)
    
    due_by_date = review_service.get_review_events_in_range(today, end_date, tz)

    reviews: dict[str, list[ReviewEvent]] = {}
    total_count = 0

    for date_key, events in due_by_date.items():
        date_str = date_key.isoformat()
        reviews[date_str] = [ReviewEvent(**event) for event in events]
        total_count += len(events)
    
    return UpcomingReviewsResponse(
        start_date=today,
        end_date=end_date,
        timezone=tz,
        reviews=reviews,
        total_count=total_count,
    )


@router.get("/range", response_model=RangeReviewsResponse)
def get_reviews_in_range(
    start: date = Query(
        ...,
        description="Start date of range (inclusive, YYYY-MM-DD)"
    ),
    end: date = Query(
        ...,
        description="End date of range (inclusive, YYYY-MM-DD)"
    ),
    tz: str = Query(
        default=settings.default_timezone,
        description="Timezone for date calculations",
        alias="tz"
    ),
    review_service: ReviewService = Depends(get_review_service),
):
    """
    Get subjects due for review in a specific date range for the current user.
    
    This endpoint is optimized for calendar views, returning due items
    grouped by date within the requested range.
    
    Args:
        start: Start date (inclusive)
        end: End date (inclusive)
        tz: Timezone string (e.g., 'Europe/Bucharest')
        
    Returns:
        Timezone, date range, and map of dates to subjects due
        
    Raises:
        400: If start > end or range exceeds MAX_RANGE_DAYS
    """
    # Validate date range
    if start > end:
        raise HTTPException(
            status_code=400,
            detail="Start date must be before or equal to end date"
        )
    
    range_days = (end - start).days + 1
    if range_days > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Date range too large. Maximum allowed: {MAX_RANGE_DAYS} days"
        )
    
    due_by_date = review_service.get_review_events_in_range(start, end, tz)

    items: dict[str, list[CalendarSubject]] = {}
    total_count = 0

    for date_key, events in due_by_date.items():
        date_str = date_key.isoformat()
        items[date_str] = [CalendarSubject(**event) for event in events]
        total_count += len(events)
    
    return RangeReviewsResponse(
        timezone=tz,
        start=start,
        end=end,
        items=items,
        total_count=total_count,
    )


@router.post("/events/complete")
def complete_review_event(
    data: ReviewEventCompleteRequest,
    review_service: ReviewService = Depends(get_review_service),
):
    """
    Mark a review event as completed or not completed.
    """
    try:
        event = review_service.set_event_completion(
            subject_id=data.subject_id,
            due_date=data.due_date,
            is_completed=data.is_completed,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"status": "ok", "event_id": event.id, "is_completed": event.is_completed}


@router.post("/events/reschedule")
def reschedule_review_event(
    data: ReviewEventRescheduleRequest,
    review_service: ReviewService = Depends(get_review_service),
    tz: str = Query(
        default=settings.default_timezone,
        description="Timezone for date calculations",
        alias="tz"
    ),
):
    """
    Reschedule a missed review event to a new date.
    """
    today = review_service.get_today(tz)
    if data.new_date < today:
        raise HTTPException(status_code=400, detail="Reschedule date must be today or later")

    try:
        event = review_service.reschedule_event(
            subject_id=data.subject_id,
            due_date=data.due_date,
            new_date=data.new_date,
            timezone=tz,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "status": "ok",
        "event_id": event.id,
        "rescheduled_to": event.rescheduled_to,
    }
