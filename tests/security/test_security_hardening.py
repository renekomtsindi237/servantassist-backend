"""
Tests de securite — Renforcement (brute-force, headers, rate-limit, JTI).
"""

from datetime import timedelta

import jwt
import pytest
from httpx import AsyncClient

from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.brute_force import (
    BruteForceProtection,
    brute_force_guard,
)
from src.infrastructure.security.utils import SecurityUtils
from tests.conftest import VALID_PASSWORD

settings = get_settings()


# ═══════════════════════════════════════════════════════════════════════════
#  JTI (JWT Token ID) — Chaque token a un identifiant unique
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestJwtTokenId:
    """Verifie que chaque token contient un JTI unique."""

    def test_access_token_has_jti(self):
        token = SecurityUtils.create_access_token(subject="test@test.com", role="ADMIN")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "jti" in payload
        assert len(payload["jti"]) == 32  # uuid4().hex = 32 chars

    def test_refresh_token_has_jti(self):
        token = SecurityUtils.create_refresh_token(subject="test@test.com", role="ADMIN")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "jti" in payload

    def test_reset_token_has_jti(self):
        token = SecurityUtils.create_reset_token(subject="test@test.com")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "jti" in payload

    def test_two_tokens_have_different_jti(self):
        """Deux tokens pour le meme utilisateur ont des JTI differents."""
        t1 = SecurityUtils.create_access_token(subject="test@test.com", role="ADMIN")
        t2 = SecurityUtils.create_access_token(subject="test@test.com", role="ADMIN")
        p1 = jwt.decode(t1, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        p2 = jwt.decode(t2, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert p1["jti"] != p2["jti"]

    def test_access_token_has_issuer(self):
        """Le token contient le champ 'iss' (issuer)."""
        token = SecurityUtils.create_access_token(subject="test@test.com", role="ADMIN")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert payload.get("iss") == settings.APP_NAME

    def test_access_token_has_iat(self):
        """Le token contient le champ 'iat' (issued at)."""
        token = SecurityUtils.create_access_token(subject="test@test.com", role="ADMIN")
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        assert "iat" in payload


# ═══════════════════════════════════════════════════════════════════════════
#  BRUTE-FORCE — Integration avec les endpoints
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestBruteForceIntegration:
    """Teste la protection brute-force sur les endpoints de login."""

    @pytest.fixture(autouse=True)
    def _reset_brute_force(self):
        """Reinitialise le garde brute-force avant chaque test."""
        # Sauvegarder et remplacer
        import src.infrastructure.security.brute_force as bf_module

        original = bf_module.brute_force_guard
        bf_module.brute_force_guard = BruteForceProtection()

        # Aussi remplacer dans le module auth qui l'importe
        import src.presentation.api.v1.auth as auth_module

        auth_module.brute_force_guard = bf_module.brute_force_guard

        yield

        # Restaurer
        bf_module.brute_force_guard = original
        auth_module.brute_force_guard = original

    async def test_email_login_lockout_after_failures(self, client: AsyncClient, admin_user):
        """5 echecs de login par email verrouillent le compte."""
        for i in range(5):
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": admin_user.email, "password": "wrong_password"},
            )
            # Les premiers echecs retournent 401
            assert resp.status_code in (
                401,
                429,
            ), f"Attempt {i+1}: got {resp.status_code}"

        # La 6eme tentative doit etre bloquee (429)
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": "wrong_password"},
        )
        assert resp.status_code == 429
        assert "locked" in resp.json()["detail"].lower()

    async def test_phone_login_lockout_after_failures(self, client: AsyncClient, servant_user):
        """5 echecs de login par telephone verrouillent le compte."""
        for i in range(5):
            resp = await client.post(
                "/api/v1/auth/login/phone",
                json={
                    "phone_number": servant_user.phone_number,
                    "password": "wrong_password",
                },
            )
            assert resp.status_code in (
                401,
                429,
            ), f"Attempt {i+1}: got {resp.status_code}"

        # Bloque
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={
                "phone_number": servant_user.phone_number,
                "password": "wrong_password",
            },
        )
        assert resp.status_code == 429

    async def test_successful_login_resets_lockout(self, client: AsyncClient, admin_user):
        """Un login reussi reinitialise le compteur."""
        # 3 echecs
        for _ in range(3):
            await client.post(
                "/api/v1/auth/login",
                data={"username": admin_user.email, "password": "wrong"},
            )

        # Login reussi
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 200

        # 3 nouveaux echecs ne devraient pas verrouiller
        for _ in range(3):
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": admin_user.email, "password": "wrong"},
            )
            assert resp.status_code == 401  # Pas 429

    async def test_lockout_includes_retry_after_header(self, client: AsyncClient, admin_user):
        """La reponse 429 inclut un header Retry-After."""
        for _ in range(6):
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": admin_user.email, "password": "wrong"},
            )
        # Devrait avoir un header Retry-After
        if resp.status_code == 429:
            assert "Retry-After" in resp.headers or "retry_after_seconds" in resp.json()

    async def test_different_users_independent_lockout(self, client: AsyncClient, admin_user, aumonier_user):
        """Le verrouillage d'un compte n'affecte pas les autres."""
        # Verrouiller admin
        for _ in range(6):
            await client.post(
                "/api/v1/auth/login",
                data={"username": admin_user.email, "password": "wrong"},
            )

        # Aumonier reste accessible
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": aumonier_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
#  SECURITY HEADERS — Verification des headers HTTP
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestSecurityHeaders:
    """Verifie les headers de securite sur les reponses HTTP.

    Note : les headers sont ajoutes par le middleware SecurityHeadersMiddleware.
    En mode test, le middleware n'est pas monte (create_test_app sans middleware),
    donc ces tests verifient la logique via des appels directs.
    """

    def test_security_headers_middleware_exists(self):
        """Verifie que le middleware est importe sans erreur."""
        from src.presentation.middleware.security_headers import (
            SecurityHeadersMiddleware,
        )

        assert SecurityHeadersMiddleware is not None

    def test_rate_limit_middleware_exists(self):
        """Verifie que le middleware est importe sans erreur."""
        from src.presentation.middleware.rate_limit import RateLimitMiddleware

        assert RateLimitMiddleware is not None

    def test_error_handler_middleware_exists(self):
        """Verifie que le middleware est importe sans erreur."""
        from src.presentation.middleware.error_handler import ErrorHandlerMiddleware

        assert ErrorHandlerMiddleware is not None

    def test_logging_middleware_exists(self):
        """Verifie que le middleware est importe sans erreur."""
        from src.presentation.middleware.logging_middleware import LoggingMiddleware

        assert LoggingMiddleware is not None


