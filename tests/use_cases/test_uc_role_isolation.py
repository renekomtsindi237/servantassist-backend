"""
╔══════════════════════════════════════════════════════════════════════════╗
║  USE CASE 6 — Isolation des rôles (RBAC transversal)                   ║
║                                                                        ║
║  Scénario :                                                            ║
║    Vérifier que chaque rôle est strictement confiné :                  ║
║    - ADMIN/AUMÔNIER : email login uniquement                           ║
║    - PARENT/SERVANT : phone login uniquement                           ║
║    - Seul ADMIN accède aux endpoints /admin/*                          ║
║    - Les rôles restreints ne peuvent pas s'auto-inscrire               ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import VALID_PASSWORD, make_auth_header


@pytest.mark.asyncio
class TestLoginMethodIsolation:
    """Chaque rôle ne peut se connecter que par sa méthode autorisée."""

    async def test_admin_cannot_login_by_phone(
        self, client: AsyncClient, admin_user: User
    ):
        """Admin n'a pas de téléphone → login phone échoue."""
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": "+237600000000", "password": VALID_PASSWORD},
        )
        # 401 car le numéro n'existe pas (admin n'a pas de phone)
        assert resp.status_code == 401

    async def test_servant_cannot_login_by_email(
        self, client: AsyncClient, servant_user: User
    ):
        """Servant connecté par email → 403."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": servant_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 403
        assert "téléphone" in resp.json()["detail"].lower()

    async def test_parent_cannot_login_by_email(
        self, client: AsyncClient, parent_user: User
    ):
        """Parent connecté par email → 403."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": parent_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 403

    async def test_aumonier_cannot_login_by_phone(
        self, client: AsyncClient, aumonier_user: User
    ):
        """Aumônier → login phone échoue (pas de phone ou mauvaise méthode)."""
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": "+237600000000", "password": VALID_PASSWORD},
        )
        assert resp.status_code == 401  # Phone number not found


@pytest.mark.asyncio
class TestAdminEndpointIsolation:
    """Seul l'admin accède aux endpoints /admin/*."""

    async def test_servant_cannot_list_invitations(
        self, client: AsyncClient, servant_user: User
    ):
        headers = make_auth_header(servant_user)
        resp = await client.get("/api/v1/admin/invitations", headers=headers)
        assert resp.status_code == 403

    async def test_parent_cannot_create_invitation(
        self, client: AsyncClient, parent_user: User
    ):
        headers = make_auth_header(parent_user)
        resp = await client.post(
            "/api/v1/admin/invitations",
            json={"role": "PARENT"},
            headers=headers,
        )
        assert resp.status_code == 403

    async def test_unauthenticated_cannot_access_admin(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/invitations")
        assert resp.status_code == 401

    async def test_admin_can_access_admin_endpoints(
        self, client: AsyncClient, admin_user: User
    ):
        headers = make_auth_header(admin_user)
        resp = await client.get("/api/v1/admin/invitations", headers=headers)
        assert resp.status_code == 200


@pytest.mark.asyncio
class TestSelfRegistrationRestriction:
    """Les rôles restreints ne peuvent pas s'auto-inscrire."""

    async def test_admin_self_register_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "selfadmin@test.com",
                "password": "AdminPass1",
                "first_name": "Self",
                "last_name": "Admin",
                "phone_number": "+237690000200",
                "role": "ADMIN",
            },
        )
        assert resp.status_code == 403

    async def test_aumonier_self_register_rejected(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "selfaumo@test.com",
                "password": "AumoPass1",
                "first_name": "Self",
                "last_name": "Aumo",
                "phone_number": "+237690000201",
                "role": "AUMÔNIER",
            },
        )
        assert resp.status_code == 403
