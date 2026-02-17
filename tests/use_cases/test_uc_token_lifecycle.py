"""
╔══════════════════════════════════════════════════════════════════════════╗
║  USE CASE 4 — Cycle de vie des tokens JWT                              ║
║                                                                        ║
║  Scénario :                                                            ║
║    1. Utilisateur se connecte → reçoit access + refresh tokens        ║
║    2. Access token expiré → accès refusé (401)                        ║
║    3. Refresh token → nouveau jeu de tokens                           ║
║    4. Nouveaux tokens sont valides                                     ║
║    5. Refresh token invalide → rejeté (401)                           ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
from datetime import timedelta

import pytest
from httpx import AsyncClient
from jose import jwt

from src.core.entities.user import User
from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.utils import SecurityUtils
from tests.conftest import VALID_PASSWORD, make_access_token

settings = get_settings()


@pytest.mark.asyncio
class TestTokenRefreshFlow:
    """Parcours : login → refresh → accès avec nouveau token."""

    async def test_full_token_refresh_cycle(
        self, client: AsyncClient, admin_user: User
    ):
        # ── Étape 1 : Login admin ────────────────────────────────────
        login_resp = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": VALID_PASSWORD},
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()

        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]

        # Valider la structure du refresh token
        refresh_payload = jwt.decode(
            refresh_token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert refresh_payload["type"] == "refresh"
        assert refresh_payload["role"] == "ADMIN"

        # ── Étape 2 : Utiliser le refresh token ──────────────────────
        refresh_resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_resp.status_code == 200

        new_tokens = refresh_resp.json()
        # Les tokens peuvent être identiques si générés dans la même seconde
        # (même exp). On vérifie simplement qu'on reçoit des tokens valides.
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["token_type"] == "bearer"

        # ── Étape 3 : Le nouveau token est valide ────────────────────
        new_payload = jwt.decode(
            new_tokens["access_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert new_payload["sub"] == admin_user.email
        assert new_payload["role"] == "ADMIN"

    async def test_invalid_refresh_token_rejected(self, client: AsyncClient):
        """Un refresh token invalide → 401."""
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401

    async def test_access_token_used_as_refresh_rejected(
        self, client: AsyncClient, admin_user: User
    ):
        """Utiliser un access token au lieu d'un refresh → 401."""
        access_token = make_access_token(admin_user)
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401

    async def test_expired_refresh_token_rejected(
        self, client: AsyncClient, admin_user: User
    ):
        """Un refresh token expiré → 401."""
        expired_refresh = SecurityUtils.create_refresh_token(
            subject=admin_user.email,
            role=admin_user.role.value,
            expires_delta=timedelta(seconds=-1),
        )
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": expired_refresh},
        )
        assert resp.status_code == 401


@pytest.mark.asyncio
class TestExpiredAccessToken:
    """Access token expiré → accès refusé aux endpoints protégés."""

    async def test_expired_token_denied_on_admin_endpoint(
        self, client: AsyncClient, admin_user: User
    ):
        expired_token = make_access_token(admin_user, expires=timedelta(seconds=-1))
        headers = {"Authorization": f"Bearer {expired_token}"}

        resp = await client.get("/api/v1/admin/invitations", headers=headers)
        assert resp.status_code == 401
