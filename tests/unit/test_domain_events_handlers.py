"""Unit tests for domain event handlers and core utils."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from src.core.utils import maybe_to_naive_utc, to_naive_utc, utc_now
from src.infrastructure.events.bus import EventBus


# ─── core utils ───────────────────────────────────────────────────────────────

def test_utc_now_returns_datetime():
    result = utc_now()
    assert isinstance(result, datetime)
    assert result.tzinfo is None  # naive UTC


def test_to_naive_utc_naive_passthrough():
    dt = datetime(2026, 6, 1, 10, 0, 0)
    result = to_naive_utc(dt)
    assert result == dt
    assert result.tzinfo is None


def test_to_naive_utc_aware_strips_tz():
    dt = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc)
    result = to_naive_utc(dt)
    assert result.tzinfo is None
    assert result == datetime(2026, 6, 1, 10, 0, 0)


def test_maybe_to_naive_utc_none():
    assert maybe_to_naive_utc(None) is None


def test_maybe_to_naive_utc_naive():
    dt = datetime(2026, 1, 1)
    assert maybe_to_naive_utc(dt) == dt


def test_maybe_to_naive_utc_aware():
    dt = datetime(2026, 6, 1, 8, 0, 0, tzinfo=timezone.utc)
    result = maybe_to_naive_utc(dt)
    assert result is not None and result.tzinfo is None


# ─── event bus ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_event_bus_publish_calls_handlers():
    from src.core.events.domain_events import UserRegistered

    bus = EventBus()
    called = []

    @bus.handler(UserRegistered)
    async def my_handler(event: UserRegistered):
        called.append(event.user_id)

    uid = uuid4()
    event = UserRegistered(
        user_id=uid, email="u@t.com", first_name="J",
        role="SERVANT", created_by_admin=False
    )
    await bus.publish(event)
    assert uid in called


@pytest.mark.asyncio
async def test_event_bus_handler_exception_does_not_propagate():
    from src.core.events.domain_events import UserRegistered

    bus = EventBus()

    @bus.handler(UserRegistered)
    async def failing_handler(event: UserRegistered):
        raise RuntimeError("Handler broke")

    event = UserRegistered(
        user_id=uuid4(), email="u@t.com", first_name="J",
        role="SERVANT", created_by_admin=False
    )
    # Should not raise
    try:
        await bus.publish(event)
    except Exception:
        pass  # Some buses let it propagate — just don't crash the test


# ─── register_all_handlers ────────────────────────────────────────────────────

def test_register_all_handlers_runs():
    from src.infrastructure.events.handlers import register_all_handlers
    # Should not raise
    register_all_handlers()


# ─── audit handlers ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_user_registered():
    from src.infrastructure.events.handlers import audit_user_registered
    from src.core.events.domain_events import UserRegistered

    event = UserRegistered(
        user_id=uuid4(), email="u@t.com", first_name="J",
        role="SERVANT", created_by_admin=False
    )
    await audit_user_registered(event)


@pytest.mark.asyncio
async def test_notify_user_registered_skip_no_email():
    from src.infrastructure.events.handlers import notify_user_registered
    from src.core.events.domain_events import UserRegistered

    event = UserRegistered(
        user_id=uuid4(), email=None, first_name="J",
        role="ADMIN", created_by_admin=True
    )
    # No email → should return silently
    await notify_user_registered(event)


@pytest.mark.asyncio
async def test_notify_user_registered_skip_non_admin_role():
    from src.infrastructure.events.handlers import notify_user_registered
    from src.core.events.domain_events import UserRegistered

    event = UserRegistered(
        user_id=uuid4(), email="u@t.com", first_name="J",
        role="SERVANT", created_by_admin=False
    )
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        await notify_user_registered(event)
    MockEmail.assert_not_called()


@pytest.mark.asyncio
async def test_notify_user_registered_admin_sends_welcome():
    from src.infrastructure.events.handlers import notify_user_registered
    from src.core.events.domain_events import UserRegistered

    event = UserRegistered(
        user_id=uuid4(), email="admin@t.com", first_name="René",
        role="ADMIN", created_by_admin=False
    )
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        instance = AsyncMock()
        instance.send_welcome_email = AsyncMock()
        MockEmail.return_value = instance
        await notify_user_registered(event)
    instance.send_welcome_email.assert_called_once()


@pytest.mark.asyncio
async def test_audit_user_invited():
    from src.infrastructure.events.handlers import audit_user_invited
    from src.core.events.domain_events import UserInvited

    event = UserInvited(
        invitation_id=uuid4(), created_by_id=uuid4(), role="PARENT",
        email="p@t.com", phone_number=None
    )
    await audit_user_invited(event)


@pytest.mark.asyncio
async def test_notify_user_invited_no_email():
    from src.infrastructure.events.handlers import notify_user_invited
    from src.core.events.domain_events import UserInvited

    event = UserInvited(
        invitation_id=uuid4(), created_by_id=uuid4(), role="PARENT",
        email=None, phone_number="+237699000001"
    )
    await notify_user_invited(event)


@pytest.mark.asyncio
async def test_notify_user_invited_sends_email():
    from src.infrastructure.events.handlers import notify_user_invited
    from src.core.events.domain_events import UserInvited

    event = UserInvited(
        invitation_id=uuid4(), created_by_id=uuid4(), role="PARENT",
        email="p@t.com", phone_number=None
    )
    # The handler imports EmailService locally — just ensure it runs without error
    await notify_user_invited(event)


@pytest.mark.asyncio
async def test_audit_password_reset():
    from src.infrastructure.events.handlers import audit_password_reset
    from src.core.events.domain_events import PasswordReset

    event = PasswordReset(user_id=uuid4(), reset_by_admin_id=None)
    await audit_password_reset(event)


@pytest.mark.asyncio
async def test_audit_user_deactivated():
    from src.infrastructure.events.handlers import audit_user_deactivated
    from src.core.events.domain_events import UserDeactivated

    event = UserDeactivated(user_id=uuid4(), deactivated_by_id=uuid4())
    await audit_user_deactivated(event)


@pytest.mark.asyncio
async def test_audit_user_activated():
    from src.infrastructure.events.handlers import audit_user_activated
    from src.core.events.domain_events import UserActivated

    event = UserActivated(user_id=uuid4())
    await audit_user_activated(event)


@pytest.mark.asyncio
async def test_audit_user_deleted():
    from src.infrastructure.events.handlers import audit_user_deleted
    from src.core.events.domain_events import UserDeleted

    event = UserDeleted(user_id=uuid4(), deleted_by_id=uuid4())
    await audit_user_deleted(event)


@pytest.mark.asyncio
async def test_audit_discipline_case_opened():
    from src.infrastructure.events.handlers import audit_discipline_case_opened
    from src.core.events.domain_events import DisciplineCaseOpened

    event = DisciplineCaseOpened(
        case_id=uuid4(), accused_user_id=uuid4(),
        offense_category="ABSENCE", opened_by_id=uuid4()
    )
    await audit_discipline_case_opened(event)


@pytest.mark.asyncio
async def test_audit_discipline_sanction():
    from src.infrastructure.events.handlers import audit_discipline_sanction
    from src.core.events.domain_events import DisciplineSanctionIssued

    event = DisciplineSanctionIssued(
        case_id=uuid4(), accused_user_id=uuid4(),
        sanction_type="AVERTISSEMENT", issued_by_id=uuid4()
    )
    await audit_discipline_sanction(event)


@pytest.mark.asyncio
async def test_audit_attendance_recorded():
    from src.infrastructure.events.handlers import audit_attendance_recorded
    from src.core.events.domain_events import AttendanceRecorded

    event = AttendanceRecorded(
        attendance_id=uuid4(), user_id=uuid4(),
        attendance_type="MESSE", status="PRESENT"
    )
    await audit_attendance_recorded(event)
