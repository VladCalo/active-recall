"""
SQLAlchemy ORM models.

This package contains all database models for the application.
Import all models here to ensure they're registered with SQLAlchemy.
"""

from app.models.subject import Subject, ScheduleType

__all__ = ["Subject", "ScheduleType"]
