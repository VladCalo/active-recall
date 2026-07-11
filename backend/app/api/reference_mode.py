"""
Reference Mode API endpoints (Phase 2: Final Rereading).

Security: All endpoints require authentication and are scoped to the current user.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.review_service import ReviewService
from app.schemas.reference_mode import (
    ReferenceModeListResponse,
    ReferenceModeChapter,
    ReferenceModeSummary,
)
from app.config import get_settings

router = APIRouter(prefix="/api/reference-mode", tags=["reference-mode"])

settings = get_settings()


def get_review_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewService:
    return ReviewService(db, current_user)


@router.get("", response_model=ReferenceModeListResponse)
def list_reference_mode_chapters(
    review_service: ReviewService = Depends(get_review_service),
):
    """
    All chapters that have reached their Final Active Recall, with the
    recommended reread intensity and completion status.
    """
    chapters = review_service.get_reference_mode_chapters()
    return ReferenceModeListResponse(
        is_reference_mode=review_service.is_reference_mode(),
        cutoff_date=settings.final_recall_cutoff_date,
        chapters=[ReferenceModeChapter(**c) for c in chapters],
    )


@router.get("/summary", response_model=ReferenceModeSummary)
def get_reference_mode_summary(
    review_service: ReviewService = Depends(get_review_service),
):
    """Chapters completed/remaining, percentage, and days until the exam."""
    return ReferenceModeSummary(**review_service.get_reference_mode_summary())


@router.post("/{subject_id}/complete-reread", response_model=ReferenceModeChapter)
def complete_reread(
    subject_id: str,
    review_service: ReviewService = Depends(get_review_service),
):
    """Mark a chapter's Final Reread as completed."""
    try:
        review_service.complete_reread(subject_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    chapters = review_service.get_reference_mode_chapters()
    updated = next((c for c in chapters if c["subject_id"] == subject_id), None)
    if not updated:
        raise HTTPException(status_code=404, detail="Subject not found")
    return ReferenceModeChapter(**updated)
