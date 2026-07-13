"""Unit tests for SundayScheduleService."""

from datetime import datetime, timezone
from unittest import mock
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.sunday_schedule_service import (
    SundayScheduleService,
    is_within_mass_window,
    parse_mass_time,
)
from src.core.entities.sunday_schedule import (
    LiturgicalPosition,
    MassLanguage,
    MassType,
    SundayMassAssignment,
    SundayMassSlot,
    SundayScheduleStatus,
    SundayScheduleTemplate,
)
from src.core.entities.user import User, UserRole
from src.presentation.schemas.sunday_schedule import (
    GenerateExceptionalScheduleRequest,
    GenerateOrdinaryScheduleRequest,
    MassTimePreset,
    SundayMassAssignmentCreate,
    SundayMassSlotCreate,
    SundayMassSlotUpdate,
    SundayScheduleTemplateCreate,
    SundayScheduleTemplateUpdate,
)

NOW = datetime(2026, 6, 1, 10, 0, 0)
SCHEDULE_DATE = datetime(2026, 6, 8, 0, 0, 0)  # next Sunday


# ── Factories ──────────────────────────────────────────────────────────────


def _make_template(
    status=SundayScheduleStatus.DRAFT,
    schedule_date=SCHEDULE_DATE,
    **kwargs,
) -> SundayScheduleTemplate:
    return SundayScheduleTemplate(
        id=uuid4(),
        title="Dimanche Ordinaire",
        schedule_date=schedule_date,
        mass_type=MassType.ORDINAIRE,
        is_exceptional=False,
        status=status,
        created_by=uuid4(),
        created_at=NOW,
        updated_at=NOW,
        **kwargs,
    )


def _make_mass(template_id=None, **kwargs) -> SundayMassSlot:
    return SundayMassSlot(
        id=uuid4(),
        template_id=template_id or uuid4(),
        mass_time="08h30",
        language=MassLanguage.FRANCAIS,
        created_at=NOW,
        updated_at=NOW,
        **kwargs,
    )


def _make_assignment(mass_slot_id=None, **kwargs) -> SundayMassAssignment:
    return SundayMassAssignment(
        id=uuid4(),
        mass_slot_id=mass_slot_id or uuid4(),
        position=LiturgicalPosition.ACOLYTE_1,
        assigned_by=uuid4(),
        created_at=NOW,
        updated_at=NOW,
        **kwargs,
    )


def _make_user(role=UserRole.SERVANT) -> User:
    return User(
        id=uuid4(),
        first_name="Jean",
        last_name="Pierre",
        email="jean@test.com",
        hashed_password="x",
        role=role,
        created_at=NOW,
        updated_at=NOW,
    )


def _enriched_template(tpl: SundayScheduleTemplate) -> dict:
    return {
        "id": tpl.id,
        "title": tpl.title,
        "schedule_date": tpl.schedule_date,
        "mass_type": tpl.mass_type,
        "is_exceptional": tpl.is_exceptional,
        "status": tpl.status,
        "notes": tpl.notes,
        "created_by": tpl.created_by,
        "updated_by": tpl.updated_by,
        "creator_first_name": None,
        "creator_last_name": None,
        "masses": [],
        "created_at": tpl.created_at,
        "updated_at": tpl.updated_at,
    }


def _enriched_mass(mass: SundayMassSlot) -> dict:
    return {
        "id": mass.id,
        "template_id": mass.template_id,
        "mass_time": mass.mass_time,
        "language": mass.language,
        "notes": mass.notes,
        "assignments": [],
        "created_at": mass.created_at,
        "updated_at": mass.updated_at,
    }


