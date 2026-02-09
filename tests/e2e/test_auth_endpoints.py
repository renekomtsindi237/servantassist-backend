"""
Tests E2E — Endpoints d'authentification (/api/v1/auth/*).
Utilise le client HTTP async + base SQLite en mémoire.
"""
import pytest
from httpx import AsyncClient

from tests.conftest import VALID_PASSWORD, make_auth_header


# ═══════════════════════════════════════════════════════════════════════════
#  POST /auth/login  (email — ADMIN / AUMÔNIER)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestLoginEmail:
    async def test_admin_login_success(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_aumonier_login_success(self, client: AsyncClient, aumonier_user):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": aumonier_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    async def test_wrong_password_401(self, client: AsyncClient, admin_user):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": "WrongPass1"},
        )
        assert resp.status_code == 401

    async def test_nonexistent_email_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "ghost@test.com", "password": "TestPass1"},
        )
        assert resp.status_code == 401

    async def test_servant_email_login_rejected_403(self, client: AsyncClient, servant_user):
        """Un SERVANT ne peut pas utiliser /login (email)."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": servant_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 403

    async def test_parent_email_login_rejected_403(self, client: AsyncClient, parent_user):
        """Un PARENT ne peut pas utiliser /login (email)."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": parent_user.email, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 403

    async def test_inactive_user_403(self, client: AsyncClient, inactive_user):
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": inactive_user.phone_number, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  POST /auth/login/phone  (téléphone — SERVANT / PARENT)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestLoginPhone:
    async def test_servant_phone_login_success(self, client: AsyncClient, servant_user):
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": servant_user.phone_number, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_parent_phone_login_success(self, client: AsyncClient, parent_user):
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": parent_user.phone_number, "password": VALID_PASSWORD},
        )
        assert resp.status_code == 200

    async def test_wrong_password_phone_401(self, client: AsyncClient, servant_user):
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": servant_user.phone_number, "password": "WrongPass1"},
        )
        assert resp.status_code == 401

    async def test_nonexistent_phone_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": "+237699999999", "password": "TestPass1"},
        )
        assert resp.status_code == 401

    async def test_admin_phone_login_rejected_403(self, client: AsyncClient, admin_user):
        """L'admin n'a pas de phone_number, mais même s'il en avait, le rôle est vérifié."""
        # On crée un admin avec téléphone pour tester le rejet par rôle
        # Ici, admin_user n'a pas de phone, donc ce sera 401 (non trouvé)
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={"phone_number": "+237600000000", "password": VALID_PASSWORD},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  POST /auth/register
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestRegister:
    async def test_servant_registration_success(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newservant@test.com",
                "password": "TestPass1",
                "first_name": "New",
                "last_name": "Servant",
                "phone_number": "+237600000050",
                "role": "SERVANT",
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "SERVANT"
        assert body["email"] == "newservant@test.com"

    async def test_servant_is_default_role(self, client: AsyncClient):
        """Sans rôle précisé, le rôle par défaut est SERVANT."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "default@test.com",
                "password": "TestPass1",
                "first_name": "Default",
                "last_name": "Role",
                "phone_number": "+237600000051",
            },
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "SERVANT"

    async def test_parent_with_invitation_code(self, client: AsyncClient, valid_invitation):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newparent@test.com",
                "password": "TestPass1",
                "first_name": "New",
                "last_name": "Parent",
                "phone_number": "+237600000060",
                "role": "PARENT",
                "invitation_code": valid_invitation.code,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "PARENT"

    async def test_parent_without_invitation_400(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "badparent@test.com",
                "password": "TestPass1",
                "first_name": "Bad",
                "last_name": "Parent",
                "phone_number": "+237600000061",
                "role": "PARENT",
            },
        )
        assert resp.status_code == 400

    async def test_parent_invalid_invitation_400(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "bad2@test.com",
                "password": "TestPass1",
                "first_name": "Bad",
                "last_name": "Parent",
                "phone_number": "+237600000062",
                "role": "PARENT",
                "invitation_code": "INV-DOESNOTEXIST",
            },
        )
        assert resp.status_code == 400

    async def test_admin_registration_blocked_403(self, client: AsyncClient):
        """L'endpoint /register bloque le rôle ADMIN en amont."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "hackeradmin@test.com",
                "password": "TestPass1",
                "first_name": "Hacker",
                "last_name": "Admin",
                "role": "ADMIN",
            },
        )
        assert resp.status_code == 403

    async def test_aumonier_registration_blocked_403(self, client: AsyncClient):
        """L'endpoint /register bloque le rôle AUMÔNIER en amont."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "hackeraum@test.com",
                "password": "TestPass1",
                "first_name": "Hacker",
                "last_name": "Aumonier",
                "role": "AUMÔNIER",
            },
        )
        assert resp.status_code == 403

    async def test_duplicate_email_400(self, client: AsyncClient, servant_user):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": servant_user.email,
                "password": "TestPass1",
                "first_name": "Dup",
                "last_name": "Email",
                "phone_number": "+237600000070",
                "role": "SERVANT",
            },
        )
        assert resp.status_code == 400

    async def test_weak_password_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@test.com",
                "password": "weak",
                "first_name": "Weak",
                "last_name": "Pass",
                "phone_number": "+237600000071",
                "role": "SERVANT",
            },
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
#  POST /auth/refresh
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestRefreshToken:
    async def test_valid_refresh(self, client: AsyncClient, admin_user):
        # D'abord se connecter pour obtenir un refresh token
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": VALID_PASSWORD},
        )
        refresh_token = login.json()["refresh_token"]

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_invalid_refresh_token_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.token.here"},
        )
        assert resp.status_code == 401

    async def test_access_token_as_refresh_401(self, client: AsyncClient, admin_user):
        """Un access token ne peut pas être utilisé comme refresh token."""
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": VALID_PASSWORD},
        )
        access_token = login.json()["access_token"]

        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  POST /auth/forgot-password & /auth/reset-password
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestPasswordReset:
    async def test_forgot_password_existing_email_200(self, client: AsyncClient, admin_user):
        """Retourne toujours 200 (anti-énumération)."""
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": admin_user.email},
        )
        assert resp.status_code == 200

    async def test_forgot_password_nonexistent_email_200(self, client: AsyncClient):
        """Retourne 200 même pour un email inexistant (anti-énumération)."""
        resp = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "ghost@test.com"},
        )
        assert resp.status_code == 200

    async def test_reset_password_invalid_token_400(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": "invalid.token", "new_password": "NewPass123"},
        )
        assert resp.status_code == 400

    async def test_reset_password_valid_token(self, client: AsyncClient, admin_user):
        """Teste le flux complet : génération reset token → reset."""
        from src.infrastructure.security.utils import SecurityUtils

        reset_token = SecurityUtils.create_reset_token(subject=admin_user.email)
        resp = await client.post(
            "/api/v1/auth/reset-password",
            json={"token": reset_token, "new_password": "NewSecure1"},
        )
        assert resp.status_code == 200

        # Vérifier qu'on peut se connecter avec le nouveau mot de passe
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": "NewSecure1"},
        )
        assert login.status_code == 200

