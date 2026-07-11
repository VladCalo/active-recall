#!/usr/bin/env python3
"""
Seed script for populating the database with sample chapters.

Usage:
    python seed.py

Creates sample chapters (attached to the first existing user) to demonstrate
the adaptive Active Recall engine. Run this after starting the backend at
least once (so the admin user and tables exist).
"""

from datetime import date, timedelta
from app.database import SessionLocal, engine, Base
from app.models.subject import Subject
from app.models.enums import Category
from app.models.user import User
from app.services.adaptive_engine import State, next_due_date

SAMPLE_SUBJECTS = [
    {"name": "Cardiology", "start_date": date.today() - timedelta(days=1), "category": Category.MEDIUM, "stage": 0},
    {"name": "Neurology", "start_date": date.today() - timedelta(days=3), "category": Category.HARD, "stage": 0},
    {"name": "Pharmacology", "start_date": date.today(), "category": Category.MEDIUM, "stage": 0},
    {"name": "Anatomy", "start_date": date.today() - timedelta(days=7), "category": Category.EASY, "stage": 1},
    {"name": "Biochemistry", "start_date": date.today() - timedelta(days=14), "category": Category.MEDIUM, "stage": 2},
]


def seed_database():
    """Create sample chapters in the database, owned by the first user found."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        user = db.query(User).order_by(User.created_at).first()
        if not user:
            print("No user found - start the backend once (so the admin user is seeded) before running this.")
            return

        existing_count = db.query(Subject).filter(Subject.user_id == user.id).count()
        if existing_count > 0:
            print(f"User {user.email} already has {existing_count} subjects. Skipping seed.")
            return

        for subject_data in SAMPLE_SUBJECTS:
            due = next_due_date(
                subject_data["start_date"],
                State(subject_data["category"], subject_data["stage"])
            )
            subject = Subject(user_id=user.id, next_due_date=due, **subject_data)
            db.add(subject)
            print(f"Created: {subject.name} (started {subject.start_date}, {subject.category.value})")

        db.commit()
        print(f"\n✓ Successfully seeded {len(SAMPLE_SUBJECTS)} subjects for {user.email}!")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
