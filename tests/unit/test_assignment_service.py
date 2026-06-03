"""Unit tests for AssignmentService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.assignment_service import AssignmentService
from src.core.entities.assignment import Assignment, AssignmentStatus, LiturgicalRole
from src.core.entities.event import Event, EventStatus, EventType
from src.core.entities.user import User, UserRole
from src.presentation.schemas.assignment import (
    AssignmentBatchCreate,
    AssignmentBatchItem,
    AssignmentCreate,
    AssignmentStatusUpdate,
    AssignmentUpdate,
)

NOW = datetime(2026, 6, 1, 10, 0, 0)
T_START = datetime(2026, 6, 8, 9, 0, 0)
T_END = datetime(2026, 6, 8, 11, 0, 0)


# ── Factories ──────────────────────────────────────────────────────────────


def _make_event(**kwargs) -> Event:
    return Event(
        id=uuid4(),
        title="Messe",
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


def _make_user(role=UserRole.SERVANT, is_active=True) -> User:
    return User(
        id=uuid4(),
        first_name="Jean",
        last_name="Pierre",
        email="jean@test.com",
        hashed_password="x",
        role=role,
        is_active=is_active,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_assignment(user_id=None, event_id=None, **kwargs) -> Assignment:
    return Assignment(
        id=uuid4(),
        event_id=event_id or uuid4(),
        user_id=user_id or uuid4(),
        liturgical_role=kwargs.pop("liturgical_role", LiturgicalRole.ACOLYTE),
        status=kwargs.pop("status", AssignmentStatus.PENDING),
        assigned_by=kwargs.pop("assigned_by", uuid4()),
        created_at=kwargs.pop("created_at", NOW),
        updated_at=kwargs.pop("updated_at", NOW),
        **kwargs,
    )


def _enriched_assignment(a: Assignment) -> dict:
    return {
        "id": a.id,
        "event_id": a.event_id,
        "user_id": a.user_id,
        "liturgical_role": a.liturgical_role,
        "status": a.status,
        "notes": a.notes,
        "assigned_by": a.assigned_by,
        "user_first_name": None,
        "user_last_name": None,
        "user_email": None,
        "user_phone": None,
        "event_title": None,
        "event_type": None,
        "event_start_time": None,
        "event_location": None,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


def _make_svc(assignment_repo=None, event_repo=None, user_repo=None) -> AssignmentService:
    if assignment_repo is None:
        assignment_repo = MagicMock()
        assignment_repo.create = AsyncMock()
        assignment_repo.get = AsyncMock(return_value=None)
        assignment_repo.update = AsyncMock()
        assignment_repo.delete = AsyncMock(return_value=True)
        assignment_repo.list_paginated = AsyncMock(return_value=([], 0))
        assignment_repo.list_by_event = AsyncMock(return_value=[])
        assignment_repo.list_by_user = AsyncMock(return_value=[])
        assignment_repo.get_upcoming_for_user = AsyncMock(return_value=[])
        assignment_repo.get_by_event_user_role = AsyncMock(return_value=None)
        assignment_repo.enrich_assignment = AsyncMock(return_value={})
        assignment_repo.enrich_assignments = AsyncMock(return_value=[])
    if event_repo is None:
        event_repo = MagicMock()
        event_repo.get = AsyncMock(return_value=None)
    if user_repo is None:
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=None)
    return AssignmentService(assignment_repo, event_repo, user_repo)


# ── create_assignment ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_assignment_event_not_found():
    svc = _make_svc()
    svc.event_repo.get.return_value = None
    data = AssignmentCreate(event_id=uuid4(), user_id=uuid4())
    with pytest.raises(Exception) as exc:
        await svc.create_assignment(data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_assignment_user_not_found():
    event = _make_event()
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.return_value = None
    data = AssignmentCreate(event_id=event.id, user_id=uuid4())
    with pytest.raises(Exception) as exc:
        await svc.create_assignment(data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_assignment_user_inactive():
    event = _make_event()
    user = _make_user(is_active=False)
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.return_value = user
    data = AssignmentCreate(event_id=event.id, user_id=user.id)
    with pytest.raises(Exception) as exc:
        await svc.create_assignment(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_assignment_not_servant():
    event = _make_event()
    user = _make_user(role=UserRole.PARENT)
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.return_value = user
    data = AssignmentCreate(event_id=event.id, user_id=user.id)
    with pytest.raises(Exception) as exc:
        await svc.create_assignment(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_assignment_duplicate():
    event = _make_event()
    user = _make_user(role=UserRole.SERVANT)
    existing = _make_assignment(user_id=user.id, event_id=event.id)
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.return_value = user
    svc.assignment_repo.get_by_event_user_role.return_value = existing
    data = AssignmentCreate(event_id=event.id, user_id=user.id, liturgical_role=LiturgicalRole.ACOLYTE)
    with pytest.raises(Exception) as exc:
        await svc.create_assignment(data, uuid4())
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_create_assignment_success():
    event = _make_event()
    user = _make_user(role=UserRole.SERVANT)
    a = _make_assignment(user_id=user.id, event_id=event.id)
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.return_value = user
    svc.assignment_repo.get_by_event_user_role.return_value = None
    svc.assignment_repo.create.return_value = a
    svc.assignment_repo.enrich_assignment.return_value = _enriched_assignment(a)
    data = AssignmentCreate(event_id=event.id, user_id=user.id)
    result = await svc.create_assignment(data, uuid4())
    assert result.id == a.id


# ── create_batch ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_batch_event_not_found():
    svc = _make_svc()
    svc.event_repo.get.return_value = None
    data = AssignmentBatchCreate(
        event_id=uuid4(),
        assignments=[AssignmentBatchItem(user_id=uuid4())],
    )
    with pytest.raises(Exception) as exc:
        await svc.create_batch(data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_batch_user_not_found_is_error():
    event = _make_event()
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.return_value = None
    data = AssignmentBatchCreate(
        event_id=event.id,
        assignments=[AssignmentBatchItem(user_id=uuid4())],
    )
    result = await svc.create_batch(data, uuid4())
    assert result.total_created == 0
    assert result.total_errors == 1


@pytest.mark.asyncio
async def test_create_batch_inactive_user_is_error():
    event = _make_event()
    user = _make_user(is_active=False)
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.return_value = user
    data = AssignmentBatchCreate(
        event_id=event.id,
        assignments=[AssignmentBatchItem(user_id=user.id)],
    )
    result = await svc.create_batch(data, uuid4())
    assert result.total_errors == 1
    assert result.total_created == 0


@pytest.mark.asyncio
async def test_create_batch_non_servant_is_error():
    event = _make_event()
    user = _make_user(role=UserRole.PARENT)
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.return_value = user
    data = AssignmentBatchCreate(
        event_id=event.id,
        assignments=[AssignmentBatchItem(user_id=user.id)],
    )
    result = await svc.create_batch(data, uuid4())
    assert result.total_errors == 1


@pytest.mark.asyncio
async def test_create_batch_duplicate_is_error():
    event = _make_event()
    user = _make_user(role=UserRole.SERVANT)
    existing = _make_assignment(user_id=user.id, event_id=event.id)
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.return_value = user
    svc.assignment_repo.get_by_event_user_role.return_value = existing
    data = AssignmentBatchCreate(
        event_id=event.id,
        assignments=[AssignmentBatchItem(user_id=user.id)],
    )
    result = await svc.create_batch(data, uuid4())
    assert result.total_errors == 1
    assert result.total_created == 0


@pytest.mark.asyncio
async def test_create_batch_success():
    event = _make_event()
    user1 = _make_user(role=UserRole.SERVANT)
    user2 = _make_user(role=UserRole.SERVANT)
    a1 = _make_assignment(user_id=user1.id, event_id=event.id)
    a2 = _make_assignment(user_id=user2.id, event_id=event.id)
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.user_repo.get.side_effect = [user1, user2]
    svc.assignment_repo.get_by_event_user_role.return_value = None
    svc.assignment_repo.create.side_effect = [a1, a2]
    svc.assignment_repo.enrich_assignment.side_effect = [
        _enriched_assignment(a1),
        _enriched_assignment(a2),
    ]
    data = AssignmentBatchCreate(
        event_id=event.id,
        assignments=[
            AssignmentBatchItem(user_id=user1.id),
            AssignmentBatchItem(user_id=user2.id),
        ],
    )
    result = await svc.create_batch(data, uuid4())
    assert result.total_created == 2
    assert result.total_errors == 0


# ── get_assignment ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_assignment_not_found():
    svc = _make_svc()
    svc.assignment_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_assignment(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_assignment_success():
    a = _make_assignment()
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.enrich_assignment.return_value = _enriched_assignment(a)
    result = await svc.get_assignment(a.id)
    assert result.id == a.id


# ── list_assignments ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_assignments_empty():
    svc = _make_svc()
    svc.assignment_repo.list_paginated.return_value = ([], 0)
    svc.assignment_repo.enrich_assignments.return_value = []
    result = await svc.list_assignments()
    assert result.total == 0


@pytest.mark.asyncio
async def test_list_assignments_with_items():
    a = _make_assignment()
    svc = _make_svc()
    svc.assignment_repo.list_paginated.return_value = ([a], 1)
    svc.assignment_repo.enrich_assignments.return_value = [_enriched_assignment(a)]
    result = await svc.list_assignments()
    assert result.total == 1


# ── get_event_assignments ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_event_assignments_event_not_found():
    svc = _make_svc()
    svc.event_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_event_assignments(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_event_assignments_filters_cancelled():
    event = _make_event()
    a_active = _make_assignment(event_id=event.id, status=AssignmentStatus.PENDING)
    a_cancelled = _make_assignment(event_id=event.id, status=AssignmentStatus.CANCELLED)
    svc = _make_svc()
    svc.event_repo.get.return_value = event
    svc.assignment_repo.list_by_event.return_value = [a_active, a_cancelled]
    svc.assignment_repo.enrich_assignments.return_value = [_enriched_assignment(a_active)]
    result = await svc.get_event_assignments(event.id)
    # Only active ones passed to enrich
    passed = svc.assignment_repo.enrich_assignments.call_args[0][0]
    assert len(passed) == 1
    assert passed[0].status == AssignmentStatus.PENDING


@pytest.mark.asyncio
async def test_get_my_assignments():
    a = _make_assignment()
    svc = _make_svc()
    svc.assignment_repo.list_by_user.return_value = [a]
    svc.assignment_repo.enrich_assignments.return_value = [_enriched_assignment(a)]
    result = await svc.get_my_assignments(a.user_id)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_get_my_upcoming():
    a = _make_assignment()
    svc = _make_svc()
    svc.assignment_repo.get_upcoming_for_user.return_value = [a]
    svc.assignment_repo.enrich_assignments.return_value = [_enriched_assignment(a)]
    result = await svc.get_my_upcoming(a.user_id)
    assert len(result) == 1


# ── update_assignment ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_assignment_not_found():
    svc = _make_svc()
    svc.assignment_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.update_assignment(uuid4(), AssignmentUpdate(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_assignment_role_conflict():
    event_id = uuid4()
    user_id = uuid4()
    a = _make_assignment(user_id=user_id, event_id=event_id, liturgical_role=LiturgicalRole.ACOLYTE)
    # Another assignment with same role
    other = _make_assignment(user_id=user_id, event_id=event_id, liturgical_role=LiturgicalRole.CRUCIFER)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.get_by_event_user_role.return_value = other  # different id
    data = AssignmentUpdate(liturgical_role=LiturgicalRole.CRUCIFER)
    with pytest.raises(Exception) as exc:
        await svc.update_assignment(a.id, data, uuid4())
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_update_assignment_same_role_no_conflict():
    """Changing to same role should not raise."""
    a = _make_assignment(liturgical_role=LiturgicalRole.ACOLYTE)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.update.return_value = a
    svc.assignment_repo.enrich_assignment.return_value = _enriched_assignment(a)
    data = AssignmentUpdate(liturgical_role=LiturgicalRole.ACOLYTE)  # same role
    result = await svc.update_assignment(a.id, data, uuid4())
    assert result.id == a.id


@pytest.mark.asyncio
async def test_update_assignment_success():
    a = _make_assignment(liturgical_role=LiturgicalRole.ACOLYTE)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.get_by_event_user_role.return_value = None
    svc.assignment_repo.update.return_value = a
    svc.assignment_repo.enrich_assignment.return_value = _enriched_assignment(a)
    data = AssignmentUpdate(liturgical_role=LiturgicalRole.CRUCIFER, status=AssignmentStatus.ACCEPTED, notes="OK")
    result = await svc.update_assignment(a.id, data, uuid4())
    assert result.id == a.id


# ── update_my_status ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_my_status_not_found():
    svc = _make_svc()
    svc.assignment_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.update_my_status(uuid4(), AssignmentStatusUpdate(status=AssignmentStatus.ACCEPTED), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_my_status_wrong_user():
    user_id = uuid4()
    a = _make_assignment(user_id=user_id)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    with pytest.raises(Exception) as exc:
        await svc.update_my_status(a.id, AssignmentStatusUpdate(status=AssignmentStatus.ACCEPTED), uuid4())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_my_status_not_pending():
    user_id = uuid4()
    a = _make_assignment(user_id=user_id, status=AssignmentStatus.ACCEPTED)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    with pytest.raises(Exception) as exc:
        await svc.update_my_status(a.id, AssignmentStatusUpdate(status=AssignmentStatus.DECLINED), user_id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_my_status_invalid_transition():
    user_id = uuid4()
    a = _make_assignment(user_id=user_id, status=AssignmentStatus.PENDING)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    with pytest.raises(Exception) as exc:
        await svc.update_my_status(a.id, AssignmentStatusUpdate(status=AssignmentStatus.PRESENT), user_id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_my_status_accept():
    user_id = uuid4()
    a = _make_assignment(user_id=user_id, status=AssignmentStatus.PENDING)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.update.return_value = a
    svc.assignment_repo.enrich_assignment.return_value = _enriched_assignment(a)
    result = await svc.update_my_status(a.id, AssignmentStatusUpdate(status=AssignmentStatus.ACCEPTED), user_id)
    assert result.id == a.id


@pytest.mark.asyncio
async def test_update_my_status_decline():
    user_id = uuid4()
    a = _make_assignment(user_id=user_id, status=AssignmentStatus.PENDING)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.update.return_value = a
    svc.assignment_repo.enrich_assignment.return_value = _enriched_assignment(a)
    result = await svc.update_my_status(a.id, AssignmentStatusUpdate(status=AssignmentStatus.DECLINED), user_id)
    assert result.id == a.id


# ── delete_assignment ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_assignment_not_found():
    svc = _make_svc()
    svc.assignment_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.delete_assignment(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_assignment_repo_fails():
    a = _make_assignment()
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.delete.return_value = False
    with pytest.raises(Exception) as exc:
        await svc.delete_assignment(a.id)
    assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_delete_assignment_success():
    a = _make_assignment()
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.delete.return_value = True
    await svc.delete_assignment(a.id)
    svc.assignment_repo.delete.assert_called_once_with(a.id)


# ── cancel_assignment ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_assignment_not_found():
    svc = _make_svc()
    svc.assignment_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.cancel_assignment(uuid4(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_cancel_assignment_already_cancelled():
    a = _make_assignment(status=AssignmentStatus.CANCELLED)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    with pytest.raises(Exception) as exc:
        await svc.cancel_assignment(a.id, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_cancel_assignment_success():
    a = _make_assignment(status=AssignmentStatus.PENDING)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.update.return_value = a
    svc.assignment_repo.enrich_assignment.return_value = _enriched_assignment(a)
    result = await svc.cancel_assignment(a.id, uuid4())
    assert result.id == a.id


# ── mark_presence ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mark_presence_not_found():
    svc = _make_svc()
    svc.assignment_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.mark_presence(uuid4(), True, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_presence_cancelled():
    a = _make_assignment(status=AssignmentStatus.CANCELLED)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    with pytest.raises(Exception) as exc:
        await svc.mark_presence(a.id, True, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_mark_presence_present():
    a = _make_assignment(status=AssignmentStatus.ACCEPTED)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.update.return_value = a
    svc.assignment_repo.enrich_assignment.return_value = _enriched_assignment(a)
    result = await svc.mark_presence(a.id, True, uuid4())
    assert result.id == a.id


@pytest.mark.asyncio
async def test_mark_presence_absent():
    a = _make_assignment(status=AssignmentStatus.ACCEPTED)
    svc = _make_svc()
    svc.assignment_repo.get.return_value = a
    svc.assignment_repo.update.return_value = a
    svc.assignment_repo.enrich_assignment.return_value = _enriched_assignment(a)
    result = await svc.mark_presence(a.id, False, uuid4())
    assert result.id == a.id
