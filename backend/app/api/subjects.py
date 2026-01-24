"""
Subject API endpoints.

Handles CRUD operations for study subjects.

Security: All endpoints require authentication and are scoped to the current user.
Users can only access their own subjects.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.subject_service import SubjectService
from app.services.review_service import ReviewService
from app.schemas.subject import (
    SubjectCreate,
    SubjectUpdate,
    SubjectResponse,
    SubjectWithNextDue,
)

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


def get_subject_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SubjectService:
    """Dependency to get SubjectService instance scoped to current user."""
    return SubjectService(db, current_user)


def get_review_service(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewService:
    """Dependency to get ReviewService instance scoped to current user."""
    return ReviewService(db, current_user)


@router.get("", response_model=list[SubjectWithNextDue])
def list_subjects(
    subject_service: SubjectService = Depends(get_subject_service),
    review_service: ReviewService = Depends(get_review_service),
):
    """
    List all subjects for the current user.
    
    Returns subjects with their computed next due date and active intervals.
    """
    subjects = subject_service.get_all()
    result = []
    
    for subject in subjects:
        next_due = review_service.get_next_due_date(subject)
        intervals = review_service.get_intervals(subject)
        
        result.append(SubjectWithNextDue(
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
    
    return result


@router.post("", response_model=SubjectWithNextDue, status_code=status.HTTP_201_CREATED)
def create_subject(
    data: SubjectCreate,
    subject_service: SubjectService = Depends(get_subject_service),
    review_service: ReviewService = Depends(get_review_service),
):
    """
    Create a new subject for the current user.
    
    Args:
        data: Subject creation data
        
    Returns:
        Created subject with next due date
        
    Raises:
        400: If subject name already exists for this user
        422: If validation fails
    """
    try:
        subject = subject_service.create(data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    next_due = review_service.get_next_due_date(subject)
    intervals = review_service.get_intervals(subject)
    
    return SubjectWithNextDue(
        id=subject.id,
        name=subject.name,
        start_date=subject.start_date,
        schedule_type=subject.schedule_type,
        custom_intervals_days=subject.custom_intervals_days,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
        next_due_date=next_due,
        intervals=intervals,
    )


@router.get("/{subject_id}", response_model=SubjectWithNextDue)
def get_subject(
    subject_id: str,
    subject_service: SubjectService = Depends(get_subject_service),
    review_service: ReviewService = Depends(get_review_service),
):
    """
    Get a subject by ID.
    
    Args:
        subject_id: UUID of the subject
        
    Returns:
        Subject with next due date
        
    Raises:
        404: If subject not found or not owned by current user
    """
    subject = subject_service.get_by_id(subject_id)
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject not found"
        )
    
    next_due = review_service.get_next_due_date(subject)
    intervals = review_service.get_intervals(subject)
    
    return SubjectWithNextDue(
        id=subject.id,
        name=subject.name,
        start_date=subject.start_date,
        schedule_type=subject.schedule_type,
        custom_intervals_days=subject.custom_intervals_days,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
        next_due_date=next_due,
        intervals=intervals,
    )


@router.put("/{subject_id}", response_model=SubjectWithNextDue)
def update_subject(
    subject_id: str,
    data: SubjectUpdate,
    subject_service: SubjectService = Depends(get_subject_service),
    review_service: ReviewService = Depends(get_review_service),
):
    """
    Update a subject.
    
    Args:
        subject_id: UUID of the subject
        data: Partial update data
        
    Returns:
        Updated subject with next due date
        
    Raises:
        400: If name conflicts with existing subject
        404: If subject not found or not owned by current user
        422: If validation fails
    """
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
            detail=f"Subject not found"
        )
    
    next_due = review_service.get_next_due_date(subject)
    intervals = review_service.get_intervals(subject)
    
    return SubjectWithNextDue(
        id=subject.id,
        name=subject.name,
        start_date=subject.start_date,
        schedule_type=subject.schedule_type,
        custom_intervals_days=subject.custom_intervals_days,
        created_at=subject.created_at,
        updated_at=subject.updated_at,
        next_due_date=next_due,
        intervals=intervals,
    )


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(
    subject_id: str,
    subject_service: SubjectService = Depends(get_subject_service),
):
    """
    Delete a subject.
    
    Args:
        subject_id: UUID of the subject
        
    Raises:
        404: If subject not found or not owned by current user
    """
    deleted = subject_service.delete(subject_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subject not found"
        )
