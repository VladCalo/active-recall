"""
Tests for the /api/subjects endpoints.

Tests cover CRUD operations and validation.
"""

import pytest
from datetime import date


class TestCreateSubject:
    """Tests for POST /api/subjects endpoint."""

    def test_creates_subject_with_default_schedule(self, client):
        """Should create subject with default schedule."""
        response = client.post("/api/subjects", json={
            "name": "Cardiology",
            "start_date": "2026-01-25",
            "schedule_type": "DEFAULT"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Cardiology"
        assert data["start_date"] == "2026-01-25"
        assert data["schedule_type"] == "DEFAULT"
        assert data["custom_intervals_days"] is None
        assert "id" in data
        assert "intervals" in data
        assert data["intervals"] == [1, 3, 7, 14, 30, 60, 120, 180]

    def test_creates_subject_with_custom_schedule(self, client):
        """Should create subject with custom intervals."""
        response = client.post("/api/subjects", json={
            "name": "Neurology",
            "start_date": "2026-01-25",
            "schedule_type": "CUSTOM",
            "custom_intervals_days": [2, 5, 10, 20]
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["schedule_type"] == "CUSTOM"
        assert data["custom_intervals_days"] == [2, 5, 10, 20]
        assert data["intervals"] == [2, 5, 10, 20]

    def test_rejects_duplicate_name(self, client, sample_subject):
        """Should reject subject with duplicate name (case-insensitive)."""
        response = client.post("/api/subjects", json={
            "name": "cardiology",  # lowercase version
            "start_date": "2026-01-25",
            "schedule_type": "DEFAULT"
        })
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_rejects_custom_without_intervals(self, client):
        """Should reject CUSTOM schedule without intervals."""
        response = client.post("/api/subjects", json={
            "name": "Test",
            "start_date": "2026-01-25",
            "schedule_type": "CUSTOM"
            # missing custom_intervals_days
        })
        
        assert response.status_code == 422

    def test_validates_intervals(self, client):
        """Should validate intervals are positive integers."""
        response = client.post("/api/subjects", json={
            "name": "Test",
            "start_date": "2026-01-25",
            "schedule_type": "CUSTOM",
            "custom_intervals_days": [0, 1, 2]  # 0 is invalid
        })
        
        assert response.status_code == 422

    def test_rejects_duplicate_intervals(self, client):
        """Should reject duplicate intervals."""
        response = client.post("/api/subjects", json={
            "name": "Test",
            "start_date": "2026-01-25",
            "schedule_type": "CUSTOM",
            "custom_intervals_days": [1, 2, 2, 3]
        })
        
        assert response.status_code == 422

    def test_sorts_intervals(self, client):
        """Should sort intervals ascending."""
        response = client.post("/api/subjects", json={
            "name": "Test",
            "start_date": "2026-01-25",
            "schedule_type": "CUSTOM",
            "custom_intervals_days": [10, 1, 5]
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["custom_intervals_days"] == [1, 5, 10]


class TestListSubjects:
    """Tests for GET /api/subjects endpoint."""

    def test_returns_empty_list(self, client):
        """Should return empty list when no subjects exist."""
        response = client.get("/api/subjects")
        
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_all_subjects(self, client, sample_subject, sample_custom_subject):
        """Should return all subjects."""
        response = client.get("/api/subjects")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_includes_computed_fields(self, client, sample_subject):
        """Should include next_due_date and intervals."""
        response = client.get("/api/subjects")
        
        data = response.json()
        subject = data[0]
        assert "next_due_date" in subject
        assert "intervals" in subject


class TestGetSubject:
    """Tests for GET /api/subjects/{id} endpoint."""

    def test_returns_subject(self, client, sample_subject):
        """Should return subject by ID."""
        response = client.get(f"/api/subjects/{sample_subject.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_subject.id
        assert data["name"] == "Cardiology"

    def test_returns_404_for_unknown_id(self, client):
        """Should return 404 for unknown ID."""
        response = client.get("/api/subjects/unknown-id")
        
        assert response.status_code == 404


class TestUpdateSubject:
    """Tests for PUT /api/subjects/{id} endpoint."""

    def test_updates_name(self, client, sample_subject):
        """Should update subject name."""
        response = client.put(f"/api/subjects/{sample_subject.id}", json={
            "name": "Cardiology Updated"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Cardiology Updated"

    def test_updates_start_date(self, client, sample_subject):
        """Should update start date."""
        response = client.put(f"/api/subjects/{sample_subject.id}", json={
            "start_date": "2026-02-01"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["start_date"] == "2026-02-01"

    def test_switches_to_custom_schedule(self, client, sample_subject):
        """Should switch from DEFAULT to CUSTOM schedule."""
        response = client.put(f"/api/subjects/{sample_subject.id}", json={
            "schedule_type": "CUSTOM",
            "custom_intervals_days": [1, 5, 10]
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["schedule_type"] == "CUSTOM"
        assert data["custom_intervals_days"] == [1, 5, 10]

    def test_switches_to_default_clears_intervals(self, client, sample_custom_subject):
        """Switching to DEFAULT should clear custom intervals."""
        response = client.put(f"/api/subjects/{sample_custom_subject.id}", json={
            "schedule_type": "DEFAULT"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["schedule_type"] == "DEFAULT"
        assert data["custom_intervals_days"] is None

    def test_rejects_duplicate_name(self, client, sample_subject, sample_custom_subject):
        """Should reject name that conflicts with another subject."""
        response = client.put(f"/api/subjects/{sample_custom_subject.id}", json={
            "name": "Cardiology"  # Already taken by sample_subject
        })
        
        assert response.status_code == 400

    def test_returns_404_for_unknown_id(self, client):
        """Should return 404 for unknown ID."""
        response = client.put("/api/subjects/unknown-id", json={
            "name": "Test"
        })
        
        assert response.status_code == 404


class TestDeleteSubject:
    """Tests for DELETE /api/subjects/{id} endpoint."""

    def test_deletes_subject(self, client, sample_subject):
        """Should delete subject."""
        response = client.delete(f"/api/subjects/{sample_subject.id}")
        
        assert response.status_code == 204
        
        # Verify deleted
        response = client.get(f"/api/subjects/{sample_subject.id}")
        assert response.status_code == 404

    def test_returns_404_for_unknown_id(self, client):
        """Should return 404 for unknown ID."""
        response = client.delete("/api/subjects/unknown-id")
        
        assert response.status_code == 404
