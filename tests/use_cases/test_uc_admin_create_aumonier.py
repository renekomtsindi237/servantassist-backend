"""
╔══════════════════════════════════════════════════════════════════════════╗
║  USE CASE 3 — Admin crée un Aumônier                                   ║
║                                                                        ║
║  Scénario :                                                            ║
║    1. Admin se connecte par email                                      ║
║    2. Admin crée un aumônier via /admin/users/aumônier                 ║
║    3. Aumônier se connecte par email                                   ║
║    4. Aumônier ne peut PAS se connecter par téléphone                  ║
║    5. Créer un 2ème aumônier → rejeté (UNIQUE)                        ║
║    6. Un non-admin ne peut PAS créer d'aumônier                        ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import pytest
from httpx import AsyncClient
from jose import jwt

from src.core.entities.user import User
from src.infrastructure.config.settings import get_settings
from tests.conftest import VALID_PASSWORD, make_auth_header

settings = get_settings()


@pytest.mark.asyncio
class TestAdminCreatesAumonier:
    """Parcours complet : admin crée aumônier → aumônier se connecte."""

    AUMONIER_DATA = {
        "email": "pere.aumonier@eglise.cm",
        "password": "AumonierPass1",
        "first_name": "Père",
        "last_name": "Aumônier",
    }

    async def test_full_aumonier_creation_flow(
        self, client: AsyncClient, admin_user: User
    ):
        admin_headers = make_auth_header(admin_user)

        # ── Étape 1 : Admin crée l'aumônier ──────────────────────────
        resp = await client.post(
            "/api/v1/admin/users/aumônier",
            json=self.AUMONIER_DATA,
            headers=admin_headers,
        )
        assert resp.status_code == 201, f"Aumônier creation failed: {resp.text}"

        body = resp.json()
        assert body["role"] == "AUMÔNIER"
        assert body["email"] == self.AUMONIER_DATA["email"]
        assert body["is_active"] is True

        # ── Étape 2 : Aumônier se connecte par email ────────────────
        login_resp = await client.post(
            "/api/v1/auth/login",
            data={
                "username": self.AUMONIER_DATA["email"],
                "password": self.AUMONIER_DATA["password"],
            },
        )
        assert login_resp.status_code == 200

        tokens = login_resp.json()
        payload = jwt.decode(
            tokens["access_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["role"] == "AUMÔNIER"

        # ── Étape 3 : Créer un 2ème aumônier → UNIQUE violated ──────
        second = {
            "email": "deuxieme.aumonier@eglise.cm",
            "password": "DeuxiemePass1",
            "first_name": "Deuxième",
            "last_name": "Aumônier",
        }
        resp2 = await client.post(
            "/api/v1/admin/users/aumônier",
            json=second,
            headers=admin_headers,
        )
        assert resp2.status_code == 400
        assert "already exists" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
class TestNonAdminCannotCreateAumonier:
    """Un non-admin ne peut pas créer d'aumônier."""

    async def test_servant_cannot_create_aumonier(
        self, client: AsyncClient, servant_user: User
    ):
        servant_headers = make_auth_header(servant_user)
        resp = await client.post(
            "/api/v1/admin/users/aumônier",
            json={
                "email": "unauth@test.com",
                "password": "UnauthPass1",
                "first_name": "Unauth",
                "last_name": "User",
            },
            headers=servant_headers,
        )
        assert resp.status_code == 403

    async def test_parent_cannot_create_aumonier(
        self, client: AsyncClient, parent_user: User
    ):
        parent_headers = make_auth_header(parent_user)
        resp = await client.post(
            "/api/v1/admin/users/aumônier",
            json={
                "email": "unauth2@test.com",
                "password": "UnauthPass2",
                "first_name": "Unauth",
                "last_name": "Parent",
            },
            headers=parent_headers,
        )
        assert resp.status_code == 403

    async def test_aumonier_self_register_forbidden(self, client: AsyncClient):
        """Aumônier ne peut pas s'auto-inscrire via /register."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "self.aumonier@test.com",
                "password": "SelfPass1",
                "first_name": "Self",
                "last_name": "Aumonier",
                "phone_number": "+237690000100",
                "role": "AUMÔNIER",
            },
        )
        assert resp.status_code == 403
        assert "publiquement" in resp.json()["detail"].lower()
