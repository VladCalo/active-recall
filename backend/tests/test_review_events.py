"""
Tests for review event completion and missed logic.
"""

from datetime import date
from unittest.mock import patch

from app.services.review_service import ReviewService


class TestReviewEvents:
    def test_mark_complete_event(self, client, sample_subject, auth_headers):
        with patch.object(ReviewService, "get_today", return_value=date(2026, 1, 26)):
            response = client.post(
                "/api/reviews/events/complete",
                headers=auth_headers,
                json={
                    "subject_id": sample_subject.id,
                    "due_date": "2026-01-26",
                    "is_completed": True,
                },
            )
            assert response.status_code == 200

            range_response = client.get(
                "/api/reviews/range?start=2026-01-26&end=2026-01-26",
                headers=auth_headers,
            )
            assert range_response.status_code == 200
            data = range_response.json()
            items = data["items"]["2026-01-26"]
            assert items[0]["is_completed"] is True

    def test_missed_event_moves_to_next_day(self, client, sample_subject, auth_headers, db, test_user):
        # Set tracking start date so missed logic applies
        test_user.review_tracking_start_date = date(2026, 1, 25)
        db.commit()

        with patch.object(ReviewService, "get_today", return_value=date(2026, 1, 27)):
            response = client.get(
                "/api/reviews/range?start=2026-01-27&end=2026-01-27",
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            items = data["items"]["2026-01-27"]
            assert items[0]["is_missed"] is True
            assert items[0]["effective_date"] == "2026-01-27"
