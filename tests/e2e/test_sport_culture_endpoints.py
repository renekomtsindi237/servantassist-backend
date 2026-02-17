"""
Tests E2E pour les endpoints d'activités sportives et culturelles (CHARGE_SPORT_CULTURE).
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.sport_culture import EventStatus, EventType, ParticipationStatus, ResultType, SportType

# ══════════════════════════════════════════════════════════════════
#  TESTS - ÉVÉNEMENTS
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_event_success(
    client: AsyncClient,
    charge_sport_culture_token: str,
):
    """Test création d'un événement."""
    response = await client.post(
        "/api/v1/sport-culture/events",
        json={
            "title": "Tournoi de football",
            "description": "Tournoi inter-paroisses",
            "event_type": "TOURNOI",
            "sport_type": "FOOTBALL",
            "date": "2026-04-01T09:00:00",
            "start_time": "09h00",
            "end_time": "17h00",
            "location": "Stade municipal",
            "max_participants": 40,
            "cost": 1500.0,
            "registration_deadline": "2026-03-25T23:59:59",
            "broadcast_notification": True,
        },
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Tournoi de football"
    assert data["event_type"] == "TOURNOI"
    assert data["sport_type"] == "FOOTBALL"
    assert data["status"] == "PLANIFIE"


@pytest.mark.asyncio
async def test_create_event_forbidden(
    client: AsyncClient,
    servant_token: str,
):
    """Test création interdite pour un servant normal."""
    response = await client.post(
        "/api/v1/sport-culture/events",
        json={
            "title": "Test",
            "description": "Test",
            "event_type": "AUTRE",
            "date": "2026-04-01T09:00:00",
            "start_time": "09h00",
            "end_time": "17h00",
            "location": "Test",
            "max_participants": 10,
        },
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_events(
    client: AsyncClient,
    servant_token: str,
    sample_sport_event,
):
    """Test liste des événements."""
    response = await client.get(
        "/api/v1/sport-culture/events",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_get_event(
    client: AsyncClient,
    servant_token: str,
    sample_sport_event,
):
    """Test récupération d'un événement."""
    response = await client.get(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_sport_event.id)
    assert data["title"] == sample_sport_event.title


@pytest.mark.asyncio
async def test_update_event(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_sport_event,
):
    """Test modification d'un événement."""
    response = await client.patch(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}",
        json={"status": "OUVERT"},
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OUVERT"


@pytest.mark.asyncio
async def test_delete_event(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_sport_event,
):
    """Test suppression d'un événement."""
    response = await client.delete(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}",
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_upcoming_events(
    client: AsyncClient,
    servant_token: str,
):
    """Test récupération des événements à venir."""
    response = await client.get(
        "/api/v1/sport-culture/events/upcoming/list",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data


# ══════════════════════════════════════════════════════════════════
#  TESTS - PARTICIPATIONS
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_register_to_event(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_sport_event,
    servant_user,
):
    """Test inscription à un événement."""
    response = await client.post(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}/register",
        json={
            "servant_id": str(servant_user.id),
            "notes": "Première participation",
        },
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["event_id"] == str(sample_sport_event.id)
    assert data["servant_id"] == str(servant_user.id)
    assert data["status"] == "INSCRIT"


@pytest.mark.asyncio
async def test_register_batch_to_event(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_sport_event,
    servant_user,
    servant_user_2,
):
    """Test inscription par lot."""
    response = await client.post(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}/register-batch",
        json={
            "servant_ids": [str(servant_user.id), str(servant_user_2.id)],
        },
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["total"] == 2


@pytest.mark.asyncio
async def test_get_event_participants(
    client: AsyncClient,
    servant_token: str,
    sample_sport_event,
    sample_event_participation,
):
    """Test liste des participants."""
    response = await client.get(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}/participants",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_mark_attendance(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_event_participation,
):
    """Test marquage de présence."""
    response = await client.post(
        f"/api/v1/sport-culture/participations/{sample_event_participation.id}/attendance",
        json={
            "status": "PRESENT",
            "notes": "Arrivé à l'heure",
        },
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PRESENT"


@pytest.mark.asyncio
async def test_mark_payment(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_event_participation,
):
    """Test marquage de paiement."""
    response = await client.post(
        f"/api/v1/sport-culture/participations/{sample_event_participation.id}/payment",
        json={
            "payment_status": True,
            "notes": "Paiement reçu",
        },
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["payment_status"] is True


@pytest.mark.asyncio
async def test_cancel_participation(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_event_participation,
):
    """Test annulation d'inscription."""
    response = await client.delete(
        f"/api/v1/sport-culture/participations/{sample_event_participation.id}",
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_servant_participations(
    client: AsyncClient,
    servant_token: str,
    servant_user,
    sample_event_participation,
):
    """Test liste des participations d'un servant."""
    response = await client.get(
        f"/api/v1/sport-culture/servants/{servant_user.id}/participations",
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
    sample_event_participation,
):
    """Test statistiques d'un servant."""
    response = await client.get(
        f"/api/v1/sport-culture/servants/{servant_user.id}/stats",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["servant_id"] == str(servant_user.id)
    assert "total_participations" in data
    assert "attendance_rate" in data


# ══════════════════════════════════════════════════════════════════
#  TESTS - RÉSULTATS
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_add_event_result(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_sport_event,
):
    """Test ajout d'un résultat."""
    response = await client.post(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}/results",
        json={
            "result_type": "VICTOIRE",
            "team_name": "Les Servants",
            "score": 5,
            "opponent_name": "Équipe adverse",
            "opponent_score": 2,
            "description": "Belle victoire de l'équipe",
        },
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["result_type"] == "VICTOIRE"
    assert data["score"] == 5


@pytest.mark.asyncio
async def test_get_event_results(
    client: AsyncClient,
    servant_token: str,
    sample_sport_event,
    sample_event_result,
):
    """Test récupération des résultats."""
    response = await client.get(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}/results",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_delete_result(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_event_result,
):
    """Test suppression d'un résultat."""
    response = await client.delete(
        f"/api/v1/sport-culture/results/{sample_event_result.id}",
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 204


# ══════════════════════════════════════════════════════════════════
#  TESTS - ÉQUIPES
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_event_team(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_sport_event,
    servant_user,
    servant_user_2,
):
    """Test création d'une équipe."""
    response = await client.post(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}/teams",
        json={
            "team_name": "Équipe Alpha",
            "captain_id": str(servant_user.id),
            "members": [str(servant_user.id), str(servant_user_2.id)],
        },
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["team_name"] == "Équipe Alpha"
    assert data["captain_id"] == str(servant_user.id)


@pytest.mark.asyncio
async def test_get_event_teams(
    client: AsyncClient,
    servant_token: str,
    sample_sport_event,
    sample_event_team,
):
    """Test récupération des équipes."""
    response = await client.get(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}/teams",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_update_team(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_event_team,
):
    """Test modification d'une équipe."""
    response = await client.patch(
        f"/api/v1/sport-culture/teams/{sample_event_team.id}",
        json={"team_name": "Équipe modifiée"},
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["team_name"] == "Équipe modifiée"


@pytest.mark.asyncio
async def test_delete_team(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_event_team,
):
    """Test suppression d'une équipe."""
    response = await client.delete(
        f"/api/v1/sport-culture/teams/{sample_event_team.id}",
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 204


# ══════════════════════════════════════════════════════════════════
#  TESTS - RAPPORTS ET STATISTIQUES
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_generate_report(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_sport_event,
):
    """Test génération d'un rapport."""
    response = await client.post(
        "/api/v1/sport-culture/report",
        json={
            "start_date": "2026-01-01T00:00:00",
            "end_date": "2026-12-31T23:59:59",
        },
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "average_participation_rate" in data
    assert data["watermark_logo"] == "logo_servant.jpeg"


@pytest.mark.asyncio
async def test_get_stats(
    client: AsyncClient,
    servant_token: str,
):
    """Test récupération des statistiques."""
    response = await client.get(
        "/api/v1/sport-culture/stats",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "total_events" in data
    assert "average_participation_rate" in data


# ══════════════════════════════════════════════════════════════════
#  TESTS - RÈGLES MÉTIER
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_cannot_register_twice(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_sport_event,
    sample_event_participation,
    servant_user,
):
    """Test qu'on ne peut pas s'inscrire deux fois."""
    response = await client.post(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}/register",
        json={"servant_id": str(servant_user.id)},
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cannot_delete_event_with_participants(
    client: AsyncClient,
    charge_sport_culture_token: str,
    sample_sport_event,
    sample_event_participation,
):
    """Test qu'on ne peut pas supprimer un événement avec participants."""
    response = await client.delete(
        f"/api/v1/sport-culture/events/{sample_sport_event.id}",
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 400
    assert "participants" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_event_full(
    client: AsyncClient,
    charge_sport_culture_token: str,
    charge_sport_culture_user,
    servant_user,
    servant_user_2,
):
    """Test qu'on ne peut pas dépasser le nombre maximum de participants."""
    # Créer un événement avec max 1 participant
    response = await client.post(
        "/api/v1/sport-culture/events",
        json={
            "title": "Événement limité",
            "description": "Test",
            "event_type": "AUTRE",
            "date": "2026-04-01T09:00:00",
            "start_time": "09h00",
            "end_time": "17h00",
            "location": "Test",
            "max_participants": 1,
        },
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    event_id = response.json()["id"]

    # Inscrire le premier servant
    response = await client.post(
        f"/api/v1/sport-culture/events/{event_id}/register",
        json={"servant_id": str(servant_user.id)},
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 201

    # Essayer d'inscrire le deuxième servant
    response = await client.post(
        f"/api/v1/sport-culture/events/{event_id}/register",
        json={"servant_id": str(servant_user_2.id)},
        headers={"Authorization": f"Bearer {charge_sport_culture_token}"},
    )
    assert response.status_code == 400
    assert "full" in response.json()["detail"].lower()
