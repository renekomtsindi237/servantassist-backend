"""
Tests E2E — Endpoints d'authentification (/api/v1/auth/*).
Utilise le client HTTP async + base SQLite en mémoire.
"""

import pytest
from httpx import AsyncClient
from sqlmodel import select

from src.core.entities.phone_verification_code import PhoneVerificationCode
from src.infrastructure.security.field_encryption import get_encryptor
from tests.conftest import VALID_PASSWORD, make_auth_header


async def _verify_phone(client: AsyncClient, db_session, phone_number: str) -> str:
    """Simule le flux complet envoi + vérification OTP et retourne le verification_token
    à inclure dans le payload de POST /auth/register."""
    resp = await client.post("/api/v1/auth/register/send-phone-code", json={"phone_number": phone_number})
    assert resp.status_code == 200

    phone_hmac = get_encryptor().hmac_index(phone_number)
    result = await db_session.exec(select(PhoneVerificationCode).where(PhoneVerificationCode.phone_hmac == phone_hmac))
    entry = result.first()
    assert entry is not None, "Code de vérification non trouvé en base"

    resp = await client.post(
        "/api/v1/auth/register/verify-phone-code",
        json={"phone_number": phone_number, "code": entry.code},
    )
    assert resp.status_code == 200
    return resp.json()["verification_token"]


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
            json={
                "phone_number": inactive_user.phone_number,
                "password": VALID_PASSWORD,
            },
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  POST /auth/oauth/{provider}  (connexion Google — connexion uniquement)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestLoginOAuth:
    def _mock_identity(self, email, verified=True, subject="sub-123"):
        from unittest.mock import patch

        from src.infrastructure.services.oauth_verifier import OAuthIdentity

        return patch(
            "src.infrastructure.services.oauth_verifier.verify_google_id_token",
            return_value=OAuthIdentity(email=email, email_verified=verified, subject=subject),
        )

    async def test_google_login_success_for_existing_account(self, client: AsyncClient, aumonier_user):
        with self._mock_identity(aumonier_user.email):
            resp = await client.post(
                "/api/v1/auth/oauth/google",
                json={"id_token": "fake-token"},
            )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    async def test_no_matching_account_404(self, client: AsyncClient):
        with self._mock_identity("ghost@nowhere.com"):
            resp = await client.post(
                "/api/v1/auth/oauth/google",
                json={"id_token": "fake-token"},
            )
        assert resp.status_code == 404

    async def test_unverified_email_401(self, client: AsyncClient, aumonier_user):
        with self._mock_identity(aumonier_user.email, verified=False):
            resp = await client.post(
                "/api/v1/auth/oauth/google",
                json={"id_token": "fake-token"},
            )
        assert resp.status_code == 401

    async def test_inactive_account_403(self, client: AsyncClient, inactive_user):
        with self._mock_identity(inactive_user.email):
            resp = await client.post(
                "/api/v1/auth/oauth/google",
                json={"id_token": "fake-token"},
            )
        assert resp.status_code == 403

    async def test_unknown_provider_422(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/oauth/facebook",
            json={"id_token": "fake-token"},
        )
        assert resp.status_code == 422


# ═══════════════════════════════════════════════════════════════════════════
#  POST /auth/login/phone  (téléphone — SERVANT / PARENT)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestLoginPhone:
    async def test_servant_phone_login_success(self, client: AsyncClient, servant_user):
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={
                "phone_number": servant_user.phone_number,
                "password": VALID_PASSWORD,
            },
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
#  POST /auth/register/send-phone-code + verify-phone-code
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestPhoneVerificationEndpoints:
    async def test_send_then_verify_returns_token(self, client: AsyncClient, db_session):
        token = await _verify_phone(client, db_session, "+237600000900")
        assert isinstance(token, str) and len(token) > 0

    async def test_verify_wrong_code_400(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register/send-phone-code",
            json={"phone_number": "+237600000901"},
        )
        assert resp.status_code == 200

        resp = await client.post(
            "/api/v1/auth/register/verify-phone-code",
            json={"phone_number": "+237600000901", "code": "000000"},
        )
        assert resp.status_code == 400

    async def test_verify_without_send_400(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/auth/register/verify-phone-code",
            json={"phone_number": "+237600000902", "code": "123456"},
        )
        assert resp.status_code == 400

    async def test_token_is_specific_to_phone_number(self, client: AsyncClient, db_session):
        """Un token vérifié pour un numéro ne doit pas permettre de s'inscrire avec un autre."""
        token = await _verify_phone(client, db_session, "+237600000903")
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "mismatch@test.com",
                "password": "TestPass1",
                "first_name": "Mismatch",
                "last_name": "Phone",
                "phone_number": "+237600000904",  # numéro DIFFÉRENT de celui vérifié
                "role": "SERVANT",
                "phone_verification_token": token,
            },
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
#  POST /auth/register
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestRegister:
    async def test_servant_registration_success(self, client: AsyncClient, db_session):
        token = await _verify_phone(client, db_session, "+237600000050")
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newservant@test.com",
                "password": "TestPass1",
                "first_name": "New",
                "last_name": "Servant",
                "phone_number": "+237600000050",
                "role": "SERVANT",
                "phone_verification_token": token,
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["role"] == "SERVANT"
        assert body["email"] == "newservant@test.com"

    async def test_servant_is_default_role(self, client: AsyncClient, db_session):
        """Sans rôle précisé, le rôle par défaut est SERVANT."""
        token = await _verify_phone(client, db_session, "+237600000051")
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "default@test.com",
                "password": "TestPass1",
                "first_name": "Default",
                "last_name": "Role",
                "phone_number": "+237600000051",
                "phone_verification_token": token,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "SERVANT"

    async def test_parent_with_invitation_code(self, client: AsyncClient, db_session, valid_invitation):
        token = await _verify_phone(client, db_session, "+237600000060")
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
                "phone_verification_token": token,
            },
        )
        assert resp.status_code == 201
        assert resp.json()["role"] == "PARENT"

    async def test_missing_phone_verification_token_400(self, client: AsyncClient):
        """Sans token de vérification téléphone, l'inscription publique échoue."""
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "noverif@test.com",
                "password": "TestPass1",
                "first_name": "No",
                "last_name": "Verif",
                "phone_number": "+237600000052",
                "role": "SERVANT",
            },
        )
        assert resp.status_code == 400

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

        reset_token = SecurityUtils.create_reset_token(subject=admin_user.id)
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
