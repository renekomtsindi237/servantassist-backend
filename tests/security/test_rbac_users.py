"""
Tests de securite RBAC — Module Users.
Verifie que seul l'admin peut acceder aux endpoints d'administration.
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import make_auth_header


@pytest.mark.security
class TestUsersRbac:
    """Seul l'admin peut acceder aux endpoints d'administration des utilisateurs."""

    # ── Endpoints admin-only ─────────────────────────────────────────
    ADMIN_ENDPOINTS = [
        ("GET", "/api/v1/users/"),
        ("GET", "/api/v1/users/{uid}"),
        ("PATCH", "/api/v1/users/{uid}"),
        ("PATCH", "/api/v1/users/{uid}/deactivate"),
        ("PATCH", "/api/v1/users/{uid}/activate"),
        ("POST", "/api/v1/users/{uid}/reset-password"),
        ("DELETE", "/api/v1/users/{uid}"),
    ]

    async def _request(self, client, method, path, headers, json=None):
        """Helper pour envoyer une requete HTTP."""
        fn = getattr(client, method.lower())
        kwargs = {"headers": headers}
        if json:
            kwargs["json"] = json
        return await fn(path, **kwargs)

    async def test_servant_cannot_access_admin_endpoints(
        self, client: AsyncClient, servant_user: User, admin_user: User
    ):
        uid = str(admin_user.id)
        for method, path in self.ADMIN_ENDPOINTS:
            url = path.replace("{uid}", uid)
            json_body = None
            if method in ("PATCH", "POST"):
                json_body = {"first_name": "X"} if "reset" not in url else {"new_password": "TestPass2"}
            resp = await self._request(client, method, url, make_auth_header(servant_user), json_body)
            assert resp.status_code == 403, f"SERVANT should get 403 on {method} {url}, got {resp.status_code}"

    async def test_parent_cannot_access_admin_endpoints(self, client: AsyncClient, parent_user: User, admin_user: User):
        uid = str(admin_user.id)
        for method, path in self.ADMIN_ENDPOINTS:
            url = path.replace("{uid}", uid)
            json_body = None
            if method in ("PATCH", "POST"):
                json_body = {"first_name": "X"} if "reset" not in url else {"new_password": "TestPass2"}
            resp = await self._request(client, method, url, make_auth_header(parent_user), json_body)
            assert resp.status_code == 403, f"PARENT should get 403 on {method} {url}, got {resp.status_code}"

    async def test_unauthenticated_cannot_access_any_user_endpoint(self, client: AsyncClient):
        """Aucun endpoint users n'est accessible sans token."""
        endpoints = [
            ("GET", "/api/v1/users/me"),
            ("PATCH", "/api/v1/users/me"),
            ("PATCH", "/api/v1/users/me/password"),
            ("GET", "/api/v1/users/"),
        ]
        for method, url in endpoints:
            resp = await self._request(client, method, url, {})
            assert resp.status_code == 401, f"Unauthenticated should get 401 on {method} {url}, got {resp.status_code}"


@pytest.mark.security
class TestSelfServiceIsolation:
    """Verifie qu'un utilisateur ne peut modifier que son propre profil."""

    async def test_servant_can_view_own_profile(self, client: AsyncClient, servant_user):
        resp = await client.get("/api/v1/users/me", headers=make_auth_header(servant_user))
        assert resp.status_code == 200
        assert resp.json()["id"] == str(servant_user.id)

    async def test_parent_can_update_own_profile(self, client: AsyncClient, parent_user):
        resp = await client.patch(
            "/api/v1/users/me",
            json={"first_name": "ParentModifie"},
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "ParentModifie"

    async def test_inactive_user_cannot_access(self, client: AsyncClient, inactive_user):
        resp = await client.get("/api/v1/users/me", headers=make_auth_header(inactive_user))
        assert resp.status_code == 400  # "Inactive user"
