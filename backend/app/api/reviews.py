"""
Review API endpoints.

Handles today's due chapters, completing a review (with rating), and
calendar range data.

Security: All endpoints require authentication and are scoped to the current user.
"""

from datetime import date
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.review_service import ReviewService
from app.schemas.review import (
    TodayReviewsResponse,
    DueItem,
    CompleteReviewRequest,
    CompleteReviewResponse,
    RangeReviewsResponse,
    CalendarItem,
)
from app.config import get_settings

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

settings = get_settings()

# Maximum allowed range in days for the /range endpoint
MAX_RANGE_DAYS = 370


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
    Get chapters due for review today (or overdue), sorted by
    overdue-priority: Hard, then Medium, then Easy.
    """
    today = review_service.get_today(tz)
    items = review_service.get_due_today(tz)

    return TodayReviewsResponse(
        today=today,
        timezone=tz,
        items=[DueItem(**item) for item in items],
        count=len(items),
    )


@router.get("/range", response_model=RangeReviewsResponse)
def get_reviews_in_range(
    start: date = Query(..., description="Start date of range (inclusive, YYYY-MM-DD)"),
    end: date = Query(..., description="End date of range (inclusive, YYYY-MM-DD)"),
    tz: str = Query(
        default=settings.default_timezone,
        description="Timezone for date calculations",
        alias="tz"
    ),
    review_service: ReviewService = Depends(get_review_service),
):
    """
    Calendar data for a date range: each chapter's single upcoming
    next_due_date (if within range) plus completed-session history.
    """
    if start > end:
        raise HTTPException(status_code=400, detail="Start date must be before or equal to end date")

    range_days = (end - start).days + 1
    if range_days > MAX_RANGE_DAYS:
        raise HTTPException(
            status_code=400,
            detail=f"Date range too large. Maximum allowed: {MAX_RANGE_DAYS} days"
        )

    by_date = review_service.get_calendar_range(start, end, tz)

    items: dict[str, list[CalendarItem]] = {}
    total_count = 0
    for date_key, entries in by_date.items():
        date_str = date_key.isoformat()
        items[date_str] = [CalendarItem(**entry) for entry in entries]
        total_count += len(entries)

    return RangeReviewsResponse(
        timezone=tz,
        start=start,
        end=end,
        items=items,
        total_count=total_count,
    )


@router.post("/complete", response_model=CompleteReviewResponse)
def complete_review(
    data: CompleteReviewRequest,
    tz: str = Query(
        default=settings.default_timezone,
        description="Timezone for date calculations",
        alias="tz"
    ),
    review_service: ReviewService = Depends(get_review_service),
):
    """
    Complete an Active Recall session with a rating. If this session
    becomes the chapter's Final Active Recall, the response flags it and
    includes the banner message.
    """
    try:
        result = review_service.complete_review(
            subject_id=data.subject_id,
            rating=data.rating,
            completed_at=data.completed_at,
            timezone=tz,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return CompleteReviewResponse(**result)
