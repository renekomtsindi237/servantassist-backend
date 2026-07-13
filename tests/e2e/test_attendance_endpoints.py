"""
Tests E2E du module Presence — suivi d'assiduite.

Couvre :
- Enregistrement individuel
- Enregistrement par lot (appel nominal)
- Modification (justification d'absence)
- Self-service (mon historique, mes stats)
- Listing et statistiques admin
- Controle d'acces (RBAC)
"""

from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.attendance import Attendance
from src.core.entities.event import Event
from src.core.entities.user import User
from tests.conftest import make_auth_header

# ═══════════════════════════════════════════════════════════════════════════
#  ENREGISTREMENT INDIVIDUEL
# ═══════════════════════════════════════════════════════════════════════════


class TestRecordAttendance:
    """Tests pour l'enregistrement de presence individuelle."""

    @pytest.mark.asyncio
    async def test_record_present(self, client: AsyncClient, aumonier_user: User, servant_user: User):
        resp = await client.post(
            "/api/v1/attendance/",
            json={
                "user_id": str(servant_user.id),
                "attendance_type": "REUNION_ORDINAIRE",
                "attendance_date": "2026-03-08T14:00:00",
                "title": "Reunion du 8 mars",
                "status": "PRESENT",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "PRESENT"
        assert body["attendance_type"] == "REUNION_ORDINAIRE"

    @pytest.mark.asyncio
    async def test_record_absent(self, client: AsyncClient, aumonier_user: User, servant_user: User):
        resp = await client.post(
            "/api/v1/attendance/",
            json={
                "user_id": str(servant_user.id),
                "attendance_type": "MESSE_CLASSEMENT",
                "attendance_date": "2026-03-09T09:00:00",
                "status": "ABSENT",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        assert resp.json()["status"] == "ABSENT"

    @pytest.mark.asyncio
    async def test_record_duplicate_rejected(self, client: AsyncClient, aumonier_user: User, servant_user: User):
        payload = {
            "user_id": str(servant_user.id),
            "attendance_type": "FORMATION",
            "attendance_date": "2026-03-15T10:00:00",
            "status": "PRESENT",
        }
        # Premier enregistrement
        resp1 = await client.post(
            "/api/v1/attendance/",
            json=payload,
            headers=make_auth_header(aumonier_user),
        )
        assert resp1.status_code == 201

        # Doublon
        resp2 = await client.post(
            "/api/v1/attendance/",
            json=payload,
            headers=make_auth_header(aumonier_user),
        )
        assert resp2.status_code == 409

    @pytest.mark.asyncio
    async def test_record_unknown_user(self, client: AsyncClient, aumonier_user: User):
        resp = await client.post(
            "/api/v1/attendance/",
            json={
                "user_id": str(uuid4()),
                "attendance_type": "REUNION_ORDINAIRE",
                "attendance_date": "2026-03-22T14:00:00",
                "status": "PRESENT",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_servant_cannot_record(self, client: AsyncClient, servant_user: User):
        resp = await client.post(
            "/api/v1/attendance/",
            json={
                "user_id": str(servant_user.id),
                "attendance_type": "REUNION_ORDINAIRE",
                "attendance_date": "2026-04-01T14:00:00",
                "status": "PRESENT",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  ENREGISTREMENT PAR LOT
# ═══════════════════════════════════════════════════════════════════════════


class TestBatchAttendance:
    """Tests de l'appel nominal (enregistrement par lot)."""

    @pytest.mark.asyncio
    async def test_batch_success(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        servant_user_2: User,
    ):
        resp = await client.post(
            "/api/v1/attendance/batch",
            json={
                "attendance_type": "REUNION_ORDINAIRE",
                "attendance_date": "2026-03-29T14:00:00",
                "title": "Reunion du 29 mars",
                "entries": [
                    {"user_id": str(servant_user.id), "status": "PRESENT"},
                    {"user_id": str(servant_user_2.id), "status": "ABSENT"},
                ],
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["total_created"] == 2
        assert body["total_errors"] == 0


# ═══════════════════════════════════════════════════════════════════════════
#  MODIFICATION (JUSTIFICATION)
# ═══════════════════════════════════════════════════════════════════════════


class TestUpdateAttendance:
    """Tests de modification (justification d'absence)."""

    @pytest.mark.asyncio
    async def test_justify_absence(self, client: AsyncClient, aumonier_user: User, servant_user: User):
        # Enregistrer une absence
        create_resp = await client.post(
            "/api/v1/attendance/",
            json={
                "user_id": str(servant_user.id),
                "attendance_type": "RECOLLECTION",
                "attendance_date": "2026-04-05T08:00:00",
                "status": "ABSENT",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert create_resp.status_code == 201
        att_id = create_resp.json()["id"]

        # Justifier
        update_resp = await client.patch(
            f"/api/v1/attendance/{att_id}",
            json={"justification": "Malade, certificat medical fourni."},
            headers=make_auth_header(aumonier_user),
        )
        assert update_resp.status_code == 200
        body = update_resp.json()
        assert body["status"] == "ABSENT_JUSTIFIE"
        assert body["justification"] is not None


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE
# ═══════════════════════════════════════════════════════════════════════════


class TestAttendanceSelfService:
    """Tests self-service (mes presences, mes stats)."""

    @pytest.mark.asyncio
    async def test_get_my_attendances(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_attendance: Attendance,
    ):
        resp = await client.get(
            "/api/v1/attendance/my",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_my_stats(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_attendance: Attendance,
    ):
        resp = await client.get(
            "/api/v1/attendance/my/stats",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == str(servant_user.id)
        assert body["total_entries"] >= 1
        assert body["presents"] >= 1


# ═══════════════════════════════════════════════════════════════════════════
#  LISTING ADMIN ET STATS
# ═══════════════════════════════════════════════════════════════════════════


class TestAttendanceAdminRead:
    """Tests de lecture admin et statistiques."""

    @pytest.mark.asyncio
    async def test_list_all_attendances(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_attendance: Attendance,
    ):
        resp = await client.get(
            "/api/v1/attendance/",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_attendance_detail(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_attendance: Attendance,
    ):
        resp = await client.get(
            f"/api/v1/attendance/{sample_attendance.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_attendance.id)

    @pytest.mark.asyncio
    async def test_get_user_stats(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_attendance: Attendance,
    ):
        resp = await client.get(
            f"/api/v1/attendance/user/{servant_user.id}/stats",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == str(servant_user.id)
        assert "taux_presence" in body
