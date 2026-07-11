"""Tests for the /api/settings endpoint (per-user editable exam date)."""

from datetime import date, timedelta


class TestGetSettings:
    def test_returns_default_when_unset(self, client, auth_headers):
        response = client.get("/api/settings", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["exam_date"] == "2026-11-13"
        assert data["final_recall_cutoff_date"] == "2026-10-13"
        assert data["reference_mode_end_date"] == "2026-11-12"

    def test_requires_authentication(self, client):
        response = client.get("/api/settings")
        assert response.status_code == 401


class TestUpdateSettings:
    def test_updates_exam_date_and_recomputes_derived_dates(self, client, auth_headers):
        new_exam_date = (date.today() + timedelta(days=60)).isoformat()
        response = client.put("/api/settings", headers=auth_headers, json={"exam_date": new_exam_date})

        assert response.status_code == 200
        data = response.json()
        assert data["exam_date"] == new_exam_date

        expected_cutoff = (date.fromisoformat(new_exam_date) - timedelta(days=31)).isoformat()
        expected_ref_end = (date.fromisoformat(new_exam_date) - timedelta(days=1)).isoformat()
        assert data["final_recall_cutoff_date"] == expected_cutoff
        assert data["reference_mode_end_date"] == expected_ref_end

    def test_rejects_exam_date_too_close(self, client, auth_headers):
        too_soon = (date.today() + timedelta(days=10)).isoformat()
        response = client.put("/api/settings", headers=auth_headers, json={"exam_date": too_soon})

        assert response.status_code == 400

    def test_per_user_isolation(self, client, auth_headers, other_auth_headers):
        new_exam_date = (date.today() + timedelta(days=60)).isoformat()
        client.put("/api/settings", headers=auth_headers, json={"exam_date": new_exam_date})

        other_response = client.get("/api/settings", headers=other_auth_headers)
        assert other_response.json()["exam_date"] == "2026-11-13"  # unaffected, still default
