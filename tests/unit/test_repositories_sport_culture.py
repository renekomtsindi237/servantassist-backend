"""
Unit tests for SportCultureEventRepository, EventParticipationRepository,
EventResultRepository, EventTeamRepository.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _sa_exec_result(scalar_one=None, scalars_list=None, scalar=None):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=scalar_one)
    r.scalar_one = MagicMock(return_value=scalar_one)
    r.scalar = MagicMock(return_value=scalar)
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = scalars_list or []
    r.scalars.return_value = scalars_obj
    return r


def _make_event(**kw):
    from src.core.entities.sport_culture import EventStatus, EventType

    e = MagicMock()
    e.id = kw.get("id", uuid4())
    e.event_type = kw.get("event_type", EventType.TOURNOI)
    e.status = kw.get("status", EventStatus.PLANIFIE)
    e.date = kw.get("date", datetime.utcnow())
    e.updated_at = kw.get("updated_at", datetime.utcnow())
    return e


def _make_participation(**kw):
    from src.core.entities.sport_culture import ParticipationStatus

    p = MagicMock()
    p.id = kw.get("id", uuid4())
    p.event_id = kw.get("event_id", uuid4())
    p.servant_id = kw.get("servant_id", uuid4())
    p.status = kw.get("status", ParticipationStatus.INSCRIT)
    p.registration_date = kw.get("registration_date", datetime.utcnow())
    p.updated_at = kw.get("updated_at", datetime.utcnow())
    p.servant_name = kw.get("servant_name", None)
    return p


def _make_result_obj(**kw):
    r = MagicMock()
    r.id = kw.get("id", uuid4())
    r.event_id = kw.get("event_id", uuid4())
    r.created_at = kw.get("created_at", datetime.utcnow())
    return r


def _make_team(**kw):
    t = MagicMock()
    t.id = kw.get("id", uuid4())
    t.event_id = kw.get("event_id", uuid4())
    t.captain_id = kw.get("captain_id", uuid4())
    t.team_name = kw.get("team_name", "Les Bleus")
    t.members = kw.get("members", [])
    t.captain_name = kw.get("captain_name", None)
    t.members_names = kw.get("members_names", [])
    return t


# ═══════════════════════════════════════════════════════════════════════════════
#  SportCultureEventRepository
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_sport_event_create():
    from src.infrastructure.repositories.sport_culture_repository import SportCultureEventRepository

    session = _mock_session()
    repo = SportCultureEventRepository(session)
    event = _make_event()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(event)
    assert result is event


@pytest.mark.asyncio
async def test_sport_event_get_by_id_found():
    from src.infrastructure.repositories.sport_culture_repository import SportCultureEventRepository

    session = _mock_session()
    repo = SportCultureEventRepository(session)
    event = _make_event()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=event))

    result = await repo.get_by_id(event.id)
    assert result is event


@pytest.mark.asyncio
async def test_sport_event_get_by_id_not_found():
    from src.infrastructure.repositories.sport_culture_repository import SportCultureEventRepository

    session = _mock_session()
    repo = SportCultureEventRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_sport_event_list_events():
    from src.infrastructure.repositories.sport_culture_repository import SportCultureEventRepository

    session = _mock_session()
    repo = SportCultureEventRepository(session)
    events = [_make_event(), _make_event()]
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=2),
            _sa_exec_result(scalars_list=events),
        ]
    )

    result, total = await repo.list_events()
    assert total == 2
    assert len(result) == 2


@pytest.mark.asyncio
async def test_sport_event_list_events_with_filters():
    from src.core.entities.sport_culture import EventStatus, EventType
    from src.infrastructure.repositories.sport_culture_repository import SportCultureEventRepository

    session = _mock_session()
    repo = SportCultureEventRepository(session)
    now = datetime.utcnow()
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=0),
            _sa_exec_result(scalars_list=[]),
        ]
    )

    result, total = await repo.list_events(
        event_type=EventType.TOURNOI,
        status=EventStatus.PLANIFIE,
        start_date=now,
        end_date=now + timedelta(days=30),
    )
    assert total == 0


@pytest.mark.asyncio
async def test_sport_event_update():
    from src.infrastructure.repositories.sport_culture_repository import SportCultureEventRepository

    session = _mock_session()
    repo = SportCultureEventRepository(session)
    event = _make_event()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(event)
    assert result is event


@pytest.mark.asyncio
async def test_sport_event_delete_found():
    from src.infrastructure.repositories.sport_culture_repository import SportCultureEventRepository

    session = _mock_session()
    repo = SportCultureEventRepository(session)
    event = _make_event()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=event))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(event.id)
    assert result is True


@pytest.mark.asyncio
async def test_sport_event_delete_not_found():
    from src.infrastructure.repositories.sport_culture_repository import SportCultureEventRepository

    session = _mock_session()
    repo = SportCultureEventRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_sport_event_get_upcoming():
    from src.infrastructure.repositories.sport_culture_repository import SportCultureEventRepository

    session = _mock_session()
    repo = SportCultureEventRepository(session)
    events = [_make_event()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=events))

    result = await repo.get_upcoming_events(limit=5)
    assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════════════
#  EventParticipationRepository
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_event_participation_create():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    p = _make_participation()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(p)
    assert result is p


@pytest.mark.asyncio
async def test_event_participation_create_batch():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    parts = [_make_participation(), _make_participation()]
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_batch(parts)
    assert len(result) == 2
    assert session.add.call_count == 2


@pytest.mark.asyncio
async def test_event_participation_get_by_id():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    p = _make_participation()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=p))

    result = await repo.get_by_id(p.id)
    assert result is p


@pytest.mark.asyncio
async def test_event_participation_get_by_event():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    parts = [_make_participation(), _make_participation()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=parts))

    result = await repo.get_by_event(uuid4())
    assert len(result) == 2


@pytest.mark.asyncio
async def test_event_participation_get_by_servant():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    parts = [_make_participation()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=parts))
    now = datetime.utcnow()

    result = await repo.get_by_servant(uuid4(), start_date=now, end_date=now + timedelta(days=7))
    assert len(result) == 1


@pytest.mark.asyncio
async def test_event_participation_get_by_event_and_servant():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    p = _make_participation()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=p))

    result = await repo.get_by_event_and_servant(uuid4(), uuid4())
    assert result is p


@pytest.mark.asyncio
async def test_event_participation_update():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    p = _make_participation()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(p)
    assert result is p


@pytest.mark.asyncio
async def test_event_participation_delete_found():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    p = _make_participation()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=p))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(p.id)
    assert result is True


@pytest.mark.asyncio
async def test_event_participation_delete_not_found():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_event_participation_count_by_event():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar=5))

    result = await repo.count_by_event(uuid4())
    assert result == 5


@pytest.mark.asyncio
async def test_event_participation_count_confirmed():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar=3))

    result = await repo.count_confirmed_by_event(uuid4())
    assert result == 3


@pytest.mark.asyncio
async def test_event_participation_enrich_found():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    p = _make_participation()
    servant = MagicMock()
    servant.first_name = "Pierre"
    servant.last_name = "Ngo"
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=servant))

    with patch("src.infrastructure.repositories.sport_culture_repository.decrypt_str_fields"):
        await repo.enrich_participation(p)

    assert p.servant_name == "Pierre Ngo"


@pytest.mark.asyncio
async def test_event_participation_enrich_not_found():
    from src.infrastructure.repositories.sport_culture_repository import EventParticipationRepository

    session = _mock_session()
    repo = EventParticipationRepository(session)
    p = _make_participation()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.enrich_participation(p)
    assert result is p


# ═══════════════════════════════════════════════════════════════════════════════
#  EventResultRepository
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_event_result_create():
    from src.infrastructure.repositories.sport_culture_repository import EventResultRepository

    session = _mock_session()
    repo = EventResultRepository(session)
    r = _make_result_obj()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(r)
    assert result is r


@pytest.mark.asyncio
async def test_event_result_get_by_event():
    from src.infrastructure.repositories.sport_culture_repository import EventResultRepository

    session = _mock_session()
    repo = EventResultRepository(session)
    results = [_make_result_obj()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=results))

    result = await repo.get_by_event(uuid4())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_event_result_delete_found():
    from src.infrastructure.repositories.sport_culture_repository import EventResultRepository

    session = _mock_session()
    repo = EventResultRepository(session)
    r = _make_result_obj()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=r))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(r.id)
    assert result is True


@pytest.mark.asyncio
async def test_event_result_delete_not_found():
    from src.infrastructure.repositories.sport_culture_repository import EventResultRepository

    session = _mock_session()
    repo = EventResultRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
#  EventTeamRepository
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_event_team_create():
    from src.infrastructure.repositories.sport_culture_repository import EventTeamRepository

    session = _mock_session()
    repo = EventTeamRepository(session)
    team = _make_team()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(team)
    assert result is team


@pytest.mark.asyncio
async def test_event_team_get_by_id():
    from src.infrastructure.repositories.sport_culture_repository import EventTeamRepository

    session = _mock_session()
    repo = EventTeamRepository(session)
    team = _make_team()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=team))

    result = await repo.get_by_id(team.id)
    assert result is team


@pytest.mark.asyncio
async def test_event_team_get_by_event():
    from src.infrastructure.repositories.sport_culture_repository import EventTeamRepository

    session = _mock_session()
    repo = EventTeamRepository(session)
    teams = [_make_team(), _make_team()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=teams))

    result = await repo.get_by_event(uuid4())
    assert len(result) == 2


@pytest.mark.asyncio
async def test_event_team_update():
    from src.infrastructure.repositories.sport_culture_repository import EventTeamRepository

    session = _mock_session()
    repo = EventTeamRepository(session)
    team = _make_team()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(team)
    assert result is team


@pytest.mark.asyncio
async def test_event_team_delete_found():
    from src.infrastructure.repositories.sport_culture_repository import EventTeamRepository

    session = _mock_session()
    repo = EventTeamRepository(session)
    team = _make_team()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=team))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(team.id)
    assert result is True


@pytest.mark.asyncio
async def test_event_team_delete_not_found():
    from src.infrastructure.repositories.sport_culture_repository import EventTeamRepository

    session = _mock_session()
    repo = EventTeamRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_event_team_enrich_with_captain():
    from src.infrastructure.repositories.sport_culture_repository import EventTeamRepository

    session = _mock_session()
    repo = EventTeamRepository(session)
    team = _make_team(members=[])
    captain = MagicMock()
    captain.first_name = "Marc"
    captain.last_name = "Ateba"
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=captain))

    with patch("src.infrastructure.repositories.sport_culture_repository.decrypt_str_fields"):
        await repo.enrich_team(team)

    assert team.captain_name == "Marc Ateba"


@pytest.mark.asyncio
async def test_event_team_enrich_with_members():
    from src.infrastructure.repositories.sport_culture_repository import EventTeamRepository

    session = _mock_session()
    repo = EventTeamRepository(session)
    member_id = uuid4()
    team = _make_team(members=[str(member_id)])
    captain = MagicMock()
    captain.first_name = "Marc"
    captain.last_name = "Ateba"
    member = MagicMock()
    member.id = member_id
    member.first_name = "Paul"
    member.last_name = "Nkolo"

    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar_one=captain),  # captain
            _sa_exec_result(scalars_list=[member]),  # members
        ]
    )

    with patch("src.infrastructure.repositories.sport_culture_repository.decrypt_str_fields"):
        await repo.enrich_team(team)

    assert "Paul Nkolo" in team.members_names


@pytest.mark.asyncio
async def test_event_team_enrich_no_captain():
    from src.infrastructure.repositories.sport_culture_repository import EventTeamRepository

    session = _mock_session()
    repo = EventTeamRepository(session)
    team = _make_team(members=[])
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.enrich_team(team)
    assert result is team
    assert team.captain_name is None
