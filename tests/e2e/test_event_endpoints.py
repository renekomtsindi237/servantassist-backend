"""
Tests E2E — Module Evenements (/api/v1/events/*).

Couvre :
- CRUD evenements (creation, lecture, modification, suppression)
- Gestion des participants (ajout, modification, retrait)
- Permissions RBAC (aumonier/admin vs servant/parent)
- Filtres et pagination
- Self-service participant (confirmer/decliner)
"""
from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.event import Event, EventParticipant, EventStatus, EventType
from src.core.entities.user import User, UserRole
from tests.conftest import VALID_PASSWORD, make_auth_header


# ═══════════════════════════════════════════════════════════════════════════
#  CREATION D'EVENEMENTS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestCreateEvent:
    """Creation d'evenements par l'aumonier et l'admin."""

    async def test_aumonier_creates_event(
        self, client: AsyncClient, aumonier_user: User
    ):
        """L'aumonier peut creer un evenement."""
        resp = await client.post(
            "/api/v1/events/",
            json={
                "title": "Messe dominicale",
                "description": "Messe du dimanche matin",
                "start_time": "2026-03-15T09:00:00",
                "end_time": "2026-03-15T11:00:00",
                "location": "Cathédrale",
                "event_type": "MESSE_DOMINICALE",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Messe dominicale"
        assert body["event_type"] == "MESSE_DOMINICALE"
        assert body["status"] == "BROUILLON"
        assert body["created_by"] == str(aumonier_user.id)

    async def test_admin_creates_event(self, client: AsyncClient, admin_user: User):
        """L'admin peut aussi creer des evenements."""
        resp = await client.post(
            "/api/v1/events/",
            json={
                "title": "Camp spirituel",
                "start_time": "2026-07-01T08:00:00",
                "end_time": "2026-07-03T18:00:00",
                "location": "Centre de retraite",
                "event_type": "CAMP_SPIRITUEL",
                "status": "PUBLIE",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        assert resp.json()["event_type"] == "CAMP_SPIRITUEL"
        assert resp.json()["status"] == "PUBLIE"

    async def test_create_event_with_participants(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        """Creer un evenement avec participants en une seule requete."""
        resp = await client.post(
            "/api/v1/events/",
            json={
                "title": "Mariage",
                "start_time": "2026-04-20T10:00:00",
                "end_time": "2026-04-20T13:00:00",
                "location": "Eglise Saint-Paul",
                "event_type": "MARIAGE",
                "participants": [
                    {"user_id": str(servant_user.id), "participant_role": "THURIFER"},
                ],
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body["participants"]) == 1
        assert body["participants"][0]["participant_role"] == "THURIFER"
        assert body["participants"][0]["user_first_name"] == "Servant"

    async def test_servant_cannot_create_event(
        self, client: AsyncClient, servant_user: User
    ):
        """Un servant ne peut pas creer d'evenement."""
        resp = await client.post(
            "/api/v1/events/",
            json={
                "title": "Test",
                "start_time": "2026-03-15T09:00:00",
                "end_time": "2026-03-15T11:00:00",
                "location": "Test",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    async def test_parent_cannot_create_event(
        self, client: AsyncClient, parent_user: User
    ):
        """Un parent ne peut pas creer d'evenement."""
        resp = await client.post(
            "/api/v1/events/",
            json={
                "title": "Test",
                "start_time": "2026-03-15T09:00:00",
                "end_time": "2026-03-15T11:00:00",
                "location": "Test",
            },
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    async def test_end_before_start_rejected(
        self, client: AsyncClient, aumonier_user: User
    ):
        """Date de fin avant date de debut -> 422."""
        resp = await client.post(
            "/api/v1/events/",
            json={
                "title": "Invalide",
                "start_time": "2026-03-15T11:00:00",
                "end_time": "2026-03-15T09:00:00",
                "location": "Test",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 422

    async def test_all_event_types_accepted(
        self, client: AsyncClient, aumonier_user: User
    ):
        """Tous les types d'evenements sont acceptes."""
        types = [
            "MESSE_DOMINICALE",
            "MESSE_SEMAINE",
            "MESSE_PONTIFICALE",
            "MESSE_SOLENNELLE_PONTIFICALE",
            "MESSE_ACTION_GRACE",
            "MARIAGE",
            "REQUIEM",
            "RECOLLECTION",
            "CAMP_SPIRITUEL",
            "JOURNEE_AMITIE",
            "JOURNEE_SPORTIVE",
            "CAMP",
            "REPETITION",
            "AUTRE",
        ]
        for i, etype in enumerate(types):
            resp = await client.post(
                "/api/v1/events/",
                json={
                    "title": f"Event type {etype}",
                    "start_time": f"2026-05-{10+i:02d}T09:00:00",
                    "end_time": f"2026-05-{10+i:02d}T11:00:00",
                    "location": "Test",
                    "event_type": etype,
                },
                headers=make_auth_header(aumonier_user),
            )
            assert resp.status_code == 201, f"Type {etype} rejected"


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURE DES EVENEMENTS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestReadEvents:
    """Lecture et filtrage des evenements."""

    async def test_list_events_authenticated(
        self, client: AsyncClient, servant_user: User, sample_event: Event
    ):
        """Tout utilisateur authentifie peut lister les evenements."""
        resp = await client.get(
            "/api/v1/events/",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["items"]) >= 1

    async def test_get_event_detail(
        self, client: AsyncClient, servant_user: User, sample_event: Event
    ):
        """Detail d'un evenement avec participants."""
        resp = await client.get(
            f"/api/v1/events/{sample_event.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Messe dominicale de test"
        assert "participants" in body

    async def test_event_not_found_404(self, client: AsyncClient, servant_user: User):
        """Evenement inexistant -> 404."""
        resp = await client.get(
            f"/api/v1/events/{uuid4()}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 404

    async def test_unauthenticated_list_events_401(self, client: AsyncClient):
        """Sans authentification -> 401."""
        resp = await client.get("/api/v1/events/")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  MODIFICATION DES EVENEMENTS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestUpdateEvent:
    """Modification d'evenements."""

    async def test_aumonier_updates_event(
        self, client: AsyncClient, aumonier_user: User, sample_event: Event
    ):
        """L'aumonier peut modifier un evenement."""
        resp = await client.patch(
            f"/api/v1/events/{sample_event.id}",
            json={"title": "Messe dominicale modifiée", "status": "EN_COURS"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Messe dominicale modifiée"
        assert body["status"] == "EN_COURS"
        assert body["updated_by"] == str(aumonier_user.id)

    async def test_servant_cannot_update_event(
        self, client: AsyncClient, servant_user: User, sample_event: Event
    ):
        """Un servant ne peut pas modifier un evenement."""
        resp = await client.patch(
            f"/api/v1/events/{sample_event.id}",
            json={"title": "Hack"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  SUPPRESSION DES EVENEMENTS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestDeleteEvent:
    """Suppression d'evenements."""

    async def test_aumonier_deletes_event(
        self, client: AsyncClient, aumonier_user: User, sample_event: Event
    ):
        """L'aumonier peut supprimer un evenement."""
        resp = await client.delete(
            f"/api/v1/events/{sample_event.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 204

        # Verifier que l'evenement est supprime
        resp2 = await client.get(
            f"/api/v1/events/{sample_event.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp2.status_code == 404

    async def test_servant_cannot_delete_event(
        self, client: AsyncClient, servant_user: User, sample_event: Event
    ):
        """Un servant ne peut pas supprimer un evenement."""
        resp = await client.delete(
            f"/api/v1/events/{sample_event.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  GESTION DES PARTICIPANTS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestParticipants:
    """Gestion des participants aux evenements."""

    async def test_add_participant(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """L'aumonier ajoute un servant comme participant."""
        resp = await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={
                "user_id": str(servant_user.id),
                "participant_role": "CRUCIFER",
                "notes": "Porte-croix titulaire",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["participant_role"] == "CRUCIFER"
        assert body["status"] == "INVITE"
        assert body["user_first_name"] == "Servant"
        assert body["notes"] == "Porte-croix titulaire"

    async def test_duplicate_participant_rejected(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """On ne peut pas ajouter deux fois le meme participant."""
        # Premier ajout
        await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={"user_id": str(servant_user.id), "participant_role": "CRUCIFER"},
            headers=make_auth_header(aumonier_user),
        )
        # Deuxieme ajout -> 409
        resp = await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={"user_id": str(servant_user.id), "participant_role": "THURIFER"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 409

    async def test_list_participants(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """Lister les participants d'un evenement."""
        # Ajouter un participant
        await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={"user_id": str(servant_user.id), "participant_role": "ACOLYTE"},
            headers=make_auth_header(aumonier_user),
        )
        resp = await client.get(
            f"/api/v1/events/{sample_event.id}/participants",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_update_participant(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """L'aumonier modifie le role d'un participant."""
        # Ajouter
        add_resp = await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={"user_id": str(servant_user.id), "participant_role": "SERVANT"},
            headers=make_auth_header(aumonier_user),
        )
        pid = add_resp.json()["id"]

        # Modifier
        resp = await client.patch(
            f"/api/v1/events/{sample_event.id}/participants/{pid}",
            json={"participant_role": "CEROMONIAIRE", "status": "CONFIRME"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["participant_role"] == "CEROMONIAIRE"
        assert resp.json()["status"] == "CONFIRME"

    async def test_remove_participant(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """L'aumonier retire un participant."""
        add_resp = await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={"user_id": str(servant_user.id)},
            headers=make_auth_header(aumonier_user),
        )
        pid = add_resp.json()["id"]

        resp = await client.delete(
            f"/api/v1/events/{sample_event.id}/participants/{pid}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 204

    async def test_servant_cannot_add_participant(
        self, client: AsyncClient, servant_user: User, sample_event: Event
    ):
        """Un servant ne peut pas ajouter de participant."""
        resp = await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={"user_id": str(servant_user.id)},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE PARTICIPATION
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestMyParticipation:
    """Le servant/parent confirme ou decline sa participation."""

    async def test_confirm_participation(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """Le servant confirme sa participation."""
        # Ajouter le servant
        await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={"user_id": str(servant_user.id)},
            headers=make_auth_header(aumonier_user),
        )

        # Confirmer
        resp = await client.patch(
            f"/api/v1/events/{sample_event.id}/my-participation?new_status=CONFIRME",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CONFIRME"

    async def test_decline_participation(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """Le servant decline sa participation."""
        await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={"user_id": str(servant_user.id)},
            headers=make_auth_header(aumonier_user),
        )

        resp = await client.patch(
            f"/api/v1/events/{sample_event.id}/my-participation?new_status=DECLINE",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "DECLINE"

    async def test_non_participant_cannot_update(
        self, client: AsyncClient, servant_user: User, sample_event: Event
    ):
        """Un non-participant ne peut pas confirmer/decliner."""
        resp = await client.patch(
            f"/api/v1/events/{sample_event.id}/my-participation?new_status=CONFIRME",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 404

    async def test_my_events(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """Le servant voit ses evenements."""
        # Ajouter le servant a l'evenement
        await client.post(
            f"/api/v1/events/{sample_event.id}/participants",
            json={"user_id": str(servant_user.id)},
            headers=make_auth_header(aumonier_user),
        )

        resp = await client.get(
            "/api/v1/events/me",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1
        assert any(e["id"] == str(sample_event.id) for e in events)
