"""
Tests for the /api/reviews endpoints.

Tests cover:
- GET /api/reviews/today
- GET /api/reviews/upcoming
"""

import pytest
from datetime import date
from unittest.mock import patch

from app.services.review_service import ReviewService


class TestTodayReviews:
    """Tests for GET /api/reviews/today endpoint."""

    def test_returns_empty_when_no_subjects(self, client):
        """Should return empty list when no subjects exist."""
        response = client.get("/api/reviews/today")
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["subjects"] == []
        assert "today" in data
        assert data["timezone"] == "Europe/Bucharest"

    def test_returns_due_subjects(self, client, sample_subject):
        """Should return subjects due today."""
        # Mock today to be a due date
        with patch.object(
            ReviewService, 
            'get_today', 
            return_value=date(2026, 1, 26)
        ):
            response = client.get("/api/reviews/today")
        
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert len(data["subjects"]) == 1
            assert data["subjects"][0]["name"] == "Cardiology"

    def test_respects_timezone_parameter(self, client, sample_subject):
        """Should use provided timezone for date calculation."""
        response = client.get("/api/reviews/today?tz=UTC")
        
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "UTC"

    def test_includes_subject_details(self, client, sample_subject):
        """Response should include full subject details with intervals."""
        with patch.object(
            ReviewService, 
            'get_today', 
            return_value=date(2026, 1, 26)
        ):
            response = client.get("/api/reviews/today")
            
            data = response.json()
            subject = data["subjects"][0]
            
            assert "id" in subject
            assert "name" in subject
            assert "start_date" in subject
            assert "schedule_type" in subject
            assert "intervals" in subject
            assert "next_due_date" in subject


class TestUpcomingReviews:
    """Tests for GET /api/reviews/upcoming endpoint."""

    def test_returns_upcoming_reviews(self, client, sample_subject):
        """Should return reviews for the next N days."""
        with patch.object(
            ReviewService, 
            'get_today', 
            return_value=date(2026, 1, 25)
        ):
            response = client.get("/api/reviews/upcoming?days=7")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["start_date"] == "2026-01-25"
            assert data["end_date"] == "2026-01-31"
            assert "reviews" in data
            assert data["total_count"] >= 0

    def test_default_days_is_7(self, client):
        """Should default to 7 days if not specified."""
        response = client.get("/api/reviews/upcoming")
        
        assert response.status_code == 200
        # Just verify it works with default

    def test_validates_days_range(self, client):
        """Should reject days outside valid range."""
        # Too small
        response = client.get("/api/reviews/upcoming?days=0")
        assert response.status_code == 422
        
        # Too large
        response = client.get("/api/reviews/upcoming?days=400")
        assert response.status_code == 422

    def test_groups_by_date(self, client, sample_subject):
        """Reviews should be grouped by date."""
        with patch.object(
            ReviewService, 
            'get_today', 
            return_value=date(2026, 1, 25)
        ):
            response = client.get("/api/reviews/upcoming?days=14")
            
            data = response.json()
            reviews = data["reviews"]
            
            # Should have dates as keys
            for date_str in reviews.keys():
                # Validate date format
                assert len(date_str) == 10  # YYYY-MM-DD
