"""
Unit tests for AttendanceService.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException

from src.application.services.attendance_service import AttendanceService
from src.core.entities.attendance import Attendance, AttendanceStatus, AttendanceType
from src.core.entities.user import User, UserRole
from src.presentation.schemas.attendance import (
    AttendanceBatchCreate,
    AttendanceBatchItem,
    AttendanceCreate,
    AttendanceUpdate,
)

NOW = datetime(2026, 6, 1, 10, 0, 0)
TODAY = datetime(2026, 6, 1, 0, 0, 0)


# ─── Factories ────────────────────────────────────────────────────────────────

def _make_attendance(**kwargs) -> Attendance:
    return Attendance(
        id=kwargs.pop("id", uuid4()),
        user_id=kwargs.pop("user_id", uuid4()),
        event_id=kwargs.pop("event_id", None),
        attendance_type=kwargs.pop("attendance_type", AttendanceType.MESSE_CLASSEMENT),
        attendance_date=kwargs.pop("attendance_date", TODAY),
        title=kwargs.pop("title", "Messe du dimanche"),
        status=kwargs.pop("status", AttendanceStatus.PRESENT),
        justification=kwargs.pop("justification", None),
        justified_at=kwargs.pop("justified_at", None),
        recorded_by=kwargs.pop("recorded_by", uuid4()),
        created_at=kwargs.pop("created_at", NOW),
        updated_at=kwargs.pop("updated_at", NOW),
        **kwargs,
    )


def _make_user(role=UserRole.SERVANT) -> User:
    return User(
        id=uuid4(),
        first_name="Jean",
        last_name="Dupont",
        email=f"jean_{uuid4().hex[:6]}@test.com",
        role=role,
        is_active=True,
    )


def _enriched_attendance(a: Attendance) -> dict:
    return {
        "id": a.id,
        "user_id": a.user_id,
        "event_id": a.event_id,
        "attendance_type": a.attendance_type,
        "attendance_date": a.attendance_date,
        "title": a.title,
        "status": a.status,
        "justification": a.justification,
        "justified_at": a.justified_at,
        "recorded_by": a.recorded_by,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "user_first_name": "Jean",
        "user_last_name": "Dupont",
    }


def _make_svc(attendance_repo=None, user_repo=None) -> AttendanceService:
    if attendance_repo is None:
        attendance_repo = AsyncMock()
    if user_repo is None:
        user_repo = AsyncMock()
    return AttendanceService(attendance_repo=attendance_repo, user_repo=user_repo)


# ─── record_attendance ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_attendance_user_not_found():
    user_repo = AsyncMock()
    user_repo.get.return_value = None
    svc = _make_svc(user_repo=user_repo)

    data = AttendanceCreate(
        user_id=uuid4(),
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=TODAY,
        status=AttendanceStatus.PRESENT,
    )
    with pytest.raises(HTTPException) as exc:
        await svc.record_attendance(data, recorded_by=uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_record_attendance_duplicate():
    user = _make_user()
    existing = _make_attendance(user_id=user.id)

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    attendance_repo = AsyncMock()
    attendance_repo.get_by_user_date_type.return_value = existing

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    data = AttendanceCreate(
        user_id=user.id,
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=TODAY,
        status=AttendanceStatus.PRESENT,
    )
    with pytest.raises(HTTPException) as exc:
        await svc.record_attendance(data, recorded_by=uuid4())
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_record_attendance_success_no_justification():
    user = _make_user()
    recorded_by = uuid4()
    created = _make_attendance(user_id=user.id, status=AttendanceStatus.PRESENT)

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    attendance_repo = AsyncMock()
    attendance_repo.get_by_user_date_type.return_value = None
    attendance_repo.create.return_value = created
    attendance_repo.enrich_attendance.return_value = _enriched_attendance(created)

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    data = AttendanceCreate(
        user_id=user.id,
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=TODAY,
        status=AttendanceStatus.PRESENT,
    )
    result = await svc.record_attendance(data, recorded_by=recorded_by)

    assert result.user_id == user.id
    assert result.status == AttendanceStatus.PRESENT
    assert result.justification is None

    created_obj = attendance_repo.create.call_args[0][0]
    assert created_obj.justified_at is None


@pytest.mark.asyncio
async def test_record_attendance_success_with_justification():
    user = _make_user()
    recorded_by = uuid4()
    created = _make_attendance(
        user_id=user.id,
        status=AttendanceStatus.ABSENT_JUSTIFIE,
        justification="Maladie",
    )

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    attendance_repo = AsyncMock()
    attendance_repo.get_by_user_date_type.return_value = None
    attendance_repo.create.return_value = created
    attendance_repo.enrich_attendance.return_value = _enriched_attendance(created)

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    data = AttendanceCreate(
        user_id=user.id,
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=TODAY,
        status=AttendanceStatus.ABSENT_JUSTIFIE,
        justification="Maladie",
    )
    result = await svc.record_attendance(data, recorded_by=recorded_by)

    assert result.justification == "Maladie"

    created_obj = attendance_repo.create.call_args[0][0]
    assert created_obj.justified_at is not None


# ─── record_batch ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_record_batch_user_not_found():
    user_repo = AsyncMock()
    user_repo.get.return_value = None

    attendance_repo = AsyncMock()

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    data = AttendanceBatchCreate(
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=TODAY,
        entries=[AttendanceBatchItem(user_id=uuid4(), status=AttendanceStatus.PRESENT)],
    )
    result = await svc.record_batch(data, recorded_by=uuid4())

    assert result.total_created == 0
    assert result.total_errors == 1
    assert "introuvable" in result.errors[0]


@pytest.mark.asyncio
async def test_record_batch_duplicate():
    user = _make_user()
    existing = _make_attendance(user_id=user.id)

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    attendance_repo = AsyncMock()
    attendance_repo.get_by_user_date_type.return_value = existing

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    data = AttendanceBatchCreate(
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=TODAY,
        entries=[AttendanceBatchItem(user_id=user.id, status=AttendanceStatus.PRESENT)],
    )
    result = await svc.record_batch(data, recorded_by=uuid4())

    assert result.total_created == 0
    assert result.total_errors == 1
    assert "deja enregistre" in result.errors[0]


@pytest.mark.asyncio
async def test_record_batch_success_two_servants():
    user1 = _make_user()
    user2 = _make_user()
    att1 = _make_attendance(user_id=user1.id)
    att2 = _make_attendance(user_id=user2.id)

    user_repo = AsyncMock()
    user_repo.get.side_effect = lambda uid: user1 if uid == user1.id else user2

    attendance_repo = AsyncMock()
    attendance_repo.get_by_user_date_type.return_value = None
    attendance_repo.create.side_effect = [att1, att2]
    attendance_repo.enrich_attendance.side_effect = [
        _enriched_attendance(att1),
        _enriched_attendance(att2),
    ]

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    data = AttendanceBatchCreate(
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=TODAY,
        entries=[
            AttendanceBatchItem(user_id=user1.id, status=AttendanceStatus.PRESENT),
            AttendanceBatchItem(user_id=user2.id, status=AttendanceStatus.ABSENT),
        ],
    )
    result = await svc.record_batch(data, recorded_by=uuid4())

    assert result.total_created == 2
    assert result.total_errors == 0
    assert len(result.created) == 2


@pytest.mark.asyncio
async def test_record_batch_mixed_success_and_error():
    user1 = _make_user()
    att1 = _make_attendance(user_id=user1.id)

    user_repo = AsyncMock()
    user_repo.get.side_effect = lambda uid: user1 if uid == user1.id else None

    attendance_repo = AsyncMock()
    attendance_repo.get_by_user_date_type.return_value = None
    attendance_repo.create.return_value = att1
    attendance_repo.enrich_attendance.return_value = _enriched_attendance(att1)

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    missing_id = uuid4()
    data = AttendanceBatchCreate(
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=TODAY,
        entries=[
            AttendanceBatchItem(user_id=user1.id, status=AttendanceStatus.PRESENT),
            AttendanceBatchItem(user_id=missing_id, status=AttendanceStatus.ABSENT),
        ],
    )
    result = await svc.record_batch(data, recorded_by=uuid4())

    assert result.total_created == 1
    assert result.total_errors == 1


@pytest.mark.asyncio
async def test_record_batch_with_justification_sets_justified_at():
    user = _make_user()
    att = _make_attendance(user_id=user.id, justification="Voyage")

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    attendance_repo = AsyncMock()
    attendance_repo.get_by_user_date_type.return_value = None
    attendance_repo.create.return_value = att
    attendance_repo.enrich_attendance.return_value = _enriched_attendance(att)

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    data = AttendanceBatchCreate(
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=TODAY,
        entries=[
            AttendanceBatchItem(
                user_id=user.id,
                status=AttendanceStatus.ABSENT_JUSTIFIE,
                justification="Voyage",
            )
        ],
    )
    result = await svc.record_batch(data, recorded_by=uuid4())

    assert result.total_created == 1
    created_obj = attendance_repo.create.call_args[0][0]
    assert created_obj.justified_at is not None


# ─── update_attendance ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_attendance_not_found():
    attendance_repo = AsyncMock()
    attendance_repo.get.return_value = None

    svc = _make_svc(attendance_repo=attendance_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.update_attendance(uuid4(), AttendanceUpdate(status=AttendanceStatus.ABSENT))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_attendance_status_only():
    att = _make_attendance(status=AttendanceStatus.PRESENT)
    updated = _make_attendance(id=att.id, user_id=att.user_id, status=AttendanceStatus.EN_RETARD)

    attendance_repo = AsyncMock()
    attendance_repo.get.return_value = att
    attendance_repo.update.return_value = updated
    attendance_repo.enrich_attendance.return_value = _enriched_attendance(updated)

    svc = _make_svc(attendance_repo=attendance_repo)

    result = await svc.update_attendance(att.id, AttendanceUpdate(status=AttendanceStatus.EN_RETARD))

    assert result.status == AttendanceStatus.EN_RETARD
    assert att.status == AttendanceStatus.EN_RETARD


@pytest.mark.asyncio
async def test_update_attendance_justification_auto_sets_absent_justifie():
    att = _make_attendance(status=AttendanceStatus.ABSENT, justification=None)
    updated = _make_attendance(
        id=att.id,
        user_id=att.user_id,
        status=AttendanceStatus.ABSENT_JUSTIFIE,
        justification="Maladie",
    )

    attendance_repo = AsyncMock()
    attendance_repo.get.return_value = att
    attendance_repo.update.return_value = updated
    attendance_repo.enrich_attendance.return_value = _enriched_attendance(updated)

    svc = _make_svc(attendance_repo=attendance_repo)

    result = await svc.update_attendance(att.id, AttendanceUpdate(justification="Maladie"))

    assert att.status == AttendanceStatus.ABSENT_JUSTIFIE
    assert att.justified_at is not None


@pytest.mark.asyncio
async def test_update_attendance_justification_no_status_change_when_not_absent():
    att = _make_attendance(status=AttendanceStatus.EN_RETARD, justification=None)
    updated = _make_attendance(
        id=att.id,
        user_id=att.user_id,
        status=AttendanceStatus.EN_RETARD,
        justification="Expliqué",
    )

    attendance_repo = AsyncMock()
    attendance_repo.get.return_value = att
    attendance_repo.update.return_value = updated
    attendance_repo.enrich_attendance.return_value = _enriched_attendance(updated)

    svc = _make_svc(attendance_repo=attendance_repo)

    await svc.update_attendance(att.id, AttendanceUpdate(justification="Expliqué"))

    assert att.status == AttendanceStatus.EN_RETARD


# ─── get_attendance ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_attendance_not_found():
    attendance_repo = AsyncMock()
    attendance_repo.get.return_value = None

    svc = _make_svc(attendance_repo=attendance_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.get_attendance(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_attendance_success():
    att = _make_attendance()

    attendance_repo = AsyncMock()
    attendance_repo.get.return_value = att
    attendance_repo.enrich_attendance.return_value = _enriched_attendance(att)

    svc = _make_svc(attendance_repo=attendance_repo)

    result = await svc.get_attendance(att.id)

    assert result.id == att.id
    assert result.user_first_name == "Jean"


# ─── list_attendances ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_attendances_empty():
    attendance_repo = AsyncMock()
    attendance_repo.list_paginated.return_value = ([], 0)
    attendance_repo.enrich_attendances.return_value = []

    svc = _make_svc(attendance_repo=attendance_repo)

    result = await svc.list_attendances(page=1, page_size=20)

    assert result.total == 0
    assert result.items == []
    assert result.total_pages == 1


@pytest.mark.asyncio
async def test_list_attendances_with_items():
    att1 = _make_attendance()
    att2 = _make_attendance()

    attendance_repo = AsyncMock()
    attendance_repo.list_paginated.return_value = ([att1, att2], 2)
    attendance_repo.enrich_attendances.return_value = [
        _enriched_attendance(att1),
        _enriched_attendance(att2),
    ]

    svc = _make_svc(attendance_repo=attendance_repo)

    result = await svc.list_attendances(page=1, page_size=20)

    assert result.total == 2
    assert len(result.items) == 2
    assert result.total_pages == 1


@pytest.mark.asyncio
async def test_list_attendances_pagination_math():
    attendances = [_make_attendance() for _ in range(5)]

    attendance_repo = AsyncMock()
    attendance_repo.list_paginated.return_value = (attendances, 25)
    attendance_repo.enrich_attendances.return_value = [_enriched_attendance(a) for a in attendances]

    svc = _make_svc(attendance_repo=attendance_repo)

    result = await svc.list_attendances(page=2, page_size=10)

    assert result.total == 25
    assert result.total_pages == 3
    assert result.page == 2


@pytest.mark.asyncio
async def test_list_attendances_passes_filters():
    uid = uuid4()
    attendance_repo = AsyncMock()
    attendance_repo.list_paginated.return_value = ([], 0)
    attendance_repo.enrich_attendances.return_value = []

    svc = _make_svc(attendance_repo=attendance_repo)

    await svc.list_attendances(
        user_id=uid,
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_status=AttendanceStatus.ABSENT,
        page=1,
        page_size=10,
    )

    call_kwargs = attendance_repo.list_paginated.call_args.kwargs
    assert call_kwargs["user_id"] == uid
    assert call_kwargs["attendance_type"] == AttendanceType.MESSE_CLASSEMENT
    assert call_kwargs["status"] == AttendanceStatus.ABSENT


# ─── get_user_stats ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_user_stats_user_not_found():
    user_repo = AsyncMock()
    user_repo.get.return_value = None

    svc = _make_svc(user_repo=user_repo)

    with pytest.raises(HTTPException) as exc:
        await svc.get_user_stats(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_user_stats_with_counts():
    user = _make_user()

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    counts = {
        AttendanceStatus.PRESENT.value: 7,
        AttendanceStatus.ABSENT.value: 2,
        AttendanceStatus.ABSENT_JUSTIFIE.value: 1,
        AttendanceStatus.EN_RETARD.value: 0,
        AttendanceStatus.EXCUSE.value: 0,
    }

    attendance_repo = AsyncMock()
    attendance_repo.get_user_stats.return_value = counts

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    result = await svc.get_user_stats(user.id)

    assert result.total_entries == 10
    assert result.presents == 7
    assert result.absents == 2
    assert result.absents_justifies == 1
    assert result.taux_presence == 70.0
    assert result.user_first_name == "Jean"
    assert result.user_last_name == "Dupont"


@pytest.mark.asyncio
async def test_get_user_stats_zero_total():
    user = _make_user()

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    attendance_repo = AsyncMock()
    attendance_repo.get_user_stats.return_value = {}

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    result = await svc.get_user_stats(user.id)

    assert result.total_entries == 0
    assert result.taux_presence == 0.0


@pytest.mark.asyncio
async def test_get_user_stats_perfect_attendance():
    user = _make_user()

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    counts = {
        AttendanceStatus.PRESENT.value: 12,
    }

    attendance_repo = AsyncMock()
    attendance_repo.get_user_stats.return_value = counts

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    result = await svc.get_user_stats(user.id)

    assert result.taux_presence == 100.0
    assert result.absents == 0


@pytest.mark.asyncio
async def test_get_user_stats_passes_date_range():
    user = _make_user()
    start = datetime(2026, 1, 1)
    end = datetime(2026, 6, 1)

    user_repo = AsyncMock()
    user_repo.get.return_value = user

    attendance_repo = AsyncMock()
    attendance_repo.get_user_stats.return_value = {}

    svc = _make_svc(attendance_repo=attendance_repo, user_repo=user_repo)

    await svc.get_user_stats(user.id, start_date=start, end_date=end)

    call_kwargs = attendance_repo.get_user_stats.call_args.kwargs
    assert call_kwargs["start_date"] == start
    assert call_kwargs["end_date"] == end
