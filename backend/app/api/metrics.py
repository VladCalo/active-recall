"""
Metrics API - aggregate stats for the Metrics page (category distribution,
overdue count, sessions, reread-completion progress).

Security: scoped to the authenticated user.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.review_service import ReviewService
from app.schemas.metrics import MetricsResponse

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


def get_review_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewService:
    return ReviewService(db, current_user)


@router.get("", response_model=MetricsResponse)
def get_metrics(review_service: ReviewService = Depends(get_review_service)):
    return MetricsResponse(**review_service.get_metrics())
