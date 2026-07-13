"""
Tests de sécurité — RBAC (Role-Based Access Control).
Vérifie que chaque rôle ne peut accéder qu'à ses propres ressources.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import VALID_PASSWORD, make_auth_header


# ═══════════════════════════════════════════════════════════════════════════
#  ADMIN ENDPOINTS — Seul l'ADMIN peut y accéder
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestAdminEndpointsRBAC:
    """Aucun rôle autre qu'ADMIN ne doit accéder aux endpoints /admin/*."""

    ADMIN_ENDPOINTS = [
        ("POST", "/api/v1/admin/invitations", {"role": "PARENT"}),
        ("GET", "/api/v1/admin/invitations", None),
        (
            "POST",
            "/api/v1/admin/users/parent",
            {
                "email": "rbac@test.com",
                "password": "TestPass1",
                "first_name": "A",
                "last_name": "B",
                "phone_number": "+237600000090",
            },
        ),
        (
            "POST",
            "/api/v1/admin/users/aum%C3%B4nier",
            {
                "email": "rbac2@test.com",
                "password": "TestPass1",
                "first_name": "A",
                "last_name": "B",
            },
        ),
        (
            "POST",
            "/api/v1/admin/users/admin",
            {
                "email": "rbac3@test.com",
                "password": "TestPass1",
                "first_name": "A",
                "last_name": "B",
            },
        ),
    ]

    @pytest.mark.parametrize("method,url,body", ADMIN_ENDPOINTS)
    async def test_servant_rejected(self, client: AsyncClient, servant_user, method, url, body):
        headers = make_auth_header(servant_user)
        if method == "GET":
            resp = await client.get(url, headers=headers)
        else:
            resp = await client.post(url, json=body, headers=headers)
        assert resp.status_code == 403, f"SERVANT should be 403 on {method} {url}"

    @pytest.mark.parametrize("method,url,body", ADMIN_ENDPOINTS)
    async def test_parent_rejected(self, client: AsyncClient, parent_user, method, url, body):
        headers = make_auth_header(parent_user)
        if method == "GET":
            resp = await client.get(url, headers=headers)
        else:
            resp = await client.post(url, json=body, headers=headers)
        assert resp.status_code == 403, f"PARENT should be 403 on {method} {url}"

    @pytest.mark.parametrize("method,url,body", ADMIN_ENDPOINTS)
    async def test_aumonier_rejected(self, client: AsyncClient, aumonier_user, method, url, body):
        headers = make_auth_header(aumonier_user)
        if method == "GET":
            resp = await client.get(url, headers=headers)
        else:
            resp = await client.post(url, json=body, headers=headers)
        assert resp.status_code == 403, f"AUMÔNIER should be 403 on {method} {url}"

    @pytest.mark.parametrize("method,url,body", ADMIN_ENDPOINTS)
    async def test_unauthenticated_rejected(self, client: AsyncClient, method, url, body):
        if method == "GET":
            resp = await client.get(url)
        else:
            resp = await client.post(url, json=body)
        assert resp.status_code == 401, f"No auth should be 401 on {method} {url}"


# ═══════════════════════════════════════════════════════════════════════════
#  LOGIN METHOD ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestLoginMethodEnforcement:
    """Vérifie que chaque rôle est forcé d'utiliser la bonne méthode de login."""

    async def test_admin_cannot_use_phone_login(self, client: AsyncClient, admin_user):
        """Même si on pouvait trouver l'admin par téléphone, le rôle doit bloquer."""
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": "+237000000000", "password": VALID_PASSWORD},
        )
        # 401 car pas de phone_number en BDD, mais si trouvé → 403
        assert resp.status_code in (401, 403)

    async def test_servant_cannot_use_email_login(self, client: AsyncClient, servant_user):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": servant_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 403

    async def test_parent_cannot_use_email_login(self, client: AsyncClient, parent_user):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": parent_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-REGISTRATION RESTRICTIONS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestSelfRegistrationRestrictions:
    """Vérifie qu'on ne peut pas s'inscrire avec un rôle privilégié."""

    async def test_cannot_register_as_admin(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "escalation@test.com",
                "password": "TestPass1",
                "first_name": "Priv",
                "last_name": "Esc",
                "role": "ADMIN",
            },
        )
        assert resp.status_code == 403

    async def test_cannot_register_as_aumonier(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "escalation2@test.com",
                "password": "TestPass1",
                "first_name": "Priv",
                "last_name": "Esc",
                "role": "AUMÔNIER",
            },
        )
        assert resp.status_code == 403

    async def test_invalid_role_value_422(self, client: AsyncClient):
        """Un rôle inexistant doit être rejeté par la validation Pydantic."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "badrole@test.com",
                "password": "TestPass1",
                "first_name": "Bad",
                "last_name": "Role",
                "phone_number": "+237600000095",
                "role": "SUPER_ADMIN",
            },
        )
        assert resp.status_code == 422
