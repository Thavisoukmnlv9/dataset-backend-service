"""Unit tests for app.core.security — JWT, password hashing, validation."""

import pytest
from app.core.security import (
    hash_password,
    verify_password,
    hash_token,
    create_access_token,
    create_refresh_token,
    verify_token,
    validate_password_strength,
    create_email_verification_token,
    verify_email_verification_token,
)


class TestPasswordHashing:
    def test_hash_and_verify_correct_password(self):
        raw = "CorrectHorse99"
        hashed = hash_password(raw)
        assert verify_password(raw, hashed) is True

    def test_wrong_password_rejected(self):
        hashed = hash_password("CorrectHorse99")
        assert verify_password("WrongPassword1", hashed) is False

    def test_hash_is_not_plaintext(self):
        raw = "MySecret123"
        hashed = hash_password(raw)
        assert raw not in hashed


class TestTokenHashing:
    def test_hash_token_deterministic(self):
        token = "some-jwt-token"
        assert hash_token(token) == hash_token(token)

    def test_different_tokens_different_hashes(self):
        assert hash_token("token-a") != hash_token("token-b")


class TestJWT:
    def test_create_and_verify_access_token(self):
        data = {"sub": "user-123"}
        token = create_access_token(data)
        payload = verify_token(token)
        assert payload["sub"] == "user-123"
        assert "exp" in payload

    def test_create_and_verify_refresh_token(self):
        data = {"sub": "user-456", "type": "refresh"}
        token = create_refresh_token(data)
        payload = verify_token(token)
        assert payload["sub"] == "user-456"

    def test_expired_token_raises(self):
        from datetime import timedelta
        token = create_access_token({"sub": "x"}, expires_delta=timedelta(seconds=-1))
        with pytest.raises(ValueError, match="expired"):
            verify_token(token)

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Invalid"):
            verify_token("not.a.jwt")


class TestEmailVerificationToken:
    def test_create_and_verify(self):
        data = {"sub": "user-789", "email": "a@b.com"}
        token = create_email_verification_token(data)
        payload = verify_email_verification_token(token)
        assert payload["sub"] == "user-789"
        assert payload["type"] == "email_verification"

    def test_wrong_type_rejected(self):
        token = create_access_token({"sub": "user-1"})
        with pytest.raises(ValueError, match="Invalid token type"):
            verify_email_verification_token(token)


class TestPasswordStrength:
    @pytest.mark.parametrize("pw,expected", [
        ("Short1A", False),
        ("alllowercase1", False),
        ("ALLUPPERCASE1", False),
        ("NoDigitsHere", False),
        ("ValidPass1", True),
        ("Another1Ok", True),
    ])
    def test_password_validation(self, pw, expected):
        assert validate_password_strength(pw) is expected
