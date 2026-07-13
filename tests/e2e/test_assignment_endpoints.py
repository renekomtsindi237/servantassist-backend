"""
Tests E2E — Module Affectations (/api/v1/assignments/*).

Couvre :
- CRUD affectations (creation, lecture, modification, suppression)
- Creation par lot (batch)
- Self-service (accepter / decliner par le servant)
- Presence / absence (par l'aumonier)
- Annulation (soft-delete)
- Permissions RBAC (aumonier/admin vs servant/parent)
- Filtres et pagination
- Enrichissement des reponses (infos user + event)
"""

from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.assignment import Assignment, AssignmentStatus, LiturgicalRole
from src.core.entities.event import Event, EventStatus, EventType
from src.core.entities.user import User, UserRole
from tests.conftest import VALID_PASSWORD, make_auth_header


# ═══════════════════════════════════════════════════════════════════════════
#  CREATION D'AFFECTATIONS
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestCreateAssignment:
    """Creation d'affectations par l'aumonier et l'admin."""

    async def test_aumonier_creates_assignment(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """L'aumonier peut creer une affectation."""
        resp = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(servant_user.id),
                "liturgical_role": "CRUCIFER",
                "notes": "Porte-croix titulaire",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["liturgical_role"] == "CRUCIFER"
        assert body["status"] == "PENDING"
        assert body["notes"] == "Porte-croix titulaire"
        assert body["user_first_name"] == "Servant"
        assert body["event_title"] == "Messe dominicale de test"
        assert body["assigned_by"] == str(aumonier_user.id)

    async def test_admin_creates_assignment(
        self,
        client: AsyncClient,
        admin_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """L'admin peut aussi creer des affectations."""
        resp = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(servant_user.id),
                "liturgical_role": "THURIFER",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        assert resp.json()["liturgical_role"] == "THURIFER"

    async def test_servant_cannot_create_assignment(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_event: Event,
    ):
        """Un servant ne peut pas creer d'affectation."""
        resp = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(servant_user.id),
                "liturgical_role": "ACOLYTE",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    async def test_parent_cannot_create_assignment(
        self,
        client: AsyncClient,
        parent_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """Un parent ne peut pas creer d'affectation."""
        resp = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(servant_user.id),
            },
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    async def test_cannot_assign_non_servant(
        self,
        client: AsyncClient,
        aumonier_user: User,
        parent_user: User,
        sample_event: Event,
    ):
        """Impossible d'affecter un parent a un role liturgique."""
        resp = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(parent_user.id),
                "liturgical_role": "CRUCIFER",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400
        assert "servant" in resp.json()["detail"].lower()

    async def test_duplicate_role_rejected(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """On ne peut pas affecter le meme servant au meme role deux fois."""
        # Premier ajout
        await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(servant_user.id),
                "liturgical_role": "ACOLYTE",
            },
            headers=make_auth_header(aumonier_user),
        )
        # Deuxieme -> 409
        resp = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(servant_user.id),
                "liturgical_role": "ACOLYTE",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 409

    async def test_different_roles_allowed(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """Le meme servant peut avoir des roles differents au meme evenement."""
        resp1 = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(servant_user.id),
                "liturgical_role": "CRUCIFER",
            },
            headers=make_auth_header(aumonier_user),
        )
        resp2 = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(servant_user.id),
                "liturgical_role": "LECTEUR",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp1.status_code == 201
        assert resp2.status_code == 201

    async def test_event_not_found(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """Evenement inexistant -> 404."""
        resp = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(uuid4()),
                "user_id": str(servant_user.id),
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 404

    async def test_user_not_found(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_event: Event,
    ):
        """Utilisateur inexistant -> 404."""
        resp = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(uuid4()),
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 404

    async def test_inactive_user_rejected(
        self,
        client: AsyncClient,
        aumonier_user: User,
        inactive_user: User,
        sample_event: Event,
    ):
        """Utilisateur inactif -> 400."""
        resp = await client.post(
            "/api/v1/assignments/",
            json={
                "event_id": str(sample_event.id),
                "user_id": str(inactive_user.id),
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    async def test_all_liturgical_roles_accepted(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_event: Event,
    ):
        """Tous les roles liturgiques sont acceptes."""
        roles = [
            "CRUCIFER",
            "THURIFER",
            "ACOLYTE",
            "CEROMONIAIRE",
            "NAVETTIER",
            "PORTE_MITRE",
            "PORTE_CROSSE",
            "PORTE_BOUGEOIR",
            "LECTEUR",
            "SERVANT_GENERAL",
            "AUTRE",
        ]
        for role in roles:
            resp = await client.post(
                "/api/v1/assignments/",
                json={
                    "event_id": str(sample_event.id),
                    "user_id": str(servant_user.id),
                    "liturgical_role": role,
                },
                headers=make_auth_header(aumonier_user),
            )
            assert resp.status_code == 201, f"Role {role} rejected"


# ═══════════════════════════════════════════════════════════════════════════
#  CREATION PAR LOT
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestBatchCreate:
    """Creation par lot d'affectations."""

    async def test_batch_create_success(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        servant_user_2: User,
        sample_event: Event,
    ):
        """Creation de plusieurs affectations en une requete."""
        resp = await client.post(
            "/api/v1/assignments/batch",
            json={
                "event_id": str(sample_event.id),
                "assignments": [
                    {"user_id": str(servant_user.id), "liturgical_role": "CRUCIFER"},
                    {"user_id": str(servant_user_2.id), "liturgical_role": "THURIFER"},
                ],
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["total_created"] == 2
        assert body["total_errors"] == 0
        assert len(body["created"]) == 2

    async def test_batch_partial_errors(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        parent_user: User,
        sample_event: Event,
    ):
        """Batch avec une erreur : le parent n'est pas servant."""
        resp = await client.post(
            "/api/v1/assignments/batch",
            json={
                "event_id": str(sample_event.id),
                "assignments": [
                    {"user_id": str(servant_user.id), "liturgical_role": "ACOLYTE"},
                    {"user_id": str(parent_user.id), "liturgical_role": "CRUCIFER"},
                ],
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["total_created"] == 1
        assert body["total_errors"] == 1
        assert len(body["errors"]) == 1


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURE
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestReadAssignments:
    """Lecture des affectations."""

    async def test_list_assignments_paginated(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """Liste paginee des affectations."""
        resp = await client.get(
            "/api/v1/assignments/",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["items"]) >= 1

    async def test_get_assignment_detail(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Detail d'une affectation avec infos enrichies."""
        resp = await client.get(
            f"/api/v1/assignments/{sample_assignment.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["liturgical_role"] == "CRUCIFER"
        assert body["user_first_name"] == "Servant"
        assert body["event_title"] == "Messe dominicale de test"

    async def test_get_event_assignments(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
        sample_event: Event,
    ):
        """Affectations d'un evenement."""
        resp = await client.get(
            f"/api/v1/assignments/event/{sample_event.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    async def test_my_assignments(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Mes affectations."""
        resp = await client.get(
            "/api/v1/assignments/me",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assignments = resp.json()
        assert len(assignments) >= 1
        assert any(a["id"] == str(sample_assignment.id) for a in assignments)

    async def test_my_upcoming(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Mes affectations a venir."""
        resp = await client.get(
            "/api/v1/assignments/me/upcoming",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        # L'evenement de test est dans le futur (2026-03-01)
        assignments = resp.json()
        assert len(assignments) >= 1

    async def test_unauthenticated_401(self, client: AsyncClient):
        """Sans authentification -> 401."""
        resp = await client.get("/api/v1/assignments/me")
        assert resp.status_code == 401

    async def test_assignment_not_found_404(self, client: AsyncClient, servant_user: User):
        """Affectation inexistante -> 404."""
        resp = await client.get(
            f"/api/v1/assignments/{uuid4()}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 404

    async def test_filter_by_status(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """Filtre par statut."""
        resp = await client.get(
            "/api/v1/assignments/?status=PENDING",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        for item in body["items"]:
            assert item["status"] == "PENDING"


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE (ACCEPTER / DECLINER)
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestSelfServiceStatus:
    """Le servant accepte ou decline ses affectations."""

    async def test_accept_assignment(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Le servant accepte son affectation."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/my-status",
            json={"status": "ACCEPTED"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACCEPTED"

    async def test_decline_assignment(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Le servant decline son affectation."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/my-status",
            json={"status": "DECLINED"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "DECLINED"

    async def test_cannot_update_others_assignment(
        self,
        client: AsyncClient,
        servant_user_2: User,
        sample_assignment: Assignment,
    ):
        """Un servant ne peut pas modifier l'affectation d'un autre."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/my-status",
            json={"status": "ACCEPTED"},
            headers=make_auth_header(servant_user_2),
        )
        assert resp.status_code == 403

    async def test_cannot_change_non_pending(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Impossible de changer un statut non-PENDING."""
        # D'abord accepter
        await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/my-status",
            json={"status": "ACCEPTED"},
            headers=make_auth_header(servant_user),
        )
        # Ensuite essayer de decliner -> 400
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/my-status",
            json={"status": "DECLINED"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 400

    async def test_invalid_status_rejected(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Seuls ACCEPTED et DECLINED sont autorises."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/my-status",
            json={"status": "PRESENT"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
#  MODIFICATION PAR L'AUMONIER
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestUpdateAssignment:
    """Modification d'affectations."""

    async def test_aumonier_updates_role(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """L'aumonier modifie le role d'une affectation."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}",
            json={"liturgical_role": "CEROMONIAIRE"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["liturgical_role"] == "CEROMONIAIRE"

    async def test_aumonier_updates_notes(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """L'aumonier modifie les notes."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}",
            json={"notes": "Notes mises a jour"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Notes mises a jour"

    async def test_servant_cannot_update_via_admin_route(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Un servant ne peut pas utiliser la route admin pour modifier."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}",
            json={"liturgical_role": "THURIFER"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  PRESENCE / ABSENCE
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestPresence:
    """Marquage de presence / absence."""

    async def test_mark_present(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """L'aumonier marque un servant comme present."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/presence?present=true",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PRESENT"

    async def test_mark_absent(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """L'aumonier marque un servant comme absent."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/presence?present=false",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ABSENT"

    async def test_servant_cannot_mark_presence(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Un servant ne peut pas marquer la presence."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/presence?present=true",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  ANNULATION ET SUPPRESSION
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.e2e
class TestCancelAndDelete:
    """Annulation et suppression d'affectations."""

    async def test_cancel_assignment(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """L'aumonier annule une affectation (soft-delete)."""
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/cancel",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"

    async def test_cancel_already_cancelled(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """Annuler une affectation deja annulee -> 400."""
        await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/cancel",
            headers=make_auth_header(aumonier_user),
        )
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/cancel",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    async def test_delete_assignment(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """L'aumonier supprime definitivement une affectation."""
        resp = await client.delete(
            f"/api/v1/assignments/{sample_assignment.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 204

        # Verifier que l'affectation est supprimee
        resp2 = await client.get(
            f"/api/v1/assignments/{sample_assignment.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp2.status_code == 404

    async def test_servant_cannot_delete(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_assignment: Assignment,
    ):
        """Un servant ne peut pas supprimer une affectation."""
        resp = await client.delete(
            f"/api/v1/assignments/{sample_assignment.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    async def test_presence_on_cancelled_rejected(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_assignment: Assignment,
    ):
        """Marquer la presence d'une affectation annulee -> 400."""
        # Annuler
        await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/cancel",
            headers=make_auth_header(aumonier_user),
        )
        # Marquer present -> 400
        resp = await client.patch(
            f"/api/v1/assignments/{sample_assignment.id}/presence?present=true",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400