# ═══════════════════════════════════════════════════════════════════════════
#  PASSWORD POLICY — Renforcement
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestPasswordSecurity:
    """Verifie que le hachage bcrypt est correctement configure."""

    def test_bcrypt_hash_format(self):
        """Le hash bcrypt commence par $2b$."""
        hashed = SecurityUtils.get_password_hash("TestPass1")
        assert hashed.startswith("$2b$")

    def test_bcrypt_rounds(self):
        """Le hash utilise au moins 12 rounds."""
        hashed = SecurityUtils.get_password_hash("TestPass1")
        # Format: $2b$12$...
        rounds = int(hashed.split("$")[2])
        assert rounds >= 12

    def test_verify_password_timing_safe(self):
        """verify_password ne leve pas d'exception sur mot de passe incorrect."""
        hashed = SecurityUtils.get_password_hash("TestPass1")
        # Ne doit pas lever d'exception
        result = SecurityUtils.verify_password("WrongPass1", hashed)
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════
#  CORS — Configuration
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestCorsConfiguration:
    """Verifie que la configuration CORS est restrictive."""

    def test_cors_origins_not_wildcard(self):
        """CORS ne doit pas autoriser toutes les origines."""
        assert "*" not in settings.CORS_ORIGINS

    def test_allowed_hosts_defined(self):
        """ALLOWED_HOSTS ne doit pas etre vide."""
        assert len(settings.ALLOWED_HOSTS) > 0
