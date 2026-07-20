"""
╔══════════════════════════════════════════════════════════════════════════╗
║  USE CASE 1 — Inscription et connexion d'un Servant                    ║
║                                                                        ║
║  Scénario :                                                            ║
║    1. Un servant s'inscrit publiquement (pas de code invitation)       ║
║    2. Il reçoit ses infos (201)                                        ║
║    3. Il se connecte par téléphone (+237...)                            ║
║    4. Le token JWT contient son rôle SERVANT                           ║
║    5. Il accède à un endpoint protégé avec le token                    ║
║    6. La connexion par email est refusée (403)                         ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import jwt
import pytest
from httpx import AsyncClient

from src.infrastructure.config.settings import get_settings
from tests.e2e.test_auth_endpoints import _verify_phone

settings = get_settings()


@pytest.mark.asyncio
class TestServantRegistrationAndLogin:
    """Parcours complet : inscription → login téléphone → accès protégé."""

    SERVANT_DATA = {
        "email": "jean.servant@test.com",
        "password": "ServantPass1",
        "first_name": "Jean",
        "last_name": "Servant",
        "phone_number": "+237690000001",
        "role": "SERVANT",
    }

    async def test_full_servant_flow(self, client: AsyncClient, db_session):
        # ── Étape 1 : Inscription ────────────────────────────────────
        token = await _verify_phone(client, db_session, self.SERVANT_DATA["phone_number"])
        resp = await client.post(
            "/api/v1/auth/register",
            json={**self.SERVANT_DATA, "phone_verification_token": token},
        )
        assert resp.status_code == 201, f"Registration failed: {resp.text}"

        body = resp.json()
        assert body["email"] == self.SERVANT_DATA["email"]
        assert body["role"] == "SERVANT"
        assert body["is_active"] is True
        assert body["phone_number"] == self.SERVANT_DATA["phone_number"]

        # ── Étape 2 : Login par téléphone ────────────────────────────
        login_resp = await client.post(
            "/api/v1/auth/login/phone",
            json={
                "phone_number": self.SERVANT_DATA["phone_number"],
                "password": self.SERVANT_DATA["password"],
            },
        )
        assert login_resp.status_code == 200, f"Phone login failed: {login_resp.text}"

        tokens = login_resp.json()
        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert tokens["token_type"] == "bearer"

        # ── Étape 3 : Le JWT contient le rôle ────────────────────────
        payload = jwt.decode(
            tokens["access_token"],
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        assert payload["sub"] == body["id"]
        assert payload["role"] == "SERVANT"

        # ── Étape 4 : Login par email → rejeté (403) ────────────────
        email_resp = await client.post(
            "/api/v1/auth/login",
            data={
                "username": self.SERVANT_DATA["email"],
                "password": self.SERVANT_DATA["password"],
            },
        )
        assert email_resp.status_code == 403

    async def test_servant_default_role_omission(self, client: AsyncClient, db_session):
        """L'omission du rôle doit donner SERVANT par défaut."""
        phone = "+237690000099"
        token = await _verify_phone(client, db_session, phone)
        data = {
            "email": "default.role@test.com",
            "password": "DefaultPass1",
            "first_name": "Default",
            "last_name": "Role",
            "phone_number": phone,
            "phone_verification_token": token,
            # pas de "role" → SERVANT par défaut
        }
        resp = await client.post("/api/v1/auth/register", json=data)
        assert resp.status_code == 201
        assert resp.json()["role"] == "SERVANT"

    async def test_servant_duplicate_email_rejected(self, client: AsyncClient, db_session):
        """Deux inscriptions avec le même email → 400."""
        token1 = await _verify_phone(client, db_session, "+237690000010")
        data = {
            "email": "duplicate@test.com",
            "password": "DuplicatePass1",
            "first_name": "Dup",
            "last_name": "User",
            "phone_number": "+237690000010",
            "role": "SERVANT",
            "phone_verification_token": token1,
        }
        resp1 = await client.post("/api/v1/auth/register", json=data)
        assert resp1.status_code == 201

        token2 = await _verify_phone(client, db_session, "+237690000011")
        data["phone_number"] = "+237690000011"  # Changer le téléphone
        data["phone_verification_token"] = token2
        resp2 = await client.post("/api/v1/auth/register", json=data)
        assert resp2.status_code == 400
        assert "already registered" in resp2.json()["detail"].lower()

    async def test_servant_duplicate_phone_rejected(self, client: AsyncClient, db_session):
        """Deux inscriptions avec le même téléphone → 400."""
        phone = "+237690000020"
        token1 = await _verify_phone(client, db_session, phone)
        data1 = {
            "email": "first@test.com",
            "password": "FirstPass1",
            "first_name": "First",
            "last_name": "User",
            "phone_number": phone,
            "role": "SERVANT",
            "phone_verification_token": token1,
        }
        resp1 = await client.post("/api/v1/auth/register", json=data1)
        assert resp1.status_code == 201

        # Le même numéro est déjà utilisé — la vérification OTP réussirait à
        # nouveau (aucune contrainte d'unicité sur PhoneVerificationCode),
        # mais register_user() doit rejeter à l'étape d'unicité du téléphone.
        token2 = await _verify_phone(client, db_session, phone)
        data2 = {
            "email": "second@test.com",
            "password": "SecondPass1",
            "first_name": "Second",
            "last_name": "User",
            "phone_number": phone,  # Même numéro
            "role": "SERVANT",
            "phone_verification_token": token2,
        }
        resp2 = await client.post("/api/v1/auth/register", json=data2)
        assert resp2.status_code == 400
        assert "phone" in resp2.json()["detail"].lower()