def _enriched_assignment(a: SundayMassAssignment) -> dict:
    return {
        "id": a.id,
        "mass_slot_id": a.mass_slot_id,
        "position": a.position,
        "servant_id": a.servant_id,
        "servant_name": a.servant_name,
        "servant_first_name": None,
        "servant_last_name": None,
        "is_present": a.is_present,
        "presence_marked_by": a.presence_marked_by,
        "presence_marked_by_name": None,
        "presence_marked_at": a.presence_marked_at,
        "notes": a.notes,
        "assigned_by": a.assigned_by,
        "assigned_by_name": None,
        "last_modified_by": a.last_modified_by,
        "last_modified_by_name": None,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


def _summary(tpl: SundayScheduleTemplate) -> dict:
    return {
        "id": tpl.id,
        "title": tpl.title,
        "schedule_date": tpl.schedule_date,
        "mass_type": tpl.mass_type,
        "is_exceptional": tpl.is_exceptional,
        "status": tpl.status,
        "total_masses": 0,
        "total_positions": 0,
        "filled_positions": 0,
        "created_by": tpl.created_by,
        "creator_first_name": None,
        "creator_last_name": None,
        "created_at": tpl.created_at,
    }


def _make_svc(schedule_repo=None, user_repo=None) -> SundayScheduleService:
    if schedule_repo is None:
        schedule_repo = MagicMock()
        schedule_repo.create_template = AsyncMock()
        schedule_repo.get_template = AsyncMock(return_value=None)
        schedule_repo.enrich_template = AsyncMock(return_value={})
        schedule_repo.update_template = AsyncMock()
        schedule_repo.delete_template = AsyncMock(return_value=True)
        schedule_repo.list_templates = AsyncMock(return_value=([], 0))
        schedule_repo.get_published_templates = AsyncMock(return_value=[])
        schedule_repo.get_template_summary = AsyncMock(return_value={})
        schedule_repo.create_mass = AsyncMock()
        schedule_repo.create_masses_batch = AsyncMock()
        schedule_repo.get_mass = AsyncMock(return_value=None)
        schedule_repo.update_mass = AsyncMock()
        schedule_repo.delete_mass = AsyncMock(return_value=True)
        schedule_repo.enrich_mass = AsyncMock(return_value={})
        schedule_repo.create_assignment = AsyncMock()
        schedule_repo.create_assignments_batch = AsyncMock()
        schedule_repo.get_assignment = AsyncMock(return_value=None)
        schedule_repo.update_assignment = AsyncMock()
        schedule_repo.delete_assignment = AsyncMock(return_value=True)
        schedule_repo.enrich_assignment = AsyncMock(return_value={})
        schedule_repo.create_modification_log = AsyncMock()
        schedule_repo.get_template_modification_logs = AsyncMock(return_value=[])
    if user_repo is None:
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=None)
    return SundayScheduleService(schedule_repo, user_repo)


# ── parse_mass_time ────────────────────────────────────────────────────────


def test_parse_mass_time_standard():
    assert parse_mass_time("06h30") == (6, 30)


def test_parse_mass_time_zero_minutes():
    assert parse_mass_time("17h00") == (17, 0)


def test_parse_mass_time_uppercase():
    assert parse_mass_time("08H30") == (8, 30)


# ── is_within_mass_window ──────────────────────────────────────────────────


def test_is_within_mass_window_inside():
    schedule_date = datetime(2026, 6, 8)
    # mass at 08h30 → window 07h30 to 10h30
    current = datetime(2026, 6, 8, 9, 0)
    assert is_within_mass_window(schedule_date, "08h30", current) is True


def test_is_within_mass_window_before():
    schedule_date = datetime(2026, 6, 8)
    current = datetime(2026, 6, 8, 7, 0)  # 1h30 before mass
    assert is_within_mass_window(schedule_date, "08h30", current) is False


def test_is_within_mass_window_after():
    schedule_date = datetime(2026, 6, 8)
    current = datetime(2026, 6, 8, 11, 0)  # 2h30 after mass start
    assert is_within_mass_window(schedule_date, "08h30", current) is False


def test_is_within_mass_window_at_boundary_start():
    schedule_date = datetime(2026, 6, 8)
    current = datetime(2026, 6, 8, 7, 30)  # exactly 1h before
    assert is_within_mass_window(schedule_date, "08h30", current) is True


def test_is_within_mass_window_timezone_aware():
    schedule_date = datetime(2026, 6, 8, tzinfo=timezone.utc)
    current = datetime(2026, 6, 8, 9, 0, tzinfo=timezone.utc)
    assert is_within_mass_window(schedule_date, "08h30", current) is True


