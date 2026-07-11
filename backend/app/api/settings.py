"""
Exam-cycle settings API - lets a user set their own exam date, from which
the Final Active Recall cutoff and Reference Mode end date are derived.

Security: scoped to the authenticated user (each user has their own exam date).
"""

from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.settings import ExamSettingsResponse, ExamSettingsUpdate
from app.services.adaptive_engine import final_recall_cutoff_date, reference_mode_end_date
from app.config import get_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])

settings = get_settings()


def _build_response(user: User) -> ExamSettingsResponse:
    exam_date = user.exam_date or settings.default_exam_date
    return ExamSettingsResponse(
        exam_date=exam_date,
        final_recall_cutoff_date=final_recall_cutoff_date(exam_date),
        reference_mode_end_date=reference_mode_end_date(exam_date),
    )


@router.get("", response_model=ExamSettingsResponse)
def get_exam_settings(current_user: User = Depends(get_current_user)):
    """Get the current user's exam date and its derived dates."""
    return _build_response(current_user)


@router.put("", response_model=ExamSettingsResponse)
def update_exam_settings(
    data: ExamSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update the current user's exam date.

    Raises:
        400: If exam_date isn't far enough in the future for the Final
             Active Recall cutoff (31 days prior) to make sense.
    """
    if data.exam_date <= date.today() + timedelta(days=31):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Exam date must be more than 31 days from today (the Final Active Recall cutoff is 31 days before it).",
        )

    current_user.exam_date = data.exam_date
    db.commit()
    db.refresh(current_user)
    return _build_response(current_user)
