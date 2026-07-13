"""
Unit tests for WeeklyScheduleRepository.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _sa_exec_result(scalar_one=None, scalars_list=None, scalar=None):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=scalar_one)
    r.scalar_one = MagicMock(return_value=scalar_one if scalar is None else scalar)
    r.scalar = MagicMock(return_value=scalar)
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = scalars_list or []
    r.scalars.return_value = scalars_obj
    return r


def _make_template(**kw):
    from src.core.entities.weekly_schedule import ScheduleStatus

    t = MagicMock()
    t.id = kw.get("id", uuid4())
    t.status = kw.get("status", ScheduleStatus.DRAFT)
    t.created_by = kw.get("created_by", uuid4())
    t.start_date = kw.get("start_date", datetime.utcnow())
    t.end_date = kw.get("end_date", datetime.utcnow())
    t.model_dump = MagicMock(return_value={"id": str(t.id), "status": "DRAFT"})
    return t


def _make_slot(**kw):
    s = MagicMock()
    s.id = kw.get("id", uuid4())
    s.template_id = kw.get("template_id", uuid4())
    s.day = kw.get("day", "DIMANCHE")
    s.mass_time = kw.get("mass_time", "08:00")
    s.model_dump = MagicMock(return_value={"id": str(s.id), "day": "DIMANCHE"})
    return s


def _make_assignment(**kw):
    a = MagicMock()
    a.id = kw.get("id", uuid4())
    a.slot_id = kw.get("slot_id", uuid4())
    a.servant_id = kw.get("servant_id", uuid4())
    a.servant_name = kw.get("servant_name", "Jean Dupont")
    a.model_dump = MagicMock(return_value={"id": str(a.id), "servant_name": "Jean Dupont"})
    return a


# ─────────────────────────────────────────────────────────────────────────────
#  TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weekly_create_template():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    template = _make_template()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_template(template)
    assert result is template


@pytest.mark.asyncio
async def test_weekly_get_template_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    template = _make_template()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=template))

    result = await repo.get_template(template.id)
    assert result is template


@pytest.mark.asyncio
async def test_weekly_get_template_not_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.get_template(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_weekly_update_template():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    template = _make_template()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update_template(template.id, template)
    assert result is template


@pytest.mark.asyncio
async def test_weekly_delete_template_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    template = _make_template()
    slot = _make_slot(template_id=template.id)
    assignment = _make_assignment(slot_id=slot.id)

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=template),         # get_template
        _sa_exec_result(scalars_list=[slot]),          # get slots
        _sa_exec_result(scalars_list=[assignment]),    # get assignments for slot
    ])
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete_template(template.id)
    assert result is True


@pytest.mark.asyncio
async def test_weekly_delete_template_not_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete_template(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_weekly_list_templates():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    templates = [_make_template(), _make_template()]
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=2),                   # count
        _sa_exec_result(scalars_list=templates),          # results
    ])

    result, total = await repo.list_templates()
    assert total == 2
    assert len(result) == 2


@pytest.mark.asyncio
async def test_weekly_list_templates_with_filters():
    from src.core.entities.weekly_schedule import ScheduleStatus
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    now = datetime.utcnow()
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=0),
        _sa_exec_result(scalars_list=[]),
    ])

    result, total = await repo.list_templates(
        status=ScheduleStatus.PUBLISHED,
        start_date=now,
        end_date=now,
    )
    assert total == 0


@pytest.mark.asyncio
async def test_weekly_get_published_templates():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    templates = [_make_template()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=templates))

    result = await repo.get_published_templates()
    assert len(result) == 1


# ─────────────────────────────────────────────────────────────────────────────
#  SLOTS
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weekly_create_slot():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    slot = _make_slot()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_slot(slot)
    assert result is slot


@pytest.mark.asyncio
async def test_weekly_create_slots_batch():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    slots = [_make_slot(), _make_slot()]
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_slots_batch(slots)
    assert len(result) == 2
    session.add_all.assert_called_once()


@pytest.mark.asyncio
async def test_weekly_get_slot_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    slot = _make_slot()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=slot))

    result = await repo.get_slot(slot.id)
    assert result is slot


@pytest.mark.asyncio
async def test_weekly_update_slot():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    slot = _make_slot()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update_slot(slot.id, slot)
    assert result is slot


@pytest.mark.asyncio
async def test_weekly_delete_slot_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    slot = _make_slot()
    assignment = _make_assignment(slot_id=slot.id)

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=slot),              # get_slot
        _sa_exec_result(scalars_list=[assignment]),     # get assignments
    ])
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete_slot(slot.id)
    assert result is True


@pytest.mark.asyncio
async def test_weekly_delete_slot_not_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete_slot(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_weekly_get_template_slots():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    slots = [_make_slot()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=slots))

    result = await repo.get_template_slots(uuid4())
    assert len(result) == 1


# ─────────────────────────────────────────────────────────────────────────────
#  ASSIGNMENTS
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weekly_create_assignment():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    assignment = _make_assignment()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    with patch("src.infrastructure.repositories.weekly_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.encrypt.return_value = "encrypted"
        enc.decrypt.return_value = "Jean Dupont"
        mock_enc.return_value = enc
        result = await repo.create_assignment(assignment)

    assert result is assignment


@pytest.mark.asyncio
async def test_weekly_create_assignments_batch():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    assignments = [_make_assignment(), _make_assignment()]
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    with patch("src.infrastructure.repositories.weekly_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.encrypt.return_value = "encrypted"
        enc.decrypt.return_value = "Jean Dupont"
        mock_enc.return_value = enc
        result = await repo.create_assignments_batch(assignments)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_weekly_get_assignment_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    assignment = _make_assignment()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=assignment))

    with patch("src.infrastructure.repositories.weekly_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "Jean Dupont"
        mock_enc.return_value = enc
        result = await repo.get_assignment(assignment.id)

    assert result is assignment


@pytest.mark.asyncio
async def test_weekly_get_assignment_not_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.get_assignment(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_weekly_get_slot_assignments():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    assignments = [_make_assignment()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=assignments))

    with patch("src.infrastructure.repositories.weekly_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "Jean Dupont"
        mock_enc.return_value = enc
        result = await repo.get_slot_assignments(uuid4())

    assert len(result) == 1


@pytest.mark.asyncio
async def test_weekly_delete_assignment_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    assignment = _make_assignment()

    # get_assignment() calls execute (result not None)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=assignment))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    with patch("src.infrastructure.repositories.weekly_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "Jean Dupont"
        mock_enc.return_value = enc
        result = await repo.delete_assignment(assignment.id)

    assert result is True


@pytest.mark.asyncio
async def test_weekly_delete_assignment_not_found():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete_assignment(uuid4())
    assert result is False


# ─────────────────────────────────────────────────────────────────────────────
#  ENRICHMENT
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_weekly_enrich_assignment_with_servant():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    assignment = _make_assignment()

    servant = MagicMock()
    servant.first_name = "Marc"
    servant.last_name = "Ateba"
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=servant))

    with patch("src.infrastructure.repositories.weekly_schedule_repository.decrypt_str_fields"):
        result = await repo.enrich_assignment(assignment)

    assert result["servant_first_name"] == "Marc"
    assert result["servant_last_name"] == "Ateba"


@pytest.mark.asyncio
async def test_weekly_enrich_assignment_no_servant():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    assignment = _make_assignment()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.enrich_assignment(assignment)
    assert "servant_first_name" not in result


@pytest.mark.asyncio
async def test_weekly_enrich_slot():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    slot = _make_slot()

    # get_slot_assignments then enrich_assignment
    assignment = _make_assignment()
    servant = MagicMock()
    servant.first_name = "Paul"
    servant.last_name = "Nkolo"
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalars_list=[assignment]),   # get_slot_assignments
        _sa_exec_result(scalar_one=servant),           # enrich_assignment servant
    ])

    with patch("src.infrastructure.repositories.weekly_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "decrypted"
        mock_enc.return_value = enc
        with patch("src.infrastructure.repositories.weekly_schedule_repository.decrypt_str_fields"):
            result = await repo.enrich_slot(slot)

    assert "servants" in result


@pytest.mark.asyncio
async def test_weekly_enrich_template():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    template = _make_template()
    creator = MagicMock()
    creator.first_name = "Admin"
    creator.last_name = "Chef"

    # creator execute, then get_template_slots (empty for simplicity)
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=creator),  # creator
        _sa_exec_result(scalars_list=[]),      # slots
    ])

    with patch("src.infrastructure.repositories.weekly_schedule_repository.decrypt_str_fields"):
        result = await repo.enrich_template(template)

    assert result["creator_first_name"] == "Admin"
    assert result["creator_last_name"] == "Chef"
    assert result["slots"] == []


@pytest.mark.asyncio
async def test_weekly_enrich_template_no_creator():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    template = _make_template()
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=None),     # no creator
        _sa_exec_result(scalars_list=[]),      # slots
    ])

    result = await repo.enrich_template(template)
    assert result["creator_first_name"] is None


@pytest.mark.asyncio
async def test_weekly_get_template_summary():
    from src.infrastructure.repositories.weekly_schedule_repository import WeeklyScheduleRepository

    session = _mock_session()
    repo = WeeklyScheduleRepository(session)
    template = _make_template()
    slot = _make_slot(template_id=template.id)
    assignment = _make_assignment(slot_id=slot.id)
    creator = MagicMock()
    creator.first_name = "Admin"
    creator.last_name = "Res"

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=creator),           # creator
        _sa_exec_result(scalars_list=[slot]),           # get_template_slots
        _sa_exec_result(scalars_list=[assignment]),     # get_slot_assignments for that slot
    ])

    with patch("src.infrastructure.repositories.weekly_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "decrypted"
        mock_enc.return_value = enc
        with patch("src.infrastructure.repositories.weekly_schedule_repository.decrypt_str_fields"):
            result = await repo.get_template_summary(template)

    assert result["total_slots"] == 1
    assert result["filled_slots"] == 1
    assert result["total_servants"] == 1
