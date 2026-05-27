"""
Tests E2E — Endpoints admin (/api/v1/admin/*).
Tous les endpoints nécessitent un token ADMIN.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import VALID_PASSWORD, make_auth_header


# ═══════════════════════════════════════════════════════════════════════════
#  POST /admin/invitations
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestCreateInvitation:
    async def test_admin_creates_invitation_201(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/admin/invitations",
            json={"role": "PARENT", "email": "invited@test.com"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["code"].startswith("INV-")
        assert body["role"] == "PARENT"
        assert body["status"] == "PENDING"

    async def test_admin_creates_aumonier_invitation(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/admin/invitations",
            json={"role": "AUMÔNIER"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "AUMÔNIER"

    async def test_invalid_role_400(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/admin/invitations",
            json={"role": "SERVANT"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 400

    async def test_no_auth_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/admin/invitations",
            json={"role": "PARENT"},
        )
        assert resp.status_code == 401

    async def test_servant_forbidden_403(self, client: AsyncClient, servant_user):
        resp = await client.post(
            "/api/v1/admin/invitations",
            json={"role": "PARENT"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    async def test_parent_forbidden_403(self, client: AsyncClient, parent_user):
        resp = await client.post(
            "/api/v1/admin/invitations",
            json={"role": "PARENT"},
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    async def test_aumonier_forbidden_403(self, client: AsyncClient, aumonier_user):
        resp = await client.post(
            "/api/v1/admin/invitations",
            json={"role": "PARENT"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  GET /admin/invitations
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestListInvitations:
    async def test_admin_lists_invitations(self, client: AsyncClient, admin_user, valid_invitation):
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1

    async def test_no_auth_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/admin/invitations")
        assert resp.status_code == 401

    async def test_servant_forbidden_403(self, client: AsyncClient, servant_user):
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  DELETE /admin/invitations/{id}
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestRevokeInvitation:
    async def test_admin_revokes_own_invitation(self, client: AsyncClient, admin_user, valid_invitation):
        resp = await client.delete(
            f"/api/v1/admin/invitations/{valid_invitation.id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 204

    async def test_revoke_nonexistent_404(self, client: AsyncClient, admin_user):
        import uuid

        resp = await client.delete(
            f"/api/v1/admin/invitations/{uuid.uuid4()}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404

    async def test_no_auth_401(self, client: AsyncClient, valid_invitation):
        resp = await client.delete(f"/api/v1/admin/invitations/{valid_invitation.id}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  POST /admin/users/aumônier
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestCreateAumonier:
    async def test_admin_creates_aumonier_201(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/admin/users/aum%C3%B4nier",  # URL-encoded ô
            json={
                "email": "newaumonier@test.com",
                "password": "TestPass1",
                "first_name": "New",
                "last_name": "Aumonier",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "AUMÔNIER"

    async def test_duplicate_aumonier_400(self, client: AsyncClient, admin_user, aumonier_user):
        """Un seul AUMÔNIER autorisé."""
        resp = await client.post(
            "/api/v1/admin/users/aum%C3%B4nier",
            json={
                "email": "dup@test.com",
                "password": "TestPass1",
                "first_name": "Dup",
                "last_name": "Aumonier",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 400

    async def test_no_auth_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/admin/users/aum%C3%B4nier",
            json={
                "email": "x@t.com",
                "password": "TestPass1",
                "first_name": "A",
                "last_name": "B",
            },
        )
        assert resp.status_code == 401

    async def test_servant_forbidden_403(self, client: AsyncClient, servant_user):
        resp = await client.post(
            "/api/v1/admin/users/aum%C3%B4nier",
            json={
                "email": "x@t.com",
                "password": "TestPass1",
                "first_name": "A",
                "last_name": "B",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  POST /admin/users/parent
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestCreateParentDirect:
    async def test_admin_creates_parent_201(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/admin/users/parent",
            json={
                "email": "directparent@test.com",
                "password": "TestPass1",
                "first_name": "Direct",
                "last_name": "Parent",
                "phone_number": "+237600000080",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "PARENT"

    async def test_no_auth_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/admin/users/parent",
            json={
                "email": "x@t.com",
                "password": "TestPass1",
                "first_name": "A",
                "last_name": "B",
                "phone_number": "+237600000081",
            },
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  POST /admin/users/admin
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestCreateAdmin:
    async def test_admin_already_exists_400(self, client: AsyncClient, admin_user):
        """Un seul ADMIN autorisé — le premier existe déjà."""
        resp = await client.post(
            "/api/v1/admin/users/admin",
            json={
                "email": "secondadmin@test.com",
                "password": "TestPass1",
                "first_name": "Second",
                "last_name": "Admin",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 400

    async def test_no_auth_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/admin/users/admin",
            json={
                "email": "x@t.com",
                "password": "TestPass1",
                "first_name": "A",
                "last_name": "B",
            },
        )
        assert resp.status_code == 401
