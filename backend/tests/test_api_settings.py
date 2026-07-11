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
        assert data["ladders"] == {"HARD": [2, 4, 6, 8], "MEDIUM": [5, 8, 11, 14], "EASY": [10, 14, 18, 21]}
        assert data["is_ladders_customized"] is False
        assert data["no_revision_enabled"] is True
        assert data["no_revision_weekday"] == 6

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


class TestUpdateLadders:
    def test_sets_custom_ladders(self, client, auth_headers):
        response = client.put("/api/settings", headers=auth_headers, json={
            "ladders": {"HARD": [1, 2, 3, 4], "MEDIUM": [5, 8, 11, 14], "EASY": [10, 14, 18, 21]}
        })

        assert response.status_code == 200
        data = response.json()
        assert data["ladders"]["HARD"] == [1, 2, 3, 4]
        assert data["is_ladders_customized"] is True

    def test_rejects_non_ascending_ladder(self, client, auth_headers):
        response = client.put("/api/settings", headers=auth_headers, json={
            "ladders": {"HARD": [4, 3, 2, 1], "MEDIUM": [5, 8, 11, 14], "EASY": [10, 14, 18, 21]}
        })
        assert response.status_code == 422

    def test_rejects_wrong_stage_count(self, client, auth_headers):
        response = client.put("/api/settings", headers=auth_headers, json={
            "ladders": {"HARD": [1, 2, 3], "MEDIUM": [5, 8, 11, 14], "EASY": [10, 14, 18, 21]}
        })
        assert response.status_code == 422

    def test_reset_to_default(self, client, auth_headers):
        client.put("/api/settings", headers=auth_headers, json={
            "ladders": {"HARD": [1, 2, 3, 4], "MEDIUM": [5, 8, 11, 14], "EASY": [10, 14, 18, 21]}
        })

        response = client.put("/api/settings", headers=auth_headers, json={"reset_ladders_to_default": True})

        assert response.status_code == 200
        data = response.json()
        assert data["ladders"]["HARD"] == [2, 4, 6, 8]
        assert data["is_ladders_customized"] is False

    def test_custom_ladder_affects_actual_scheduling(self, client, sample_subject, auth_headers):
        settings_response = client.put("/api/settings", headers=auth_headers, json={
            "ladders": {"HARD": [1, 2, 3, 4], "MEDIUM": [90, 95, 100, 105], "EASY": [10, 14, 18, 21]}
        })
        assert settings_response.status_code == 200
        assert settings_response.json()["is_ladders_customized"] is True

        response = client.post(
            "/api/reviews/complete",
            headers=auth_headers,
            json={"subject_id": sample_subject.id, "rating": "MANY_CONFUSIONS", "completed_at": "2026-01-25"},
        )
        assert response.status_code == 200
        data = response.json()
        # Medium + Many confusions -> Medium stage 0, using the custom 90-day interval
        assert data["next_due_date"] == "2026-04-25"


class TestUpdateNoRevisionRule:
    def test_disables_no_revision_shift(self, client, sample_subject, auth_headers):
        client.put("/api/settings", headers=auth_headers, json={"no_revision_enabled": False})

        # Medium stage0 (+5d) from Tue 2026-01-20 would normally shift off Sunday 1/25 -> Mon 1/26
        response = client.post(
            "/api/reviews/complete",
            headers=auth_headers,
            json={"subject_id": sample_subject.id, "rating": "MANY_CONFUSIONS", "completed_at": "2026-01-20"},
        )
        assert response.status_code == 200
        # Many confusions on Medium -> Medium stage0 (+5d) = Jan 25 (Sunday), unshifted since disabled
        assert response.json()["next_due_date"] == "2026-01-25"

    def test_changes_no_revision_weekday(self, client, sample_subject, auth_headers):
        client.put("/api/settings", headers=auth_headers, json={"no_revision_weekday": 2})  # Wednesday

        response = client.post(
            "/api/reviews/complete",
            headers=auth_headers,
            json={"subject_id": sample_subject.id, "rating": "MANY_CONFUSIONS", "completed_at": "2026-01-16"},
        )
        assert response.status_code == 200
        # Many confusions on Medium -> Medium stage0 (+5d) from Jan16 = Jan21 (Wednesday) -> shifted to Jan22
        assert response.json()["next_due_date"] == "2026-01-22"
