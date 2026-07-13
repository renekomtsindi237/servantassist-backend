"""
Unit tests for SundayScheduleRepository.
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
    from src.core.entities.sunday_schedule import SundayScheduleStatus

    t = MagicMock()
    t.id = kw.get("id", uuid4())
    t.status = kw.get("status", SundayScheduleStatus.DRAFT)
    t.created_by = kw.get("created_by", uuid4())
    t.schedule_date = kw.get("schedule_date", datetime.utcnow())
    t.model_dump = MagicMock(return_value={"id": str(t.id), "status": "DRAFT"})
    return t


def _make_mass(**kw):
    m = MagicMock()
    m.id = kw.get("id", uuid4())
    m.template_id = kw.get("template_id", uuid4())
    m.mass_time = kw.get("mass_time", "08:00")
    m.model_dump = MagicMock(return_value={"id": str(m.id)})
    return m


def _make_assignment(**kw):
    a = MagicMock()
    a.id = kw.get("id", uuid4())
    a.mass_slot_id = kw.get("mass_slot_id", uuid4())
    a.servant_id = kw.get("servant_id", uuid4())
    a.servant_name = kw.get("servant_name", None)
    a.assigned_by = kw.get("assigned_by", uuid4())
    a.last_modified_by = kw.get("last_modified_by", None)
    a.presence_marked_by = kw.get("presence_marked_by", None)
    a.position = kw.get("position", 1)
    a.model_dump = MagicMock(return_value={"id": str(a.id)})
    return a


# ─────────────────────────────────────────────────────────────────────────────
#  TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sunday_create_template():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_template(template)
    assert result is template


@pytest.mark.asyncio
async def test_sunday_get_template_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=template))

    result = await repo.get_template(template.id)
    assert result is template


@pytest.mark.asyncio
async def test_sunday_get_template_not_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.get_template(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_sunday_update_template():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update_template(template.id, template)
    assert result is template


@pytest.mark.asyncio
async def test_sunday_delete_template_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()
    mass = _make_mass(template_id=template.id)
    assignment = _make_assignment(mass_slot_id=mass.id)

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=template),         # get_template
        _sa_exec_result(scalars_list=[mass]),          # get masses
        _sa_exec_result(scalars_list=[assignment]),    # assignments for mass
    ])
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete_template(template.id)
    assert result is True


@pytest.mark.asyncio
async def test_sunday_delete_template_not_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete_template(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_sunday_list_templates():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    templates = [_make_template(), _make_template()]
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=2),
        _sa_exec_result(scalars_list=templates),
    ])

    result, total = await repo.list_templates()
    assert total == 2
    assert len(result) == 2


@pytest.mark.asyncio
async def test_sunday_list_templates_with_filters():
    from src.core.entities.sunday_schedule import SundayScheduleStatus
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    now = datetime.utcnow()
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=0),
        _sa_exec_result(scalars_list=[]),
    ])

    result, total = await repo.list_templates(
        status=SundayScheduleStatus.PUBLISHED,
        start_date=now,
        end_date=now,
    )
    assert total == 0


@pytest.mark.asyncio
async def test_sunday_get_published_templates():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    templates = [_make_template()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=templates))

    result = await repo.get_published_templates()
    assert len(result) == 1


# ─────────────────────────────────────────────────────────────────────────────
#  MASS SLOTS
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sunday_create_mass():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    mass = _make_mass()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_mass(mass)
    assert result is mass


@pytest.mark.asyncio
async def test_sunday_create_masses_batch():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    masses = [_make_mass(), _make_mass()]
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_masses_batch(masses)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_sunday_get_mass_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    mass = _make_mass()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=mass))

    result = await repo.get_mass(mass.id)
    assert result is mass


@pytest.mark.asyncio
async def test_sunday_update_mass():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    mass = _make_mass()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update_mass(mass.id, mass)
    assert result is mass


@pytest.mark.asyncio
async def test_sunday_delete_mass_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    mass = _make_mass()
    assignment = _make_assignment(mass_slot_id=mass.id)

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=mass),              # get_mass
        _sa_exec_result(scalars_list=[assignment]),     # get assignments
    ])
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete_mass(mass.id)
    assert result is True


@pytest.mark.asyncio
async def test_sunday_delete_mass_not_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete_mass(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_sunday_get_template_masses():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    masses = [_make_mass()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=masses))

    result = await repo.get_template_masses(uuid4())
    assert len(result) == 1


# ─────────────────────────────────────────────────────────────────────────────
#  ASSIGNMENTS
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sunday_create_assignment():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    assignment = _make_assignment()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    with patch("src.infrastructure.repositories.sunday_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.encrypt.return_value = "encrypted"
        enc.decrypt.return_value = "Jean Dupont"
        mock_enc.return_value = enc
        result = await repo.create_assignment(assignment)

    assert result is assignment


@pytest.mark.asyncio
async def test_sunday_create_assignments_batch():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    assignments = [_make_assignment(), _make_assignment()]
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    with patch("src.infrastructure.repositories.sunday_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.encrypt.return_value = "encrypted"
        enc.decrypt.return_value = "decrypted"
        mock_enc.return_value = enc
        result = await repo.create_assignments_batch(assignments)

    assert len(result) == 2


@pytest.mark.asyncio
async def test_sunday_get_assignment_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    assignment = _make_assignment()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=assignment))

    with patch("src.infrastructure.repositories.sunday_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "Jean Dupont"
        mock_enc.return_value = enc
        result = await repo.get_assignment(assignment.id)

    assert result is assignment


@pytest.mark.asyncio
async def test_sunday_get_assignment_not_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.get_assignment(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_sunday_get_mass_assignments():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    assignments = [_make_assignment()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=assignments))

    with patch("src.infrastructure.repositories.sunday_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "decrypted"
        mock_enc.return_value = enc
        result = await repo.get_mass_assignments(uuid4())

    assert len(result) == 1


@pytest.mark.asyncio
async def test_sunday_delete_assignment_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    assignment = _make_assignment()

    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=assignment))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    with patch("src.infrastructure.repositories.sunday_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "Jean Dupont"
        mock_enc.return_value = enc
        result = await repo.delete_assignment(assignment.id)

    assert result is True


@pytest.mark.asyncio
async def test_sunday_delete_assignment_not_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete_assignment(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_sunday_update_assignment():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    assignment = _make_assignment()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    with patch("src.infrastructure.repositories.sunday_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.encrypt.return_value = "encrypted"
        enc.decrypt.return_value = "decrypted"
        mock_enc.return_value = enc
        result = await repo.update_assignment(assignment.id, assignment)

    assert result is assignment


# ─────────────────────────────────────────────────────────────────────────────
#  ENRICHISSEMENT
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sunday_enrich_assignment_full():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    modifier_id = uuid4()
    presence_id = uuid4()
    assignment = _make_assignment(last_modified_by=modifier_id, presence_marked_by=presence_id)

    servant = MagicMock(); servant.first_name = "Jean"; servant.last_name = "D."
    assignee = MagicMock(); assignee.first_name = "Admin"; assignee.last_name = "Res"
    modifier = MagicMock(); modifier.first_name = "Chef"; modifier.last_name = "R"
    presence = MagicMock(); presence.first_name = "Pres"; presence.last_name = "B"

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=servant),    # servant
        _sa_exec_result(scalar_one=assignee),   # assigned_by
        _sa_exec_result(scalar_one=modifier),   # last_modified_by
        _sa_exec_result(scalar_one=presence),   # presence_marked_by
    ])

    with patch("src.infrastructure.repositories.sunday_schedule_repository.decrypt_str_fields"):
        result = await repo.enrich_assignment(assignment)

    assert result["servant_first_name"] == "Jean"
    assert result["assigned_by_name"] == "Admin Res"
    assert result["last_modified_by_name"] == "Chef R"
    assert result["presence_marked_by_name"] == "Pres B"


@pytest.mark.asyncio
async def test_sunday_enrich_assignment_minimal():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    assignment = _make_assignment(servant_id=None, last_modified_by=None, presence_marked_by=None)

    assignee = MagicMock(); assignee.first_name = "Admin"; assignee.last_name = "R"
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=assignee))

    with patch("src.infrastructure.repositories.sunday_schedule_repository.decrypt_str_fields"):
        result = await repo.enrich_assignment(assignment)

    assert "servant_first_name" not in result
    assert result["assigned_by_name"] == "Admin R"


@pytest.mark.asyncio
async def test_sunday_enrich_template():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()
    creator = MagicMock(); creator.first_name = "Admin"; creator.last_name = "Resp"

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=creator),  # creator
        _sa_exec_result(scalars_list=[]),      # get_template_masses -> empty
    ])

    with patch("src.infrastructure.repositories.sunday_schedule_repository.decrypt_str_fields"):
        result = await repo.enrich_template(template)

    assert result["creator_first_name"] == "Admin"
    assert result["masses"] == []


@pytest.mark.asyncio
async def test_sunday_enrich_template_no_creator():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=None),  # no creator
        _sa_exec_result(scalars_list=[]),   # no masses
    ])

    result = await repo.enrich_template(template)
    assert result["creator_first_name"] is None


@pytest.mark.asyncio
async def test_sunday_get_template_summary():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()
    mass = _make_mass(template_id=template.id)
    assignment = _make_assignment(mass_slot_id=mass.id)
    creator = MagicMock(); creator.first_name = "Chef"; creator.last_name = "X"

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=creator),           # creator
        _sa_exec_result(scalars_list=[mass]),           # masses
        _sa_exec_result(scalars_list=[assignment]),     # assignments for mass
    ])

    with patch("src.infrastructure.repositories.sunday_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "decrypted"
        mock_enc.return_value = enc
        with patch("src.infrastructure.repositories.sunday_schedule_repository.decrypt_str_fields"):
            result = await repo.get_template_summary(template)

    assert result["total_masses"] == 1
    assert result["total_positions"] == 1


# ─────────────────────────────────────────────────────────────────────────────
#  MODIFICATION LOGS
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_sunday_create_modification_log():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    log = MagicMock()
    log.modified_by_name = "Admin"
    log.ip_address = "127.0.0.1"
    log.user_agent = "test-agent"
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    with patch("src.infrastructure.repositories.sunday_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.encrypt.return_value = "encrypted"
        enc.decrypt.return_value = "decrypted"
        mock_enc.return_value = enc
        result = await repo.create_modification_log(log)

    assert result is log


@pytest.mark.asyncio
async def test_sunday_get_modification_logs():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    log = MagicMock()
    log.modified_by_name = "Admin"
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=[log]))

    with patch("src.infrastructure.repositories.sunday_schedule_repository.get_encryptor") as mock_enc:
        enc = MagicMock()
        enc.decrypt.return_value = "decrypted"
        mock_enc.return_value = enc
        result = await repo.get_template_modification_logs(uuid4())

    assert len(result) == 1
