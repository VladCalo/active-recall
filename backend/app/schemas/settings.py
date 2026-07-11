"""Pydantic schemas for user-customizable rules: exam date and adaptive-engine rules."""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from app.services.adaptive_engine import validate_ladders


class LaddersModel(BaseModel):
    HARD: list[int] = Field(..., min_length=4, max_length=4)
    MEDIUM: list[int] = Field(..., min_length=4, max_length=4)
    EASY: list[int] = Field(..., min_length=4, max_length=4)

    @field_validator("HARD", "MEDIUM", "EASY")
    @classmethod
    def _positive(cls, v: list[int]) -> list[int]:
        if not all(isinstance(d, int) and d > 0 for d in v):
            raise ValueError("All stage intervals must be positive integers")
        return v


class ExamSettingsResponse(BaseModel):
    exam_date: date
    final_recall_cutoff_date: date = Field(..., description="exam_date minus 31 days")
    reference_mode_end_date: date = Field(..., description="exam_date minus 1 day")

    ladders: LaddersModel = Field(..., description="Effective interval ladders (default or customized)")
    is_ladders_customized: bool

    no_revision_enabled: bool
    no_revision_weekday: int = Field(..., ge=0, le=6, description="0=Monday ... 6=Sunday")


class ExamSettingsUpdate(BaseModel):
    exam_date: Optional[date] = None
    ladders: Optional[LaddersModel] = Field(
        None, description="Set to override all three categories at once, or omit/null to leave unchanged"
    )
    reset_ladders_to_default: bool = Field(False, description="If true, clears any custom ladders")
    no_revision_enabled: Optional[bool] = None
    no_revision_weekday: Optional[int] = Field(None, ge=0, le=6)

    @field_validator("ladders")
    @classmethod
    def _validate_ladders(cls, v: Optional[LaddersModel]) -> Optional[LaddersModel]:
        if v is not None:
            validate_ladders(v.model_dump())
        return v
