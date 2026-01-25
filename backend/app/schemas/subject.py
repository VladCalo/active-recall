"""
Pydantic schemas for Subject-related operations.

These schemas handle validation for creating, updating, and reading subjects.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from app.models.subject import ScheduleType


class SubjectBase(BaseModel):
    """Base schema with common subject fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Subject name")
    start_date: date = Field(..., description="Date when studying began (ISO format)")
    schedule_type: ScheduleType = Field(
        default=ScheduleType.DEFAULT,
        description="Schedule type: DEFAULT or CUSTOM"
    )
    custom_intervals_days: Optional[list[int]] = Field(
        default=None,
        description="Custom intervals in days (only for CUSTOM schedule)"
    )

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Strip whitespace and ensure name is not empty."""
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty or whitespace only')
        return v

    @field_validator('custom_intervals_days')
    @classmethod
    def validate_intervals(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        """
        Validate custom intervals:
        - Must be positive integers
        - Must be unique
        - Must be sorted ascending
        - Max 50 intervals
        """
        if v is None:
            return None
        
        if len(v) == 0:
            raise ValueError('Custom intervals cannot be empty when provided')
        
        if len(v) > 50:
            raise ValueError('Maximum 50 intervals allowed')
        
        for interval in v:
            if not isinstance(interval, int) or interval <= 0:
                raise ValueError('All intervals must be positive integers')
        
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError('Intervals must be unique')
        
        # Sort ascending
        return sorted(v)

    @model_validator(mode='after')
    def validate_schedule_consistency(self):
        """
        Ensure custom_intervals_days is set only when schedule_type is CUSTOM,
        and is required when schedule_type is CUSTOM.
        """
        if self.schedule_type == ScheduleType.CUSTOM:
            if not self.custom_intervals_days:
                raise ValueError('Custom intervals are required when schedule_type is CUSTOM')
        else:
            # Clear custom intervals for DEFAULT schedule
            self.custom_intervals_days = None
        return self


class SubjectCreate(SubjectBase):
    """Schema for creating a new subject."""
    pass


class SubjectUpdate(BaseModel):
    """
    Schema for updating an existing subject.
    All fields are optional - only provided fields will be updated.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    schedule_type: Optional[ScheduleType] = None
    custom_intervals_days: Optional[list[int]] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Name cannot be empty or whitespace only')
        return v

    @field_validator('custom_intervals_days')
    @classmethod
    def validate_intervals(cls, v: Optional[list[int]]) -> Optional[list[int]]:
        if v is None:
            return None
        
        if len(v) == 0:
            raise ValueError('Custom intervals cannot be empty when provided')
        
        if len(v) > 50:
            raise ValueError('Maximum 50 intervals allowed')
        
        for interval in v:
            if not isinstance(interval, int) or interval <= 0:
                raise ValueError('All intervals must be positive integers')
        
        if len(v) != len(set(v)):
            raise ValueError('Intervals must be unique')
        
        return sorted(v)


class SubjectResponse(BaseModel):
    """Schema for subject responses."""
    id: str
    name: str
    start_date: date
    schedule_type: ScheduleType
    custom_intervals_days: Optional[list[int]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubjectWithNextDue(SubjectResponse):
    """Subject response with computed next due date."""
    next_due_date: Optional[date] = Field(
        None, 
        description="Next scheduled review date (None if all reviews completed)"
    )
    intervals: list[int] = Field(
        ...,
        description="Active intervals (either default or custom)"
    )
    revision_number: Optional[int] = Field(
        None,
        description="Which revision this is (1-based), None if not due today"
    )
    total_revisions: int = Field(
        ...,
        description="Total number of revisions in schedule"
    )
    is_completed: bool = Field(
        False,
        description="Whether all revisions are completed"
    )
