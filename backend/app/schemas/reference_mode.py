"""
Pydantic schemas for Reference Mode (Phase 2: Final Rereading).
"""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.enums import Category


class ReferenceModeChapter(BaseModel):
    subject_id: str
    subject_name: str
    last_active_recall_date: Optional[date]
    final_category: Category
    total_active_recall_count: int
    recommended_intensity_label: str = Field(..., description="Deep Reread / Focused Reread / Quick Reread")
    recommended_focus: list[str]
    reread_completed: bool
    reread_completed_at: Optional[datetime]


class ReferenceModeListResponse(BaseModel):
    is_reference_mode: bool = Field(..., description="True once today is on/after the cutoff date")
    cutoff_date: date
    chapters: list[ReferenceModeChapter]


class ReferenceModeSummary(BaseModel):
    is_reference_mode: bool
    chapters_completed: int
    chapters_remaining: int
    percentage_completed: float
    days_remaining_until_exam: int
    exam_date: date
