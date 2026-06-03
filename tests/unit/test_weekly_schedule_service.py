"""
Unit tests for WeeklyScheduleService.
Covers all CRUD methods, status transitions, slot management, and error paths.
"""

from datetime import datetime, timezone
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.services.weekly_schedule_service import (
    WeeklyScheduleService,
    is_within_mass_window,
    parse_mass_time,
)
from src.core.entities.user import User, UserRole
from src.core.entities.weekly_schedule import (
    MassTime,
    ScheduleStatus,
    SlotServantAssignment,
    WeekDay,
    WeeklyScheduleSlot,
    WeeklyScheduleTemplate,
)
from src.presentation.schemas.weekly_schedule import (
    SlotServantCreate,
    WeeklyScheduleSlotCreate,
    WeeklyScheduleSlotUpdate,
    WeeklyScheduleTemplateCreate,
    WeeklyScheduleTemplateUpdate,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def _make_template(
    status: ScheduleStatus = ScheduleStatus.DRAFT,
    start_date: datetime = datetime(2026, 2, 9, tzinfo=timezone.utc),  # Monday
    end_date: datetime = datetime(2026, 2, 15, tzinfo=timezone.utc),   # Sunday
) -> WeeklyScheduleTemplate:
    return WeeklyScheduleTemplate(
        id=uuid4(),
        title="Classement Test",
        start_date=start_date,
        end_date=end_date,
        status=status,
        created_by=uuid4(),
    )


def _make_slot(template: WeeklyScheduleTemplate, day: WeekDay = WeekDay.LUNDI) -> WeeklyScheduleSlot:
    return WeeklyScheduleSlot(
        id=uuid4(),
        template_id=template.id,
        day=day,
        mass_time=MassTime.MATIN,
    )


def _make_assignment(slot: WeeklyScheduleSlot) -> SlotServantAssignment:
    return SlotServantAssignment(
        id=uuid4(),
        slot_id=slot.id,
        servant_name="Jean Test",
        assigned_by=uuid4(),
    )


def _enriched_template(tpl: WeeklyScheduleTemplate) -> dict:
    return {
        "id": tpl.id,
        "title": tpl.title,
        "start_date": tpl.start_date,
        "end_date": tpl.end_date,
        "status": tpl.status,
        "notes": tpl.notes,
        "created_by": tpl.created_by,
        "updated_by": tpl.updated_by,
        "creator_first_name": None,
        "creator_last_name": None,
        "slots": [],
        "created_at": tpl.created_at,
        "updated_at": tpl.updated_at,
    }


def _enriched_slot(slot: WeeklyScheduleSlot) -> dict:
    return {
        "id": slot.id,
        "template_id": slot.template_id,
        "day": slot.day,
        "mass_time": slot.mass_time,
        "notes": slot.notes,
        "servants": [],
        "created_at": slot.created_at,
        "updated_at": slot.updated_at,
    }


def _enriched_assignment(a: SlotServantAssignment) -> dict:
    return {
        "id": a.id,
        "slot_id": a.slot_id,
        "servant_id": a.servant_id,
        "servant_name": a.servant_name,
        "servant_first_name": None,
        "servant_last_name": None,
        "notes": a.notes,
        "assigned_by": a.assigned_by,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


def _summary(tpl: WeeklyScheduleTemplate) -> dict:
    return {
        "id": tpl.id,
        "title": tpl.title,
        "start_date": tpl.start_date,
        "end_date": tpl.end_date,
        "status": tpl.status,
        "total_slots": 0,
        "filled_slots": 0,
        "total_servants": 0,
        "created_by": tpl.created_by,
        "creator_first_name": None,
        "creator_last_name": None,
        "created_at": tpl.created_at,
    }


def _make_svc(schedule_repo=None, user_repo=None) -> WeeklyScheduleService:
    return WeeklyScheduleService(
        schedule_repository=schedule_repo or AsyncMock(),
        user_repository=user_repo or AsyncMock(),
    )


# ── parse_mass_time and is_within_mass_window ──────────────────────────────


def test_parse_mass_time_standard():
    assert parse_mass_time("06h15") == (6, 15)
    assert parse_mass_time("12h00") == (12, 0)
    assert parse_mass_time("18h00") == (18, 0)


def test_is_within_mass_window_matin_enum():
    """MATIN enum alias maps to 06h15."""
    slot_date = datetime(2026, 2, 9)
    assert is_within_mass_window(slot_date, MassTime.MATIN, slot_date.replace(hour=5, minute=45))
    assert is_within_mass_window(slot_date, MassTime.MATIN, slot_date.replace(hour=8, minute=14))
    assert not is_within_mass_window(slot_date, MassTime.MATIN, slot_date.replace(hour=9, minute=0))


def test_is_within_mass_window_midi_soir():
    slot_date = datetime(2026, 2, 9)
    assert is_within_mass_window(slot_date, "MIDI", slot_date.replace(hour=11, minute=30))
    assert is_within_mass_window(slot_date, "SOIR", slot_date.replace(hour=17, minute=30))
    assert not is_within_mass_window(slot_date, "SOIR", slot_date.replace(hour=21, minute=0))


def test_is_within_mass_window():
    """Keep original test — validates all boundary cases."""
    slot_date = datetime(2026, 2, 9, tzinfo=timezone.utc)
    mass_time = "06h15"

    assert is_within_mass_window(slot_date, mass_time, slot_date.replace(hour=5, minute=45)) is True
    assert is_within_mass_window(slot_date, mass_time, slot_date.replace(hour=6, minute=45)) is True
    assert is_within_mass_window(slot_date, mass_time, slot_date.replace(hour=7, minute=45)) is True
    assert is_within_mass_window(slot_date, mass_time, slot_date.replace(hour=3, minute=0)) is False


# ── Create template ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_template_success():
    schedule_repo = AsyncMock()
    template = _make_template()
    schedule_repo.create_template.return_value = template
    schedule_repo.enrich_template.return_value = _enriched_template(template)

    svc = _make_svc(schedule_repo=schedule_repo)
    data = WeeklyScheduleTemplateCreate(
        title=template.title,
        start_date=template.start_date,
        end_date=template.end_date,
        slots=[],
    )
    result = await svc.create_template(data, uuid4())

    assert result.title == template.title
    schedule_repo.create_template.assert_called_once()


@pytest.mark.asyncio
async def test_create_template_with_slot_servant_not_found_raises_404():
    schedule_repo = AsyncMock()
    user_repo = AsyncMock()
    template = _make_template()
    slot = _make_slot(template)
    schedule_repo.create_template.return_value = template
    schedule_repo.create_slot.return_value = slot
    user_repo.get.return_value = None

    svc = _make_svc(schedule_repo=schedule_repo, user_repo=user_repo)
    data = WeeklyScheduleTemplateCreate(
        title=template.title,
        start_date=template.start_date,
        end_date=template.end_date,
        slots=[
            WeeklyScheduleSlotCreate(
                day=WeekDay.LUNDI,
                mass_time=MassTime.MATIN,
                servants=[SlotServantCreate(servant_id=uuid4())],
            )
        ],
    )

    with pytest.raises(HTTPException) as exc:
        await svc.create_template(data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_template_with_slot_non_servant_raises_400():
    schedule_repo = AsyncMock()
    user_repo = AsyncMock()
    template = _make_template()
    slot = _make_slot(template)
    user = MagicMock(spec=User)
    user.role = UserRole.PARENT
    user.first_name = "Alice"
    user.last_name = "Parent"
    schedule_repo.create_template.return_value = template
    schedule_repo.create_slot.return_value = slot
    user_repo.get.return_value = user

    svc = _make_svc(schedule_repo=schedule_repo, user_repo=user_repo)
    data = WeeklyScheduleTemplateCreate(
        title=template.title,
        start_date=template.start_date,
        end_date=template.end_date,
        slots=[
            WeeklyScheduleSlotCreate(
                day=WeekDay.LUNDI,
                mass_time=MassTime.MATIN,
                servants=[SlotServantCreate(servant_id=uuid4())],
            )
        ],
    )

    with pytest.raises(HTTPException) as exc:
        await svc.create_template(data, uuid4())
    assert exc.value.status_code == 400


# ── Get template ───────────────────────────────────────────────────────────


class TestGetTemplate:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_template.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.get_template(uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_enriched_response(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        schedule_repo.get_template.return_value = template
        schedule_repo.enrich_template.return_value = _enriched_template(template)

        svc = _make_svc(schedule_repo=schedule_repo)
        result = await svc.get_template(template.id)

        assert result.id == template.id
        assert result.title == template.title


# ── List templates ─────────────────────────────────────────────────────────


class TestListTemplates:
    @pytest.mark.asyncio
    async def test_returns_empty_paginated_with_total_pages_one(self):
        schedule_repo = AsyncMock()
        schedule_repo.list_templates.return_value = ([], 0)

        svc = _make_svc(schedule_repo=schedule_repo)
        result = await svc.list_templates()

        assert result.total == 0
        assert result.items == []
        assert result.total_pages == 1

    @pytest.mark.asyncio
    async def test_returns_items_list(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        schedule_repo.list_templates.return_value = ([template], 1)
        schedule_repo.get_template_summary.return_value = _summary(template)

        svc = _make_svc(schedule_repo=schedule_repo)
        result = await svc.list_templates()

        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].id == template.id

    @pytest.mark.asyncio
    async def test_pagination_math(self):
        schedule_repo = AsyncMock()
        templates = [_make_template() for _ in range(3)]
        schedule_repo.list_templates.return_value = (templates, 25)
        schedule_repo.get_template_summary.side_effect = [_summary(t) for t in templates]

        svc = _make_svc(schedule_repo=schedule_repo)
        result = await svc.list_templates(page=2, page_size=10)

        assert result.total == 25
        assert result.total_pages == 3
        assert result.page == 2
        assert result.page_size == 10


# ── Get published templates ────────────────────────────────────────────────


class TestGetPublishedTemplates:
    @pytest.mark.asyncio
    async def test_returns_empty_list(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_published_templates.return_value = []

        svc = _make_svc(schedule_repo=schedule_repo)
        result = await svc.get_published_templates()
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_summaries_for_published(self):
        schedule_repo = AsyncMock()
        template = _make_template(status=ScheduleStatus.PUBLISHED)
        schedule_repo.get_published_templates.return_value = [template]
        schedule_repo.get_template_summary.return_value = _summary(template)

        svc = _make_svc(schedule_repo=schedule_repo)
        result = await svc.get_published_templates()

        assert len(result) == 1
        assert result[0].id == template.id


# ── Update template ────────────────────────────────────────────────────────


class TestUpdateTemplate:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_template.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.update_template(uuid4(), WeeklyScheduleTemplateUpdate(), uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_updates_title(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        schedule_repo.get_template.return_value = template
        schedule_repo.update_template.return_value = template
        schedule_repo.enrich_template.return_value = _enriched_template(template)

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.update_template(template.id, WeeklyScheduleTemplateUpdate(title="Nouveau"), uuid4())

        assert template.title == "Nouveau"
        schedule_repo.update_template.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_none_fields(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        original_title = template.title
        schedule_repo.get_template.return_value = template
        schedule_repo.update_template.return_value = template
        schedule_repo.enrich_template.return_value = _enriched_template(template)

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.update_template(template.id, WeeklyScheduleTemplateUpdate(notes="Note seule"), uuid4())

        assert template.title == original_title

    @pytest.mark.asyncio
    async def test_updates_status_and_notes(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        schedule_repo.get_template.return_value = template
        schedule_repo.update_template.return_value = template
        schedule_repo.enrich_template.return_value = _enriched_template(template)

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.update_template(
            template.id,
            WeeklyScheduleTemplateUpdate(status=ScheduleStatus.PUBLISHED, notes="Publié"),
            uuid4(),
        )

        assert template.status == ScheduleStatus.PUBLISHED
        assert template.notes == "Publié"


# ── Publish template ───────────────────────────────────────────────────────


class TestPublishTemplate:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_template.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.publish_template(uuid4(), uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_already_published(self):
        schedule_repo = AsyncMock()
        template = _make_template(status=ScheduleStatus.PUBLISHED)
        schedule_repo.get_template.return_value = template

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.publish_template(template.id, uuid4())
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_sets_published_status(self):
        schedule_repo = AsyncMock()
        template = _make_template(status=ScheduleStatus.DRAFT)
        schedule_repo.get_template.return_value = template
        schedule_repo.update_template.return_value = template
        schedule_repo.enrich_template.return_value = _enriched_template(template)

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.publish_template(template.id, uuid4())

        assert template.status == ScheduleStatus.PUBLISHED
        schedule_repo.update_template.assert_called_once()


# ── Archive template ───────────────────────────────────────────────────────


class TestArchiveTemplate:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_template.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.archive_template(uuid4(), uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_sets_archived_status(self):
        schedule_repo = AsyncMock()
        template = _make_template(status=ScheduleStatus.PUBLISHED)
        schedule_repo.get_template.return_value = template
        schedule_repo.update_template.return_value = template
        schedule_repo.enrich_template.return_value = _enriched_template(template)

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.archive_template(template.id, uuid4())

        assert template.status == ScheduleStatus.ARCHIVED
        schedule_repo.update_template.assert_called_once()


# ── Delete template ────────────────────────────────────────────────────────


class TestDeleteTemplate:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_template.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.delete_template(uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_500_when_repo_returns_false(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        schedule_repo.get_template.return_value = template
        schedule_repo.delete_template.return_value = False

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.delete_template(template.id)
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_success(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        schedule_repo.get_template.return_value = template
        schedule_repo.delete_template.return_value = True

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.delete_template(template.id)
        schedule_repo.delete_template.assert_called_once_with(template.id)


# ── Update slot ────────────────────────────────────────────────────────────


class TestUpdateSlot:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_slot.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.update_slot(uuid4(), WeeklyScheduleSlotUpdate())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_updates_notes(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        slot = _make_slot(template)
        schedule_repo.get_slot.return_value = slot
        schedule_repo.update_slot.return_value = slot
        schedule_repo.enrich_slot.return_value = _enriched_slot(slot)

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.update_slot(slot.id, WeeklyScheduleSlotUpdate(notes="Nouvelle note"))

        assert slot.notes == "Nouvelle note"
        schedule_repo.update_slot.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_none_notes(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        slot = _make_slot(template)
        slot.notes = "Note originale"
        schedule_repo.get_slot.return_value = slot
        schedule_repo.update_slot.return_value = slot
        schedule_repo.enrich_slot.return_value = _enriched_slot(slot)

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.update_slot(slot.id, WeeklyScheduleSlotUpdate(notes=None))

        assert slot.notes == "Note originale"


# ── Delete slot ────────────────────────────────────────────────────────────


class TestDeleteSlot:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_slot.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.delete_slot(uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_500_when_repo_returns_false(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        slot = _make_slot(template)
        schedule_repo.get_slot.return_value = slot
        schedule_repo.delete_slot.return_value = False

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.delete_slot(slot.id)
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_success(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        slot = _make_slot(template)
        schedule_repo.get_slot.return_value = slot
        schedule_repo.delete_slot.return_value = True

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.delete_slot(slot.id)
        schedule_repo.delete_slot.assert_called_once_with(slot.id)


# ── Add servant to slot ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_servant_to_slot_outside_window():
    """Original test — outside time window → 400."""
    schedule_repo = AsyncMock()
    template = _make_template(
        start_date=datetime(2026, 2, 9, tzinfo=timezone.utc),
        end_date=datetime(2026, 2, 15, tzinfo=timezone.utc),
    )
    slot = _make_slot(template, day=WeekDay.LUNDI)
    schedule_repo.get_slot.return_value = slot
    schedule_repo.get_template.return_value = template

    svc = _make_svc(schedule_repo=schedule_repo)
    with pytest.raises(HTTPException) as exc:
        await svc.add_servant_to_slot(slot.id, SlotServantCreate(servant_name="Jean"), uuid4())
    assert exc.value.status_code == 400
    assert "fenêtre" in exc.value.detail


class TestAddServantToSlot:
    @pytest.mark.asyncio
    async def test_raises_404_when_slot_not_found(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_slot.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.add_servant_to_slot(uuid4(), SlotServantCreate(servant_name="Jean"), uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_when_template_not_found(self):
        schedule_repo = AsyncMock()
        template = _make_template()
        slot = _make_slot(template)
        schedule_repo.get_slot.return_value = slot
        schedule_repo.get_template.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.add_servant_to_slot(slot.id, SlotServantCreate(servant_name="Jean"), uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_day_not_in_period(self):
        """Template covers Mon-Fri, slot.day=SAMEDI → day not found → 400."""
        schedule_repo = AsyncMock()
        template = _make_template(
            start_date=datetime(2026, 2, 9),   # Monday
            end_date=datetime(2026, 2, 13),    # Friday
        )
        slot = _make_slot(template, day=WeekDay.SAMEDI)
        schedule_repo.get_slot.return_value = slot
        schedule_repo.get_template.return_value = template

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.add_servant_to_slot(slot.id, SlotServantCreate(servant_name="Jean"), uuid4())
        assert exc.value.status_code == 400
        assert "n'existe pas" in exc.value.detail

    @pytest.mark.asyncio
    async def test_raises_404_when_servant_user_not_found(self):
        """Within window, servant_id provided but user doesn't exist → 404."""
        import unittest.mock as mock

        schedule_repo = AsyncMock()
        user_repo = AsyncMock()
        template = _make_template(
            start_date=datetime(2026, 2, 9),
            end_date=datetime(2026, 2, 15),
        )
        slot = _make_slot(template, day=WeekDay.LUNDI)
        schedule_repo.get_slot.return_value = slot
        schedule_repo.get_template.return_value = template
        user_repo.get.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo, user_repo=user_repo)
        with mock.patch(
            "src.application.services.weekly_schedule_service.is_within_mass_window",
            return_value=True,
        ):
            with pytest.raises(HTTPException) as exc:
                await svc.add_servant_to_slot(
                    slot.id,
                    SlotServantCreate(servant_id=uuid4()),
                    uuid4(),
                )
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_user_not_servant_role(self):
        """Within window, user found but not SERVANT role → 400."""
        import unittest.mock as mock

        schedule_repo = AsyncMock()
        user_repo = AsyncMock()
        template = _make_template(
            start_date=datetime(2026, 2, 9),
            end_date=datetime(2026, 2, 15),
        )
        slot = _make_slot(template, day=WeekDay.LUNDI)
        user = MagicMock(spec=User)
        user.role = UserRole.PARENT
        user.first_name = "Alice"
        user.last_name = "Parent"
        schedule_repo.get_slot.return_value = slot
        schedule_repo.get_template.return_value = template
        user_repo.get.return_value = user

        svc = _make_svc(schedule_repo=schedule_repo, user_repo=user_repo)
        with mock.patch(
            "src.application.services.weekly_schedule_service.is_within_mass_window",
            return_value=True,
        ):
            with pytest.raises(HTTPException) as exc:
                await svc.add_servant_to_slot(
                    slot.id,
                    SlotServantCreate(servant_id=uuid4()),
                    uuid4(),
                )
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_success_with_servant_name_only(self):
        """No servant_id, just name → skips user lookup, creates assignment."""
        import unittest.mock as mock

        schedule_repo = AsyncMock()
        template = _make_template(
            start_date=datetime(2026, 2, 9),
            end_date=datetime(2026, 2, 15),
        )
        slot = _make_slot(template, day=WeekDay.LUNDI)
        assignment = _make_assignment(slot)
        schedule_repo.get_slot.return_value = slot
        schedule_repo.get_template.return_value = template
        schedule_repo.create_assignment.return_value = assignment
        schedule_repo.enrich_assignment.return_value = _enriched_assignment(assignment)

        svc = _make_svc(schedule_repo=schedule_repo)
        with mock.patch(
            "src.application.services.weekly_schedule_service.is_within_mass_window",
            return_value=True,
        ):
            result = await svc.add_servant_to_slot(
                slot.id, SlotServantCreate(servant_name="Jean"), uuid4()
            )
        assert result.slot_id == slot.id
        schedule_repo.create_assignment.assert_called_once()


# ── Remove servant from slot ───────────────────────────────────────────────


class TestRemoveServantFromSlot:
    @pytest.mark.asyncio
    async def test_raises_404_when_assignment_not_found(self):
        schedule_repo = AsyncMock()
        schedule_repo.get_assignment.return_value = None

        svc = _make_svc(schedule_repo=schedule_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.remove_servant_from_slot(uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_outside_window(self):
        """Slot and template found, current time outside mass window → 400."""
        schedule_repo = AsyncMock()
        template = _make_template(
            start_date=datetime(2026, 2, 9, tzinfo=timezone.utc),
            end_date=datetime(2026, 2, 15, tzinfo=timezone.utc),
        )
        slot = _make_slot(template, day=WeekDay.LUNDI)
        assignment = _make_assignment(slot)
        schedule_repo.get_assignment.return_value = assignment
        schedule_repo.get_slot.return_value = slot
        schedule_repo.get_template.return_value = template

        svc = _make_svc(schedule_repo=schedule_repo)
        # No mock → current time (2026-06-01) is outside Feb 9 06h15 window
        with pytest.raises(HTTPException) as exc:
            await svc.remove_servant_from_slot(assignment.id)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_500_when_delete_fails(self):
        import unittest.mock as mock

        schedule_repo = AsyncMock()
        template = _make_template(
            start_date=datetime(2026, 2, 9),
            end_date=datetime(2026, 2, 15),
        )
        slot = _make_slot(template, day=WeekDay.LUNDI)
        assignment = _make_assignment(slot)
        schedule_repo.get_assignment.return_value = assignment
        schedule_repo.get_slot.return_value = slot
        schedule_repo.get_template.return_value = template
        schedule_repo.delete_assignment.return_value = False

        svc = _make_svc(schedule_repo=schedule_repo)
        with mock.patch(
            "src.application.services.weekly_schedule_service.is_within_mass_window",
            return_value=True,
        ):
            with pytest.raises(HTTPException) as exc:
                await svc.remove_servant_from_slot(assignment.id)
        assert exc.value.status_code == 500

    @pytest.mark.asyncio
    async def test_success_when_within_window(self):
        import unittest.mock as mock

        schedule_repo = AsyncMock()
        template = _make_template(
            start_date=datetime(2026, 2, 9),
            end_date=datetime(2026, 2, 15),
        )
        slot = _make_slot(template, day=WeekDay.LUNDI)
        assignment = _make_assignment(slot)
        schedule_repo.get_assignment.return_value = assignment
        schedule_repo.get_slot.return_value = slot
        schedule_repo.get_template.return_value = template
        schedule_repo.delete_assignment.return_value = True

        svc = _make_svc(schedule_repo=schedule_repo)
        with mock.patch(
            "src.application.services.weekly_schedule_service.is_within_mass_window",
            return_value=True,
        ):
            await svc.remove_servant_from_slot(assignment.id)
        schedule_repo.delete_assignment.assert_called_once_with(assignment.id)

    @pytest.mark.asyncio
    async def test_skips_window_check_when_slot_none(self):
        """Slot not found → window check skipped → deletion proceeds."""
        schedule_repo = AsyncMock()
        template = _make_template()
        slot = _make_slot(template)
        assignment = _make_assignment(slot)
        schedule_repo.get_assignment.return_value = assignment
        schedule_repo.get_slot.return_value = None
        schedule_repo.delete_assignment.return_value = True

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.remove_servant_from_slot(assignment.id)
        schedule_repo.delete_assignment.assert_called_once_with(assignment.id)

    @pytest.mark.asyncio
    async def test_skips_window_check_when_template_none(self):
        """Template not found → window check skipped → deletion proceeds."""
        schedule_repo = AsyncMock()
        template = _make_template()
        slot = _make_slot(template)
        assignment = _make_assignment(slot)
        schedule_repo.get_assignment.return_value = assignment
        schedule_repo.get_slot.return_value = slot
        schedule_repo.get_template.return_value = None
        schedule_repo.delete_assignment.return_value = True

        svc = _make_svc(schedule_repo=schedule_repo)
        await svc.remove_servant_from_slot(assignment.id)
        schedule_repo.delete_assignment.assert_called_once_with(assignment.id)
