"""
Review API endpoints.

Handles review scheduling queries - what's due today, upcoming reviews, etc.
"""

from datetime import timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.review_service import ReviewService
from app.schemas.subject import SubjectWithNextDue
from app.schemas.review import TodayReviewsResponse, UpcomingReviewsResponse
from app.config import get_settings

router = APIRouter(prefix="/api/reviews", tags=["reviews"])

settings = get_settings()


def get_review_service(db: Session = Depends(get_db)) -> ReviewService:
    """Dependency to get ReviewService instance."""
    return ReviewService(db)


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
    Get subjects due for review today.
    
    Args:
        tz: Timezone string (e.g., 'Europe/Bucharest')
        
    Returns:
        Today's date, timezone, and list of subjects due
    """
    today = review_service.get_today(tz)
    subjects = review_service.get_subjects_due_today(tz)
    
    result_subjects = []
    for subject in subjects:
        next_due = review_service.get_next_due_date(subject, timezone=tz)
        intervals = review_service.get_intervals(subject)
        
        result_subjects.append(SubjectWithNextDue(
            id=subject.id,
            name=subject.name,
            start_date=subject.start_date,
            schedule_type=subject.schedule_type,
            custom_intervals_days=subject.custom_intervals_days,
            created_at=subject.created_at,
            updated_at=subject.updated_at,
            next_due_date=next_due,
            intervals=intervals,
        ))
    
    return TodayReviewsResponse(
        today=today,
        timezone=tz,
        subjects=result_subjects,
        count=len(result_subjects),
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
    Get subjects due for review in the upcoming N days.
    
    Args:
        days: Number of days to look ahead (1-365)
        tz: Timezone string
        
    Returns:
        Date range, timezone, and map of dates to subjects
    """
    today = review_service.get_today(tz)
    end_date = today + timedelta(days=days - 1)
    
    due_by_date = review_service.get_subjects_due_in_range(today, end_date)
    
    # Convert to response format
    reviews: dict[str, list[SubjectWithNextDue]] = {}
    total_count = 0
    
    for date_key, subjects in due_by_date.items():
        date_str = date_key.isoformat()
        reviews[date_str] = []
        
        for subject in subjects:
            next_due = review_service.get_next_due_date(subject, timezone=tz)
            intervals = review_service.get_intervals(subject)
            
            reviews[date_str].append(SubjectWithNextDue(
                id=subject.id,
                name=subject.name,
                start_date=subject.start_date,
                schedule_type=subject.schedule_type,
                custom_intervals_days=subject.custom_intervals_days,
                created_at=subject.created_at,
                updated_at=subject.updated_at,
                next_due_date=next_due,
                intervals=intervals,
            ))
            total_count += 1
    
    return UpcomingReviewsResponse(
        start_date=today,
        end_date=end_date,
        timezone=tz,
        reviews=reviews,
        total_count=total_count,
    )