# ── create_template ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_template_no_masses():
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.create_template.return_value = tpl
    svc.schedule_repo.enrich_template.return_value = _enriched_template(tpl)

    data = SundayScheduleTemplateCreate(
        title="Dimanche Ordinaire",
        schedule_date=SCHEDULE_DATE,
        masses=[],
    )
    result = await svc.create_template(data, tpl.created_by)

    svc.schedule_repo.create_template.assert_called_once()
    assert result.id == tpl.id


@pytest.mark.asyncio
async def test_create_template_with_masses():
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    svc = _make_svc()
    svc.schedule_repo.create_template.return_value = tpl
    svc.schedule_repo.create_mass.return_value = mass
    svc.schedule_repo.enrich_template.return_value = _enriched_template(tpl)

    servant = _make_user(role=UserRole.SERVANT)
    svc.user_repo.get.return_value = servant

    mass_slot = SundayMassSlotCreate(
        mass_time="08h30",
        language=MassLanguage.FRANCAIS,
        assignments=[
            SundayMassAssignmentCreate(
                position=LiturgicalPosition.ACOLYTE_1,
                servant_id=servant.id,
                servant_name=None,
            )
        ],
    )
    data = SundayScheduleTemplateCreate(
        title="Dimanche",
        schedule_date=SCHEDULE_DATE,
        masses=[mass_slot],
    )
    result = await svc.create_template(data, tpl.created_by)

    svc.schedule_repo.create_mass.assert_called_once()
    svc.schedule_repo.create_assignments_batch.assert_called_once()
    assert result.id == tpl.id


@pytest.mark.asyncio
async def test_create_template_servant_not_found():
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    svc = _make_svc()
    svc.schedule_repo.create_template.return_value = tpl
    svc.schedule_repo.create_mass.return_value = mass
    svc.user_repo.get.return_value = None  # servant not found

    mass_slot = SundayMassSlotCreate(
        mass_time="08h30",
        language=MassLanguage.FRANCAIS,
        assignments=[
            SundayMassAssignmentCreate(
                position=LiturgicalPosition.ACOLYTE_1,
                servant_id=uuid4(),
                servant_name=None,
            )
        ],
    )
    data = SundayScheduleTemplateCreate(
        title="Dimanche",
        schedule_date=SCHEDULE_DATE,
        masses=[mass_slot],
    )
    with pytest.raises(Exception) as exc:
        await svc.create_template(data, tpl.created_by)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_template_not_servant_role():
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    svc = _make_svc()
    svc.schedule_repo.create_template.return_value = tpl
    svc.schedule_repo.create_mass.return_value = mass

    admin_user = _make_user(role=UserRole.ADMIN)
    svc.user_repo.get.return_value = admin_user

    mass_slot = SundayMassSlotCreate(
        mass_time="08h30",
        language=MassLanguage.FRANCAIS,
        assignments=[
            SundayMassAssignmentCreate(
                position=LiturgicalPosition.ACOLYTE_1,
                servant_id=admin_user.id,
                servant_name=None,
            )
        ],
    )
    data = SundayScheduleTemplateCreate(
        title="Dimanche",
        schedule_date=SCHEDULE_DATE,
        masses=[mass_slot],
    )
    with pytest.raises(Exception) as exc:
        await svc.create_template(data, tpl.created_by)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_template_assignment_no_servant_id_uses_name():
    """Assignment with only servant_name (no servant_id) — skips user validation."""
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    svc = _make_svc()
    svc.schedule_repo.create_template.return_value = tpl
    svc.schedule_repo.create_mass.return_value = mass
    svc.schedule_repo.enrich_template.return_value = _enriched_template(tpl)

    mass_slot = SundayMassSlotCreate(
        mass_time="08h30",
        language=MassLanguage.FRANCAIS,
        assignments=[
            SundayMassAssignmentCreate(
                position=LiturgicalPosition.ACOLYTE_1,
                servant_id=None,
                servant_name="Jean Dupont",
            )
        ],
    )
    data = SundayScheduleTemplateCreate(
        title="Dimanche",
        schedule_date=SCHEDULE_DATE,
        masses=[mass_slot],
    )
    result = await svc.create_template(data, tpl.created_by)
    svc.user_repo.get.assert_not_called()
    assert result.id == tpl.id


