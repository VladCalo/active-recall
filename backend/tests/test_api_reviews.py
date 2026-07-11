"""
Tests for the /api/reviews endpoints: today's due list, completing a
review, and calendar range data.
"""

from datetime import date
from unittest.mock import patch

from app.services.review_service import ReviewService


class TestTodayReviews:
    """Tests for GET /api/reviews/today endpoint."""

    def test_returns_empty_when_no_subjects(self, client, auth_headers):
        response = client.get("/api/reviews/today", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
        assert data["items"] == []
        assert "today" in data
        assert data["timezone"] == "Europe/Bucharest"

    def test_returns_due_subjects(self, client, sample_subject, auth_headers):
        # sample_subject: Medium/stage0, next_due_date = start(2026-01-25)+5 = 2026-01-30
        with patch.object(ReviewService, "get_today", return_value=date(2026, 1, 30)):
            response = client.get("/api/reviews/today", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["items"][0]["subject_name"] == "Cardiology"
        assert data["items"][0]["is_overdue"] is False

    def test_overdue_flagged_correctly(self, client, sample_subject, auth_headers):
        with patch.object(ReviewService, "get_today", return_value=date(2026, 2, 5)):
            response = client.get("/api/reviews/today", headers=auth_headers)

        data = response.json()
        assert data["items"][0]["is_overdue"] is True

    def test_respects_timezone_parameter(self, client, auth_headers):
        response = client.get("/api/reviews/today?tz=UTC", headers=auth_headers)

        assert response.status_code == 200
        assert response.json()["timezone"] == "UTC"


class TestCompleteReview:
    """Tests for POST /api/reviews/complete endpoint."""

    def test_completes_review_and_updates_state(self, client, sample_subject, auth_headers):
        response = client.post(
            "/api/reviews/complete",
            headers=auth_headers,
            json={
                "subject_id": sample_subject.id,
                "rating": "EXCELLENT",
                "completed_at": "2026-01-25",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Medium + Excellent -> Easy, stage 0 (+10 days)
        assert data["category"] == "EASY"
        assert data["stage"] == 0
        assert data["next_due_date"] == "2026-02-04"
        assert data["is_final_recall"] is False

    def test_returns_404_style_400_for_unknown_subject(self, client, auth_headers):
        response = client.post(
            "/api/reviews/complete",
            headers=auth_headers,
            json={"subject_id": "unknown-id", "rating": "EXCELLENT"},
        )
        assert response.status_code == 400

    def test_rejects_invalid_rating(self, client, sample_subject, auth_headers):
        response = client.post(
            "/api/reviews/complete",
            headers=auth_headers,
            json={"subject_id": sample_subject.id, "rating": "NOT_A_RATING"},
        )
        assert response.status_code == 422

    def test_requires_authentication(self, client, sample_subject):
        response = client.post(
            "/api/reviews/complete",
            json={"subject_id": sample_subject.id, "rating": "EXCELLENT"},
        )
        assert response.status_code == 401


class TestRangeReviews:
    """Tests for GET /api/reviews/range endpoint (calendar support)."""

    def test_returns_upcoming_due_date_in_range(self, client, sample_subject, auth_headers):
        # next_due_date = 2026-01-30
        response = client.get(
            "/api/reviews/range?start=2026-01-25&end=2026-02-05",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert "2026-01-30" in data["items"]
        assert data["items"]["2026-01-30"][0]["subject_name"] == "Cardiology"
        assert data["items"]["2026-01-30"][0]["type"] == "upcoming"

    def test_user_isolation(self, client, sample_subject, other_user_subject, auth_headers, other_auth_headers):
        response_a = client.get(
            "/api/reviews/range?start=2026-01-25&end=2026-02-05", headers=auth_headers
        )
        response_b = client.get(
            "/api/reviews/range?start=2026-01-25&end=2026-02-05", headers=other_auth_headers
        )
        assert response_a.status_code == 200
        assert response_b.status_code == 200

        names_a = [item["subject_name"] for items in response_a.json()["items"].values() for item in items]
        names_b = [item["subject_name"] for items in response_b.json()["items"].values() for item in items]

        assert "Cardiology" in names_a and "Pharmacology" not in names_a
        assert "Pharmacology" in names_b and "Cardiology" not in names_b

    def test_validates_start_before_end(self, client, auth_headers):
        response = client.get(
            "/api/reviews/range?start=2026-02-01&end=2026-01-01", headers=auth_headers
        )
        assert response.status_code == 400
        assert "Start date must be before" in response.json()["detail"]

    def test_validates_range_not_too_large(self, client, auth_headers):
        response = client.get(
            "/api/reviews/range?start=2026-01-01&end=2028-01-01", headers=auth_headers
        )
        assert response.status_code == 400
        assert "Date range too large" in response.json()["detail"]

    def test_returns_empty_when_no_subjects(self, client, auth_headers):
        response = client.get(
            "/api/reviews/range?start=2026-01-01&end=2026-01-31", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == {}
        assert data["total_count"] == 0

    def test_includes_completed_session_history(self, client, sample_subject, auth_headers):
        client.post(
            "/api/reviews/complete",
            headers=auth_headers,
            json={"subject_id": sample_subject.id, "rating": "GOOD_MINOR_HESITATION", "completed_at": "2026-01-28"},
        )

        response = client.get(
            "/api/reviews/range?start=2026-01-01&end=2026-02-28", headers=auth_headers
        )
        data = response.json()
        completed_entries = [
            item for items in data["items"].values() for item in items if item["type"] == "completed"
        ]
        assert len(completed_entries) == 1
        assert completed_entries[0]["rating"] == "GOOD_MINOR_HESITATION"

    def test_requires_authentication(self, client):
        response = client.get("/api/reviews/range?start=2026-01-01&end=2026-01-31")
        assert response.status_code == 401
