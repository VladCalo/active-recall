"""Tests for the /api/metrics endpoint."""

from datetime import date


class TestMetrics:
    def test_empty_when_no_subjects(self, client, auth_headers):
        response = client.get("/api/metrics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_chapters"] == 0
        assert data["category_distribution"] == {"HARD": 0, "MEDIUM": 0, "EASY": 0}
        assert data["overdue_count"] == 0
        assert data["average_sessions_per_chapter"] == 0.0

    def test_counts_category_distribution(self, client, sample_subject, sample_hard_subject, auth_headers):
        response = client.get("/api/metrics", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_chapters"] == 2
        assert data["category_distribution"]["MEDIUM"] == 1
        assert data["category_distribution"]["HARD"] == 1

    def test_counts_average_sessions(self, client, sample_subject, auth_headers):
        client.post(
            "/api/reviews/complete",
            headers=auth_headers,
            json={"subject_id": sample_subject.id, "rating": "EXCELLENT", "completed_at": "2026-01-25"},
        )
        response = client.get("/api/metrics", headers=auth_headers)

        data = response.json()
        assert data["total_sessions"] == 1
        assert data["average_sessions_per_chapter"] == 1.0

    def test_uses_final_category_for_completed_chapters(self, client, db, sample_subject, auth_headers):
        from app.services.subject_service import SubjectService
        from app.models.user import User
        from app.models.enums import Category

        user = db.query(User).first()
        subject = SubjectService(db, user).get_by_id(sample_subject.id)
        subject.is_final_recall_reached = True
        subject.final_category = Category.EASY
        subject.category = Category.HARD  # stale/irrelevant once final
        db.commit()

        response = client.get("/api/metrics", headers=auth_headers)
        data = response.json()
        # Should count by final_category (EASY), not the frozen in-flight category (HARD)
        assert data["category_distribution"]["EASY"] == 1
        assert data["category_distribution"]["HARD"] == 0
        assert data["final_recall_reached_count"] == 1

    def test_requires_authentication(self, client):
        response = client.get("/api/metrics")
        assert response.status_code == 401
