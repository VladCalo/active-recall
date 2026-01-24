"""
Pytest fixtures and configuration.

This module provides shared fixtures for all tests:
- Test database with in-memory SQLite
- Test client for API testing
- Sample data factories
"""

import pytest
from datetime import date
from typing import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, StaticPool
from sqlalchemy.orm import sessionmaker, Session

from app.main import app
from app.database import Base, get_db
from app.models.subject import Subject, ScheduleType


# Create test database engine (in-memory SQLite with StaticPool for thread safety)
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Use single connection for in-memory SQLite
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """
    Create a fresh database for each test.
    
    Creates all tables before the test and drops them after.
    """
    # Create tables
    Base.metadata.create_all(bind=test_engine)
    
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        # Drop all tables after test
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
def sample_subject(db: Session) -> Subject:
    """Create a sample subject for testing."""
    subject = Subject(
        name="Cardiology",
        start_date=date(2026, 1, 25),
        schedule_type=ScheduleType.DEFAULT,
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@pytest.fixture
def sample_custom_subject(db: Session) -> Subject:
    """Create a sample subject with custom schedule."""
    subject = Subject(
        name="Neurology",
        start_date=date(2026, 1, 25),
        schedule_type=ScheduleType.CUSTOM,
        custom_intervals_days=[2, 5, 10, 20],
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject
