"""
Tests de sécurité — JWT (tokens falsifiés, expirés, manipulés).
"""

from datetime import timedelta

import jwt
import pytest
from httpx import AsyncClient

from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.utils import SecurityUtils
from tests.conftest import make_access_token

settings = get_settings()


# ═══════════════════════════════════════════════════════════════════════════
#  TOKENS INVALIDES
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestInvalidTokens:
    """Vérifie que les tokens invalides sont rejetés."""

    async def test_no_token_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/invitations")
        assert resp.status_code == 401

    async def test_empty_bearer_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": "Bearer "},
        )
        assert resp.status_code == 401

    async def test_garbage_token_401(self, client: AsyncClient):
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": "Bearer not.a.valid.jwt.token"},
        )
        assert resp.status_code == 401

    async def test_wrong_signature_401(self, client: AsyncClient, admin_user):
        """Token signé avec une mauvaise clé."""
        payload = {"sub": admin_user.email, "role": "ADMIN", "exp": 9999999999}
        bad_token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code == 401

    async def test_wrong_algorithm_401(self, client: AsyncClient, admin_user):
        """Token encodé avec un algorithme différent."""
        payload = {"sub": admin_user.email, "role": "ADMIN", "exp": 9999999999}
        # Encode avec HS384 au lieu de HS256
        bad_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS384")
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  TOKEN EXPIRÉ
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestExpiredToken:
    async def test_expired_access_token_401(self, client: AsyncClient, admin_user):
        """Token expiré = rejeté."""
        expired_token = SecurityUtils.create_access_token(
            subject=admin_user.email,
            role=admin_user.role.value,
            expires_delta=timedelta(seconds=-10),
        )
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  TOKEN SANS RÔLE
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestTokenMissingRole:
    async def test_token_without_role_rejected(self, client: AsyncClient, admin_user):
        """Un token sans le champ 'role' doit être rejeté (role est obligatoire)."""
        payload = {
            "sub": admin_user.email,
            "exp": 9999999999,
            # PAS de "role"
        }
        token_no_role = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": f"Bearer {token_no_role}"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  TOKEN ROLE MISMATCH (JWT ≠ BDD)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestTokenRoleMismatch:
    async def test_servant_token_claiming_admin_role(self, client: AsyncClient, servant_user):
        """Token prétend être ADMIN mais l'utilisateur en BDD est SERVANT → 401."""
        fake_token = SecurityUtils.create_access_token(
            subject=servant_user.email,
            role="ADMIN",  # Rôle falsifié
            expires_delta=timedelta(minutes=30),
        )
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": f"Bearer {fake_token}"},
        )
        assert resp.status_code == 401
        assert "mismatch" in resp.json().get("detail", "").lower()

    async def test_parent_token_claiming_admin_role(self, client: AsyncClient, parent_user):
        """Token prétend être ADMIN mais l'utilisateur est PARENT → 401."""
        fake_token = SecurityUtils.create_access_token(
            subject=parent_user.email,
            role="ADMIN",
            expires_delta=timedelta(minutes=30),
        )
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": f"Bearer {fake_token}"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  TOKEN POUR UTILISATEUR INEXISTANT
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestTokenNonexistentUser:
    async def test_token_for_deleted_user_401(self, client: AsyncClient):
        """Token valide pour un email qui n'existe pas en BDD → 401."""
        ghost_token = SecurityUtils.create_access_token(
            subject="deleted@test.com",
            role="ADMIN",
            expires_delta=timedelta(minutes=30),
        )
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": f"Bearer {ghost_token}"},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  INJECTION ATTEMPTS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestInjectionAttempts:
    """Vérifie que les tentatives d'injection SQL / XSS sont inoffensives."""

    SQL_INJECTION_PAYLOADS = [
        "' OR 1=1 --",
        "'; DROP TABLE users; --",
        "admin@test.com' OR '1'='1",
        "1; SELECT * FROM users",
    ]

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_sql_injection_in_email_login(self, client: AsyncClient, payload):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": payload, "password": "whatever"},
        )
        # L'injection ne doit JAMAIS retourner 200 (accès réussi).
        # Les payloads non-email → 401 (Pydantic rejette le format email).
        assert resp.status_code in (
            401,
            422,
        ), f"SQL injection should return 401/422, got {resp.status_code}: {payload}"

    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    async def test_sql_injection_in_phone_login(self, client: AsyncClient, payload):
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": payload, "password": "whatever"},
        )
        assert resp.status_code in (401, 422)

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "javascript:alert(1)",
        "<img src=x onerror=alert(1)>",
    ]

    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_registration(self, client: AsyncClient, payload):
        import re
        import uuid as _uuid

        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": f"xss-{_uuid.uuid4().hex[:6]}@test.com",
                "password": "TestPass1",
                "first_name": payload,
                "last_name": payload,
                "phone_number": f"+23760009{_uuid.uuid4().int % 9999:04d}",
                "role": "SERVANT",
            },
        )
        # HTML tags are stripped by the sanitization layer before storage.
        # 201 = succès, 422 = rejeté par validation
        assert resp.status_code in (201, 422)
        if resp.status_code == 201:
            body = resp.json()
            expected = re.sub(r"<[^>]+>", "", payload).strip()
            # Stored value must equal the sanitized input (no HTML tags)
            assert body["first_name"] == expected
            assert "<" not in body["first_name"]
            assert ">" not in body["first_name"]


# ═══════════════════════════════════════════════════════════════════════════
#  REFRESH TOKEN MISUSE
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestRefreshTokenMisuse:
    async def test_refresh_token_cannot_be_used_as_access(self, client: AsyncClient, admin_user):
        """Un refresh token ne doit pas fonctionner comme access token."""
        refresh = SecurityUtils.create_refresh_token(
            subject=admin_user.email,
            role=admin_user.role.value,
        )
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": f"Bearer {refresh}"},
        )
        assert resp.status_code == 401

    async def test_reset_token_cannot_be_used_as_access(self, client: AsyncClient, admin_user):
        """Un reset token ne doit pas fonctionner comme access token."""
        reset = SecurityUtils.create_reset_token(subject=admin_user.email)
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers={"Authorization": f"Bearer {reset}"},
        )
        # Reset token n'a pas de "role" → rejeté en 401
        assert resp.status_code == 401
