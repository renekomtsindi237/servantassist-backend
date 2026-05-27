"""
Tests E2E pour les endpoints de formations liturgiques (CHARGE_LITURGIE).
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.training import (
    MaterialType,
    ParticipationStatus,
    TrainingLevel,
    TrainingStatus,
)

# ══════════════════════════════════════════════════════════════════
#  TESTS - SESSIONS DE FORMATION
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_training_session_success(
    client: AsyncClient,
    charge_liturgie_token: str,
    charge_liturgie_user,
):
    """Test création d'une session de formation."""
    response = await client.post(
        "/api/v1/training/sessions",
        json={
            "title": "Formation liturgique de base",
            "description": "Introduction aux gestes liturgiques",
            "objectives": "Maîtriser les gestes de base",
            "level": "DEBUTANT",
            "date": "2026-03-01T14:00:00",
            "start_time": "14h00",
            "end_time": "16h00",
            "duration_minutes": 120,
            "location": "Salle paroissiale",
            "trainer_id": str(charge_liturgie_user.id),
            "max_participants": 20,
        },
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Formation liturgique de base"
    assert data["level"] == "DEBUTANT"
    assert data["status"] == "PLANIFIEE"


@pytest.mark.asyncio
async def test_create_training_session_forbidden(
    client: AsyncClient,
    servant_token: str,
):
    """Test création interdite pour un servant normal."""
    response = await client.post(
        "/api/v1/training/sessions",
        json={
            "title": "Formation test",
            "description": "Test",
            "level": "DEBUTANT",
            "date": "2026-03-01T14:00:00",
            "start_time": "14h00",
            "end_time": "16h00",
            "duration_minutes": 120,
            "location": "Test",
            "trainer_id": str(uuid4()),
            "max_participants": 20,
        },
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_training_sessions(
    client: AsyncClient,
    servant_token: str,
    sample_training_session,
):
    """Test liste des sessions."""
    response = await client.get(
        "/api/v1/training/sessions",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_training_session(
    client: AsyncClient,
    servant_token: str,
    sample_training_session,
):
    """Test récupération d'une session."""
    response = await client.get(
        f"/api/v1/training/sessions/{sample_training_session.id}",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_training_session.id)
    assert data["title"] == sample_training_session.title


@pytest.mark.asyncio
async def test_update_training_session(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_session,
):
    """Test modification d'une session."""
    response = await client.patch(
        f"/api/v1/training/sessions/{sample_training_session.id}",
        json={"title": "Formation modifiée"},
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Formation modifiée"


@pytest.mark.asyncio
async def test_delete_training_session(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_session,
):
    """Test suppression d'une session."""
    response = await client.delete(
        f"/api/v1/training/sessions/{sample_training_session.id}",
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 204


# ══════════════════════════════════════════════════════════════════
#  TESTS - PARTICIPATIONS
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_register_to_session(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_session,
    servant_user,
):
    """Test inscription à une session."""
    response = await client.post(
        f"/api/v1/training/sessions/{sample_training_session.id}/register",
        json={
            "servant_id": str(servant_user.id),
            "notes": "Première formation",
        },
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["session_id"] == str(sample_training_session.id)
    assert data["servant_id"] == str(servant_user.id)
    assert data["status"] == "INSCRIT"


@pytest.mark.asyncio
async def test_register_batch_to_session(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_session,
    servant_user,
    servant_user_2,
):
    """Test inscription par lot."""
    response = await client.post(
        f"/api/v1/training/sessions/{sample_training_session.id}/register-batch",
        json={
            "servant_ids": [str(servant_user.id), str(servant_user_2.id)],
        },
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_get_session_participants(
    client: AsyncClient,
    servant_token: str,
    sample_training_session,
    sample_training_participation,
):
    """Test liste des participants."""
    response = await client.get(
        f"/api/v1/training/sessions/{sample_training_session.id}/participants",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_mark_attendance(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_participation,
):
    """Test marquage de présence."""
    response = await client.post(
        f"/api/v1/training/participations/{sample_training_participation.id}/attendance",
        json={
            "status": "PRESENT",
            "notes": "Arrivé à l'heure",
        },
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PRESENT"


@pytest.mark.asyncio
async def test_evaluate_participant(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_participation,
):
    """Test évaluation d'un participant."""
    response = await client.post(
        f"/api/v1/training/participations/{sample_training_participation.id}/evaluate",
        json={
            "evaluation_score": 85,
            "evaluation_comments": "Très bonne participation",
            "certificate_issued": True,
        },
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["evaluation_score"] == 85
    assert data["certificate_issued"] is True


@pytest.mark.asyncio
async def test_get_servant_participations(
    client: AsyncClient,
    servant_token: str,
    servant_user,
    sample_training_participation,
):
    """Test liste des participations d'un servant."""
    response = await client.get(
        f"/api/v1/training/servants/{servant_user.id}/participations",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_servant_stats(
    client: AsyncClient,
    servant_token: str,
    servant_user,
    sample_training_participation,
):
    """Test statistiques d'un servant."""
    response = await client.get(
        f"/api/v1/training/servants/{servant_user.id}/stats",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["servant_id"] == str(servant_user.id)
    assert "total_sessions" in data
    assert "attendance_rate" in data


# ══════════════════════════════════════════════════════════════════
#  TESTS - MATÉRIELS PÉDAGOGIQUES
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_training_material(
    client: AsyncClient,
    charge_liturgie_token: str,
):
    """Test création d'un matériel."""
    response = await client.post(
        "/api/v1/training/materials",
        json={
            "title": "Guide du servant",
            "description": "Document PDF complet",
            "type": "DOCUMENT",
            "file_url": "https://storage.example.com/guide.pdf",
            "file_type": "application/pdf",
            "file_size": 1024000,
            "level": "DEBUTANT",
            "tags": ["liturgie", "guide"],
            "is_public": True,
        },
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Guide du servant"
    assert data["type"] == "DOCUMENT"


@pytest.mark.asyncio
async def test_list_training_materials(
    client: AsyncClient,
    servant_token: str,
    sample_training_material,
):
    """Test liste des matériels."""
    response = await client.get(
        "/api/v1/training/materials",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_training_material(
    client: AsyncClient,
    servant_token: str,
    sample_training_material,
):
    """Test récupération d'un matériel."""
    response = await client.get(
        f"/api/v1/training/materials/{sample_training_material.id}",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_training_material.id)
    # Le compteur de vues devrait être incrémenté
    assert data["view_count"] >= 1


@pytest.mark.asyncio
async def test_update_training_material(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_material,
):
    """Test modification d'un matériel."""
    response = await client.patch(
        f"/api/v1/training/materials/{sample_training_material.id}",
        json={"title": "Guide modifié"},
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Guide modifié"


@pytest.mark.asyncio
async def test_delete_training_material(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_material,
):
    """Test suppression d'un matériel."""
    response = await client.delete(
        f"/api/v1/training/materials/{sample_training_material.id}",
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 204


# ══════════════════════════════════════════════════════════════════
#  TESTS - RAPPORTS
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_generate_training_report(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_session,
):
    """Test génération d'un rapport."""
    response = await client.post(
        "/api/v1/training/report",
        json={
            "start_date": "2026-01-01T00:00:00",
            "end_date": "2026-12-31T23:59:59",
            "include_stats": True,
        },
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_sessions" in data
    assert "average_attendance_rate" in data
    assert data["watermark_logo"] == "logo_servant.jpeg"


# ══════════════════════════════════════════════════════════════════
#  TESTS - RÈGLES MÉTIER
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cannot_register_twice(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_session,
    sample_training_participation,
    servant_user,
):
    """Test qu'on ne peut pas s'inscrire deux fois."""
    response = await client.post(
        f"/api/v1/training/sessions/{sample_training_session.id}/register",
        json={"servant_id": str(servant_user.id)},
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cannot_delete_session_with_participants(
    client: AsyncClient,
    charge_liturgie_token: str,
    sample_training_session,
    sample_training_participation,
):
    """Test qu'on ne peut pas supprimer une session avec participants."""
    response = await client.delete(
        f"/api/v1/training/sessions/{sample_training_session.id}",
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 400
    assert "participants" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_session_full(
    client: AsyncClient,
    charge_liturgie_token: str,
    charge_liturgie_user,
    servant_user,
    servant_user_2,
):
    """Test qu'on ne peut pas dépasser le nombre maximum de participants."""
    # Créer une session avec max 1 participant
    response = await client.post(
        "/api/v1/training/sessions",
        json={
            "title": "Session limitée",
            "description": "Test",
            "level": "DEBUTANT",
            "date": "2026-03-01T14:00:00",
            "start_time": "14h00",
            "end_time": "16h00",
            "duration_minutes": 120,
            "location": "Test",
            "trainer_id": str(charge_liturgie_user.id),
            "max_participants": 1,
        },
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    session_id = response.json()["id"]

    # Inscrire le premier servant
    response = await client.post(
        f"/api/v1/training/sessions/{session_id}/register",
        json={"servant_id": str(servant_user.id)},
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 201

    # Essayer d'inscrire le deuxième servant
    response = await client.post(
        f"/api/v1/training/sessions/{session_id}/register",
        json={"servant_id": str(servant_user_2.id)},
        headers={"Authorization": f"Bearer {charge_liturgie_token}"},
    )
    assert response.status_code == 400
    assert "full" in response.json()["detail"].lower()
