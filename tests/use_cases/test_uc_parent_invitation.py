"""
╔══════════════════════════════════════════════════════════════════════════╗
║  USE CASE 2 — Parcours complet d'inscription Parent via Invitation     ║
║                                                                        ║
║  Scénario :                                                            ║
║    1. Admin se connecte par email                                      ║
║    2. Admin crée un code invitation pour PARENT                        ║
║    3. Admin liste ses invitations (le code y figure)                   ║
║    4. Parent s'inscrit avec le code invitation                         ║
║    5. Parent se connecte par téléphone                                 ║
║    6. Le code invitation est marqué « utilisé »                        ║
║    7. Réutiliser le même code échoue                                   ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import VALID_PASSWORD, make_auth_header


@pytest.mark.asyncio
class TestParentInvitationFlow:
    """Parcours complet : admin crée invitation → parent s'inscrit → login."""

    async def test_full_parent_invitation_flow(
        self, client: AsyncClient, admin_user: User
    ):
        admin_headers = make_auth_header(admin_user)

        # ── Étape 1 : Admin crée un code invitation ──────────────────
        inv_resp = await client.post(
            "/api/v1/admin/invitations",
            json={"role": "PARENT", "notes": "Test invitation"},
            headers=admin_headers,
        )
        assert (
            inv_resp.status_code == 201
        ), f"Invitation creation failed: {inv_resp.text}"

        invitation = inv_resp.json()
        assert invitation["role"] == "PARENT"
        assert invitation["status"] == "PENDING"
        code = invitation["code"]
        assert code.startswith("INV-")

        # ── Étape 2 : Admin liste ses invitations ────────────────────
        list_resp = await client.get(
            "/api/v1/admin/invitations",
            headers=admin_headers,
        )
        assert list_resp.status_code == 200
        invitations = list_resp.json()
        codes = [inv["code"] for inv in invitations]
        assert code in codes

        # ── Étape 3 : Parent s'inscrit avec le code ──────────────────
        parent_data = {
            "email": "nouveau.parent@test.com",
            "password": "ParentPass1",
            "first_name": "Nouveau",
            "last_name": "Parent",
            "phone_number": "+237680000001",
            "role": "PARENT",
            "invitation_code": code,
        }
        reg_resp = await client.post("/api/v1/auth/register", json=parent_data)
        assert (
            reg_resp.status_code == 201
        ), f"Parent registration failed: {reg_resp.text}"

        parent = reg_resp.json()
        assert parent["role"] == "PARENT"
        assert parent["email"] == "nouveau.parent@test.com"

        # ── Étape 4 : Parent se connecte par téléphone ───────────────
        login_resp = await client.post(
            "/api/v1/auth/login/phone",
            json={
                "phone_number": "+237680000001",
                "password": "ParentPass1",
            },
        )
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        assert "access_token" in tokens

        # ── Étape 5 : Réutiliser le même code → échec ───────────────
        reuse_data = {
            "email": "autre.parent@test.com",
            "password": "AutrePass1",
            "first_name": "Autre",
            "last_name": "Parent",
            "phone_number": "+237680000002",
            "role": "PARENT",
            "invitation_code": code,
        }
        reuse_resp = await client.post("/api/v1/auth/register", json=reuse_data)
        # Le code est déjà utilisé → 400
        assert reuse_resp.status_code == 400


@pytest.mark.asyncio
class TestParentWithoutInvitation:
    """Parent sans code invitation → rejeté."""

    async def test_parent_registration_without_code_rejected(self, client: AsyncClient):
        data = {
            "email": "sans.code@test.com",
            "password": "NoCodePass1",
            "first_name": "Sans",
            "last_name": "Code",
            "phone_number": "+237680000099",
            "role": "PARENT",
            # pas de invitation_code
        }
        resp = await client.post("/api/v1/auth/register", json=data)
        assert resp.status_code == 400
        assert "invitation" in resp.json()["detail"].lower()


@pytest.mark.asyncio
class TestEmailLockedInvitation:
    """Invitation verrouillée sur un email spécifique."""

    async def test_email_locked_invitation_wrong_email(
        self, client: AsyncClient, admin_user: User
    ):
        admin_headers = make_auth_header(admin_user)

        # Admin crée une invitation avec email spécifique
        inv_resp = await client.post(
            "/api/v1/admin/invitations",
            json={
                "role": "PARENT",
                "email": "locked@test.com",
            },
            headers=admin_headers,
        )
        assert inv_resp.status_code == 201
        code = inv_resp.json()["code"]

        # Parent tente de s'inscrire avec un AUTRE email → 403
        data = {
            "email": "wrong.email@test.com",
            "password": "WrongPass1",
            "first_name": "Wrong",
            "last_name": "Email",
            "phone_number": "+237680000003",
            "role": "PARENT",
            "invitation_code": code,
        }
        resp = await client.post("/api/v1/auth/register", json=data)
        assert resp.status_code == 403
        assert "email" in resp.json()["detail"].lower()

    async def test_email_locked_invitation_correct_email(
        self, client: AsyncClient, admin_user: User
    ):
        admin_headers = make_auth_header(admin_user)

        inv_resp = await client.post(
            "/api/v1/admin/invitations",
            json={
                "role": "PARENT",
                "email": "correct@test.com",
            },
            headers=admin_headers,
        )
        assert inv_resp.status_code == 201
        code = inv_resp.json()["code"]

        # Parent s'inscrit avec le BON email → 201
        data = {
            "email": "correct@test.com",
            "password": "CorrectPass1",
            "first_name": "Correct",
            "last_name": "Email",
            "phone_number": "+237680000004",
            "role": "PARENT",
            "invitation_code": code,
        }
        resp = await client.post("/api/v1/auth/register", json=data)
        assert resp.status_code == 201
        assert resp.json()["email"] == "correct@test.com"