# ── generate_ordinary_template ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_ordinary_template():
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.create_template.return_value = tpl
    svc.schedule_repo.enrich_template.return_value = _enriched_template(tpl)

    data = GenerateOrdinaryScheduleRequest(
        title="Classement Ordinaire",
        schedule_date=SCHEDULE_DATE,
    )
    result = await svc.generate_ordinary_template(data, tpl.created_by)

    svc.schedule_repo.create_masses_batch.assert_called_once()
    assert result.id == tpl.id


# ── generate_exceptional_template ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_exceptional_template():
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.create_template.return_value = tpl
    svc.schedule_repo.enrich_template.return_value = _enriched_template(tpl)

    data = GenerateExceptionalScheduleRequest(
        title="Classement Exceptionnel",
        schedule_date=SCHEDULE_DATE,
        mass_times=[
            MassTimePreset(time="09h00", language=MassLanguage.FRANCAIS),
            MassTimePreset(time="11h00", language=MassLanguage.EWONDO),
        ],
    )
    result = await svc.generate_exceptional_template(data, tpl.created_by)

    svc.schedule_repo.create_masses_batch.assert_called_once()
    assert result.id == tpl.id


# ── get_template ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_template_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_template(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_template_success():
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.enrich_template.return_value = _enriched_template(tpl)
    result = await svc.get_template(tpl.id)
    assert result.id == tpl.id


# ── list_templates ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_templates_empty():
    svc = _make_svc()
    svc.schedule_repo.list_templates.return_value = ([], 0)
    result = await svc.list_templates()
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_list_templates_with_items():
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.list_templates.return_value = ([tpl], 1)
    svc.schedule_repo.get_template_summary.return_value = _summary(tpl)
    result = await svc.list_templates(page=1, page_size=20)
    assert result.total == 1
    assert len(result.items) == 1


# ── get_published_templates ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_published_templates_empty():
    svc = _make_svc()
    svc.schedule_repo.get_published_templates.return_value = []
    result = await svc.get_published_templates()
    assert result == []


@pytest.mark.asyncio
async def test_get_published_templates_with_items():
    tpl = _make_template(status=SundayScheduleStatus.PUBLISHED)
    svc = _make_svc()
    svc.schedule_repo.get_published_templates.return_value = [tpl]
    svc.schedule_repo.get_template_summary.return_value = _summary(tpl)
    result = await svc.get_published_templates()
    assert len(result) == 1


# ── update_template ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_template_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.update_template(uuid4(), SundayScheduleTemplateUpdate(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_template_success():
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.update_template.return_value = tpl
    svc.schedule_repo.enrich_template.return_value = _enriched_template(tpl)

    data = SundayScheduleTemplateUpdate(title="Nouveau Titre", status=SundayScheduleStatus.PUBLISHED)
    result = await svc.update_template(tpl.id, data, uuid4())
    assert result.id == tpl.id


