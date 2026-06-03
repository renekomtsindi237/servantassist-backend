"""
Tests E2E pour l'endpoint dossier — GET /api/v1/dossier/{user_id}

Couvre :
- RBAC : servant ne peut voir que son propre dossier
- Admin/Aumônier peuvent voir n'importe quel dossier
- 404 si servant inexistant
- Structure de la réponse (tous les champs)
- Statistiques d'attendance intégrées
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.attendance_session import AttendanceRecord, AttendanceSession, AttendanceStatus
from src.core.entities.user import User
from tests.conftest import make_auth_header

# ═══════════════════════════════════════════════════════════════════════════
#  Accès non authentifié
# ═══════════════════════════════════════════════════════════════════════════


class TestDossierAuth:
    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient, servant_user: User):
        resp = await client.get(f"/api/v1/dossier/{servant_user.id}")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  RBAC
# ═══════════════════════════════════════════════════════════════════════════


class TestDossierRBAC:
    @pytest.mark.asyncio
    async def test_servant_can_read_own_dossier(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_servant_cannot_read_other_servant_dossier(
        self,
        client: AsyncClient,
        servant_user: User,
        servant_user_2: User,
    ):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user_2.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_can_read_any_dossier(self, client: AsyncClient, admin_user: User, servant_user: User):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_aumonier_can_read_any_dossier(self, client: AsyncClient, aumonier_user: User, servant_user: User):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_parent_can_read_any_dossier(self, client: AsyncClient, parent_user: User, servant_user: User):
        # PARENT is not SERVANT, so no cross-access restriction
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
#  404 Not Found
# ═══════════════════════════════════════════════════════════════════════════


class TestDossierNotFound:
    @pytest.mark.asyncio
    async def test_nonexistent_user_returns_404(self, client: AsyncClient, admin_user: User):
        random_id = uuid4()
        resp = await client.get(
            f"/api/v1/dossier/{random_id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  Structure de la réponse
# ═══════════════════════════════════════════════════════════════════════════


class TestDossierStructure:
    @pytest.mark.asyncio
    async def test_response_has_user_info(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(servant_user),
        )
        body = resp.json()
        assert "user" in body
        user_info = body["user"]
        assert user_info["id"] == str(servant_user.id)
        assert user_info["role"] == "SERVANT"
        assert "first_name" in user_info
        assert "last_name" in user_info

    @pytest.mark.asyncio
    async def test_response_has_attendance_stats(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(servant_user),
        )
        body = resp.json()
        assert "attendance_stats" in body
        stats = body["attendance_stats"]
        assert "total_sessions" in stats
        assert "present_count" in stats
        assert "absent_count" in stats
        assert "late_count" in stats
        assert "excused_count" in stats
        assert "attendance_rate" in stats

    @pytest.mark.asyncio
    async def test_response_has_all_required_sections(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(servant_user),
        )
        body = resp.json()
        assert "nominations" in body
        assert "cotisations" in body
        assert "trainings" in body
        assert "discipline_cases" in body
        assert "sport_culture" in body
        assert "generated_at" in body

    @pytest.mark.asyncio
    async def test_empty_servant_has_zero_stats(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(servant_user),
        )
        body = resp.json()
        stats = body["attendance_stats"]
        assert stats["total_sessions"] == 0
        assert stats["attendance_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_dossier_with_attendance_records(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_attendance_record: AttendanceRecord,
    ):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(servant_user),
        )
        body = resp.json()
        stats = body["attendance_stats"]
        # We have 1 PRESENT record from sample_attendance_record
        assert stats["total_sessions"] >= 1
        assert stats["present_count"] >= 1

    @pytest.mark.asyncio
    async def test_dossier_with_nominations(
        self,
        client: AsyncClient,
        servant_user: User,
        nomination_delegue,
    ):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(servant_user),
        )
        body = resp.json()
        nominations = body["nominations"]
        assert len(nominations) >= 1
        assert nominations[0]["poste"] == "DELEGUE"

    @pytest.mark.asyncio
    async def test_sections_are_lists(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            f"/api/v1/dossier/{servant_user.id}",
            headers=make_auth_header(servant_user),
        )
        body = resp.json()
        assert isinstance(body["nominations"], list)
        assert isinstance(body["cotisations"], list)
        assert isinstance(body["trainings"], list)
        assert isinstance(body["discipline_cases"], list)
        assert isinstance(body["sport_culture"], list)
