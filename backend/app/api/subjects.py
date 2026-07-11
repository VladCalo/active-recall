"""
Subject API endpoints.

Handles CRUD operations for study subjects (chapters).

Security: All endpoints require authentication and are scoped to the current user.
Users can only access their own subjects.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.subject_service import SubjectService
from app.schemas.subject import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
)

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


def get_subject_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubjectService:
    """Dependency to get SubjectService instance scoped to current user."""
    return SubjectService(db, current_user)


def build_subject_response(subject, subject_service: SubjectService) -> SubjectResponse:
    """Build SubjectResponse with computed fields."""
    return SubjectResponse(
        id=subject.id,
        name=subject.name,
        start_date=subject.start_date,
        category=subject.category,
        stage=subject.stage,
        next_due_date=subject.next_due_date,
        last_active_recall_date=subject.last_active_recall_date,
        total_active_recall_count=subject_service.total_active_recall_count(subject),
        is_final_recall_reached=subject.is_final_recall_reached,
        final_active_recall_date=subject.final_active_recall_date,
        final_category=subject.final_category,
        reread_completed_at=subject.reread_completed_at,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
    )


@router.get("", response_model=list[SubjectResponse])
def list_subjects(
    subject_service: SubjectService = Depends(get_subject_service),
):
    """List all chapters for the current user."""
    subjects = subject_service.get_all()
    return [build_subject_response(s, subject_service) for s in subjects]


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(
    data: SubjectCreate,
    subject_service: SubjectService = Depends(get_subject_service),
):
    """
    Create a new chapter for the current user, starting at Medium/stage 0.

    Raises:
        400: If subject name already exists, or Reference Mode has started
        422: If validation fails
    """
    try:
        subject = subject_service.create(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    return build_subject_response(subject, subject_service)


@router.get("/{subject_id}", response_model=SubjectResponse)
def get_subject(
    subject_id: str,
    subject_service: SubjectService = Depends(get_subject_service),
):
    """Get a chapter by ID."""
    subject = subject_service.get_by_id(subject_id)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )

    return build_subject_response(subject, subject_service)


@router.put("/{subject_id}", response_model=SubjectResponse)
def update_subject(
    subject_id: str,
    data: SubjectUpdate,
    subject_service: SubjectService = Depends(get_subject_service),
):
    """Update a chapter's name/start_date."""
    try:
        subject = subject_service.update(subject_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )

    return build_subject_response(subject, subject_service)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: str,
    subject_service: SubjectService = Depends(get_subject_service),
):
    """Delete a chapter."""
    deleted = subject_service.delete(subject_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject not found"
        )