# ── publish_template ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_publish_template_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.publish_template(uuid4(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_publish_template_already_published():
    tpl = _make_template(status=SundayScheduleStatus.PUBLISHED)
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = tpl
    with pytest.raises(Exception) as exc:
        await svc.publish_template(tpl.id, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_publish_template_success():
    tpl = _make_template(status=SundayScheduleStatus.DRAFT)
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.update_template.return_value = tpl
    svc.schedule_repo.enrich_template.return_value = _enriched_template(tpl)
    result = await svc.publish_template(tpl.id, uuid4())
    assert result.id == tpl.id


# ── archive_template ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_archive_template_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.archive_template(uuid4(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_archive_template_success():
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.update_template.return_value = tpl
    svc.schedule_repo.enrich_template.return_value = _enriched_template(tpl)
    result = await svc.archive_template(tpl.id, uuid4())
    assert result.id == tpl.id


# ── delete_template ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_template_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.delete_template(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_template_repo_fails():
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.delete_template.return_value = False
    with pytest.raises(Exception) as exc:
        await svc.delete_template(tpl.id)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_delete_template_success():
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.delete_template.return_value = True
    await svc.delete_template(tpl.id)
    svc.schedule_repo.delete_template.assert_called_once_with(tpl.id)


# ── update_mass ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_mass_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.update_mass(uuid4(), SundayMassSlotUpdate())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_mass_success():
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.update_mass.return_value = mass
    svc.schedule_repo.enrich_mass.return_value = _enriched_mass(mass)

    data = SundayMassSlotUpdate(mass_time="10h00", language=MassLanguage.EWONDO, notes="note")
    result = await svc.update_mass(mass.id, data)
    assert result.id == mass.id


# ── delete_mass ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_mass_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.delete_mass(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_mass_repo_fails():
    mass = _make_mass()
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.delete_mass.return_value = False
    with pytest.raises(Exception) as exc:
        await svc.delete_mass(mass.id)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_delete_mass_success():
    mass = _make_mass()
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.delete_mass.return_value = True
    await svc.delete_mass(mass.id)
    svc.schedule_repo.delete_mass.assert_called_once_with(mass.id)


# ── add_assignment_to_mass ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_assignment_mass_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = None
    data = SundayMassAssignmentCreate(position=LiturgicalPosition.ACOLYTE_1, servant_name="Jean")
    with pytest.raises(Exception) as exc:
        await svc.add_assignment_to_mass(uuid4(), data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_assignment_template_not_found():
    mass = _make_mass()
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = None
    data = SundayMassAssignmentCreate(position=LiturgicalPosition.ACOLYTE_1, servant_name="Jean")
    with pytest.raises(Exception) as exc:
        await svc.add_assignment_to_mass(mass.id, data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_assignment_outside_time_window():
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl

    data = SundayMassAssignmentCreate(position=LiturgicalPosition.ACOLYTE_1, servant_name="Jean")
    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=False,
    ):
        with pytest.raises(Exception) as exc:
            await svc.add_assignment_to_mass(mass.id, data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_add_assignment_servant_not_found():
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl
    svc.user_repo.get.return_value = None

    data = SundayMassAssignmentCreate(position=LiturgicalPosition.ACOLYTE_1, servant_id=uuid4(), servant_name=None)
    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=True,
    ):
        with pytest.raises(Exception) as exc:
            await svc.add_assignment_to_mass(mass.id, data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_assignment_not_servant_role():
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl
    svc.user_repo.get.return_value = _make_user(role=UserRole.PARENT)

    data = SundayMassAssignmentCreate(position=LiturgicalPosition.ACOLYTE_1, servant_id=uuid4(), servant_name=None)
    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=True,
    ):
        with pytest.raises(Exception) as exc:
            await svc.add_assignment_to_mass(mass.id, data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_add_assignment_success_with_servant_id():
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    servant = _make_user(role=UserRole.SERVANT)
    a = _make_assignment(mass_slot_id=mass.id, servant_id=servant.id)
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl
    svc.user_repo.get.return_value = servant
    svc.schedule_repo.create_assignment.return_value = a
    svc.schedule_repo.enrich_assignment.return_value = _enriched_assignment(a)

    data = SundayMassAssignmentCreate(position=LiturgicalPosition.ACOLYTE_1, servant_id=servant.id, servant_name=None)
    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=True,
    ):
        result = await svc.add_assignment_to_mass(mass.id, data, uuid4())
    assert result.id == a.id


@pytest.mark.asyncio
async def test_add_assignment_success_name_only():
    tpl = _make_template()
    mass = _make_mass(template_id=tpl.id)
    a = _make_assignment(mass_slot_id=mass.id, servant_name="Jean Dupont")
    svc = _make_svc()
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.create_assignment.return_value = a
    svc.schedule_repo.enrich_assignment.return_value = _enriched_assignment(a)

    data = SundayMassAssignmentCreate(
        position=LiturgicalPosition.ACOLYTE_1, servant_id=None, servant_name="Jean Dupont"
    )
    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=True,
    ):
        result = await svc.add_assignment_to_mass(mass.id, data, uuid4())
    assert result.id == a.id


# ── remove_assignment ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_assignment_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.remove_assignment(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_remove_assignment_outside_window():
    a = _make_assignment()
    mass = _make_mass()
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl

    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=False,
    ):
        with pytest.raises(Exception) as exc:
            await svc.remove_assignment(a.id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_remove_assignment_repo_fails():
    a = _make_assignment()
    mass = _make_mass()
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.delete_assignment.return_value = False

    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=True,
    ):
        with pytest.raises(Exception) as exc:
            await svc.remove_assignment(a.id)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_remove_assignment_success():
    a = _make_assignment()
    mass = _make_mass()
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.delete_assignment.return_value = True

    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=True,
    ):
        await svc.remove_assignment(a.id)
    svc.schedule_repo.delete_assignment.assert_called_once_with(a.id)


