"""
Pytest fixtures and configuration.

This module provides shared fixtures for all tests:
- Test database with in-memory SQLite
- Test client for API testing
- Authentication helpers
- Sample data factories
"""

import os
import pytest
from datetime import date
from typing import Generator

# Set testing mode before importing app
os.environ["TESTING"] = "1"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.subject import Subject, ScheduleType
from app.models.refresh_token import RefreshToken
from app.core.security import hash_password, create_access_token


# Create test database engine (in-memory SQLite with StaticPool for thread safety)
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test.
    
    Creates all tables before the test and drops them after.
    """
    Base.metadata.create_all(bind=test_engine)
    
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db: Session) -> Generator[TestClient, None, None]:
    """
    Create a test client with database override.
    
    Uses the test database instead of the production database.
    """
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user with a strong password."""
    user = User(
        email="test@example.com",
        # Password: Test@Password123 (meets all requirements)
        password_hash=hash_password("Test@Password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def other_user(db: Session) -> User:
    """Create another test user for isolation tests."""
    user = User(
        email="other@example.com",
        password_hash=hash_password("Other@Password123"),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User) -> dict:
    """Create auth headers for test user."""
    token = create_access_token({"sub": test_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_auth_headers(other_user: User) -> dict:
    """Create auth headers for other user."""
    token = create_access_token({"sub": other_user.id})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_subject(db: Session, test_user: User) -> Subject:
    """Create a sample subject for the test user."""
    subject = Subject(
        user_id=test_user.id,
        name="Cardiology",
        start_date=date(2026, 1, 25),
        schedule_type=ScheduleType.DEFAULT,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@pytest.fixture
def sample_custom_subject(db: Session, test_user: User) -> Subject:
    """Create a sample subject with custom schedule for the test user."""
    subject = Subject(
        user_id=test_user.id,
        name="Neurology",
        start_date=date(2026, 1, 25),
        schedule_type=ScheduleType.CUSTOM,
        custom_intervals_days=[2, 5, 10, 20],
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@pytest.fixture
def other_user_subject(db: Session, other_user: User) -> Subject:
    """Create a subject belonging to other user (for isolation tests)."""
    subject = Subject(
        user_id=other_user.id,
        name="Pharmacology",
        start_date=date(2026, 1, 25),
        schedule_type=ScheduleType.DEFAULT,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject
