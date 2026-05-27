"""
Tests end-to-end pour les endpoints d'appels (CENSEUR).
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAttendanceSessionEndpoints:
    """Tests des endpoints de sessions d'appel."""

    async def test_create_session_as_censeur(
        self, client: AsyncClient, censeur_token: str
    ):
        """Test : Le CENSEUR peut créer une session."""
        response = await client.post(
            "/api/v1/attendance-sessions/",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "session_date": datetime(2026, 2, 15, tzinfo=timezone.utc).isoformat(),
                "session_time": "07h30",
                "location": "Sacristie",
                "notes": "Appel du samedi 15 février",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["session_time"] == "07h30"
        assert data["location"] == "Sacristie"

    async def test_create_session_as_servant_forbidden(
        self, client: AsyncClient, servant_token: str
    ):
        """Test : Un SERVANT ne peut pas créer de session."""
        response = await client.post(
            "/api/v1/attendance-sessions/",
            headers={"Authorization": f"Bearer {servant_token}"},
            json={
                "session_date": datetime(2026, 2, 15, tzinfo=timezone.utc).isoformat(),
                "session_time": "07h30",
                "location": "Sacristie",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_list_sessions(self, client: AsyncClient, censeur_token: str):
        """Test : Lister les sessions."""
        response = await client.get(
            "/api/v1/attendance-sessions/",
            headers={"Authorization": f"Bearer {censeur_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_session(
        self, client: AsyncClient, censeur_token: str, attendance_session_id: str
    ):
        """Test : Récupérer une session."""
        response = await client.get(
            f"/api/v1/attendance-sessions/{attendance_session_id}",
            headers={"Authorization": f"Bearer {censeur_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == attendance_session_id

    async def test_mark_attendance_present(
        self,
        client: AsyncClient,
        censeur_token: str,
        attendance_session_id: str,
        servant_user_id: str,
    ):
        """Test : Marquer un servant présent."""
        response = await client.post(
            f"/api/v1/attendance-sessions/{attendance_session_id}/records",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "servant_id": servant_user_id,
                "status": "PRESENT",
                "arrival_time": "07h25",
                "notes": "À l'heure",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "PRESENT"
        assert data["arrival_time"] == "07h25"

    async def test_mark_attendance_absent(
        self,
        client: AsyncClient,
        censeur_token: str,
        attendance_session_id: str,
        servant_user_id: str,
    ):
        """Test : Marquer un servant absent."""
        response = await client.post(
            f"/api/v1/attendance-sessions/{attendance_session_id}/records",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "servant_id": servant_user_id,
                "status": "ABSENT",
                "notes": "Absence non justifiée",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "ABSENT"

    async def test_mark_attendance_late(
        self,
        client: AsyncClient,
        censeur_token: str,
        attendance_session_id: str,
        servant_user_id: str,
    ):
        """Test : Marquer un servant en retard."""
        response = await client.post(
            f"/api/v1/attendance-sessions/{attendance_session_id}/records",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "servant_id": servant_user_id,
                "status": "LATE",
                "arrival_time": "07h45",
                "notes": "Retard de 15 minutes",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "LATE"

    async def test_mark_attendance_excused(
        self,
        client: AsyncClient,
        censeur_token: str,
        attendance_session_id: str,
        servant_user_id: str,
    ):
        """Test : Marquer un servant excusé."""
        response = await client.post(
            f"/api/v1/attendance-sessions/{attendance_session_id}/records",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "servant_id": servant_user_id,
                "status": "EXCUSED",
                "notes": "Maladie justifiée",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "EXCUSED"

    async def test_update_attendance_record(
        self, client: AsyncClient, censeur_token: str, attendance_record_id: str
    ):
        """Test : Modifier un enregistrement."""
        response = await client.patch(
            f"/api/v1/attendance-sessions/records/{attendance_record_id}",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "status": "LATE",
                "arrival_time": "07h40",
                "notes": "Finalement en retard",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "LATE"

    async def test_get_servant_stats(
        self, client: AsyncClient, censeur_token: str, servant_user_id: str
    ):
        """Test : Récupérer les statistiques d'un servant."""
        response = await client.get(
            f"/api/v1/attendance-sessions/servants/{servant_user_id}/stats",
            headers={"Authorization": f"Bearer {censeur_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "servant_id" in data
        assert "attendance_rate" in data
        assert "consecutive_absences" in data

    async def test_generate_report(self, client: AsyncClient, censeur_token: str):
        """Test : Générer un rapport de présence."""
        response = await client.post(
            "/api/v1/attendance-sessions/report",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=timezone.utc).isoformat(),
            },
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_sessions" in data
        assert "average_attendance_rate" in data
        assert "watermark_logo" in data
        assert data["watermark_logo"] == "logo_servant.jpeg"

    async def test_get_servants_list(self, client: AsyncClient, censeur_token: str):
        """Test : Récupérer la liste des servants."""
        response = await client.get(
            "/api/v1/attendance-sessions/servants/list",
            headers={"Authorization": f"Bearer {censeur_token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        if len(data) > 0:
            assert "id" in data[0]
            assert "full_name" in data[0]


@pytest.mark.asyncio
class TestAttendanceSessionPermissions:
    """Tests des permissions pour les appels."""

    async def test_servant_cannot_create_session(
        self, client: AsyncClient, servant_token: str
    ):
        """Test : Un SERVANT ne peut pas créer de session."""
        response = await client.post(
            "/api/v1/attendance-sessions/",
            headers={"Authorization": f"Bearer {servant_token}"},
            json={
                "session_date": datetime(2026, 2, 15, tzinfo=timezone.utc).isoformat(),
                "session_time": "07h30",
                "location": "Sacristie",
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_servant_can_view_sessions(
        self, client: AsyncClient, servant_token: str
    ):
        """Test : Un SERVANT peut consulter les sessions."""
        response = await client.get(
            "/api/v1/attendance-sessions/",
            headers={"Authorization": f"Bearer {servant_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_servant_can_view_own_stats(
        self, client: AsyncClient, servant_token: str, servant_user_id: str
    ):
        """Test : Un SERVANT peut consulter ses propres stats."""
        response = await client.get(
            f"/api/v1/attendance-sessions/servants/{servant_user_id}/stats",
            headers={"Authorization": f"Bearer {servant_token}"},
        )
        assert response.status_code == status.HTTP_200_OK

    async def test_unauthenticated_cannot_access(self, client: AsyncClient):
        """Test : Accès non authentifié refusé."""
        response = await client.get("/api/v1/attendance-sessions/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestAttendanceSessionBusinessRules:
    """Tests des règles métier des appels."""

    async def test_servant_must_exist(
        self, client: AsyncClient, censeur_token: str, attendance_session_id: str
    ):
        """Test : Le servant doit exister."""
        fake_servant_id = str(uuid4())
        response = await client.post(
            f"/api/v1/attendance-sessions/{attendance_session_id}/records",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "servant_id": fake_servant_id,
                "status": "PRESENT",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_session_must_exist(
        self, client: AsyncClient, censeur_token: str, servant_user_id: str
    ):
        """Test : La session doit exister."""
        fake_session_id = str(uuid4())
        response = await client.post(
            f"/api/v1/attendance-sessions/{fake_session_id}/records",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "servant_id": servant_user_id,
                "status": "PRESENT",
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_invalid_status_rejected(
        self,
        client: AsyncClient,
        censeur_token: str,
        attendance_session_id: str,
        servant_user_id: str,
    ):
        """Test : Statut invalide rejeté."""
        response = await client.post(
            f"/api/v1/attendance-sessions/{attendance_session_id}/records",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "servant_id": servant_user_id,
                "status": "INVALID_STATUS",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
