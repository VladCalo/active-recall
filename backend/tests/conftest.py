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
from app.models.subject import Subject
from app.models.enums import Category
from app.models.refresh_token import RefreshToken
from app.core.security import hash_password, create_access_token
from app.services.adaptive_engine import State, next_due_date


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


def _make_subject(db: Session, user: User, name: str, start_date: date,
                   category: Category = Category.MEDIUM, stage: int = 0) -> Subject:
    subject = Subject(
        user_id=user.id,
        name=name,
        start_date=start_date,
        category=category,
        stage=stage,
        next_due_date=next_due_date(start_date, State(category, stage)),
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@pytest.fixture
def sample_subject(db: Session, test_user: User) -> Subject:
    """Create a sample subject (Medium, stage 0) for the test user."""
    return _make_subject(db, test_user, "Cardiology", date(2026, 1, 25))


@pytest.fixture
def sample_hard_subject(db: Session, test_user: User) -> Subject:
    """Create a sample Hard-category subject for the test user."""
    return _make_subject(db, test_user, "Neurology", date(2026, 1, 25), Category.HARD, 0)


@pytest.fixture
def other_user_subject(db: Session, other_user: User) -> Subject:
    """Create a subject belonging to other user (for isolation tests)."""
    return _make_subject(db, other_user, "Pharmacology", date(2026, 1, 25))
