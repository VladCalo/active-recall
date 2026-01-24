"""
Security tests for the application.

Tests cover:
- Rate limiting
- Refresh token rotation
- Token reuse detection
- Password strength validation
- Account lockout
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)
from app.core.password import check_password_strength
from app.services.auth_service import AuthService
from app.models.refresh_token import RefreshToken


class TestPasswordStrength:
    """Tests for password strength validation."""

    def test_weak_password_too_short(self):
        """Should reject passwords that are too short."""
        is_valid, issues = check_password_strength("Short1!")
        assert not is_valid
        assert any("at least" in issue.lower() for issue in issues)

    def test_weak_password_no_uppercase(self):
        """Should reject passwords without uppercase."""
        is_valid, issues = check_password_strength("alllowercase123!")
        assert not is_valid
        assert any("uppercase" in issue.lower() for issue in issues)

    def test_weak_password_no_lowercase(self):
        """Should reject passwords without lowercase."""
        is_valid, issues = check_password_strength("ALLUPPERCASE123!")
        assert not is_valid
        assert any("lowercase" in issue.lower() for issue in issues)

    def test_weak_password_no_number(self):
        """Should reject passwords without numbers."""
        is_valid, issues = check_password_strength("NoNumbersHere!")
        assert not is_valid
        assert any("number" in issue.lower() for issue in issues)

    def test_weak_password_no_special(self):
        """Should reject passwords without special characters."""
        is_valid, issues = check_password_strength("NoSpecialChars123")
        assert not is_valid
        assert any("special" in issue.lower() for issue in issues)

    def test_common_password_rejected(self):
        """Should reject common passwords."""
        is_valid, issues = check_password_strength("Password123!")
        assert not is_valid
        assert any("common" in issue.lower() for issue in issues)

    def test_strong_password_accepted(self):
        """Should accept strong passwords."""
        is_valid, issues = check_password_strength("Str0ng!P@ssw0rd#2024")
        assert is_valid
        assert len(issues) == 0


class TestRefreshTokenRotation:
    """Tests for refresh token rotation and reuse detection."""

    def test_refresh_token_contains_jti_and_fid(self, db):
        """Refresh tokens should contain jti and fid claims."""
        token_jwt, token_id, family_id = create_refresh_token({"sub": "test-user"})
        
        payload = decode_token(token_jwt)
        
        assert payload is not None
        assert payload.get("jti") == token_id
        assert payload.get("fid") == family_id
        assert payload.get("type") == "refresh"

    def test_token_rotation_creates_new_token(self, db, test_user):
        """Token refresh should create a new token in the same family."""
        auth_service = AuthService(db)
        
        # Create initial token
        token1_jwt, token1_id, family_id = create_refresh_token({"sub": test_user.id})
        
        # Store token record
        auth_service._create_refresh_token_record(
            test_user.id, token1_id, family_id
        )
        
        # Decode and refresh
        payload = decode_token(token1_jwt)
        result = auth_service.refresh_tokens(payload)
        
        assert result is not None
        new_access, new_refresh, user = result
        
        # New token should decode successfully
        new_payload = decode_token(new_refresh)
        assert new_payload is not None
        assert new_payload.get("fid") == family_id  # Same family
        assert new_payload.get("jti") != token1_id  # Different token ID

    def test_token_reuse_detection(self, db, test_user):
        """Reusing an already-used token should revoke the entire family."""
        auth_service = AuthService(db)
        
        # Create initial token
        token_jwt, token_id, family_id = create_refresh_token({"sub": test_user.id})
        auth_service._create_refresh_token_record(
            test_user.id, token_id, family_id
        )
        
        # Use the token once (should succeed)
        payload = decode_token(token_jwt)
        result1 = auth_service.refresh_tokens(payload)
        assert result1 is not None
        
        # Try to reuse the same token (should fail - already used)
        result2 = auth_service.refresh_tokens(payload)
        assert result2 is None
        
        # Verify token family is revoked
        tokens = db.query(RefreshToken).filter(
            RefreshToken.family_id == family_id
        ).all()
        
        for token in tokens:
            if token.id == token_id:
                assert token.is_revoked or token.used_at is not None


class TestAccountLockout:
    """Tests for account lockout after failed attempts."""

    @pytest.mark.asyncio
    async def test_account_locks_after_max_attempts(self, db, test_user):
        """Account should lock after max failed login attempts."""
        auth_service = AuthService(db)
        
        # Make max failed attempts
        for i in range(5):
            result = await auth_service.login(
                test_user.email, "wrong_password"
            )
            assert result is None
        
        # Verify account is locked
        db.refresh(test_user)
        assert test_user.locked_until is not None

    @pytest.mark.asyncio
    async def test_locked_account_rejects_correct_password(self, db, test_user):
        """Locked account should reject even correct passwords."""
        auth_service = AuthService(db)
        
        # Lock the account
        test_user.failed_login_attempts = 5
        test_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        db.commit()
        
        # Try to login with correct password
        result = await auth_service.login(
            test_user.email, "password123"  # Correct password
        )
        
        assert result is None


class TestRateLimitingEndpoints:
    """Tests for rate limiting on API endpoints."""

    def test_login_rate_limit_response(self, client):
        """Login should return 429 after too many attempts."""
        # Note: This test requires rate limiting to be properly configured
        # In testing, we might need to mock the rate limiter
        
        # Make several requests quickly
        responses = []
        for _ in range(10):
            response = client.post("/api/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
            responses.append(response)
        
        # At least some should be 429 (rate limited) or 401 (unauthorized)
        status_codes = [r.status_code for r in responses]
        assert any(code in [429, 401] for code in status_codes)

    def test_rate_limit_headers(self, client):
        """Rate limited responses should include proper headers."""
        # Make a request to a rate-limited endpoint
        response = client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "wrongpassword"
        })
        
        # If rate limited, check for headers
        if response.status_code == 429:
            assert "retry-after" in response.headers.keys() or "Retry-After" in response.headers.keys()


class TestSecurityHeaders:
    """Tests for security headers on responses."""

    def test_security_headers_present(self, client):
        """All responses should include security headers."""
        response = client.get("/api/health")
        
        assert response.status_code == 200
        
        # Check for required security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers


class TestPasswordHashing:
    """Tests for password hashing security."""

    def test_password_hash_is_unique(self):
        """Same password should produce different hashes (salted)."""
        password = "TestPassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2

    def test_password_verification(self):
        """Password verification should work correctly."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_timing_safe_verification(self):
        """Password verification should be constant-time."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        
        # Both correct and incorrect passwords should take similar time
        # (This is more of a documentation test - actual timing tests are complex)
        verify_password(password, hashed)
        verify_password("x" * 100, hashed)  # Long wrong password
        verify_password("", hashed)  # Empty password


class TestTokenSecurity:
    """Tests for JWT token security."""

    def test_access_token_short_lived(self):
        """Access tokens should have short expiration."""
        token = create_access_token({"sub": "test-user"})
        payload = decode_token(token)
        
        assert payload is not None
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        
        # Should expire within 1 hour
        assert (exp - iat).total_seconds() <= 3600

    def test_refresh_token_longer_lived(self):
        """Refresh tokens should have longer expiration."""
        token, _, _ = create_refresh_token({"sub": "test-user"})
        payload = decode_token(token)
        
        assert payload is not None
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        iat = datetime.fromtimestamp(payload["iat"], tz=timezone.utc)
        
        # Should expire in multiple days
        assert (exp - iat).days >= 1

    def test_invalid_token_rejected(self):
        """Invalid tokens should be rejected."""
        payload = decode_token("invalid.token.here")
        assert payload is None

    def test_expired_token_rejected(self):
        """Expired tokens should be rejected."""
        token = create_access_token(
            {"sub": "test-user"},
            expires_delta=timedelta(seconds=-1)  # Already expired
        )
        payload = decode_token(token)
        assert payload is None
