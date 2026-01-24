"""
Tests for user data isolation.

These tests ensure that users can only access their own data
and cannot see or modify other users' subjects.

Security: These tests verify the multi-tenant isolation.
"""

import pytest
from datetime import date


class TestSubjectIsolation:
    """Tests for subject data isolation between users."""

    def test_cannot_see_other_user_subjects(
        self, 
        client, 
        test_user,
        other_user_subject,
        auth_headers
    ):
        """User A should not see User B's subjects in list."""
        response = client.get("/api/subjects", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Should not contain other user's subject
        subject_ids = [s["id"] for s in data]
        assert other_user_subject.id not in subject_ids

    def test_cannot_get_other_user_subject_by_id(
        self,
        client,
        other_user_subject,
        auth_headers
    ):
        """User A should get 404 when trying to access User B's subject."""
        response = client.get(
            f"/api/subjects/{other_user_subject.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    def test_cannot_update_other_user_subject(
        self,
        client,
        other_user_subject,
        auth_headers
    ):
        """User A should get 404 when trying to update User B's subject."""
        response = client.put(
            f"/api/subjects/{other_user_subject.id}",
            headers=auth_headers,
            json={"name": "Hacked Subject"}
        )
        
        assert response.status_code == 404

    def test_cannot_delete_other_user_subject(
        self,
        client,
        other_user_subject,
        auth_headers
    ):
        """User A should get 404 when trying to delete User B's subject."""
        response = client.delete(
            f"/api/subjects/{other_user_subject.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 404

    def test_same_name_allowed_for_different_users(
        self,
        client,
        sample_subject,
        other_auth_headers
    ):
        """Different users should be able to use the same subject name."""
        # sample_subject belongs to test_user with name "Cardiology"
        # other_user should be able to create a subject with same name
        response = client.post(
            "/api/subjects",
            headers=other_auth_headers,
            json={
                "name": sample_subject.name,  # Same name
                "start_date": "2026-01-25",
                "schedule_type": "DEFAULT"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == sample_subject.name


class TestReviewsIsolation:
    """Tests for review data isolation between users."""

    def test_today_reviews_only_shows_own_subjects(
        self,
        client,
        sample_subject,
        other_user_subject,
        auth_headers
    ):
        """Today's reviews should only include user's own subjects."""
        response = client.get("/api/reviews/today", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that no other user's subjects are included
        subject_ids = [s["id"] for s in data["subjects"]]
        assert other_user_subject.id not in subject_ids

    def test_upcoming_reviews_only_shows_own_subjects(
        self,
        client,
        sample_subject,
        other_user_subject,
        auth_headers
    ):
        """Upcoming reviews should only include user's own subjects."""
        response = client.get(
            "/api/reviews/upcoming?days=30",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Collect all subject IDs from all dates
        all_subject_ids = []
        for date_subjects in data["reviews"].values():
            all_subject_ids.extend([s["id"] for s in date_subjects])
        
        assert other_user_subject.id not in all_subject_ids


class TestAuthRequired:
    """Tests that all protected endpoints require authentication."""

    def test_subjects_list_requires_auth(self, client):
        """GET /api/subjects should require authentication."""
        response = client.get("/api/subjects")
        assert response.status_code == 401

    def test_subjects_create_requires_auth(self, client):
        """POST /api/subjects should require authentication."""
        response = client.post("/api/subjects", json={
            "name": "Test",
            "start_date": "2026-01-25",
            "schedule_type": "DEFAULT"
        })
        assert response.status_code == 401

    def test_subjects_get_requires_auth(self, client, sample_subject):
        """GET /api/subjects/{id} should require authentication."""
        response = client.get(f"/api/subjects/{sample_subject.id}")
        assert response.status_code == 401

    def test_subjects_update_requires_auth(self, client, sample_subject):
        """PUT /api/subjects/{id} should require authentication."""
        response = client.put(
            f"/api/subjects/{sample_subject.id}",
            json={"name": "Updated"}
        )
        assert response.status_code == 401

    def test_subjects_delete_requires_auth(self, client, sample_subject):
        """DELETE /api/subjects/{id} should require authentication."""
        response = client.delete(f"/api/subjects/{sample_subject.id}")
        assert response.status_code == 401

    def test_reviews_today_requires_auth(self, client):
        """GET /api/reviews/today should require authentication."""
        response = client.get("/api/reviews/today")
        assert response.status_code == 401

    def test_reviews_upcoming_requires_auth(self, client):
        """GET /api/reviews/upcoming should require authentication."""
        response = client.get("/api/reviews/upcoming")
        assert response.status_code == 401
