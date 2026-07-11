"""
Pydantic schemas for Subject-related operations.
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.models.enums import Category


class SubjectCreate(BaseModel):
    """Schema for creating a new subject (chapter)."""
    name: str = Field(..., min_length=1, max_length=255, description="Chapter name")
    start_date: date = Field(..., description="Date when studying began (ISO format)")

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError('Name cannot be empty or whitespace only')
        return v


class SubjectUpdate(BaseModel):
    """
    Schema for updating an existing subject.
    Only name/start_date are user-editable - category/stage/final-recall
    state only change via completing a review or a final reread.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Name cannot be empty or whitespace only')
        return v


class SubjectResponse(BaseModel):
    """Full subject state, including adaptive engine and final-recall fields."""
    id: str
    name: str
    start_date: date

    category: Category
    stage: int
    next_due_date: Optional[date] = Field(
        None, description="Next scheduled Active Recall date (None once Final Active Recall is reached)"
    )
    last_active_recall_date: Optional[date] = None
    total_active_recall_count: int = Field(..., description="Number of completed Active Recall sessions")

    is_final_recall_reached: bool = False
    final_active_recall_date: Optional[date] = None
    final_category: Optional[Category] = None
    reread_completed_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
