"""Pydantic schemas for the exam-cycle settings (exam date + derived dates)."""

from datetime import date
from pydantic import BaseModel, Field


class ExamSettingsResponse(BaseModel):
    exam_date: date
    final_recall_cutoff_date: date = Field(..., description="exam_date minus 31 days")
    reference_mode_end_date: date = Field(..., description="exam_date minus 1 day")


class ExamSettingsUpdate(BaseModel):
    exam_date: date
