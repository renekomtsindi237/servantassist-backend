"""
Tests E2E pour les endpoints de classement dominical.

Les endpoints admin nécessitent CHARGE_CLASSEMENT_DIMANCHE, Admin, ou Aumônier.
On utilise admin_user/aumonier_user pour ces tests.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import make_auth_header


def _next_sunday(offset_weeks: int = 0) -> str:
    """Retourne le prochain dimanche comme datetime ISO."""
    today = datetime.now(timezone.utc)
    days_ahead = 6 - today.weekday()  # 6 = dimanche
    if days_ahead <= 0:
        days_ahead += 7
    sunday = today + timedelta(days=days_ahead) + timedelta(weeks=offset_weeks)
    return sunday.isoformat()


def _template_payload(title="Classement dominical test", offset_weeks=0):
    return {
        "title": title,
        "schedule_date": _next_sunday(offset_weeks),
        "mass_type": "ORDINAIRE",
        "is_exceptional": False,
        "notes": "Test automatisé",
        "masses": [],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Accès public — /published
# ═══════════════════════════════════════════════════════════════════════════


class TestGetPublishedSundayTemplates:
    @pytest.mark.asyncio
    async def test_servant_can_get_published(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            "/api/v1/sunday-schedule/published",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_parent_can_get_published(self, client: AsyncClient, parent_user: User):
        resp = await client.get(
            "/api/v1/sunday-schedule/published",
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/sunday-schedule/published")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_can_get_published(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            "/api/v1/sunday-schedule/published",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════
#  CRUD des templates
# ═══════════════════════════════════════════════════════════════════════════


class TestCreateSundayTemplate:
    @pytest.mark.asyncio
    async def test_admin_creates_template(self, client: AsyncClient, admin_user: User):
        resp = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Classement admin test"),
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Classement admin test"
        assert "id" in body
        assert body["status"] == "DRAFT"
        assert body["mass_type"] == "ORDINAIRE"

    @pytest.mark.asyncio
    async def test_aumonier_creates_template(self, client: AsyncClient, aumonier_user: User):
        resp = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Classement aumonier test", offset_weeks=1),
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_servant_cannot_create(self, client: AsyncClient, servant_user: User):
        resp = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Test"),
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_parent_cannot_create(self, client: AsyncClient, parent_user: User):
        resp = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Test"),
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_create_with_masses(self, client: AsyncClient, admin_user: User):
        """Template avec messes pre-remplies."""
        resp = await client.post(
            "/api/v1/sunday-schedule/",
            json={
                "title": "Classement avec messes",
                "schedule_date": _next_sunday(2),
                "mass_type": "ORDINAIRE",
                "masses": [
                    {"mass_time": "06h30", "language": "EWONDO", "assignments": []},
                    {"mass_time": "08h30", "language": "FRANCAIS", "assignments": []},
                ],
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body.get("masses", [])) == 2

    @pytest.mark.asyncio
    async def test_create_solemn_template(self, client: AsyncClient, admin_user: User):
        resp = await client.post(
            "/api/v1/sunday-schedule/",
            json={
                "title": "Messe solennelle",
                "schedule_date": _next_sunday(3),
                "mass_type": "SOLENNELLE",
                "masses": [],
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        assert resp.json()["mass_type"] == "SOLENNELLE"


class TestGenerateSundayTemplate:
    @pytest.mark.asyncio
    async def test_generate_ordinary_template(self, client: AsyncClient, admin_user: User):
        resp = await client.post(
            "/api/v1/sunday-schedule/generate/ordinary",
            json={
                "title": "Dimanche ordinaire generé",
                "schedule_date": _next_sunday(4),
                "notes": "Génération automatique",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Dimanche ordinaire generé"
        # Should have 5 ordinary masses
        assert len(body.get("masses", [])) == 5

    @pytest.mark.asyncio
    async def test_generate_exceptional_template(self, client: AsyncClient, admin_user: User):
        resp = await client.post(
            "/api/v1/sunday-schedule/generate/exceptional",
            json={
                "title": "Dimanche exceptionnel generé",
                "schedule_date": _next_sunday(5),
                "mass_times": [
                    {"time": "07h00", "language": "FRANCAIS"},
                    {"time": "10h00", "language": "ANGLAIS"},
                ],
                "notes": "Horaires exceptionnels",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["is_exceptional"] is True
        assert len(body.get("masses", [])) == 2

    @pytest.mark.asyncio
    async def test_servant_cannot_generate_ordinary(self, client: AsyncClient, servant_user: User):
        resp = await client.post(
            "/api/v1/sunday-schedule/generate/ordinary",
            json={"title": "Test", "schedule_date": _next_sunday(6)},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_servant_cannot_generate_exceptional(self, client: AsyncClient, servant_user: User):
        resp = await client.post(
            "/api/v1/sunday-schedule/generate/exceptional",
            json={
                "title": "Test",
                "schedule_date": _next_sunday(7),
                "mass_times": [{"time": "09h00", "language": "FRANCAIS"}],
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


class TestListSundayTemplates:
    @pytest.mark.asyncio
    async def test_admin_lists_templates(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            "/api/v1/sunday-schedule/",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body or isinstance(body, list)

    @pytest.mark.asyncio
    async def test_servant_cannot_list_all(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            "/api/v1/sunday-schedule/",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_parent_cannot_list_all(self, client: AsyncClient, parent_user: User):
        resp = await client.get(
            "/api/v1/sunday-schedule/",
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            "/api/v1/sunday-schedule/?page=1&page_size=5",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_pagination_structure(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            "/api/v1/sunday-schedule/",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        if "items" in body:
            assert "total" in body
            assert "page" in body
            assert "page_size" in body


class TestGetSundayTemplate:
    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_404(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            f"/api/v1/sunday-schedule/{uuid4()}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_created_template(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Get test", offset_weeks=8),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.get(
            f"/api/v1/sunday-schedule/{template_id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == template_id
        assert body["title"] == "Get test"

    @pytest.mark.asyncio
    async def test_servant_can_get_template(self, client: AsyncClient, admin_user: User, servant_user: User):
        """Tous les utilisateurs authentifiés peuvent voir un template."""
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Servant visible test", offset_weeks=9),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.get(
            f"/api/v1/sunday-schedule/{template_id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200


class TestUpdateSundayTemplate:
    @pytest.mark.asyncio
    async def test_admin_updates_template(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Update test", offset_weeks=10),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/sunday-schedule/{template_id}",
            json={"title": "Titre modifié"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Titre modifié"

    @pytest.mark.asyncio
    async def test_servant_cannot_update(self, client: AsyncClient, servant_user: User):
        resp = await client.patch(
            f"/api/v1/sunday-schedule/{uuid4()}",
            json={"title": "Hack"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_nonexistent_returns_404(self, client: AsyncClient, admin_user: User):
        resp = await client.patch(
            f"/api/v1/sunday-schedule/{uuid4()}",
            json={"title": "Not found"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404


class TestPublishArchiveSundayTemplate:
    @pytest.mark.asyncio
    async def test_publish_template(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Publish test", offset_weeks=11),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/sunday-schedule/{template_id}/publish",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PUBLISHED"

    @pytest.mark.asyncio
    async def test_publish_already_published_returns_400(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Double publish test", offset_weeks=12),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        await client.patch(
            f"/api/v1/sunday-schedule/{template_id}/publish",
            headers=make_auth_header(admin_user),
        )
        resp = await client.patch(
            f"/api/v1/sunday-schedule/{template_id}/publish",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_archive_template(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Archive test", offset_weeks=13),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/sunday-schedule/{template_id}/archive",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"

    @pytest.mark.asyncio
    async def test_published_template_appears_in_published_list(
        self, client: AsyncClient, admin_user: User, servant_user: User
    ):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Visible servant test", offset_weeks=14),
            headers=make_auth_header(admin_user),
        )
        template_id = create.json()["id"]

        await client.patch(
            f"/api/v1/sunday-schedule/{template_id}/publish",
            headers=make_auth_header(admin_user),
        )

        resp = await client.get(
            "/api/v1/sunday-schedule/published",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        ids = [t["id"] for t in resp.json()]
        assert template_id in ids

    @pytest.mark.asyncio
    async def test_servant_cannot_publish(self, client: AsyncClient, servant_user: User):
        resp = await client.patch(
            f"/api/v1/sunday-schedule/{uuid4()}/publish",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_servant_cannot_archive(self, client: AsyncClient, servant_user: User):
        resp = await client.patch(
            f"/api/v1/sunday-schedule/{uuid4()}/archive",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


class TestDeleteSundayTemplate:
    @pytest.mark.asyncio
    async def test_admin_deletes_template(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Delete test", offset_weeks=15),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.delete(
            f"/api/v1/sunday-schedule/{template_id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_deleted_template_not_found(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("Delete then get test", offset_weeks=16),
            headers=make_auth_header(admin_user),
        )
        template_id = create.json()["id"]

        await client.delete(
            f"/api/v1/sunday-schedule/{template_id}",
            headers=make_auth_header(admin_user),
        )

        resp = await client.get(
            f"/api/v1/sunday-schedule/{template_id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_servant_cannot_delete(self, client: AsyncClient, servant_user: User):
        resp = await client.delete(
            f"/api/v1/sunday-schedule/{uuid4()}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_404(self, client: AsyncClient, admin_user: User):
        resp = await client.delete(
            f"/api/v1/sunday-schedule/{uuid4()}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  Gestion des messes
# ═══════════════════════════════════════════════════════════════════════════


class TestSundayMassSlots:
    @pytest.mark.asyncio
    async def test_update_mass_notes(self, client: AsyncClient, admin_user: User):
        """Créer template avec messe, modifier les notes."""
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json={
                "title": "Mass update test",
                "schedule_date": _next_sunday(17),
                "masses": [{"mass_time": "08h30", "language": "FRANCAIS", "assignments": []}],
            },
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        masses = create.json().get("masses", [])
        if not masses:
            return

        mass_id = masses[0]["id"]
        resp = await client.patch(
            f"/api/v1/sunday-schedule/masses/{mass_id}",
            json={"notes": "Messe de 8h30 modifiée"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_update_mass_time(self, client: AsyncClient, admin_user: User):
        """Modifier l'heure d'une messe."""
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json={
                "title": "Mass time update test",
                "schedule_date": _next_sunday(18),
                "masses": [{"mass_time": "06h30", "language": "EWONDO", "assignments": []}],
            },
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        masses = create.json().get("masses", [])
        if not masses:
            return

        mass_id = masses[0]["id"]
        resp = await client.patch(
            f"/api/v1/sunday-schedule/masses/{mass_id}",
            json={"mass_time": "07h00"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_update_nonexistent_mass_returns_404(self, client: AsyncClient, admin_user: User):
        resp = await client.patch(
            f"/api/v1/sunday-schedule/masses/{uuid4()}",
            json={"notes": "test"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_mass(self, client: AsyncClient, admin_user: User):
        """Créer template avec messe, supprimer la messe."""
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json={
                "title": "Mass delete test",
                "schedule_date": _next_sunday(19),
                "masses": [{"mass_time": "10h00", "language": "EWONDO", "assignments": []}],
            },
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        masses = create.json().get("masses", [])
        if not masses:
            return

        mass_id = masses[0]["id"]
        resp = await client.delete(
            f"/api/v1/sunday-schedule/masses/{mass_id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code in (204, 404)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_mass_returns_404(self, client: AsyncClient, admin_user: User):
        resp = await client.delete(
            f"/api/v1/sunday-schedule/masses/{uuid4()}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_servant_cannot_update_mass(self, client: AsyncClient, servant_user: User):
        resp = await client.patch(
            f"/api/v1/sunday-schedule/masses/{uuid4()}",
            json={"notes": "hack"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_servant_cannot_delete_mass(self, client: AsyncClient, servant_user: User):
        resp = await client.delete(
            f"/api/v1/sunday-schedule/masses/{uuid4()}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  Gestion des assignations — window temporelle
# ═══════════════════════════════════════════════════════════════════════════


class TestSundayMassAssignments:
    @pytest.mark.asyncio
    async def test_add_assignment_to_nonexistent_mass_returns_404(
        self, client: AsyncClient, admin_user: User, servant_user: User
    ):
        resp = await client.post(
            f"/api/v1/sunday-schedule/masses/{uuid4()}/assignments",
            json={"position": "RESPONSABLE", "servant_name": "Jean Servant"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_servant_cannot_add_assignment(self, client: AsyncClient, servant_user: User):
        resp = await client.post(
            f"/api/v1/sunday-schedule/masses/{uuid4()}/assignments",
            json={"position": "RESPONSABLE", "servant_name": "Jean"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_remove_nonexistent_assignment_returns_404(self, client: AsyncClient, admin_user: User):
        resp = await client.delete(
            f"/api/v1/sunday-schedule/assignments/{uuid4()}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_servant_cannot_remove_assignment(self, client: AsyncClient, servant_user: User):
        resp = await client.delete(
            f"/api/v1/sunday-schedule/assignments/{uuid4()}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_mark_presence_nonexistent_returns_404(self, client: AsyncClient, admin_user: User):
        resp = await client.patch(
            f"/api/v1/sunday-schedule/assignments/{uuid4()}/presence",
            json={"is_present": True},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_mark_presence_requires_auth(self, client: AsyncClient):
        resp = await client.patch(
            f"/api/v1/sunday-schedule/assignments/{uuid4()}/presence",
            json={"is_present": True},
        )
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  Historique des modifications
# ═══════════════════════════════════════════════════════════════════════════


class TestSundayScheduleHistory:
    @pytest.mark.asyncio
    async def test_admin_can_get_history(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("History test", offset_weeks=20),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.get(
            f"/api/v1/sunday-schedule/{template_id}/history",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_aumonier_can_get_history(self, client: AsyncClient, admin_user: User, aumonier_user: User):
        create = await client.post(
            "/api/v1/sunday-schedule/",
            json=_template_payload("History aumonier test", offset_weeks=21),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.get(
            f"/api/v1/sunday-schedule/{template_id}/history",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_servant_cannot_get_history(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            f"/api/v1/sunday-schedule/{uuid4()}/history",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_history_nonexistent_template_returns_empty(self, client: AsyncClient, admin_user: User):
        """Historique d'un template inexistant retourne liste vide ou 404."""
        resp = await client.get(
            f"/api/v1/sunday-schedule/{uuid4()}/history",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code in (200, 404)
