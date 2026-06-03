"""Unit tests for DashboardService."""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.application.services.dashboard_service import DashboardService
from src.core.entities.assignment import Assignment, AssignmentStatus
from src.core.entities.attendance import Attendance, AttendanceStatus
from src.core.entities.cotisation import CotisationPeriod, MemberCotisation
from src.core.entities.cotisation import CotisationStatus as CotisationPaymentStatus
from src.core.entities.event import Event
from src.core.entities.user import User, UserRole

NOW = datetime(2026, 6, 1, 10, 0, 0)


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _mock_session() -> AsyncMock:
    return AsyncMock()


def _user(role=UserRole.SERVANT, is_active=True) -> User:
    return User(
        id=uuid4(), first_name="J", last_name="D", email=f"{uuid4().hex[:6]}@t.com", role=role, is_active=is_active
    )


def _exec_returning(value):
    """Return a mock that session.exec() returns, where .all() gives a list or .one() gives a scalar."""
    r = MagicMock()
    if isinstance(value, list):
        r.all.return_value = value
        r.one.return_value = len(value)
        r.first.return_value = value[0] if value else None
    else:
        r.one.return_value = value
        r.first.return_value = value
        r.all.return_value = [value] if value is not None else []
    return r


def _svc_with_exec(*side_effects) -> DashboardService:
    """Build DashboardService whose session.exec() returns the given sequence."""
    session = AsyncMock()
    session.exec = AsyncMock(side_effect=[_exec_returning(v) for v in side_effects])
    return DashboardService(session)


# ─── get_summary ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_summary_empty_db():
    """All zeros when no data."""
    # Calls: users, events count, assignments count, attendances, cotisation period
    svc = _svc_with_exec(
        [],  # all_users
        0,  # total_events
        0,  # total_assign
        [],  # all attendances
        None,  # cotisation period (None → no period)
    )
    result = await svc.get_summary()
    assert result.total_servants == 0
    assert result.total_parents == 0
    assert result.attendance_rate_percent == 0.0
    assert result.cotisation_rate_percent == 0.0


@pytest.mark.asyncio
async def test_get_summary_with_data():
    servant = _user(role=UserRole.SERVANT)
    parent = _user(role=UserRole.PARENT)

    att_present = MagicMock()
    att_present.status = AttendanceStatus.PRESENT
    att_absent = MagicMock()
    att_absent.status = AttendanceStatus.ABSENT

    svc = _svc_with_exec(
        [servant, parent],  # all_users
        10,  # total_events
        20,  # total_assign
        [att_present, att_absent],  # attendances (1 present, 1 absent → 50%)
        None,  # cotisation period
    )
    result = await svc.get_summary()
    assert result.total_servants == 1
    assert result.total_parents == 1
    assert result.total_active_users == 2
    assert result.total_events == 10
    assert result.total_assignments == 20
    assert result.attendance_rate_percent == 50.0


# ─── get_attendance_trend ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_attendance_trend_empty():
    svc = _svc_with_exec([])
    result = await svc.get_attendance_trend()
    assert result.points == []
    assert result.average_rate_percent == 0.0
    assert result.period_label == "Tendance mensuelle"


@pytest.mark.asyncio
async def test_get_attendance_trend_monthly():
    rec1 = MagicMock()
    rec1.attendance_date = datetime(2026, 1, 15)
    rec1.status = AttendanceStatus.PRESENT

    rec2 = MagicMock()
    rec2.attendance_date = datetime(2026, 1, 20)
    rec2.status = AttendanceStatus.ABSENT

    rec3 = MagicMock()
    rec3.attendance_date = datetime(2026, 2, 5)
    rec3.status = AttendanceStatus.PRESENT

    svc = _svc_with_exec([rec1, rec2, rec3])
    result = await svc.get_attendance_trend(group_by="month")

    assert len(result.points) == 2
    jan = next(p for p in result.points if "2026-01" in p.period)
    assert jan.total == 2 and jan.present == 1
    feb = next(p for p in result.points if "2026-02" in p.period)
    assert feb.total == 1 and feb.present == 1


@pytest.mark.asyncio
async def test_get_attendance_trend_weekly():
    rec = MagicMock()
    rec.attendance_date = datetime(2026, 1, 5)  # Week 2
    rec.status = AttendanceStatus.PRESENT

    svc = _svc_with_exec([rec])
    result = await svc.get_attendance_trend(group_by="week")
    assert len(result.points) == 1
    assert "Semaine" in result.points[0].period


@pytest.mark.asyncio
async def test_get_attendance_trend_no_date():
    """Records with no attendance_date are skipped."""
    rec = MagicMock()
    rec.attendance_date = None
    rec.status = AttendanceStatus.PRESENT

    svc = _svc_with_exec([rec])
    result = await svc.get_attendance_trend()
    assert result.points == []


@pytest.mark.asyncio
async def test_get_attendance_trend_with_date_filters():
    svc = _svc_with_exec([])
    result = await svc.get_attendance_trend(
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 6, 1),
    )
    assert result.points == []


@pytest.mark.asyncio
async def test_get_attendance_trend_weekly_label():
    svc = _svc_with_exec([])
    result = await svc.get_attendance_trend(group_by="week")
    assert result.period_label == "Tendance hebdomadaire"


# ─── get_cotisation_status ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_cotisation_status_no_period():
    svc = _svc_with_exec(None)
    result = await svc.get_cotisation_status()
    assert result is not None
    assert result.total_members == 0
    assert result.rate_percent == 0.0
    assert result.period_name == "Aucune période"