@pytest.mark.asyncio
async def test_remove_assignment_skips_window_if_no_mass():
    """When mass is None, time window check is skipped."""
    a = _make_assignment()
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = None
    svc.schedule_repo.delete_assignment.return_value = True
    await svc.remove_assignment(a.id)
    svc.schedule_repo.delete_assignment.assert_called_once()


@pytest.mark.asyncio
async def test_remove_assignment_skips_window_if_no_template():
    """When template is None, time window check is skipped."""
    a = _make_assignment()
    mass = _make_mass()
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = None
    svc.schedule_repo.delete_assignment.return_value = True
    await svc.remove_assignment(a.id)
    svc.schedule_repo.delete_assignment.assert_called_once()


# ── mark_presence ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mark_presence_assignment_not_found():
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.mark_presence(uuid4(), True, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_presence_mass_not_found():
    a = _make_assignment()
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.mark_presence(a.id, True, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_presence_template_not_found():
    a = _make_assignment()
    mass = _make_mass()
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.mark_presence(a.id, True, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_presence_outside_window():
    a = _make_assignment()
    mass = _make_mass()
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl

    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=False,
    ):
        with pytest.raises(Exception) as exc:
            await svc.mark_presence(a.id, True, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_mark_presence_marker_not_found():
    a = _make_assignment()
    mass = _make_mass()
    tpl = _make_template()
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl
    svc.user_repo.get.return_value = None

    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=True,
    ):
        with pytest.raises(Exception) as exc:
            await svc.mark_presence(a.id, True, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_presence_success_present():
    a = _make_assignment()
    mass = _make_mass()
    tpl = _make_template()
    marker = _make_user(role=UserRole.ADMIN)
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl
    svc.user_repo.get.return_value = marker
    svc.schedule_repo.update_assignment.return_value = a
    svc.schedule_repo.enrich_assignment.return_value = _enriched_assignment(a)

    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=True,
    ):
        result = await svc.mark_presence(a.id, True, marker.id)
    svc.schedule_repo.create_modification_log.assert_called_once()
    assert result.id == a.id


@pytest.mark.asyncio
async def test_mark_presence_success_absent():
    a = _make_assignment(servant_id=uuid4(), servant_name=None)
    mass = _make_mass()
    tpl = _make_template()
    marker = _make_user(role=UserRole.ADMIN)
    servant = _make_user(role=UserRole.SERVANT)
    svc = _make_svc()
    svc.schedule_repo.get_assignment.return_value = a
    svc.schedule_repo.get_mass.return_value = mass
    svc.schedule_repo.get_template.return_value = tpl
    svc.schedule_repo.update_assignment.return_value = a
    svc.schedule_repo.enrich_assignment.return_value = _enriched_assignment(a)
    # First call returns marker, second returns servant
    svc.user_repo.get.side_effect = [marker, servant]

    with mock.patch(
        "src.application.services.sunday_schedule_service.is_within_mass_window",
        return_value=True,
    ):
        result = await svc.mark_presence(a.id, False, marker.id)
    assert result.id == a.id


# ── get_modification_history ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_modification_history_empty():
    svc = _make_svc()
    svc.schedule_repo.get_template_modification_logs.return_value = []
    result = await svc.get_modification_history(uuid4())
    assert result == []
