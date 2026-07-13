"""
Unit tests for EventRepository, DisciplineCaseRepository.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _exec_result(first=None, all_=None, one=None):
    r = MagicMock()
    r.first = MagicMock(return_value=first)
    r.all = MagicMock(return_value=all_ if all_ is not None else [])
    r.one = MagicMock(return_value=one if one is not None else 0)
    return r


# ═══════════════════════════════════════════════════════════════════════════════
#  EventRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_event(**kw):
    from src.core.entities.event import Event, EventStatus, EventType

    e = MagicMock()
    e.id = kw.get("id", uuid4())
    e.title = kw.get("title", "Messe dimanche")
    e.status = kw.get("status", EventStatus.PUBLIE)
    e.event_type = kw.get("event_type", EventType.MESSE_DOMINICALE)
    e.start_time = kw.get("start_time", datetime.utcnow() + timedelta(days=1))
    e.location = kw.get("location", "Cathédrale")
    return e


def _make_participant(**kw):
    from src.core.entities.event import EventParticipant

    p = MagicMock()
    p.id = kw.get("id", uuid4())
    p.event_id = kw.get("event_id", uuid4())
    p.user_id = kw.get("user_id", uuid4())
    p.participant_role = kw.get("participant_role", "servant")
    p.status = kw.get("status", "CONFIRMED")
    p.notes = kw.get("notes", None)
    p.added_by = kw.get("added_by", None)
    p.created_at = kw.get("created_at", datetime.utcnow())
    p.updated_at = kw.get("updated_at", datetime.utcnow())
    return p


@pytest.mark.asyncio
async def test_event_get_found():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    event = _make_event()
    session.exec = AsyncMock(return_value=_exec_result(first=event))

    result = await repo.get(event.id)
    assert result is event


@pytest.mark.asyncio
async def test_event_get_not_found():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_event_list():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    events = [_make_event(), _make_event()]
    session.exec = AsyncMock(return_value=_exec_result(all_=events))

    result = await repo.list()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_event_list_with_dates():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(all_=[]))
    now = datetime.utcnow()

    result = await repo.list(date_from=now, date_to=now + timedelta(days=7))
    assert result == []


@pytest.mark.asyncio
async def test_event_list_paginated():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    events = [_make_event()]
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=1),        # count
        _exec_result(all_=events),  # results
    ])

    result, total = await repo.list_paginated()
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_event_list_paginated_with_filters():
    from src.core.entities.event import EventStatus, EventType
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=0),
        _exec_result(all_=[]),
    ])
    now = datetime.utcnow()

    result, total = await repo.list_paginated(
        event_type=EventType.MESSE_DOMINICALE,
        status=EventStatus.PUBLIE,
        start_date=now,
        end_date=now + timedelta(days=7),
        search="messe",
    )
    assert result == []
    assert total == 0


@pytest.mark.asyncio
async def test_event_create():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    event = _make_event()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(event)
    assert result is event


@pytest.mark.asyncio
async def test_event_update():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    event = _make_event()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(event.id, event)
    assert result is event


@pytest.mark.asyncio
async def test_event_delete_found():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    event = _make_event()

    # First exec: participants (empty), Second exec: event itself
    session.exec = AsyncMock(side_effect=[
        _exec_result(all_=[]),      # participants
        _exec_result(first=event),  # event
    ])
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(event.id)
    assert result is True
    session.delete.assert_called_with(event)


@pytest.mark.asyncio
async def test_event_delete_not_found():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)

    session.exec = AsyncMock(side_effect=[
        _exec_result(all_=[]),   # participants
        _exec_result(first=None),  # event not found
    ])

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_event_delete_with_participants():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    event = _make_event()
    p = _make_participant(event_id=event.id)

    session.exec = AsyncMock(side_effect=[
        _exec_result(all_=[p]),     # participants
        _exec_result(first=event),  # event
    ])
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(event.id)
    assert result is True
    # Delete called twice (participant + event)
    assert session.delete.call_count == 2


@pytest.mark.asyncio
async def test_event_get_participant_count():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(one=3))

    result = await repo.get_participant_count(uuid4())
    assert result == 3


@pytest.mark.asyncio
async def test_event_get_participants():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    p = _make_participant()
    user = MagicMock()
    user.first_name = "Jean"
    user.last_name = "Nkemelu"
    user.email = "jean@example.com"
    user.phone_number = "+237"

    session.exec = AsyncMock(side_effect=[
        _exec_result(all_=[p]),      # participants
        _exec_result(first=user),    # user for participant
    ])

    with patch("src.infrastructure.repositories.event_repository.decrypt_str_fields"):
        result = await repo.get_participants(uuid4())

    assert len(result) == 1
    assert result[0]["user_first_name"] == "Jean"


@pytest.mark.asyncio
async def test_event_get_participants_no_user():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    p = _make_participant()

    session.exec = AsyncMock(side_effect=[
        _exec_result(all_=[p]),
        _exec_result(first=None),
    ])

    result = await repo.get_participants(uuid4())
    assert result[0]["user_first_name"] is None


@pytest.mark.asyncio
async def test_event_add_participant():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    p = _make_participant()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.add_participant(p)
    assert result is p


@pytest.mark.asyncio
async def test_event_get_participant_by_event_and_user():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    p = _make_participant()
    session.exec = AsyncMock(return_value=_exec_result(first=p))

    result = await repo.get_participant_by_event_and_user(p.event_id, p.user_id)
    assert result is p


@pytest.mark.asyncio
async def test_event_remove_participant_found():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    p = _make_participant()
    session.exec = AsyncMock(return_value=_exec_result(first=p))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.remove_participant(p.id)
    assert result is True


@pytest.mark.asyncio
async def test_event_remove_participant_not_found():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.remove_participant(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_event_update_participant():
    from src.infrastructure.repositories.event_repository import EventRepository

    session = _mock_session()
    repo = EventRepository(session)
    p = _make_participant()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update_participant(p)
    assert result is p


# ═══════════════════════════════════════════════════════════════════════════════
#  DisciplineCaseRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_discipline_case(**kw):
    from src.core.entities.discipline import DisciplineCase, DisciplineCaseStatus, OffenseCategory, SanctionSeverity

    d = MagicMock()
    d.id = kw.get("id", uuid4())
    d.accused_user_id = kw.get("accused_user_id", uuid4())
    d.reporter_user_id = kw.get("reporter_user_id", uuid4())
    d.offense_description = kw.get("offense_description", "Comportement incorrect")
    d.status = kw.get("status", DisciplineCaseStatus.SIGNALE)
    d.severity = kw.get("severity", SanctionSeverity.MINEUR)
    d.offense_category = kw.get("offense_category", OffenseCategory.INSUBORDINATION)
    d.verdict_notes = kw.get("verdict_notes", None)
    d.convocation_notes = kw.get("convocation_notes", None)
    d.created_at = kw.get("created_at", datetime.utcnow())
    return d


def _make_enc_disc_repo(session):
    from src.infrastructure.repositories.discipline_repository import DisciplineCaseRepository

    repo = DisciplineCaseRepository(session)
    repo._encrypt_model = MagicMock()
    repo._decrypt_model = MagicMock()
    repo._decrypt_list = MagicMock()
    return repo


@pytest.mark.asyncio
async def test_discipline_get_found():
    session = _mock_session()
    repo = _make_enc_disc_repo(session)
    case = _make_discipline_case()
    session.exec = AsyncMock(return_value=_exec_result(first=case))

    result = await repo.get(case.id)
    assert result is case
    repo._decrypt_model.assert_called_once_with(case)


@pytest.mark.asyncio
async def test_discipline_get_not_found():
    session = _mock_session()
    repo = _make_enc_disc_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_discipline_list_paginated():
    from src.infrastructure.repositories.discipline_repository import DisciplineCaseRepository

    session = _mock_session()
    repo = _make_enc_disc_repo(session)
    cases = [_make_discipline_case()]
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=1),        # count
        _exec_result(all_=cases),   # items
    ])

    result, total = await repo.list_paginated()
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_discipline_list_paginated_with_filters():
    from src.core.entities.discipline import DisciplineCaseStatus, OffenseCategory, SanctionSeverity
    from src.infrastructure.repositories.discipline_repository import DisciplineCaseRepository

    session = _mock_session()
    repo = _make_enc_disc_repo(session)
    session.exec = AsyncMock(side_effect=[
        _exec_result(one=0),
        _exec_result(all_=[]),
    ])

    result, total = await repo.list_paginated(
        accused_user_id=uuid4(),
        status=DisciplineCaseStatus.SIGNALE,
        severity=SanctionSeverity.MINEUR,
        offense_category=OffenseCategory.INSUBORDINATION,
    )
    assert result == []
    assert total == 0
