"""
╔══════════════════════════════════════════════════════════════════════════╗
║  USE CASE 8 — Contrainte d'unicité des rôles ADMIN et AUMÔNIER        ║
║                                                                        ║
║  Scénario :                                                            ║
║    1. Un seul ADMIN peut exister (init_db en crée un)                 ║
║    2. Créer un 2ème ADMIN → rejeté                                    ║
║    3. Un seul AUMÔNIER peut exister                                    ║
║    4. Créer un 2ème AUMÔNIER → rejeté                                 ║
║    5. Plusieurs SERVANT/PARENT peuvent coexister                      ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import make_auth_header
from tests.e2e.test_auth_endpoints import _verify_phone


@pytest.mark.asyncio
class TestAdminUniqueness:
    """Un seul admin dans le système."""

    async def test_second_admin_creation_rejected(self, client: AsyncClient, admin_user: User):
        """admin_user existe déjà → créer un 2ème = 400."""
        headers = make_auth_header(admin_user)
        resp = await client.post(
            "/api/v1/admin/users/admin",
            json={
                "email": "secondadmin@test.com",
                "password": "SecondAdmin1",
                "first_name": "Second",
                "last_name": "Admin",
            },
            headers=headers,
        )
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"].lower()


@pytest.mark.asyncio
class TestAumonierUniqueness:
    """Un seul aumônier dans le système."""

    async def test_second_aumonier_creation_rejected(self, client: AsyncClient, admin_user: User):
        """Créer 2 aumôniers → le 2ème est rejeté."""
        headers = make_auth_header(admin_user)

        # Créer le 1er
        resp1 = await client.post(
            "/api/v1/admin/users/aumônier",
            json={
                "email": "premier.aumonier@test.com",
                "password": "PremierPass1",
                "first_name": "Premier",
                "last_name": "Aumônier",
            },
            headers=headers,
        )
        assert resp1.status_code == 201

        # Créer le 2ème → rejeté
        resp2 = await client.post(
            "/api/v1/admin/users/aumônier",
            json={
                "email": "deuxieme.aumonier@test.com",
                "password": "DeuxiemePass1",
                "first_name": "Deuxième",
                "last_name": "Aumônier",
            },
            headers=headers,
        )
        assert resp2.status_code == 400
        assert "already exists" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
class TestMultipleServantParent:
    """Plusieurs SERVANT et PARENT peuvent coexister."""

    async def test_multiple_servants_allowed(self, client: AsyncClient, db_session):
        for i in range(3):
            phone = f"+23769{i:07d}"
            token = await _verify_phone(client, db_session, phone)
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"servant.multi{i}@test.com",
                    "password": "MultiServ1",
                    "first_name": f"Servant{i}",
                    "last_name": "Multi",
                    "phone_number": phone,
                    "role": "SERVANT",
                    "phone_verification_token": token,
                },
            )
            assert resp.status_code == 201, f"Servant {i} failed: {resp.text}"

    async def test_multiple_parents_with_separate_invitations(self, client: AsyncClient, db_session, admin_user: User):
        headers = make_auth_header(admin_user)

        for i in range(3):
            # Créer une invitation par parent
            inv_resp = await client.post(
                "/api/v1/admin/invitations",
                json={"role": "PARENT"},
                headers=headers,
            )
            assert inv_resp.status_code == 201
            code = inv_resp.json()["code"]

            # Inscrire le parent
            phone = f"+23768{i:07d}"
            token = await _verify_phone(client, db_session, phone)
            reg_resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"parent.multi{i}@test.com",
                    "password": "MultiPar1",
                    "first_name": f"Parent{i}",
                    "last_name": "Multi",
                    "phone_number": phone,
                    "role": "PARENT",
                    "invitation_code": code,
                    "phone_verification_token": token,
                },
            )
            assert reg_resp.status_code == 201, f"Parent {i} failed: {reg_resp.text}"