@pytest.mark.asyncio
async def test_get_cotisation_status_with_period():
    period = MagicMock(spec=CotisationPeriod)
    period.id = uuid4()
    period.title = "Cotisation 2026"
    period.amount_expected = 5000.0

    cot_paid = MagicMock()
    cot_paid.status = CotisationPaymentStatus.PAYE
    cot_paid.amount_paid = 5000.0

    cot_partial = MagicMock()
    cot_partial.status = CotisationPaymentStatus.PAYE_PARTIELLEMENT
    cot_partial.amount_paid = 2500.0

    cot_unpaid = MagicMock()
    cot_unpaid.status = CotisationPaymentStatus.EN_ATTENTE
    cot_unpaid.amount_paid = 0.0

    svc = _svc_with_exec(period, [cot_paid, cot_partial, cot_unpaid])
    result = await svc.get_cotisation_status()

    assert result.period_name == "Cotisation 2026"
    assert result.paid_count == 1
    assert result.partial_count == 1
    assert result.total_members == 3
    assert round(result.rate_percent, 1) == 33.3


@pytest.mark.asyncio
async def test_get_cotisation_status_all_paid():
    period = MagicMock(spec=CotisationPeriod)
    period.id = uuid4()
    period.title = "P1"
    period.amount_expected = 5000.0

    cot1 = MagicMock()
    cot1.status = CotisationPaymentStatus.PAYE
    cot1.amount_paid = 5000.0
    cot2 = MagicMock()
    cot2.status = CotisationPaymentStatus.PAYE
    cot2.amount_paid = 5000.0

    svc = _svc_with_exec(period, [cot1, cot2])
    result = await svc.get_cotisation_status()
    assert result.rate_percent == 100.0


@pytest.mark.asyncio
async def test_get_cotisation_status_empty_cotisations():
    period = MagicMock(spec=CotisationPeriod)
    period.id = uuid4()
    period.title = "P1"
    period.amount_expected = 5000.0

    svc = _svc_with_exec(period, [])
    result = await svc.get_cotisation_status()
    assert result.rate_percent == 0.0 and result.total_members == 0


# ─── get_upcoming_events ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_upcoming_events_empty():
    svc = _svc_with_exec([])
    result = await svc.get_upcoming_events()
    assert result == []


@pytest.mark.asyncio
async def test_get_upcoming_events_with_events():
    ev = MagicMock(spec=Event)
    ev.id = uuid4()
    ev.title = "Messe du dimanche"
    ev.start_time = datetime(2026, 6, 8, 8, 0)
    ev.location = "Basilique"

    acc = MagicMock()
    acc.status = AssignmentStatus.ACCEPTED
    pen = MagicMock()
    pen.status = AssignmentStatus.PENDING

    svc = _svc_with_exec([ev], [acc, pen])
    result = await svc.get_upcoming_events()
    assert len(result) == 1
    assert result[0].title == "Messe du dimanche"
    assert result[0].total_assignments == 2
    assert result[0].confirmed_assignments == 1


@pytest.mark.asyncio
async def test_get_upcoming_events_no_assignments():
    ev = MagicMock(spec=Event)
    ev.id = uuid4()
    ev.title = "Répétition"
    ev.start_time = datetime(2026, 6, 10, 18, 0)
    ev.location = ""

    svc = _svc_with_exec([ev], [])
    result = await svc.get_upcoming_events()
    assert result[0].total_assignments == 0
    assert result[0].confirmed_assignments == 0


@pytest.mark.asyncio
async def test_get_upcoming_events_limit():
    svc = _svc_with_exec([])
    result = await svc.get_upcoming_events(limit=3)
    assert result == []


# ─── get_top_servants ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_top_servants_empty():
    svc = _svc_with_exec([])
    result = await svc.get_top_servants()
    assert result == []


@pytest.mark.asyncio
async def test_get_top_servants_ranked():
    s1 = _user(role=UserRole.SERVANT)
    s2 = _user(role=UserRole.SERVANT)
    s1.first_name = "Alice"
    s1.last_name = "A"
    s2.first_name = "Bob"
    s2.last_name = "B"

    att_s1_present = MagicMock()
    att_s1_present.status = AttendanceStatus.PRESENT
    att_s2_present = MagicMock()
    att_s2_present.status = AttendanceStatus.PRESENT
    att_s2_absent = MagicMock()
    att_s2_absent.status = AttendanceStatus.ABSENT

    # servants list, then attendances for s1 (1/1=100%), then for s2 (1/2=50%)
    svc = _svc_with_exec([s1, s2], [att_s1_present], [att_s2_present, att_s2_absent])
    result = await svc.get_top_servants()

    assert len(result) == 2
    # s1 has 100% → rank 1
    assert result[0].full_name == "Alice A"
    assert result[0].rank == 1
    assert result[0].attendance_rate_percent == 100.0
    # s2 has 50% → rank 2
    assert result[1].rank == 2
    assert result[1].attendance_rate_percent == 50.0


@pytest.mark.asyncio
async def test_get_top_servants_no_attendance():
    s = _user(role=UserRole.SERVANT)
    s.first_name = "X"
    s.last_name = "Y"
    svc = _svc_with_exec([s], [])
    result = await svc.get_top_servants()
    assert result[0].attendance_rate_percent == 0.0
    assert result[0].total_sessions == 0


@pytest.mark.asyncio
async def test_get_top_servants_en_retard_counted_as_present():
    s = _user(role=UserRole.SERVANT)
    s.first_name = "X"
    s.last_name = "Y"
    att = MagicMock()
    att.status = AttendanceStatus.EN_RETARD
    svc = _svc_with_exec([s], [att])
    result = await svc.get_top_servants()
    assert result[0].attendance_rate_percent == 100.0
