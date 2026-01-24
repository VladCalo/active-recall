"""
Subject service - handles all subject-related business logic.

This service provides CRUD operations for subjects and handles
validation logic like case-insensitive name uniqueness.
"""

from datetime import date
from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.subject import Subject, ScheduleType
from app.schemas.subject import SubjectCreate, SubjectUpdate
from app.config import get_settings


class SubjectService:
    """
    Service class for Subject operations.
    
    All database operations for subjects should go through this service
    to ensure business rules are consistently applied.
    """

    def __init__(self, db: Session):
        """Initialize with database session."""
        self.db = db
        self.settings = get_settings()

    def get_all(self) -> list[Subject]:
        """Get all subjects, ordered by name."""
        return self.db.query(Subject).order_by(Subject.name).all()

    def get_by_id(self, subject_id: str) -> Optional[Subject]:
        """Get a subject by its ID."""
        return self.db.query(Subject).filter(Subject.id == subject_id).first()

    def get_by_name(self, name: str) -> Optional[Subject]:
        """
        Get a subject by name (case-insensitive).
        
        Args:
            name: Subject name to search for
            
        Returns:
            Subject if found, None otherwise
        """
        return self.db.query(Subject).filter(
            func.lower(Subject.name) == name.lower().strip()
        ).first()

    def create(self, data: SubjectCreate) -> Subject:
        """
        Create a new subject.
        
        Args:
            data: Validated subject creation data
            
        Returns:
            Created subject
            
        Raises:
            ValueError: If a subject with the same name already exists
        """
        # Check for existing subject with same name (case-insensitive)
        existing = self.get_by_name(data.name)
        if existing:
            raise ValueError(f"A subject with name '{data.name}' already exists")

        subject = Subject(
            name=data.name.strip(),
            start_date=data.start_date,
            schedule_type=data.schedule_type,
            custom_intervals_days=data.custom_intervals_days,
        )
        
        self.db.add(subject)
        self.db.commit()
        self.db.refresh(subject)
        return subject

    def update(self, subject_id: str, data: SubjectUpdate) -> Optional[Subject]:
        """
        Update an existing subject.
        
        Args:
            subject_id: ID of subject to update
            data: Partial update data (only provided fields are updated)
            
        Returns:
            Updated subject, or None if not found
            
        Raises:
            ValueError: If new name conflicts with existing subject
        """
        subject = self.get_by_id(subject_id)
        if not subject:
            return None

        # Handle name update with uniqueness check
        if data.name is not None and data.name.strip().lower() != subject.name.lower():
            existing = self.get_by_name(data.name)
            if existing:
                raise ValueError(f"A subject with name '{data.name}' already exists")
            subject.name = data.name.strip()

        # Handle start_date update
        if data.start_date is not None:
            subject.start_date = data.start_date

        # Handle schedule type and intervals update
        if data.schedule_type is not None:
            subject.schedule_type = data.schedule_type
            
            # If switching to DEFAULT, clear custom intervals
            if data.schedule_type == ScheduleType.DEFAULT:
                subject.custom_intervals_days = None
            # If switching to CUSTOM, require intervals
            elif data.schedule_type == ScheduleType.CUSTOM:
                if data.custom_intervals_days:
                    subject.custom_intervals_days = data.custom_intervals_days
                elif not subject.custom_intervals_days:
                    raise ValueError(
                        "Custom intervals are required when schedule_type is CUSTOM"
                    )
        
        # Handle custom intervals update (without schedule type change)
        elif data.custom_intervals_days is not None:
            if subject.schedule_type == ScheduleType.CUSTOM:
                subject.custom_intervals_days = data.custom_intervals_days
            # If currently DEFAULT and providing intervals, ignore them
            # (user must explicitly change schedule_type to CUSTOM)

        self.db.commit()
        self.db.refresh(subject)
        return subject

    def delete(self, subject_id: str) -> bool:
        """
        Delete a subject.
        
        Args:
            subject_id: ID of subject to delete
            
        Returns:
            True if deleted, False if not found
        """
        subject = self.get_by_id(subject_id)
        if not subject:
            return False
        
        self.db.delete(subject)
        self.db.commit()
        return True

    def get_intervals(self, subject: Subject) -> list[int]:
        """
        Get the active intervals for a subject.
        
        Args:
            subject: Subject to get intervals for
            
        Returns:
            List of interval days (either custom or default)
        """
        if subject.schedule_type == ScheduleType.CUSTOM and subject.custom_intervals_days:
            return subject.custom_intervals_days
        return self.settings.default_intervals
