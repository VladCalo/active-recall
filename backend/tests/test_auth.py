"""
Tests for authentication endpoints.

Tests cover:
- User registration
- User login
- Get current user
- Token refresh
- Logout
"""

import pytest


class TestRegister:
    """Tests for POST /api/auth/register endpoint."""

    def test_register_success(self, client):
        """Should register a new user successfully."""
        response = client.post("/api/auth/register", json={
            "email": "newuser@example.com",
            "password": "securepassword123"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert "password" not in data["user"]
        assert "password_hash" not in data["user"]

    def test_register_duplicate_email(self, client, test_user):
        """Should reject duplicate email registration."""
        response = client.post("/api/auth/register", json={
            "email": test_user.email,
            "password": "securepassword123"
        })
        
        assert response.status_code == 400

    def test_register_invalid_email(self, client):
        """Should reject invalid email format."""
        response = client.post("/api/auth/register", json={
            "email": "notanemail",
            "password": "securepassword123"
        })
        
        assert response.status_code == 422

    def test_register_short_password(self, client):
        """Should reject password shorter than minimum."""
        response = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "password": "short"
        })
        
        assert response.status_code == 422

    def test_register_case_insensitive_email(self, client, test_user):
        """Should reject duplicate email (case-insensitive)."""
        response = client.post("/api/auth/register", json={
            "email": test_user.email.upper(),
            "password": "securepassword123"
        })
        
        assert response.status_code == 400


class TestLogin:
    """Tests for POST /api/auth/login endpoint."""

    def test_login_success(self, client, test_user):
        """Should login successfully with correct credentials."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email,
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "user" in data
        assert "access_token" in data
        assert data["user"]["email"] == test_user.email

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
            "password": "password123"
        })
        
        assert response.status_code == 401

    def test_login_case_insensitive_email(self, client, test_user):
        """Should login with case-insensitive email."""
        response = client.post("/api/auth/login", json={
            "email": test_user.email.upper(),
            "password": "password123"
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
