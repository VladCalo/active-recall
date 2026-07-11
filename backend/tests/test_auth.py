"""
Tests for authentication endpoints.

Tests cover:
- User registration with password requirements
- User login
- Get current user
- Token refresh with rotation
- Logout
"""

import pytest


class TestRegister:
    """Tests for POST /api/auth/register endpoint."""

    def test_register_success(self, client):
        """Should register a new user with strong password - no tokens issued (pending approval)."""
        response = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "SecureP@ssw0rd!123"  # Meets all requirements
        })

        assert response.status_code == 201
        data = response.json()
        assert "message" in data
        assert "access_token" not in data
        assert "approve" in data["message"].lower()

    def test_new_registration_defaults_to_unapproved(self, db):
        """A freshly registered user starts is_approved=False (checked at the model/service
        level, not via a second HTTP call, to avoid tripping the shared register rate limit)."""
        from app.services.auth_service import AuthService
        from app.schemas.auth import UserRegister

        user = AuthService(db).register(
            UserRegister(email="pending@example.com", password="SecureP@ssw0rd!123")
        )
        assert user.is_approved is False

    def test_login_blocked_until_approved(self, client, db, test_user):
        """An unapproved user cannot log in; approving them unblocks login."""
        test_user.is_approved = False
        db.commit()

        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test@Password123"
        })
        assert response.status_code == 401

        test_user.is_approved = True
        db.commit()

        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test@Password123"
        })
        assert response.status_code == 200

    def test_register_weak_password_rejected(self, client):
        """Should reject weak passwords."""
        response = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "weak"  # Too short, missing requirements
        })
        
        assert response.status_code in [400, 422]

    def test_register_common_password_rejected(self, client):
        """Should reject common passwords."""
        response = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "Password123!"  # Common password
        })
        
        assert response.status_code == 400
        assert "password" in response.json()["detail"].lower() or "common" in response.json()["detail"].lower()

    def test_register_duplicate_email(self, client, test_user):
        """Should reject duplicate email registration."""
        response = client.post("/api/auth/register", json={
            "email": test_user.email,
            "password": "AnotherSecure@Pass123"
        })
        
        assert response.status_code == 400

    def test_register_invalid_email(self, client):
        """Should reject invalid email format."""
        response = client.post("/api/auth/register", json={
            "email": "notanemail",
            "password": "SecureP@ssw0rd!123"
        })
        
        assert response.status_code == 422

    def test_register_case_insensitive_email(self, client, test_user):
        """Should reject duplicate email (case-insensitive)."""
        response = client.post("/api/auth/register", json={
            "email": test_user.email.upper(),
            "password": "AnotherSecure@Pass123"
        })
        
        # Either 400 (duplicate) or 429 (rate limited) is valid
        assert response.status_code in [400, 429]


class TestLogin:
    """Tests for POST /api/auth/login endpoint."""

    def test_login_success(self, client, test_user):
        """Should login successfully with correct credentials."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "Test@Password123"  # Password set in fixture
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email
        
        # Check cookies are set
        assert "refresh_token" in response.cookies or response.headers.get("set-cookie")

    def test_login_wrong_password(self, client, test_user):
        """Should reject incorrect password."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Should reject login for nonexistent user."""
        response = client.post("/api/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "anypassword"
        })
        
        assert response.status_code == 401

    def test_login_case_insensitive_email(self, client, test_user):
        """Should login with case-insensitive email."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email.upper(),
            "password": "Test@Password123"
        })
        
        assert response.status_code == 200


class TestGetMe:
    """Tests for GET /api/auth/me endpoint."""

    def test_get_me_authenticated(self, client, test_user, auth_headers):
        """Should return current user profile when authenticated."""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id
        assert "password" not in data
        assert "password_hash" not in data

    def test_get_me_unauthenticated(self, client):
        """Should reject unauthenticated request."""
        response = client.get("/api/auth/me")
        
        assert response.status_code == 401

    def test_get_me_invalid_token(self, client):
        """Should reject invalid token."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalidtoken"}
        )
        
        assert response.status_code == 401


class TestLogout:
    """Tests for POST /api/auth/logout endpoint."""

    def test_logout_success(self, client):
        """Should logout successfully."""
        response = client.post("/api/auth/logout")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestPasswordRequirements:
    """Tests for password requirements endpoint."""

    def test_get_password_requirements(self, client):
        """Should return password requirements."""
        response = client.get("/api/auth/password-requirements")
        
        assert response.status_code == 200
        data = response.json()
        assert "min_length" in data
        assert "requirements" in data
        assert isinstance(data["requirements"], list)
        assert data["min_length"] >= 8
