"""
Tests E2E pour le module Parent — tableau de bord parent.

Couvre :
- GET /api/v1/parent/children — RBAC, liste vide, liste avec enfant
- POST /api/v1/parent/children — RBAC, création de profil enfant
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.servant_parent import ServantParent
from src.core.entities.user import User
from tests.conftest import VALID_PASSWORD, make_auth_header

# ═══════════════════════════════════════════════════════════════════════════
#  GET /parent/children
# ═══════════════════════════════════════════════════════════════════════════


class TestGetMyChildren:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/parent/children")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_servant_gets_403(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            "/api/v1/parent/children",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_gets_403(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            "/api/v1/parent/children",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_aumonier_gets_403(self, client: AsyncClient, aumonier_user: User):
        resp = await client.get(
            "/api/v1/parent/children",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_parent_with_no_children_returns_empty_list(self, client: AsyncClient, parent_user: User):
        resp = await client.get(
            "/api/v1/parent/children",
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert body == []

    @pytest.mark.asyncio
    async def test_parent_with_linked_child_returns_child_data(
        self,
        client: AsyncClient,
        parent_user: User,
        servant_user: User,
        db_session,
    ):
        # Link servant to parent via ServantParent junction table
        link = ServantParent(servant_id=servant_user.id, parent_id=parent_user.id)
        db_session.add(link)
        await db_session.commit()

        resp = await client.get(
            "/api/v1/parent/children",
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        child = body[0]
        assert child["id"] == str(servant_user.id)
        assert "attendance_rate" in child
        assert "present_count" in child
        assert "absent_count" in child
        assert "total_sessions" in child
        assert "last_attendances" in child
        assert "pending_contributions" in child
        assert "open_discipline_cases" in child

    @pytest.mark.asyncio
    async def test_child_summary_has_correct_fields(
        self,
        client: AsyncClient,
        parent_user: User,
        servant_user: User,
        db_session,
    ):
        link = ServantParent(servant_id=servant_user.id, parent_id=parent_user.id)
        db_session.add(link)
        await db_session.commit()

        resp = await client.get(
            "/api/v1/parent/children",
            headers=make_auth_header(parent_user),
        )
        child = resp.json()[0]
        assert child["first_name"] == servant_user.first_name
        assert child["last_name"] == servant_user.last_name
        assert isinstance(child["attendance_rate"], (int, float))
        assert isinstance(child["open_discipline_cases"], int)


# ═══════════════════════════════════════════════════════════════════════════
#  POST /parent/children — Création du profil enfant
# ═══════════════════════════════════════════════════════════════════════════


class TestCreateChildProfile:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/parent/children",
            json={
                "first_name": "Jean",
                "last_name": "Petit",
                "birth_date": "2015-03-01T00:00:00",
                "password": "SecurePass1",
            },
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_servant_gets_403(self, client: AsyncClient, servant_user: User):
        resp = await client.post(
            "/api/v1/parent/children",
            json={
                "first_name": "Jean",
                "last_name": "Petit",
                "birth_date": "2015-03-01T00:00:00",
                "password": "SecurePass1",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_gets_403(self, client: AsyncClient, admin_user: User):
        resp = await client.post(
            "/api/v1/parent/children",
            json={
                "first_name": "Jean",
                "last_name": "Petit",
                "birth_date": "2015-03-01T00:00:00",
                "password": "SecurePass1",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_parent_creates_child_successfully(self, client: AsyncClient, parent_user: User):
        resp = await client.post(
            "/api/v1/parent/children",
            json={
                "first_name": "Marie",
                "last_name": "Dupont",
                "birth_date": "2014-06-15T00:00:00",
                "password": "SecurePass1",
                "phone_number": "+237600000099",
            },
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "id" in body
        assert body["first_name"] == "Marie"
        assert body["last_name"] == "Dupont"
        assert body["is_active"] is True

    @pytest.mark.asyncio
    async def test_created_child_appears_in_children_list(self, client: AsyncClient, parent_user: User):
        # Create child
        create_resp = await client.post(
            "/api/v1/parent/children",
            json={
                "first_name": "Pierre",
                "last_name": "Martin",
                "birth_date": "2013-09-20T00:00:00",
                "password": "SecurePass1",
            },
            headers=make_auth_header(parent_user),
        )
        assert create_resp.status_code == 201
        child_id = create_resp.json()["id"]

        # Fetch children list
        list_resp = await client.get(
            "/api/v1/parent/children",
            headers=make_auth_header(parent_user),
        )
        assert list_resp.status_code == 200
        ids = [c["id"] for c in list_resp.json()]
        assert child_id in ids

    @pytest.mark.asyncio
    async def test_child_without_email_stays_null(self, client: AsyncClient, parent_user: User):
        resp = await client.post(
            "/api/v1/parent/children",
            json={
                "first_name": "Luc",
                "last_name": "Bernard",
                "birth_date": "2016-01-01T00:00:00",
                "password": "SecurePass1",
            },
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        # Plus d'auto-génération : NULL reste NULL, pas de valeur technique.
        assert body.get("email") is None

    @pytest.mark.asyncio
    async def test_missing_required_fields_returns_422(self, client: AsyncClient, parent_user: User):
        resp = await client.post(
            "/api/v1/parent/children",
            json={"first_name": "Incomplete"},  # missing last_name, birth_date, password
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_short_password_returns_422(self, client: AsyncClient, parent_user: User):
        resp = await client.post(
            "/api/v1/parent/children",
            json={
                "first_name": "Test",
                "last_name": "Child",
                "birth_date": "2015-01-01T00:00:00",
                "password": "short",  # < 8 chars
            },
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 422
