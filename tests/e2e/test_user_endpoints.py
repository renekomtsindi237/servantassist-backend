"""
Tests e2e — Endpoints Users (profil self-service + administration).
"""

import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import VALID_PASSWORD, make_auth_header


# ═══════════════════════════════════════════════════════════════════════════
#  GET /me — Profil self-service
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestGetMyProfile:
    async def test_get_profile_servant(self, client: AsyncClient, servant_user: User):
        resp = await client.get("/api/v1/users/me", headers=make_auth_header(servant_user))
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == servant_user.email
        assert body["role"] == "SERVANT"

    async def test_get_profile_admin(self, client: AsyncClient, admin_user: User):
        resp = await client.get("/api/v1/users/me", headers=make_auth_header(admin_user))
        assert resp.status_code == 200
        assert resp.json()["role"] == "ADMIN"

    async def test_unauthenticated_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/me")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  PATCH /me — Modifier mon profil
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestUpdateMyProfile:
    async def test_update_first_name(self, client: AsyncClient, servant_user: User):
        resp = await client.patch(
            "/api/v1/users/me",
            json={"first_name": "Modifie"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Modifie"

    async def test_update_phone_number(self, client: AsyncClient, servant_user: User):
        resp = await client.patch(
            "/api/v1/users/me",
            json={"phone_number": "+237699887766"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert resp.json()["phone_number"] == "+237699887766"

    async def test_update_phone_conflict(self, client: AsyncClient, servant_user, parent_user):
        """Numero deja utilise par un autre utilisateur."""
        resp = await client.patch(
            "/api/v1/users/me",
            json={"phone_number": parent_user.phone_number},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 409

    async def test_invalid_phone_format(self, client: AsyncClient, servant_user):
        resp = await client.patch(
            "/api/v1/users/me",
            json={"phone_number": "pas-un-numero"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 422

    async def test_partial_update(self, client: AsyncClient, servant_user):
        """Ne modifier qu'un champ ne touche pas les autres."""
        resp = await client.patch(
            "/api/v1/users/me",
            json={"last_name": "NouveauNom"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["last_name"] == "NouveauNom"
        assert body["first_name"] == servant_user.first_name


# ═══════════════════════════════════════════════════════════════════════════
#  PATCH /me/password — Changer mot de passe
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestChangePassword:
    async def test_change_password_success(self, client: AsyncClient, servant_user):
        resp = await client.patch(
            "/api/v1/users/me/password",
            json={"current_password": VALID_PASSWORD, "new_password": "NewPass123"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 204

    async def test_wrong_current_password(self, client: AsyncClient, servant_user):
        resp = await client.patch(
            "/api/v1/users/me/password",
            json={"current_password": "MauvaisPass1", "new_password": "NewPass123"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 400

    async def test_weak_new_password(self, client: AsyncClient, servant_user):
        resp = await client.patch(
            "/api/v1/users/me/password",
            json={"current_password": VALID_PASSWORD, "new_password": "faible"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
#  GET /directory — Répertoire (tout utilisateur authentifié)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestListDirectory:
    async def test_servant_can_access_directory(
        self,
        client: AsyncClient,
        servant_user: User,
        admin_user: User,
        parent_user: User,
    ):
        resp = await client.get("/api/v1/users/directory", headers=make_auth_header(servant_user))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body

    async def test_parent_can_access_directory(self, client: AsyncClient, parent_user: User, servant_user: User):
        resp = await client.get("/api/v1/users/directory", headers=make_auth_header(parent_user))
        assert resp.status_code == 200

    async def test_admin_can_access_directory(self, client: AsyncClient, admin_user: User, servant_user: User):
        resp = await client.get("/api/v1/users/directory", headers=make_auth_header(admin_user))
        assert resp.status_code == 200

    async def test_unauthenticated_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/users/directory")
        assert resp.status_code == 401

    async def test_filter_by_role(
        self,
        client: AsyncClient,
        servant_user: User,
        parent_user: User,
        admin_user: User,
    ):
        resp = await client.get(
            "/api/v1/users/directory?role=SERVANT",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["role"] == "SERVANT"

    async def test_pagination_defaults(
        self,
        client: AsyncClient,
        servant_user: User,
        admin_user: User,
        parent_user: User,
    ):
        resp = await client.get(
            "/api/v1/users/directory?page=1&page_size=1",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["total"] >= 1

    async def test_returns_only_active_by_default(self, client: AsyncClient, servant_user: User, inactive_user: User):
        resp = await client.get("/api/v1/users/directory", headers=make_auth_header(servant_user))
        assert resp.status_code == 200
        ids = [item["id"] for item in resp.json()["items"]]
        assert str(inactive_user.id) not in ids


# ═══════════════════════════════════════════════════════════════════════════
#  GET / — Liste paginee (admin)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestListUsers:
    async def test_admin_can_list(self, client: AsyncClient, admin_user, servant_user, parent_user):
        resp = await client.get("/api/v1/users/", headers=make_auth_header(admin_user))
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 3

    async def test_filter_by_role(self, client: AsyncClient, admin_user, servant_user):
        resp = await client.get("/api/v1/users/?role=SERVANT", headers=make_auth_header(admin_user))
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["role"] == "SERVANT"

    async def test_search(self, client: AsyncClient, admin_user, servant_user):
        resp = await client.get("/api/v1/users/?search=Servant", headers=make_auth_header(admin_user))
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_pagination(self, client: AsyncClient, admin_user, servant_user, parent_user):
        resp = await client.get("/api/v1/users/?page=1&page_size=1", headers=make_auth_header(admin_user))
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 1
        assert body["total_pages"] >= 3

    async def test_servant_cannot_list(self, client: AsyncClient, servant_user):
        resp = await client.get("/api/v1/users/", headers=make_auth_header(servant_user))
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  GET /{user_id} — Detail (admin)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestGetUser:
    async def test_admin_can_view_user(self, client: AsyncClient, admin_user, servant_user):
        resp = await client.get(
            f"/api/v1/users/{servant_user.id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == servant_user.email

    async def test_nonexistent_user_404(self, client: AsyncClient, admin_user):
        from uuid import uuid4

        resp = await client.get(
            f"/api/v1/users/{uuid4()}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  PATCH /{user_id} — Modifier un utilisateur (admin)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestAdminUpdateUser:
    async def test_admin_updates_name(self, client: AsyncClient, admin_user, servant_user):
        resp = await client.patch(
            f"/api/v1/users/{servant_user.id}",
            json={"first_name": "AdminModified"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "AdminModified"

    async def test_admin_updates_email(self, client: AsyncClient, admin_user, servant_user):
        resp = await client.patch(
            f"/api/v1/users/{servant_user.id}",
            json={"email": "newemail@test.com"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "newemail@test.com"


# ═══════════════════════════════════════════════════════════════════════════
#  PATCH /{user_id}/deactivate et /activate — Admin
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestActivateDeactivate:
    async def test_deactivate_user(self, client: AsyncClient, admin_user, servant_user):
        resp = await client.patch(
            f"/api/v1/users/{servant_user.id}/deactivate",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    async def test_activate_user(self, client: AsyncClient, admin_user, inactive_user):
        resp = await client.patch(
            f"/api/v1/users/{inactive_user.id}/activate",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    async def test_deactivate_self_rejected(self, client: AsyncClient, admin_user):
        resp = await client.patch(
            f"/api/v1/users/{admin_user.id}/deactivate",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
#  POST /{user_id}/reset-password — Admin
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestAdminResetPassword:
    async def test_reset_password(self, client: AsyncClient, admin_user, servant_user):
        resp = await client.post(
            f"/api/v1/users/{servant_user.id}/reset-password",
            json={"new_password": "ResetPass1"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════
#  DELETE /{user_id} — Admin
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestDeleteUser:
    async def test_delete_user(self, client: AsyncClient, admin_user, servant_user):
        resp = await client.delete(
            f"/api/v1/users/{servant_user.id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 204
        # Verifier qu'il n'existe plus
        resp2 = await client.get(
            f"/api/v1/users/{servant_user.id}",
            headers=make_auth_header(admin_user),
        )
        assert resp2.status_code == 404

    async def test_delete_self_rejected(self, client: AsyncClient, admin_user):
        resp = await client.delete(
            f"/api/v1/users/{admin_user.id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 400

    async def test_servant_cannot_delete(self, client: AsyncClient, servant_user, parent_user):
        resp = await client.delete(
            f"/api/v1/users/{parent_user.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403
