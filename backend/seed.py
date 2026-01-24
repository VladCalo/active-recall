#!/usr/bin/env python3
"""
Seed script for populating the database with sample subjects.

Usage:
    python seed.py

This script creates sample study subjects to demonstrate the app's functionality.
Run this after starting the backend at least once (to create the database).
"""

from datetime import date, timedelta
from app.database import SessionLocal, engine, Base
from app.models.subject import Subject, ScheduleType

# Sample subjects with varied schedules
SAMPLE_SUBJECTS = [
    {
        "name": "Cardiology",
        "start_date": date.today() - timedelta(days=1),  # Started yesterday
        "schedule_type": ScheduleType.DEFAULT,
        "custom_intervals_days": None,
    },
    {
        "name": "Neurology",
        "start_date": date.today() - timedelta(days=3),  # Started 3 days ago
        "schedule_type": ScheduleType.DEFAULT,
        "custom_intervals_days": None,
    },
    {
        "name": "Pharmacology",
        "start_date": date.today(),  # Started today
        "schedule_type": ScheduleType.DEFAULT,
        "custom_intervals_days": None,
    },
    {
        "name": "Anatomy",
        "start_date": date.today() - timedelta(days=7),  # Started a week ago
        "schedule_type": ScheduleType.CUSTOM,
        "custom_intervals_days": [1, 2, 4, 7, 14, 28],  # More frequent review
    },
    {
        "name": "Biochemistry",
        "start_date": date.today() - timedelta(days=14),  # Started 2 weeks ago
        "schedule_type": ScheduleType.CUSTOM,
        "custom_intervals_days": [3, 7, 14, 30, 60],  # Less frequent
    },
]


def seed_database():
    """Create sample subjects in the database."""
    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        existing_count = db.query(Subject).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} subjects. Skipping seed.")
            print("To re-seed, delete the app.db file and run again.")
            return
        
        # Create subjects
        for subject_data in SAMPLE_SUBJECTS:
            subject = Subject(**subject_data)
            db.add(subject)
            print(f"Created: {subject.name} (started {subject.start_date})")
        
        db.commit()
        print(f"\n✓ Successfully seeded {len(SAMPLE_SUBJECTS)} subjects!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
