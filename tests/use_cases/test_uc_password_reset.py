"""
╔══════════════════════════════════════════════════════════════════════════╗
║  USE CASE 5 — Réinitialisation de mot de passe                         ║
║                                                                        ║
║  Scénario :                                                            ║
║    1. Utilisateur demande la réinitialisation (forgot-password)        ║
║    2. L'API retourne 200 même si l'email n'existe pas (anti-enum)     ║
║    3. Avec un reset token valide → mot de passe changé                ║
║    4. Login avec l'ancien mot de passe → échoue                       ║
║    5. Login avec le nouveau mot de passe → réussit                    ║
║    6. Token expiré / invalide → rejeté                                ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from src.infrastructure.security.utils import SecurityUtils
from tests.conftest import VALID_PASSWORD


@pytest.mark.asyncio
class TestPasswordResetFlow:
    """Parcours complet de réinitialisation de mot de passe."""

    async def test_forgot_password_always_returns_200(self, client: AsyncClient):
        """L'endpoint retourne toujours 200 pour empêcher l'énumération d'emails."""
        # Email qui existe
        resp1 = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "admin@test.com"},
        )
        assert resp1.status_code == 200

        # Email qui n'existe PAS
        resp2 = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nexiste.pas@test.com"},
        )
        assert resp2.status_code == 200

    async def test_reset_password_with_valid_token(self, client: AsyncClient, admin_user: User):
        """Réinitialisation complète avec token valide."""
        # Générer un reset token manuellement (en production, envoyé par email)
        reset_token = SecurityUtils.create_reset_token(admin_user.email)

        new_password = "NouveauPass1"

        # ── Réinitialiser ────────────────────────────────────────────
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": new_password},
        )
        assert resp.status_code == 200

        # ── Login ancien mot de passe → échec ────────────────────────
        old_login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": VALID_PASSWORD},
        )
        assert old_login.status_code == 401

        # ── Login nouveau mot de passe → succès ──────────────────────
        new_login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": new_password},
        )
        assert new_login.status_code == 200
        assert "access_token" in new_login.json()

    async def test_reset_with_invalid_token(self, client: AsyncClient):
        """Token invalide → 400."""
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalid.token.garbage", "new_password": "NewPass1"},
        )
        assert resp.status_code == 400

    async def test_reset_with_access_token_fails(self, client: AsyncClient, admin_user: User):
        """Un access token ne peut pas servir de reset token."""
        access_token = SecurityUtils.create_access_token(subject=admin_user.email, role="ADMIN")
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": access_token, "new_password": "NewPass1"},
        )
        assert resp.status_code == 400
