"""
Use-cases — Gestion des utilisateurs.

Scenarios complets testant les flux metier de bout en bout.
"""
import pytest
from httpx import AsyncClient

from src.core.entities.user import User, UserRole
from src.infrastructure.security.utils import SecurityUtils
from tests.conftest import VALID_PASSWORD, make_auth_header


# ═══════════════════════════════════════════════════════════════════════════
#  UC-1 : Un servant modifie son profil et change son mot de passe
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.use_cases
class TestServantProfileManagement:
    async def test_full_profile_update_flow(self, client: AsyncClient, servant_user: User):
        headers = make_auth_header(servant_user)

        # 1. Consulter le profil
        resp = await client.get("/api/v1/users/me", headers=headers)
        assert resp.status_code == 200
        original = resp.json()
        assert original["first_name"] == "Servant"

        # 2. Modifier le prenom
        resp = await client.patch(
            "/api/v1/users/me",
            json={"first_name": "Jean-Pierre"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["first_name"] == "Jean-Pierre"

        # 3. Modifier le telephone
        resp = await client.patch(
            "/api/v1/users/me",
            json={"phone_number": "+237655443322"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["phone_number"] == "+237655443322"

        # 4. Changer le mot de passe
        resp = await client.patch(
            "/api/v1/users/me/password",
            json={"current_password": VALID_PASSWORD, "new_password": "NouveauMdp1"},
            headers=headers,
        )
        assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════
#  UC-2 : L'admin gere les utilisateurs
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.use_cases
class TestAdminUserManagement:
    async def test_admin_views_and_filters_users(self, client: AsyncClient, admin_user, servant_user, parent_user):
        headers = make_auth_header(admin_user)

        # 1. Lister tous les utilisateurs
        resp = await client.get("/api/v1/users/", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 3

        # 2. Filtrer par role SERVANT
        resp = await client.get("/api/v1/users/?role=SERVANT", headers=headers)
        assert resp.status_code == 200
        for item in resp.json()["items"]:
            assert item["role"] == "SERVANT"

        # 3. Rechercher par nom
        resp = await client.get("/api/v1/users/?search=Parent", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

    async def test_admin_deactivates_and_reactivates_user(self, client: AsyncClient, admin_user, servant_user):
        headers = make_auth_header(admin_user)

        # 1. Desactiver le servant
        resp = await client.patch(f"/api/v1/users/{servant_user.id}/deactivate", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        # 2. Verifier qu'il est bien inactif dans la liste
        resp = await client.get("/api/v1/users/?is_active=false", headers=headers)
        assert any(u["id"] == str(servant_user.id) for u in resp.json()["items"])

        # 3. Reactiver le servant
        resp = await client.patch(f"/api/v1/users/{servant_user.id}/activate", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True

    async def test_admin_resets_user_password(self, client: AsyncClient, admin_user, servant_user):
        headers = make_auth_header(admin_user)

        # Reinitialiser le mot de passe
        resp = await client.post(
            f"/api/v1/users/{servant_user.id}/reset-password",
            json={"new_password": "AdminReset1"},
            headers=headers,
        )
        assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════
#  UC-3 : Tentative de suppression avec garde-fous
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.use_cases
class TestDeleteGuardrails:
    async def test_admin_deletes_servant(self, client: AsyncClient, admin_user, servant_user):
        headers = make_auth_header(admin_user)

        # Supprimer un servant
        resp = await client.delete(f"/api/v1/users/{servant_user.id}", headers=headers)
        assert resp.status_code == 204

        # Verifier qu'il n'apparait plus
        resp = await client.get(f"/api/v1/users/{servant_user.id}", headers=headers)
        assert resp.status_code == 404

    async def test_admin_cannot_delete_himself(self, client: AsyncClient, admin_user):
        headers = make_auth_header(admin_user)
        resp = await client.delete(f"/api/v1/users/{admin_user.id}", headers=headers)
        assert resp.status_code == 400
        assert "propre" in resp.json()["detail"].lower() or "supprimer" in resp.json()["detail"].lower()
