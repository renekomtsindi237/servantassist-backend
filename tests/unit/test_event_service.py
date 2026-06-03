"""Unit tests for EventService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.event_service import EventService
from src.core.entities.event import (
    Event,
    EventParticipant,
    EventStatus,
    EventType,
    ParticipantRole,
    ParticipantStatus,
)
from src.core.entities.user import User, UserRole
from src.presentation.schemas.event import (
    EventCreate,
    EventUpdate,
    ParticipantAdd,
    ParticipantUpdate,
)

NOW = datetime(2026, 6, 1, 10, 0, 0)
T_START = datetime(2026, 6, 8, 9, 0, 0)
T_END = datetime(2026, 6, 8, 11, 0, 0)


# ── Factories ──────────────────────────────────────────────────────────────


def _make_event(**kwargs) -> Event:
    return Event(
        id=uuid4(),
        title="Messe Dominicale",
        start_time=T_START,
        end_time=T_END,
        location="Cathédrale",
        event_type=EventType.MESSE_DOMINICALE,
        status=EventStatus.BROUILLON,
        created_by=uuid4(),
        created_at=NOW,
        updated_at=NOW,
        **kwargs,
    )


def _make_participant(event_id=None, user_id=None, **kwargs) -> EventParticipant:
    return EventParticipant(
        id=uuid4(),
        event_id=event_id or uuid4(),
        user_id=user_id or uuid4(),
        participant_role=ParticipantRole.SERVANT,
        status=ParticipantStatus.INVITE,
        added_by=uuid4(),
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


def _participant_dict(p: EventParticipant) -> dict:
    return {
        "id": p.id,
        "event_id": p.event_id,
        "user_id": p.user_id,
        "participant_role": p.participant_role,
        "status": p.status,
        "notes": p.notes,
        "added_by": p.added_by,
        "user_first_name": None,
        "user_last_name": None,
        "user_email": None,
        "user_phone": None,
        "created_at": p.created_at,
        "updated_at": p.updated_at,
    }


def _make_event_repo(event=None):
    repo = MagicMock()
    repo.create = AsyncMock(return_value=event)
    repo.get = AsyncMock(return_value=event)
    repo.update = AsyncMock(return_value=event)
    repo.delete = AsyncMock(return_value=True)
    repo.list_paginated = AsyncMock(return_value=([], 0))
    repo.get_participant_count = AsyncMock(return_value=0)
    repo.get_events_for_user = AsyncMock(return_value=[])
    repo.add_participant = AsyncMock()
    repo.get_participant = AsyncMock(return_value=None)
    repo.get_participant_by_event_and_user = AsyncMock(return_value=None)
    repo.update_participant = AsyncMock()
    repo.remove_participant = AsyncMock()
    repo.get_participants = AsyncMock(return_value=[])
    return repo


def _make_user_repo(user=None):
    repo = MagicMock()
    repo.get = AsyncMock(return_value=user)
    return repo


def _make_svc(event_repo=None, user_repo=None) -> EventService:
    if event_repo is None:
        event_repo = _make_event_repo()
    return EventService(event_repo, user_repo)


# ── create_event ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_event_no_participants():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    event_repo.get_participants.return_value = []
    svc = _make_svc(event_repo)

    data = EventCreate(
        title="Messe",
        start_time=T_START,
        end_time=T_END,
        location="Cathédrale",
    )
    result = await svc.create_event(data, event.created_by)
    event_repo.create.assert_called_once()
    assert result.id == event.id


@pytest.mark.asyncio
async def test_create_event_with_participants():
    event = _make_event()
    user = _make_user()
    p = _make_participant(event_id=event.id, user_id=user.id)
    event_repo = _make_event_repo(event=event)
    event_repo.add_participant.return_value = p
    event_repo.get_participant_by_event_and_user.return_value = None
    event_repo.get_participants.return_value = [_participant_dict(p)]
    user_repo = _make_user_repo(user=user)
    svc = _make_svc(event_repo, user_repo)

    data = EventCreate(
        title="Messe",
        start_time=T_START,
        end_time=T_END,
        location="Cathédrale",
        participants=[ParticipantAdd(user_id=user.id)],
    )
    result = await svc.create_event(data, event.created_by)
    event_repo.add_participant.assert_called_once()
    assert len(result.participants) == 1


# ── update_event ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_event_not_found():
    svc = _make_svc()
    svc.event_repository.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.update_event(uuid4(), EventUpdate(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_event_end_before_start():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    svc = _make_svc(event_repo)

    data = EventUpdate(end_time=T_START, start_time=T_END)  # inverted
    with pytest.raises(Exception) as exc:
        await svc.update_event(event.id, data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_event_success():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    event_repo.get_participants.return_value = []
    svc = _make_svc(event_repo)

    data = EventUpdate(title="Messe Solennelle", location="Basilique")
    result = await svc.update_event(event.id, data, uuid4())
    event_repo.update.assert_called_once()
    assert result.id == event.id


@pytest.mark.asyncio
async def test_update_event_status_change():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    event_repo.get_participants.return_value = []
    svc = _make_svc(event_repo)

    data = EventUpdate(status=EventStatus.PUBLIE)
    result = await svc.update_event(event.id, data, uuid4())
    assert result.id == event.id


# ── get_event ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_event_not_found():
    svc = _make_svc()
    svc.event_repository.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_event(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_event_success():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    event_repo.get_participants.return_value = []
    svc = _make_svc(event_repo)
    result = await svc.get_event(event.id)
    assert result.id == event.id
    assert result.participants == []


# ── list_events ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_events_empty():
    svc = _make_svc()
    svc.event_repository.list_paginated.return_value = ([], 0)
    result = await svc.list_events()
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_list_events_with_items():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    event_repo.list_paginated.return_value = ([event], 1)
    event_repo.get_participant_count.return_value = 3
    svc = _make_svc(event_repo)
    result = await svc.list_events()
    assert result.total == 1
    assert result.items[0].participant_count == 3


@pytest.mark.asyncio
async def test_list_events_pagination():
    svc = _make_svc()
    svc.event_repository.list_paginated.return_value = ([], 0)
    result = await svc.list_events(page=2, page_size=5)
    assert result.page == 2
    assert result.page_size == 5


# ── delete_event ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_event_not_found():
    svc = _make_svc()
    svc.event_repository.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.delete_event(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_event_repo_fails():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    event_repo.delete.return_value = False
    svc = _make_svc(event_repo)
    with pytest.raises(Exception) as exc:
        await svc.delete_event(event.id)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_delete_event_success():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    event_repo.delete.return_value = True
    svc = _make_svc(event_repo)
    await svc.delete_event(event.id)
    event_repo.delete.assert_called_once_with(event.id)


# ── get_my_events ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_my_events_empty():
    svc = _make_svc()
    svc.event_repository.get_events_for_user.return_value = []
    result = await svc.get_my_events(uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_get_my_events_with_items():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    event_repo.get_events_for_user.return_value = [event]
    event_repo.get_participant_count.return_value = 2
    svc = _make_svc(event_repo)
    result = await svc.get_my_events(uuid4())
    assert len(result) == 1
    assert result[0].participant_count == 2


# ── add_participant ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_participant_event_not_found():
    svc = _make_svc()
    svc.event_repository.get.return_value = None
    data = ParticipantAdd(user_id=uuid4())
    with pytest.raises(Exception) as exc:
        await svc.add_participant(uuid4(), data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_participant_user_not_found():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    user_repo = _make_user_repo(user=None)
    svc = _make_svc(event_repo, user_repo)
    data = ParticipantAdd(user_id=uuid4())
    with pytest.raises(Exception) as exc:
        await svc.add_participant(event.id, data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_participant_duplicate():
    event = _make_event()
    user = _make_user()
    existing_p = _make_participant(event_id=event.id, user_id=user.id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participant_by_event_and_user.return_value = existing_p
    user_repo = _make_user_repo(user=user)
    svc = _make_svc(event_repo, user_repo)
    data = ParticipantAdd(user_id=user.id)
    with pytest.raises(Exception) as exc:
        await svc.add_participant(event.id, data, uuid4())
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_add_participant_success_with_user_repo():
    event = _make_event()
    user = _make_user()
    p = _make_participant(event_id=event.id, user_id=user.id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participant_by_event_and_user.return_value = None
    event_repo.add_participant.return_value = p
    user_repo = _make_user_repo(user=user)
    svc = _make_svc(event_repo, user_repo)
    data = ParticipantAdd(user_id=user.id)
    result = await svc.add_participant(event.id, data, uuid4())
    assert result.user_id == user.id
    assert result.user_first_name == user.first_name


@pytest.mark.asyncio
async def test_add_participant_success_no_user_repo():
    """Without user_repo, participant can be added without user validation."""
    event = _make_event()
    user_id = uuid4()
    p = _make_participant(event_id=event.id, user_id=user_id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participant_by_event_and_user.return_value = None
    event_repo.add_participant.return_value = p
    svc = _make_svc(event_repo, user_repo=None)
    data = ParticipantAdd(user_id=user_id)
    result = await svc.add_participant(event.id, data, uuid4())
    assert result.user_id == user_id
    assert result.user_first_name is None


# ── update_participant ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_participant_not_found():
    svc = _make_svc()
    svc.event_repository.get_participant.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.update_participant(uuid4(), uuid4(), ParticipantUpdate())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_participant_wrong_event():
    event_id = uuid4()
    p = _make_participant(event_id=uuid4())  # different event
    svc = _make_svc()
    svc.event_repository.get_participant.return_value = p
    with pytest.raises(Exception) as exc:
        await svc.update_participant(event_id, p.id, ParticipantUpdate())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_participant_success():
    event = _make_event()
    p = _make_participant(event_id=event.id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participant.return_value = p
    event_repo.update_participant.return_value = p
    user_repo = _make_user_repo(user=None)
    svc = _make_svc(event_repo, user_repo)

    data = ParticipantUpdate(status=ParticipantStatus.CONFIRME, notes="OK")
    result = await svc.update_participant(event.id, p.id, data)
    assert result.id == p.id


@pytest.mark.asyncio
async def test_update_participant_with_user_info():
    event = _make_event()
    user = _make_user()
    p = _make_participant(event_id=event.id, user_id=user.id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participant.return_value = p
    event_repo.update_participant.return_value = p
    user_repo = _make_user_repo(user=user)
    svc = _make_svc(event_repo, user_repo)

    data = ParticipantUpdate(participant_role=ParticipantRole.ACOLYTE)
    result = await svc.update_participant(event.id, p.id, data)
    assert result.user_first_name == user.first_name


# ── remove_participant ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_participant_not_found():
    svc = _make_svc()
    svc.event_repository.get_participant.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.remove_participant(uuid4(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_remove_participant_wrong_event():
    p = _make_participant(event_id=uuid4())
    svc = _make_svc()
    svc.event_repository.get_participant.return_value = p
    with pytest.raises(Exception) as exc:
        await svc.remove_participant(uuid4(), p.id)  # different event_id
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_remove_participant_success():
    event = _make_event()
    p = _make_participant(event_id=event.id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participant.return_value = p
    svc = _make_svc(event_repo)
    await svc.remove_participant(event.id, p.id)
    event_repo.remove_participant.assert_called_once_with(p.id)


# ── get_event_participants ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_event_participants_event_not_found():
    svc = _make_svc()
    svc.event_repository.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_event_participants(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_event_participants_success():
    event = _make_event()
    p = _make_participant(event_id=event.id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participants.return_value = [_participant_dict(p)]
    svc = _make_svc(event_repo)
    result = await svc.get_event_participants(event.id)
    assert len(result) == 1
    assert result[0].id == p.id


@pytest.mark.asyncio
async def test_get_event_participants_empty():
    event = _make_event()
    event_repo = _make_event_repo(event=event)
    event_repo.get_participants.return_value = []
    svc = _make_svc(event_repo)
    result = await svc.get_event_participants(event.id)
    assert result == []


# ── update_my_participation ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_my_participation_not_found():
    svc = _make_svc()
    svc.event_repository.get_participant_by_event_and_user.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.update_my_participation(uuid4(), uuid4(), ParticipantStatus.CONFIRME)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_my_participation_invalid_status():
    event = _make_event()
    user = _make_user()
    p = _make_participant(event_id=event.id, user_id=user.id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participant_by_event_and_user.return_value = p
    svc = _make_svc(event_repo)
    with pytest.raises(Exception) as exc:
        await svc.update_my_participation(event.id, user.id, ParticipantStatus.PRESENT)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_my_participation_confirme():
    event = _make_event()
    user = _make_user()
    p = _make_participant(event_id=event.id, user_id=user.id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participant_by_event_and_user.return_value = p
    event_repo.update_participant.return_value = p
    user_repo = _make_user_repo(user=None)
    svc = _make_svc(event_repo, user_repo)
    result = await svc.update_my_participation(event.id, user.id, ParticipantStatus.CONFIRME)
    assert result.id == p.id


@pytest.mark.asyncio
async def test_update_my_participation_decline():
    event = _make_event()
    user = _make_user()
    p = _make_participant(event_id=event.id, user_id=user.id)
    event_repo = _make_event_repo(event=event)
    event_repo.get_participant_by_event_and_user.return_value = p
    event_repo.update_participant.return_value = p
    user_repo = _make_user_repo(user=user)
    svc = _make_svc(event_repo, user_repo)
    result = await svc.update_my_participation(event.id, user.id, ParticipantStatus.DECLINE)
    assert result.user_first_name == user.first_name
