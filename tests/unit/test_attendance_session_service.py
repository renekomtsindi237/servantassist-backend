"""Unit tests for AttendanceSessionService — coverage complète."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException

from src.application.services.attendance_session_service import AttendanceSessionService
from src.core.entities.attendance_session import (
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
)
from src.core.entities.user import User, UserRole
from src.presentation.schemas.attendance_session import (
    AttendanceRecordCreate,
    AttendanceRecordUpdate,
    AttendanceReportRequest,
    AttendanceSessionCreate,
)

NOW = datetime(2026, 6, 1, 10, 0, 0)
TODAY = datetime(2026, 6, 1, 0, 0, 0)


# ─── Factories ────────────────────────────────────────────────────────────────


def _make_session(**kw) -> AttendanceSession:
    return AttendanceSession(
        id=kw.pop("id", uuid4()),
        session_date=kw.pop("session_date", TODAY),
        session_time=kw.pop("session_time", "07h30"),
        location=kw.pop("location", "Sacristie"),
        session_type=kw.pop("session_type", "REUNION_HEBDOMADAIRE"),
        conducted_by=kw.pop("conducted_by", uuid4()),
        notes=kw.pop("notes", None),
        created_at=kw.pop("created_at", NOW),
        updated_at=kw.pop("updated_at", NOW),
        **kw,
    )


def _make_record(**kw) -> AttendanceRecord:
    return AttendanceRecord(
        id=kw.pop("id", uuid4()),
        session_id=kw.pop("session_id", uuid4()),
        servant_id=kw.pop("servant_id", uuid4()),
        status=kw.pop("status", AttendanceStatus.PRESENT),
        recorded_by=kw.pop("recorded_by", uuid4()),
        created_at=kw.pop("created_at", NOW),
        updated_at=kw.pop("updated_at", NOW),
        **kw,
    )


def _make_servant(**kw) -> User:
    return User(
        id=kw.pop("id", uuid4()),
        first_name=kw.pop("first_name", "Jean"),
        last_name=kw.pop("last_name", "Dupont"),
        email=f"jean_{uuid4().hex[:6]}@test.com",
        role=UserRole.SERVANT,
        is_active=kw.pop("is_active", True),
        **kw,
    )


def _enr_session(s: AttendanceSession) -> dict:
    return {
        "id": s.id,
        "session_date": s.session_date,
        "session_time": s.session_time,
        "location": s.location,
        "session_type": s.session_type,
        "conducted_by": s.conducted_by,
        "conducted_by_name": "Admin",
        "notes": s.notes,
        "records": [],
        "total_servants": 0,
        "present_count": 0,
        "absent_count": 0,
        "late_count": 0,
        "excused_count": 0,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def _enr_record(r: AttendanceRecord) -> dict:
    return {
        "id": r.id,
        "session_id": r.session_id,
        "servant_id": r.servant_id,
        "servant_name": "Jean Dupont",
        "status": r.status,
        "arrival_time": None,
        "notes": None,
        "recorded_by": r.recorded_by,
        "recorded_by_name": "Admin",
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


def _make_stats(**kw):
    m = MagicMock()
    m.absent_count = kw.get("absent_count", 0)
    m.present_count = kw.get("present_count", 5)
    m.late_count = kw.get("late_count", 0)
    m.excused_count = kw.get("excused_count", 0)
    m.total_sessions = kw.get("total_sessions", 5)
    m.attendance_rate = kw.get("attendance_rate", 100.0)
    m.consecutive_absences = kw.get("consecutive_absences", 0)
    m.model_dump.return_value = {
        "absent_count": m.absent_count,
        "present_count": m.present_count,
        "late_count": m.late_count,
        "excused_count": m.excused_count,
        "total_sessions": m.total_sessions,
        "attendance_rate": m.attendance_rate,
        "consecutive_absences": m.consecutive_absences,
        "servant_id": kw.get("servant_id", uuid4()),
        "servant_name": "Jean Dupont",
    }
    return m


def _svc(attendance_repo=None, user_repo=None, notification_repo=None):
    ar = attendance_repo or AsyncMock()
    ur = user_repo or AsyncMock()
    svc = AttendanceSessionService(ar, ur, notification_repo=notification_repo)
    svc.email_service = AsyncMock()
    return svc


# ─── create_session ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_session_success():
    s = _make_session()
    ar = AsyncMock()
    ar.create_session.return_value = s
    ar.enrich_session.return_value = _enr_session(s)
    result = await _svc(ar).create_session(
        AttendanceSessionCreate(session_date=TODAY, session_time="07h30", location="Sacristie"),
        conducted_by=uuid4(),
    )
    assert result.id == s.id


# ─── get_session ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_session_not_found():
    ar = AsyncMock()
    ar.get_session.return_value = None
    with pytest.raises(HTTPException) as e:
        await _svc(ar).get_session(uuid4())
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_get_session_success():
    s = _make_session()
    ar = AsyncMock()
    ar.get_session.return_value = s
    ar.enrich_session.return_value = _enr_session(s)
    result = await _svc(ar).get_session(s.id)
    assert result.id == s.id


# ─── list_sessions ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_empty():
    ar = AsyncMock()
    ar.list_sessions.return_value = ([], 0)
    result = await _svc(ar).list_sessions()
    assert result.total == 0 and result.items == []


@pytest.mark.asyncio
async def test_list_sessions_with_items():
    sessions = [_make_session(), _make_session()]
    ar = AsyncMock()
    ar.list_sessions.return_value = (sessions, 2)
    ar.enrich_session.side_effect = [_enr_session(s) for s in sessions]
    result = await _svc(ar).list_sessions(page=1, page_size=20)
    assert result.total == 2 and len(result.items) == 2


@pytest.mark.asyncio
async def test_list_sessions_pagination():
    sessions = [_make_session() for _ in range(5)]
    ar = AsyncMock()
    ar.list_sessions.return_value = (sessions, 50)
    ar.enrich_session.side_effect = [_enr_session(s) for s in sessions]
    result = await _svc(ar).list_sessions(page=2, page_size=10)
    assert result.total_pages == 5 and result.page == 2


# ─── mark_attendance ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mark_attendance_session_not_found():
    ar = AsyncMock()
    ar.get_session.return_value = None
    with pytest.raises(HTTPException) as e:
        await _svc(ar).mark_attendance(
            uuid4(), AttendanceRecordCreate(servant_id=uuid4(), status=AttendanceStatus.PRESENT), uuid4()
        )
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_attendance_servant_not_found():
    ar = AsyncMock()
    ar.get_session.return_value = _make_session()
    ur = AsyncMock()
    ur.get.return_value = None
    with pytest.raises(HTTPException) as e:
        await _svc(ar, ur).mark_attendance(
            uuid4(), AttendanceRecordCreate(servant_id=uuid4(), status=AttendanceStatus.PRESENT), uuid4()
        )
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_attendance_not_servant_role():
    ar = AsyncMock()
    ar.get_session.return_value = _make_session()
    parent = User(id=uuid4(), first_name="M", last_name="D", email="p@t.com", role=UserRole.PARENT, is_active=True)
    ur = AsyncMock()
    ur.get.return_value = parent
    with pytest.raises(HTTPException) as e:
        await _svc(ar, ur).mark_attendance(
            uuid4(), AttendanceRecordCreate(servant_id=parent.id, status=AttendanceStatus.PRESENT), uuid4()
        )
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_mark_attendance_duplicate():
    servant = _make_servant()
    ar = AsyncMock()
    ar.get_session.return_value = _make_session()
    ar.get_record_by_session_and_servant.return_value = _make_record(servant_id=servant.id)
    ur = AsyncMock()
    ur.get.return_value = servant
    with pytest.raises(HTTPException) as e:
        await _svc(ar, ur).mark_attendance(
            uuid4(), AttendanceRecordCreate(servant_id=servant.id, status=AttendanceStatus.PRESENT), uuid4()
        )
    assert e.value.status_code == 400


@pytest.mark.asyncio
async def test_mark_attendance_present_success():
    session = _make_session()
    servant = _make_servant()
    rec = _make_record(servant_id=servant.id, status=AttendanceStatus.PRESENT)
    ar = AsyncMock()
    ar.get_session.return_value = session
    ar.get_record_by_session_and_servant.return_value = None
    ar.create_record.return_value = rec
    ar.enrich_record.return_value = _enr_record(rec)
    ur = AsyncMock()
    ur.get.return_value = servant
    result = await _svc(ar, ur).mark_attendance(
        session.id, AttendanceRecordCreate(servant_id=servant.id, status=AttendanceStatus.PRESENT), uuid4()
    )
    assert result.servant_id == servant.id
    ar.calculate_servant_stats.assert_not_called()


@pytest.mark.asyncio
async def test_mark_attendance_absent_triggers_threshold():
    session = _make_session()
    servant = _make_servant()
    rec = _make_record(servant_id=servant.id, status=AttendanceStatus.ABSENT)
    ar = AsyncMock()
    ar.get_session.return_value = session
    ar.get_record_by_session_and_servant.return_value = None
    ar.create_record.return_value = rec
    ar.enrich_record.return_value = _enr_record(rec)
    ar.calculate_servant_stats.return_value = _make_stats(absent_count=1)
    ur = AsyncMock()
    ur.get.return_value = servant
    result = await _svc(ar, ur).mark_attendance(
        session.id, AttendanceRecordCreate(servant_id=servant.id, status=AttendanceStatus.ABSENT), uuid4()
    )
    assert result.status == AttendanceStatus.ABSENT


# ─── _handle_absence_thresholds ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_absence_no_notif_repo():
    svc = _svc(notification_repo=None)
    svc.attendance_repo = AsyncMock()
    await svc._handle_absence_thresholds(_make_servant(), _make_session())
    svc.attendance_repo.calculate_servant_stats.assert_not_called()


@pytest.mark.asyncio
async def test_handle_absence_3_sends_warning():
    servant = _make_servant()
    session = _make_session()
    notif_repo = MagicMock()
    notif_repo.session = MagicMock()
    notif_repo.session.add = MagicMock()
    notif_repo.session.commit = AsyncMock()
    ar = AsyncMock()
    ar.calculate_servant_stats.return_value = _make_stats(absent_count=3)
    svc = _svc(ar, notification_repo=notif_repo)
    svc.email_service.send_absence_warning_email = AsyncMock(return_value=True)
    await svc._handle_absence_thresholds(servant, session)
    svc.email_service.send_absence_warning_email.assert_called_once()
    notif_repo.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_absence_5_convokes_parents():
    servant = _make_servant()
    session = _make_session()
    parent = User(id=uuid4(), first_name="M", last_name="D", email="m@t.com", role=UserRole.PARENT, is_active=True)
    notif_repo = MagicMock()
    notif_repo.session = MagicMock()
    notif_repo.session.add = MagicMock()
    notif_repo.session.commit = AsyncMock()
    ar = AsyncMock()
    ar.calculate_servant_stats.return_value = _make_stats(absent_count=5)
    ur = AsyncMock()
    ur.get_parents_of.return_value = [parent]
    svc = _svc(ar, ur, notification_repo=notif_repo)
    svc.email_service.send_parent_convocation_email = AsyncMock(return_value=True)
    await svc._handle_absence_thresholds(servant, session)
    svc.email_service.send_parent_convocation_email.assert_called_once()
    notif_repo.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_absence_5_no_parents():
    servant = _make_servant()
    session = _make_session()
    notif_repo = MagicMock()
    notif_repo.session = MagicMock()
    notif_repo.session.add = MagicMock()
    notif_repo.session.commit = AsyncMock()
    ar = AsyncMock()
    ar.calculate_servant_stats.return_value = _make_stats(absent_count=5)
    ur = AsyncMock()
    ur.get_parents_of.return_value = []
    svc = _svc(ar, ur, notification_repo=notif_repo)
    svc.email_service.send_parent_convocation_email = AsyncMock()
    await svc._handle_absence_thresholds(servant, session)
    svc.email_service.send_parent_convocation_email.assert_not_called()
    notif_repo.session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_handle_absence_email_fail_non_fatal():
    servant = _make_servant()
    session = _make_session()
    notif_repo = MagicMock()
    notif_repo.session = MagicMock()
    notif_repo.session.add = MagicMock()
    notif_repo.session.commit = AsyncMock()
    ar = AsyncMock()
    ar.calculate_servant_stats.return_value = _make_stats(absent_count=3)
    svc = _svc(ar, notification_repo=notif_repo)
    svc.email_service.send_absence_warning_email = AsyncMock(side_effect=Exception("SMTP down"))
    await svc._handle_absence_thresholds(servant, session)
    notif_repo.session.commit.assert_called_once()


# ─── update_attendance ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_attendance_not_found():
    ar = AsyncMock()
    ar.get_record.return_value = None
    with pytest.raises(HTTPException) as e:
        await _svc(ar).update_attendance(uuid4(), AttendanceRecordUpdate(status=AttendanceStatus.PRESENT))
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_update_attendance_status():
    rec = _make_record(status=AttendanceStatus.PRESENT)
    upd = _make_record(id=rec.id, servant_id=rec.servant_id, status=AttendanceStatus.LATE)
    ar = AsyncMock()
    ar.get_record.return_value = rec
    ar.update_record.return_value = upd
    ar.enrich_record.return_value = _enr_record(upd)
    result = await _svc(ar).update_attendance(rec.id, AttendanceRecordUpdate(status=AttendanceStatus.LATE))
    assert result.status == AttendanceStatus.LATE


@pytest.mark.asyncio
async def test_update_attendance_notes():
    rec = _make_record()
    upd = _make_record(id=rec.id, servant_id=rec.servant_id)
    ar = AsyncMock()
    ar.get_record.return_value = rec
    ar.update_record.return_value = upd
    ar.enrich_record.return_value = _enr_record(upd)
    result = await _svc(ar).update_attendance(rec.id, AttendanceRecordUpdate(notes="Test note"))
    assert result is not None


@pytest.mark.asyncio
async def test_update_attendance_absent_triggers_threshold():
    servant = _make_servant()
    session = _make_session()
    rec = _make_record(status=AttendanceStatus.PRESENT, servant_id=servant.id, session_id=session.id)
    upd = _make_record(id=rec.id, servant_id=servant.id, session_id=session.id, status=AttendanceStatus.ABSENT)
    ar = AsyncMock()
    ar.get_record.return_value = rec
    ar.update_record.return_value = upd
    ar.enrich_record.return_value = _enr_record(upd)
    ar.get_session.return_value = session
    ar.calculate_servant_stats.return_value = _make_stats(absent_count=1)
    ur = AsyncMock()
    ur.get.return_value = servant
    result = await _svc(ar, ur).update_attendance(rec.id, AttendanceRecordUpdate(status=AttendanceStatus.ABSENT))
    assert result.status == AttendanceStatus.ABSENT


# ─── get_servant_stats ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_servant_stats_not_found():
    ur = AsyncMock()
    ur.get.return_value = None
    with pytest.raises(HTTPException) as e:
        await _svc(user_repo=ur).get_servant_stats(uuid4())
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_get_servant_stats_success():
    servant = _make_servant()
    stats = _make_stats(absent_count=2, present_count=8, total_sessions=10, attendance_rate=80.0)
    ar = AsyncMock()
    ar.calculate_servant_stats.return_value = stats
    ur = AsyncMock()
    ur.get.return_value = servant
    result = await _svc(ar, ur).get_servant_stats(servant.id)
    assert result.absent_count == 2 and result.present_count == 8


# ─── generate_report ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_report_empty():
    generator = _make_servant()
    ar = AsyncMock()
    ar.list_sessions.return_value = ([], 0)
    ar.get_all_servants.return_value = []
    ur = AsyncMock()
    ur.get.return_value = generator
    req = AttendanceReportRequest(start_date=datetime(2026, 1, 1), end_date=datetime(2026, 6, 1))
    result = await _svc(ar, ur).generate_report(req, generated_by=generator.id)
    assert result.total_sessions == 0 and result.average_attendance_rate == 0


@pytest.mark.asyncio
async def test_generate_report_with_servants():
    generator = _make_servant()
    s1 = _make_servant()
    s2 = _make_servant()
    ar = AsyncMock()
    ar.list_sessions.return_value = ([_make_session()], 1)
    ar.get_all_servants.return_value = [s1, s2]
    ar.calculate_servant_stats.side_effect = [
        _make_stats(servant_id=s1.id, attendance_rate=90.0),
        _make_stats(servant_id=s2.id, attendance_rate=70.0),
    ]
    ur = AsyncMock()
    ur.get.return_value = generator
    req = AttendanceReportRequest(start_date=datetime(2026, 1, 1), end_date=datetime(2026, 6, 1))
    result = await _svc(ar, ur).generate_report(req, generated_by=generator.id)
    assert result.total_servants == 2 and result.average_attendance_rate == 80.0


@pytest.mark.asyncio
async def test_generate_report_filters_servant_ids():
    generator = _make_servant()
    s1 = _make_servant()
    s2 = _make_servant()
    ar = AsyncMock()
    ar.list_sessions.return_value = ([], 0)
    ar.get_all_servants.return_value = [s1, s2]
    ar.calculate_servant_stats.return_value = _make_stats(servant_id=s1.id, attendance_rate=90.0)
    ur = AsyncMock()
    ur.get.return_value = generator
    req = AttendanceReportRequest(start_date=datetime(2026, 1, 1), end_date=datetime(2026, 6, 1), servant_ids=[s1.id])
    result = await _svc(ar, ur).generate_report(req, generated_by=generator.id)
    assert result.total_servants == 1


# ─── get_all_servants_stats ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_all_servants_stats_empty():
    ar = AsyncMock()
    ar.get_all_servants.return_value = []
    assert await _svc(ar).get_all_servants_stats() == []


@pytest.mark.asyncio
async def test_get_all_servants_stats_with_servants():
    servant = _make_servant()
    ar = AsyncMock()
    ar.get_all_servants.return_value = [servant]
    ar.calculate_servant_stats.return_value = _make_stats(
        servant_id=servant.id, absent_count=2, present_count=8, attendance_rate=80.0
    )
    result = await _svc(ar).get_all_servants_stats()
    assert len(result) == 1 and result[0]["absent_count"] == 2


# ─── get_servants_list ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_servants_list():
    s1 = _make_servant(first_name="Alice")
    s2 = _make_servant(first_name="Bob")
    ar = AsyncMock()
    ar.get_all_servants.return_value = [s1, s2]
    result = await _svc(ar).get_servants_list()
    assert len(result) == 2 and result[0].first_name == "Alice"


# ─── init_roll_call ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_init_roll_call_not_found():
    ar = AsyncMock()
    ar.get_session.return_value = None
    with pytest.raises(HTTPException) as e:
        await _svc(ar).init_roll_call(uuid4(), recorded_by=uuid4())
    assert e.value.status_code == 404


@pytest.mark.asyncio
async def test_init_roll_call_creates_records_for_active():
    session = _make_session()
    active = _make_servant(is_active=True)
    inactive = _make_servant(is_active=False)
    ar = MagicMock()
    ar.get_session = AsyncMock(return_value=session)
    ar.get_all_servants = AsyncMock(return_value=[active, inactive])
    ar.get_record_by_session_and_servant = AsyncMock(return_value=None)
    ar.enrich_session = AsyncMock(return_value=_enr_session(session))
    ar.session = MagicMock()
    ar.session.add = MagicMock()
    ar.session.commit = AsyncMock()
    result = await _svc(ar).init_roll_call(session.id, recorded_by=uuid4())
    assert result.id == session.id
    ar.session.add.assert_called_once()  # only active servant


@pytest.mark.asyncio
async def test_init_roll_call_skips_existing():
    session = _make_session()
    servant = _make_servant(is_active=True)
    ar = MagicMock()
    ar.get_session = AsyncMock(return_value=session)
    ar.get_all_servants = AsyncMock(return_value=[servant])
    ar.get_record_by_session_and_servant = AsyncMock(return_value=_make_record(servant_id=servant.id))
    ar.enrich_session = AsyncMock(return_value=_enr_session(session))
    ar.session = MagicMock()
    ar.session.add = MagicMock()
    ar.session.commit = AsyncMock()
    await _svc(ar).init_roll_call(session.id, recorded_by=uuid4())
    ar.session.add.assert_not_called()
