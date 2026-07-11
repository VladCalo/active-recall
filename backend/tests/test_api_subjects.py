"""
Tests for the /api/subjects endpoints.

Tests cover CRUD operations and validation for the simplified
(name, start_date) chapter schema. All tests use authenticated requests.
"""

from datetime import date
from unittest.mock import patch

from app.services.subject_service import SubjectService


class TestCreateSubject:
    """Tests for POST /api/subjects endpoint."""

    def test_creates_subject_starting_at_medium_stage_0(self, client, auth_headers):
        response = client.post("/api/subjects", headers=auth_headers, json={
            "name": "Cardiology",
            "start_date": "2026-01-25",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Cardiology"
        assert data["start_date"] == "2026-01-25"
        assert data["category"] == "MEDIUM"
        assert data["stage"] == 0
        assert data["next_due_date"] == "2026-01-30"  # +5 days
        assert data["total_active_recall_count"] == 0
        assert data["is_final_recall_reached"] is False
        assert "id" in data

    def test_rejects_duplicate_name_for_same_user(self, client, sample_subject, auth_headers):
        response = client.post("/api/subjects", headers=auth_headers, json={
            "name": sample_subject.name.lower(),  # case-insensitive
            "start_date": "2026-01-25",
        })

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_rejects_creation_during_reference_mode(self, client, auth_headers):
        with patch.object(SubjectService, "_today", return_value=date(2026, 10, 20)):
            response = client.post("/api/subjects", headers=auth_headers, json={
                "name": "Test",
                "start_date": "2026-10-20",
            })

        assert response.status_code == 400
        assert "Reference Mode" in response.json()["detail"]


class TestListSubjects:
    """Tests for GET /api/subjects endpoint."""

    def test_returns_empty_list(self, client, auth_headers):
        response = client.get("/api/subjects", headers=auth_headers)

        assert response.status_code == 200
        assert response.json() == []

    def test_returns_user_subjects(self, client, sample_subject, sample_hard_subject, auth_headers):
        response = client.get("/api/subjects", headers=auth_headers)

        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_includes_computed_fields(self, client, sample_subject, auth_headers):
        response = client.get("/api/subjects", headers=auth_headers)

        subject = response.json()[0]
        assert "next_due_date" in subject
        assert "category" in subject
        assert "stage" in subject
        assert "total_active_recall_count" in subject


class TestGetSubject:
    """Tests for GET /api/subjects/{id} endpoint."""

    def test_returns_subject(self, client, sample_subject, auth_headers):
        response = client.get(f"/api/subjects/{sample_subject.id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_subject.id
        assert data["name"] == "Cardiology"

    def test_returns_404_for_unknown_id(self, client, auth_headers):
        response = client.get("/api/subjects/unknown-id", headers=auth_headers)
        assert response.status_code == 404


class TestUpdateSubject:
    """Tests for PUT /api/subjects/{id} endpoint."""

    def test_updates_name(self, client, sample_subject, auth_headers):
        response = client.put(f"/api/subjects/{sample_subject.id}", headers=auth_headers, json={
            "name": "Cardiology Updated"
        })

        assert response.status_code == 200
        assert response.json()["name"] == "Cardiology Updated"

    def test_updates_start_date(self, client, sample_subject, auth_headers):
        response = client.put(f"/api/subjects/{sample_subject.id}", headers=auth_headers, json={
            "start_date": "2026-02-01"
        })

        assert response.status_code == 200
        assert response.json()["start_date"] == "2026-02-01"

    def test_rejects_duplicate_name(self, client, sample_subject, sample_hard_subject, auth_headers):
        response = client.put(f"/api/subjects/{sample_hard_subject.id}", headers=auth_headers, json={
            "name": sample_subject.name
        })

        assert response.status_code == 400

    def test_returns_404_for_unknown_id(self, client, auth_headers):
        response = client.put("/api/subjects/unknown-id", headers=auth_headers, json={
            "name": "Test"
        })

        assert response.status_code == 404


class TestDeleteSubject:
    """Tests for DELETE /api/subjects/{id} endpoint."""

    def test_deletes_subject(self, client, sample_subject, auth_headers):
        response = client.delete(f"/api/subjects/{sample_subject.id}", headers=auth_headers)
        assert response.status_code == 204

        response = client.get(f"/api/subjects/{sample_subject.id}", headers=auth_headers)
        assert response.status_code == 404

    def test_returns_404_for_unknown_id(self, client, auth_headers):
        response = client.delete("/api/subjects/unknown-id", headers=auth_headers)
        assert response.status_code == 404
