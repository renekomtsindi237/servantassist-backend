"""
Unit tests for AssignmentRepository and AttendanceRepository.
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
#  AssignmentRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_assignment(**kw):
    from src.core.entities.assignment import Assignment, AssignmentStatus, LiturgicalRole

    a = MagicMock()
    a.id = kw.get("id", uuid4())
    a.event_id = kw.get("event_id", uuid4())
    a.user_id = kw.get("user_id", uuid4())
    a.liturgical_role = kw.get("liturgical_role", LiturgicalRole.SERVANT_GENERAL)
    a.status = kw.get("status", AssignmentStatus.PENDING)
    a.notes = kw.get("notes", None)
    a.assigned_by = kw.get("assigned_by", None)
    a.created_at = kw.get("created_at", datetime.utcnow())
    a.updated_at = kw.get("updated_at", datetime.utcnow())
    return a


@pytest.mark.asyncio
async def test_assignment_get_found():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    a = _make_assignment()
    session.exec = AsyncMock(return_value=_exec_result(first=a))

    result = await repo.get(a.id)
    assert result is a


@pytest.mark.asyncio
async def test_assignment_get_not_found():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_assignment_list():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    assignments = [_make_assignment(), _make_assignment()]
    session.exec = AsyncMock(return_value=_exec_result(all_=assignments))

    result = await repo.list()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_assignment_list_by_user():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    user_id = uuid4()
    assignments = [_make_assignment(user_id=user_id)]
    session.exec = AsyncMock(return_value=_exec_result(all_=assignments))

    result = await repo.list_by_user(user_id)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_assignment_list_by_event():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    event_id = uuid4()
    assignments = [_make_assignment(event_id=event_id), _make_assignment(event_id=event_id)]
    session.exec = AsyncMock(return_value=_exec_result(all_=assignments))

    result = await repo.list_by_event(event_id)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_assignment_list_paginated():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    assignments = [_make_assignment()]
    session.exec = AsyncMock(
        side_effect=[
            _exec_result(one=1),
            _exec_result(all_=assignments),
        ]
    )

    result, total = await repo.list_paginated()
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_assignment_list_paginated_with_filters():
    from src.core.entities.assignment import AssignmentStatus, LiturgicalRole
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    session.exec = AsyncMock(
        side_effect=[
            _exec_result(one=0),
            _exec_result(all_=[]),
        ]
    )
    now = datetime.utcnow()

    result, total = await repo.list_paginated(
        event_id=uuid4(),
        user_id=uuid4(),
        status=AssignmentStatus.PENDING,
        liturgical_role=LiturgicalRole.SERVANT_GENERAL,
        start_date=now,
        end_date=now + timedelta(days=7),
    )
    assert total == 0
    assert result == []


@pytest.mark.asyncio
async def test_assignment_get_by_event_and_user():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    a = _make_assignment()
    session.exec = AsyncMock(return_value=_exec_result(first=a))

    result = await repo.get_by_event_and_user(a.event_id, a.user_id)
    assert result is a


@pytest.mark.asyncio
async def test_assignment_count_by_event():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(one=5))

    count = await repo.count_by_event(uuid4())
    assert count == 5


@pytest.mark.asyncio
async def test_assignment_count_by_user():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(one=3))

    count = await repo.count_by_user(uuid4())
    assert count == 3


@pytest.mark.asyncio
async def test_assignment_get_upcoming_for_user():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    assignments = [_make_assignment()]
    session.exec = AsyncMock(return_value=_exec_result(all_=assignments))

    result = await repo.get_upcoming_for_user(uuid4())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_assignment_list_by_event_with_cancelled():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    assignments = [_make_assignment()]
    session.exec = AsyncMock(return_value=_exec_result(all_=assignments))

    result = await repo.list_by_event_with_cancelled(uuid4())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_assignment_enrich_assignment():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    a = _make_assignment()

    user = MagicMock()
    user.first_name = "Jean"
    user.last_name = "Doe"
    user.email = "jean@example.com"
    user.phone_number = "+237"

    event = MagicMock()
    event.title = "Messe dimanche"
    event.event_type = "MESSE_DOMINICALE"
    event.start_time = datetime.utcnow()
    event.location = "Cathédrale"

    session.exec = AsyncMock(
        side_effect=[
            _exec_result(first=user),
            _exec_result(first=event),
        ]
    )

    with patch("src.infrastructure.repositories.assignment_repository.decrypt_str_fields"):
        result = await repo.enrich_assignment(a)

    assert result["user_first_name"] == "Jean"
    assert result["event_title"] == "Messe dimanche"


@pytest.mark.asyncio
async def test_assignment_create():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    a = _make_assignment()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(a)
    assert result is a


@pytest.mark.asyncio
async def test_assignment_update():
    from src.infrastructure.repositories.assignment_repository import AssignmentRepository

    session = _mock_session()
    repo = AssignmentRepository(session)
    a = _make_assignment()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(a.id, a)
    assert result is a


# ═══════════════════════════════════════════════════════════════════════════════
#  AttendanceRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_attendance(**kw):
    from src.core.entities.attendance import Attendance, AttendanceStatus, AttendanceType

    a = MagicMock()
    a.id = kw.get("id", uuid4())
    a.user_id = kw.get("user_id", uuid4())
    a.event_id = kw.get("event_id", uuid4())
    a.attendance_type = kw.get("attendance_type", AttendanceType.MESSE_CLASSEMENT)
    a.attendance_date = kw.get("attendance_date", datetime.utcnow())
    a.title = kw.get("title", "Messe")
    a.status = kw.get("status", AttendanceStatus.PRESENT)
    a.justification = kw.get("justification", None)
    a.justified_at = kw.get("justified_at", None)
    a.recorded_by = kw.get("recorded_by", uuid4())
    a.created_at = kw.get("created_at", datetime.utcnow())
    a.updated_at = kw.get("updated_at", datetime.utcnow())
    return a


def _make_att_repo(session):
    from src.infrastructure.repositories.attendance_repository import AttendanceRepository

    repo = AttendanceRepository(session)
    repo._encrypt_model = MagicMock()
    repo._decrypt_model = MagicMock()
    repo._decrypt_list = MagicMock()
    return repo


@pytest.mark.asyncio
async def test_attendance_get_found():
    session = _mock_session()
    repo = _make_att_repo(session)
    a = _make_attendance()
    session.exec = AsyncMock(return_value=_exec_result(first=a))

    result = await repo.get(a.id)
    assert result is a
    repo._decrypt_model.assert_called_once_with(a)


@pytest.mark.asyncio
async def test_attendance_get_not_found():
    session = _mock_session()
    repo = _make_att_repo(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_attendance_get_by_user_date_type():
    from src.core.entities.attendance import AttendanceType

    session = _mock_session()
    repo = _make_att_repo(session)
    a = _make_attendance()
    session.exec = AsyncMock(return_value=_exec_result(first=a))

    result = await repo.get_by_user_date_type(a.user_id, a.attendance_date, AttendanceType.MESSE_CLASSEMENT)
    assert result is a


@pytest.mark.asyncio
async def test_attendance_list_paginated():
    session = _mock_session()
    repo = _make_att_repo(session)
    atts = [_make_attendance()]
    session.exec = AsyncMock(
        side_effect=[
            _exec_result(one=1),
            _exec_result(all_=atts),
        ]
    )

    result, total = await repo.list_paginated()
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_attendance_list_paginated_with_filters():
    from src.core.entities.attendance import AttendanceStatus, AttendanceType

    session = _mock_session()
    repo = _make_att_repo(session)
    session.exec = AsyncMock(
        side_effect=[
            _exec_result(one=0),
            _exec_result(all_=[]),
        ]
    )
    now = datetime.utcnow()

    result, total = await repo.list_paginated(
        user_id=uuid4(),
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        status=AttendanceStatus.PRESENT,
        start_date=now,
        end_date=now + timedelta(days=7),
        event_id=uuid4(),
    )
    assert total == 0
    assert result == []


@pytest.mark.asyncio
async def test_attendance_get_user_stats():
    from src.core.entities.attendance import AttendanceStatus

    session = _mock_session()
    repo = _make_att_repo(session)
    # One exec call per status
    session.exec = AsyncMock(return_value=_exec_result(one=2))

    result = await repo.get_user_stats(uuid4())
    assert isinstance(result, dict)
    # Check that we got a count for each status
    for s in AttendanceStatus:
        assert s.value in result


@pytest.mark.asyncio
async def test_attendance_enrich_attendance():
    session = _mock_session()
    repo = _make_att_repo(session)
    a = _make_attendance()

    user = MagicMock()
    user.first_name = "Marie"
    user.last_name = "Nkemelu"
    session.exec = AsyncMock(return_value=_exec_result(first=user))

    with patch("src.infrastructure.repositories.attendance_repository.decrypt_str_fields"):
        result = await repo.enrich_attendance(a)

    assert result["user_first_name"] == "Marie"


@pytest.mark.asyncio
async def test_attendance_enrich_no_user():
    session = _mock_session()
    repo = _make_att_repo(session)
    a = _make_attendance()

    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.enrich_attendance(a)
    assert result["user_first_name"] is None


@pytest.mark.asyncio
async def test_attendance_create():
    session = _mock_session()
    repo = _make_att_repo(session)
    a = _make_attendance()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.expunge = MagicMock()

    result = await repo.create(a)
    assert result is a
    repo._encrypt_model.assert_called_once()


@pytest.mark.asyncio
async def test_attendance_update():
    session = _mock_session()
    repo = _make_att_repo(session)
    a = _make_attendance()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.expunge = MagicMock()

    result = await repo.update(a)
    assert result is a


@pytest.mark.asyncio
async def test_attendance_delete_found():
    session = _mock_session()
    repo = _make_att_repo(session)
    a = _make_attendance()

    # get() calls exec → first
    session.exec = AsyncMock(return_value=_exec_result(first=a))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(a.id)
    assert result is True
    session.delete.assert_called_once_with(a)


@pytest.mark.asyncio
async def test_attendance_delete_not_found():
    session = _mock_session()
    repo = _make_att_repo(session)

    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.delete(uuid4())
    assert result is False
