"""
Tests unitaires — SecurityUtils (hashing, JWT tokens).
"""
from datetime import timedelta

import pytest
from jose import jwt

from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.utils import SecurityUtils

settings = get_settings()


# ═══════════════════════════════════════════════════════════════════════════
#  PASSWORD HASHING
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestPasswordHashing:
    def test_hash_returns_non_empty_string(self):
        hashed = SecurityUtils.get_password_hash("MonMotDePasse1")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    def test_hash_differs_from_plain_text(self):
        plain = "MonMotDePasse1"
        hashed = SecurityUtils.get_password_hash(plain)
        assert hashed != plain

    def test_same_password_produces_different_hashes(self):
        """Bcrypt utilise un salt aléatoire, donc 2 hashes diffèrent."""
        h1 = SecurityUtils.get_password_hash("MonMotDePasse1")
        h2 = SecurityUtils.get_password_hash("MonMotDePasse1")
        assert h1 != h2

    def test_verify_correct_password(self):
        plain = "MonMotDePasse1"
        hashed = SecurityUtils.get_password_hash(plain)
        assert SecurityUtils.verify_password(plain, hashed) is True

    def test_verify_wrong_password(self):
        hashed = SecurityUtils.get_password_hash("MonMotDePasse1")
        assert SecurityUtils.verify_password("MauvaisMotDePasse", hashed) is False

    def test_verify_empty_password(self):
        hashed = SecurityUtils.get_password_hash("MonMotDePasse1")
        assert SecurityUtils.verify_password("", hashed) is False


# ═══════════════════════════════════════════════════════════════════════════
#  ACCESS TOKEN
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestAccessToken:
    def test_contains_sub_and_role(self):
        token = SecurityUtils.create_access_token(
            subject="admin@test.com",
            role="ADMIN",
            expires_delta=timedelta(minutes=30),
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "admin@test.com"
        assert payload["role"] == "ADMIN"

    def test_contains_expiration(self):
        token = SecurityUtils.create_access_token(
            subject="admin@test.com",
            role="ADMIN",
            expires_delta=timedelta(minutes=30),
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "exp" in payload

    def test_does_not_contain_type_field(self):
        """L'access token ne doit PAS avoir le champ 'type' (reserve a refresh/reset)."""
        token = SecurityUtils.create_access_token(
            subject="admin@test.com",
            role="ADMIN",
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "type" not in payload

    def test_contains_jti(self):
        """L'access token contient un JTI unique."""
        token = SecurityUtils.create_access_token(subject="u@t.com", role="ADMIN")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "jti" in payload
        assert isinstance(payload["jti"], str)
        assert len(payload["jti"]) == 32

    def test_contains_iat_and_iss(self):
        """L'access token contient iat et iss."""
        token = SecurityUtils.create_access_token(subject="u@t.com", role="ADMIN")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "iat" in payload
        assert payload["iss"] == settings.APP_NAME

    def test_custom_expiration_delta(self):
        token = SecurityUtils.create_access_token(
            subject="user@test.com",
            role="SERVANT",
            expires_delta=timedelta(minutes=5),
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "user@test.com"

    def test_default_expiration_no_delta(self):
        """Sans expires_delta, utilise JWT_ACCESS_TOKEN_EXPIRE_MINUTES."""
        token = SecurityUtils.create_access_token(
            subject="user@test.com",
            role="SERVANT",
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "user@test.com"

    def test_all_roles_accepted(self):
        for role in ("ADMIN", "AUMÔNIER", "SERVANT", "PARENT"):
            token = SecurityUtils.create_access_token(subject="u@t.com", role=role)
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            assert payload["role"] == role


# ═══════════════════════════════════════════════════════════════════════════
#  REFRESH TOKEN
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestRefreshToken:
    def test_contains_type_refresh(self):
        token = SecurityUtils.create_refresh_token(
            subject="admin@test.com",
            role="ADMIN",
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "refresh"

    def test_contains_role(self):
        token = SecurityUtils.create_refresh_token(
            subject="admin@test.com",
            role="ADMIN",
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["role"] == "ADMIN"

    def test_contains_sub_and_exp(self):
        token = SecurityUtils.create_refresh_token(
            subject="user@test.com",
            role="SERVANT",
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "user@test.com"
        assert "exp" in payload

    def test_custom_expiration(self):
        token = SecurityUtils.create_refresh_token(
            subject="user@test.com",
            role="PARENT",
            expires_delta=timedelta(days=1),
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "refresh"


# ═══════════════════════════════════════════════════════════════════════════
#  RESET TOKEN
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestResetToken:
    def test_contains_type_reset(self):
        token = SecurityUtils.create_reset_token(subject="user@test.com")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["type"] == "reset"

    def test_contains_sub(self):
        token = SecurityUtils.create_reset_token(subject="user@test.com")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "user@test.com"

    def test_does_not_contain_role(self):
        """Le reset token ne contient pas de rôle — il sert uniquement au reset."""
        token = SecurityUtils.create_reset_token(subject="user@test.com")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "role" not in payload

    def test_custom_expiration(self):
        token = SecurityUtils.create_reset_token(
            subject="user@test.com",
            expires_delta=timedelta(minutes=5),
        )
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload["sub"] == "user@test.com"


# ═══════════════════════════════════════════════════════════════════════════
#  TOKEN DECODING — INVALID CASES
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestTokenDecodingErrors:
    def test_wrong_secret_key_fails(self):
        token = SecurityUtils.create_access_token(subject="u@t.com", role="ADMIN")
        with pytest.raises(Exception):
            jwt.decode(token, "wrong-secret-key", algorithms=[settings.JWT_ALGORITHM])

    def test_wrong_algorithm_fails(self):
        token = SecurityUtils.create_access_token(subject="u@t.com", role="ADMIN")
        with pytest.raises(Exception):
            jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS384"])

    def test_expired_token_fails(self):
        token = SecurityUtils.create_access_token(
            subject="u@t.com",
            role="ADMIN",
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(Exception):
            jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

    def test_garbage_token_fails(self):
        with pytest.raises(Exception):
            jwt.decode(
                "not.a.real.token",
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
