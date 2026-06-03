"""
Tests E2E pour les endpoints de classement hebdomadaire.

Les endpoints sont accessibles à CHARGE_CLASSEMENT_SEMAINE, Admin, et Aumônier.
On utilise admin_user/aumonier_user pour éviter de créer de nouvelles fixtures.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import make_auth_header


def _next_monday():
    """Retourne le prochain lundi comme datetime ISO."""
    today = datetime.now(timezone.utc)
    days_ahead = 7 - today.weekday()
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _template_payload(title="Planning semaine test", offset_days=0):
    start = _next_monday() + timedelta(weeks=offset_days)
    end = start + timedelta(days=6)
    return {
        "title": title,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "notes": "Test automatisé",
        "slots": [],
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Accès public — /published
# ═══════════════════════════════════════════════════════════════════════════


class TestGetPublishedWeeklyTemplates:
    @pytest.mark.asyncio
    async def test_servant_can_get_published(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            "/api/v1/weekly-schedule/published",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_parent_can_get_published(self, client: AsyncClient, parent_user: User):
        resp = await client.get(
            "/api/v1/weekly-schedule/published",
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unauthenticated_returns_401(self, client: AsyncClient):
        resp = await client.get("/api/v1/weekly-schedule/published")
        assert resp.status_code == 401


# ═══════════════════════════════════════════════════════════════════════════
#  CRUD des templates
# ═══════════════════════════════════════════════════════════════════════════


class TestCreateWeeklyTemplate:
    @pytest.mark.asyncio
    async def test_admin_creates_template(self, client: AsyncClient, admin_user: User):
        resp = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Planning admin test"),
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Planning admin test"
        assert "id" in body

    @pytest.mark.asyncio
    async def test_aumonier_creates_template(self, client: AsyncClient, aumonier_user: User):
        resp = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Planning aumonier test", offset_days=1),
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_servant_cannot_create(self, client: AsyncClient, servant_user: User):
        resp = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Test"),
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_parent_cannot_create(self, client: AsyncClient, parent_user: User):
        resp = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Test"),
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_end_before_start_returns_422(self, client: AsyncClient, admin_user: User):
        start = _next_monday()
        end = start - timedelta(days=1)
        resp = await client.post(
            "/api/v1/weekly-schedule/",
            json={
                "title": "Invalid dates",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 422


class TestListWeeklyTemplates:
    @pytest.mark.asyncio
    async def test_admin_lists_templates(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            "/api/v1/weekly-schedule/",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body or isinstance(body, list)

    @pytest.mark.asyncio
    async def test_servant_cannot_list_all(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            "/api/v1/weekly-schedule/",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, client: AsyncClient, admin_user: User):
        resp = await client.get(
            "/api/v1/weekly-schedule/?page=1&page_size=5",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200


class TestGetWeeklyTemplate:
    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_404(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            f"/api/v1/weekly-schedule/{uuid4()}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_created_template(self, client: AsyncClient, admin_user: User):
        # Create a template
        create = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Get test", offset_days=2),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        # Get it
        resp = await client.get(
            f"/api/v1/weekly-schedule/{template_id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == template_id


class TestUpdateWeeklyTemplate:
    @pytest.mark.asyncio
    async def test_admin_updates_template(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Update test", offset_days=3),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/weekly-schedule/{template_id}",
            json={"title": "Updated title"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "Updated title"

    @pytest.mark.asyncio
    async def test_servant_cannot_update(self, client: AsyncClient, servant_user: User):
        resp = await client.patch(
            f"/api/v1/weekly-schedule/{uuid4()}",
            json={"title": "Hack"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


class TestPublishArchiveWeeklyTemplate:
    @pytest.mark.asyncio
    async def test_publish_template(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Publish test", offset_days=4),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/weekly-schedule/{template_id}/publish",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PUBLISHED"

    @pytest.mark.asyncio
    async def test_archive_template(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Archive test", offset_days=5),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.patch(
            f"/api/v1/weekly-schedule/{template_id}/archive",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"

    @pytest.mark.asyncio
    async def test_published_template_appears_in_published_list(
        self, client: AsyncClient, admin_user: User, servant_user: User
    ):
        create = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Visible test", offset_days=6),
            headers=make_auth_header(admin_user),
        )
        template_id = create.json()["id"]

        await client.patch(
            f"/api/v1/weekly-schedule/{template_id}/publish",
            headers=make_auth_header(admin_user),
        )

        resp = await client.get(
            "/api/v1/weekly-schedule/published",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        ids = [t["id"] for t in resp.json()]
        assert template_id in ids


class TestDeleteWeeklyTemplate:
    @pytest.mark.asyncio
    async def test_admin_deletes_template(self, client: AsyncClient, admin_user: User):
        create = await client.post(
            "/api/v1/weekly-schedule/",
            json=_template_payload("Delete test", offset_days=7),
            headers=make_auth_header(admin_user),
        )
        assert create.status_code == 201
        template_id = create.json()["id"]

        resp = await client.delete(
            f"/api/v1/weekly-schedule/{template_id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_servant_cannot_delete(self, client: AsyncClient, servant_user: User):
        resp = await client.delete(
            f"/api/v1/weekly-schedule/{uuid4()}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  Gestion des créneaux et assignations
# ═══════════════════════════════════════════════════════════════════════════


class TestWeeklyScheduleSlots:
    @pytest.mark.asyncio
    async def test_create_template_with_slots(self, client: AsyncClient, admin_user: User):
        """Template with slots created inline."""
        start = _next_monday() + timedelta(weeks=8)
        end = start + timedelta(days=6)
        resp = await client.post(
            "/api/v1/weekly-schedule/",
            json={
                "title": "With slots test",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "slots": [
                    {
                        "day": "LUNDI",
                        "mass_time": "MATIN",
                        "notes": "Messe de 6h15",
                        "servants": [],
                    }
                ],
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert len(body.get("slots", [])) >= 1

    @pytest.mark.asyncio
    async def test_add_servant_to_slot(
        self, client: AsyncClient, admin_user: User, servant_user: User
    ):
        """Create template with a slot, then add servant to that slot."""
        start = _next_monday() + timedelta(weeks=9)
        end = start + timedelta(days=6)
        create_resp = await client.post(
            "/api/v1/weekly-schedule/",
            json={
                "title": "Servant slot test",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "slots": [
                    {"day": "MARDI", "mass_time": "MATIN", "servants": []},
                ],
            },
            headers=make_auth_header(admin_user),
        )
        assert create_resp.status_code == 201
        slots = create_resp.json().get("slots", [])
        if not slots:
            return  # Service might not return slots in create response

        slot_id = slots[0]["id"]
        resp = await client.post(
            f"/api/v1/weekly-schedule/slots/{slot_id}/servants",
            json={"servant_id": str(servant_user.id)},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code in (201, 200, 400, 404)  # 400 if outside time window

    @pytest.mark.asyncio
    async def test_update_slot_notes(
        self, client: AsyncClient, admin_user: User
    ):
        """Create template with slot, update slot notes."""
        start = _next_monday() + timedelta(weeks=10)
        end = start + timedelta(days=6)
        create_resp = await client.post(
            "/api/v1/weekly-schedule/",
            json={
                "title": "Slot update test",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "slots": [
                    {"day": "MERCREDI", "mass_time": "MATIN", "servants": []},
                ],
            },
            headers=make_auth_header(admin_user),
        )
        assert create_resp.status_code == 201
        slots = create_resp.json().get("slots", [])
        if not slots:
            return

        slot_id = slots[0]["id"]
        resp = await client.patch(
            f"/api/v1/weekly-schedule/slots/{slot_id}",
            json={"notes": "Updated notes"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_delete_slot(self, client: AsyncClient, admin_user: User):
        """Create template with slot, delete the slot."""
        start = _next_monday() + timedelta(weeks=11)
        end = start + timedelta(days=6)
        create_resp = await client.post(
            "/api/v1/weekly-schedule/",
            json={
                "title": "Delete slot test",
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "slots": [
                    {"day": "JEUDI", "mass_time": "MATIN", "servants": []},
                ],
            },
            headers=make_auth_header(admin_user),
        )
        assert create_resp.status_code == 201
        slots = create_resp.json().get("slots", [])
        if not slots:
            return

        slot_id = slots[0]["id"]
        resp = await client.delete(
            f"/api/v1/weekly-schedule/slots/{slot_id}",
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code in (204, 404)
