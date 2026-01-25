"""
Tests for the /api/reviews endpoints.

Tests cover:
- GET /api/reviews/today
- GET /api/reviews/upcoming

All tests use authenticated requests.
"""

import pytest
from datetime import date
from unittest.mock import patch

from app.services.review_service import ReviewService


class TestTodayReviews:
    """Tests for GET /api/reviews/today endpoint."""

    def test_returns_empty_when_no_subjects(self, client, auth_headers):
        """Should return empty list when no subjects exist."""
        response = client.get("/api/reviews/today", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["subjects"] == []
        assert "today" in data
        assert data["timezone"] == "Europe/Bucharest"

    def test_returns_due_subjects(self, client, sample_subject, auth_headers):
        """Should return subjects due today."""
        # Mock today to be a due date
        with patch.object(
            ReviewService, 
            'get_today', 
            return_value=date(2026, 1, 26)
        ):
            response = client.get("/api/reviews/today", headers=auth_headers)
        
            assert response.status_code == 200
            data = response.json()
            assert data["count"] == 1
            assert len(data["subjects"]) == 1
            assert data["subjects"][0]["name"] == "Cardiology"

    def test_respects_timezone_parameter(self, client, sample_subject, auth_headers):
        """Should use provided timezone for date calculation."""
        response = client.get("/api/reviews/today?tz=UTC", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "UTC"

    def test_includes_subject_details(self, client, sample_subject, auth_headers):
        """Response should include full subject details with intervals."""
        with patch.object(
            ReviewService, 
            'get_today', 
            return_value=date(2026, 1, 26)
        ):
            response = client.get("/api/reviews/today", headers=auth_headers)
            
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

    def test_returns_upcoming_reviews(self, client, sample_subject, auth_headers):
        """Should return reviews for the next N days."""
        with patch.object(
            ReviewService, 
            'get_today', 
            return_value=date(2026, 1, 25)
        ):
            response = client.get("/api/reviews/upcoming?days=7", headers=auth_headers)
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["start_date"] == "2026-01-25"
            assert data["end_date"] == "2026-01-31"
            assert "reviews" in data
            assert data["total_count"] >= 0

    def test_default_days_is_7(self, client, auth_headers):
        """Should default to 7 days if not specified."""
        response = client.get("/api/reviews/upcoming", headers=auth_headers)
        
        assert response.status_code == 200

    def test_validates_days_range(self, client, auth_headers):
        """Should reject days outside valid range."""
        # Too small
        response = client.get("/api/reviews/upcoming?days=0", headers=auth_headers)
        assert response.status_code == 422
        
        # Too large
        response = client.get("/api/reviews/upcoming?days=400", headers=auth_headers)
        assert response.status_code == 422

    def test_groups_by_date(self, client, sample_subject, auth_headers):
        """Reviews should be grouped by date."""
        with patch.object(
            ReviewService, 
            'get_today', 
            return_value=date(2026, 1, 25)
        ):
            response = client.get("/api/reviews/upcoming?days=14", headers=auth_headers)
            
            data = response.json()
            reviews = data["reviews"]
            
            # Should have dates as keys
            for date_str in reviews.keys():
                # Validate date format
                assert len(date_str) == 10  # YYYY-MM-DD


class TestRangeReviews:
    """Tests for GET /api/reviews/range endpoint (calendar support)."""

    def test_returns_reviews_in_range(self, client, sample_subject, auth_headers):
        """Should return reviews grouped by date within the range."""
        # sample_subject has start_date=2026-01-25 with DEFAULT schedule
        # Due dates: 2026-01-26 (day 1), 2026-01-28 (day 3), 2026-02-01 (day 7)
        response = client.get(
            "/api/reviews/range?start=2026-01-25&end=2026-02-05",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["start"] == "2026-01-25"
        assert data["end"] == "2026-02-05"
        assert data["timezone"] == "Europe/Bucharest"
        assert "items" in data
        
        # Check specific due dates
        items = data["items"]
        assert "2026-01-26" in items  # Day 1
        assert "2026-01-28" in items  # Day 3
        assert "2026-02-01" in items  # Day 7
        
        # Verify subject info
        subject_item = items["2026-01-26"][0]
        assert subject_item["subject_name"] == "Cardiology"
        assert subject_item["schedule_type"] == "DEFAULT"

    def test_returns_custom_schedule_due_dates(
        self, client, sample_custom_subject, auth_headers
    ):
        """Should correctly calculate due dates for CUSTOM schedule."""
        # sample_custom_subject has start_date=2026-01-25 with intervals [2, 5, 10]
        # Due dates: 2026-01-27 (day 2), 2026-01-30 (day 5), 2026-02-04 (day 10)
        response = client.get(
            "/api/reviews/range?start=2026-01-25&end=2026-02-10",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        items = data["items"]
        
        # Check custom schedule due dates
        assert "2026-01-27" in items  # Day 2
        assert "2026-01-30" in items  # Day 5
        assert "2026-02-04" in items  # Day 10
        
        subject_item = items["2026-01-27"][0]
        assert subject_item["schedule_type"] == "CUSTOM"

    def test_user_isolation(
        self, client, sample_subject, other_user_subject, auth_headers, other_auth_headers
    ):
        """User A should not see User B's subjects."""
        # User A sees their subject
        response_a = client.get(
            "/api/reviews/range?start=2026-01-25&end=2026-02-05",
            headers=auth_headers
        )
        assert response_a.status_code == 200
        data_a = response_a.json()
        
        # User B sees their subject
        response_b = client.get(
            "/api/reviews/range?start=2026-01-25&end=2026-02-05",
            headers=other_auth_headers
        )
        assert response_b.status_code == 200
        data_b = response_b.json()
        
        # User A should see "Cardiology" (sample_subject)
        all_names_a = []
        for subjects in data_a["items"].values():
            for s in subjects:
                all_names_a.append(s["subject_name"])
        assert "Cardiology" in all_names_a
        assert "Pharmacology" not in all_names_a  # other_user_subject
        
        # User B should see "Pharmacology" (other_user_subject)
        all_names_b = []
        for subjects in data_b["items"].values():
            for s in subjects:
                all_names_b.append(s["subject_name"])
        assert "Pharmacology" in all_names_b
        assert "Cardiology" not in all_names_b

    def test_validates_start_before_end(self, client, auth_headers):
        """Should reject if start date is after end date."""
        response = client.get(
            "/api/reviews/range?start=2026-02-01&end=2026-01-01",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Start date must be before" in response.json()["detail"]

    def test_validates_range_not_too_large(self, client, auth_headers):
        """Should reject if date range exceeds maximum."""
        response = client.get(
            "/api/reviews/range?start=2026-01-01&end=2028-01-01",
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "Date range too large" in response.json()["detail"]

    def test_validates_date_format(self, client, auth_headers):
        """Should reject invalid date format."""
        response = client.get(
            "/api/reviews/range?start=invalid&end=2026-01-31",
            headers=auth_headers
        )
        assert response.status_code == 422

    def test_returns_empty_when_no_subjects(self, client, auth_headers):
        """Should return empty items when user has no subjects."""
        response = client.get(
            "/api/reviews/range?start=2026-01-01&end=2026-01-31",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == {}
        assert data["total_count"] == 0

    def test_returns_total_count(self, client, sample_subject, auth_headers):
        """Should return correct total count of due items."""
        response = client.get(
            "/api/reviews/range?start=2026-01-25&end=2026-02-28",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Count should match actual items
        actual_count = sum(len(subjects) for subjects in data["items"].values())
        assert data["total_count"] == actual_count

    def test_respects_timezone_parameter(self, client, sample_subject, auth_headers):
        """Should accept and return timezone parameter."""
        response = client.get(
            "/api/reviews/range?start=2026-01-25&end=2026-02-05&tz=UTC",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["timezone"] == "UTC"

    def test_requires_authentication(self, client):
        """Should require authentication."""
        response = client.get("/api/reviews/range?start=2026-01-01&end=2026-01-31")
        assert response.status_code == 401
