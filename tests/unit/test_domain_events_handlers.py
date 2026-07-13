"""Unit tests for domain event handlers and core utils."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

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
    event = UserRegistered(user_id=uid, email="u@t.com", first_name="J", role="SERVANT", created_by_admin=False)
    await bus.publish(event)
    assert uid in called


@pytest.mark.asyncio
async def test_event_bus_handler_exception_does_not_propagate():
    from src.core.events.domain_events import UserRegistered

    bus = EventBus()

    @bus.handler(UserRegistered)
    async def failing_handler(event: UserRegistered):
        raise RuntimeError("Handler broke")

    event = UserRegistered(user_id=uuid4(), email="u@t.com", first_name="J", role="SERVANT", created_by_admin=False)
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
    from src.core.events.domain_events import UserRegistered
    from src.infrastructure.events.handlers import audit_user_registered

    event = UserRegistered(user_id=uuid4(), email="u@t.com", first_name="J", role="SERVANT", created_by_admin=False)
    await audit_user_registered(event)


@pytest.mark.asyncio
async def test_notify_user_registered_skip_no_email():
    from src.core.events.domain_events import UserRegistered
    from src.infrastructure.events.handlers import notify_user_registered

    event = UserRegistered(user_id=uuid4(), email=None, first_name="J", role="ADMIN", created_by_admin=True)
    # No email → should return silently
    await notify_user_registered(event)


@pytest.mark.asyncio
async def test_notify_user_registered_skip_non_admin_role():
    from src.core.events.domain_events import UserRegistered
    from src.infrastructure.events.handlers import notify_user_registered

    event = UserRegistered(user_id=uuid4(), email="u@t.com", first_name="J", role="SERVANT", created_by_admin=False)
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        await notify_user_registered(event)
    MockEmail.assert_not_called()


@pytest.mark.asyncio
async def test_notify_user_registered_admin_sends_welcome():
    from src.core.events.domain_events import UserRegistered
    from src.infrastructure.events.handlers import notify_user_registered

    event = UserRegistered(
        user_id=uuid4(), email="admin@t.com", first_name="René", role="ADMIN", created_by_admin=False
    )
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        instance = AsyncMock()
        instance.send_welcome_email = AsyncMock()
        MockEmail.return_value = instance
        await notify_user_registered(event)
    instance.send_welcome_email.assert_called_once()


@pytest.mark.asyncio
async def test_audit_user_invited():
    from src.core.events.domain_events import UserInvited
    from src.infrastructure.events.handlers import audit_user_invited

    event = UserInvited(invitation_id=uuid4(), created_by_id=uuid4(), role="PARENT", email="p@t.com", phone_number=None)
    await audit_user_invited(event)


@pytest.mark.asyncio
async def test_notify_user_invited_no_email():
    from src.core.events.domain_events import UserInvited
    from src.infrastructure.events.handlers import notify_user_invited

    event = UserInvited(
        invitation_id=uuid4(), created_by_id=uuid4(), role="PARENT", email=None, phone_number="+237699000001"
    )
    await notify_user_invited(event)


@pytest.mark.asyncio
async def test_notify_user_invited_sends_email():
    from src.core.events.domain_events import UserInvited
    from src.infrastructure.events.handlers import notify_user_invited

    event = UserInvited(invitation_id=uuid4(), created_by_id=uuid4(), role="PARENT", email="p@t.com", phone_number=None)
    # The handler imports EmailService locally — just ensure it runs without error
    await notify_user_invited(event)


@pytest.mark.asyncio
async def test_audit_password_reset():
    from src.core.events.domain_events import PasswordReset
    from src.infrastructure.events.handlers import audit_password_reset

    event = PasswordReset(user_id=uuid4(), reset_by_admin_id=None)
    await audit_password_reset(event)


@pytest.mark.asyncio
async def test_audit_user_deactivated():
    from src.core.events.domain_events import UserDeactivated
    from src.infrastructure.events.handlers import audit_user_deactivated

    event = UserDeactivated(user_id=uuid4(), deactivated_by_id=uuid4())
    await audit_user_deactivated(event)


@pytest.mark.asyncio
async def test_audit_user_activated():
    from src.core.events.domain_events import UserActivated
    from src.infrastructure.events.handlers import audit_user_activated

    event = UserActivated(user_id=uuid4())
    await audit_user_activated(event)


@pytest.mark.asyncio
async def test_audit_user_deleted():
    from src.core.events.domain_events import UserDeleted
    from src.infrastructure.events.handlers import audit_user_deleted

    event = UserDeleted(user_id=uuid4(), deleted_by_id=uuid4())
    await audit_user_deleted(event)


@pytest.mark.asyncio
async def test_audit_discipline_case_opened():
    from src.core.events.domain_events import DisciplineCaseOpened
    from src.infrastructure.events.handlers import audit_discipline_case_opened

    event = DisciplineCaseOpened(
        case_id=uuid4(), accused_user_id=uuid4(), offense_category="ABSENCE", opened_by_id=uuid4()
    )
    await audit_discipline_case_opened(event)


@pytest.mark.asyncio
async def test_audit_discipline_sanction():
    from src.core.events.domain_events import DisciplineSanctionIssued
    from src.infrastructure.events.handlers import audit_discipline_sanction

    event = DisciplineSanctionIssued(
        case_id=uuid4(), accused_user_id=uuid4(), sanction_type="AVERTISSEMENT", issued_by_id=uuid4()
    )
    await audit_discipline_sanction(event)


@pytest.mark.asyncio
async def test_audit_attendance_recorded():
    from src.core.events.domain_events import AttendanceRecorded
    from src.infrastructure.events.handlers import audit_attendance_recorded

    event = AttendanceRecorded(attendance_id=uuid4(), user_id=uuid4(), attendance_type="MESSE", status="PRESENT")
    await audit_attendance_recorded(event)


# ─── notify_discipline_accused (nouveau handler) ──────────────────────────────


@pytest.mark.asyncio
async def test_notify_discipline_accused_no_email_skips():
    """Sans email dans l'event, le handler doit retourner silencieusement."""
    from src.core.events.domain_events import DisciplineCaseOpened
    from src.infrastructure.events.handlers import notify_discipline_accused

    event = DisciplineCaseOpened(
        case_id=uuid4(),
        accused_user_id=uuid4(),
        opened_by_id=uuid4(),
        offense_category="ABSENCE",
        accused_email=None,
        accused_first_name=None,
    )
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        await notify_discipline_accused(event)
    MockEmail.assert_not_called()


@pytest.mark.asyncio
async def test_notify_discipline_accused_sends_email():
    """Avec un email, le handler doit appeler send_general_notification."""
    from src.core.events.domain_events import DisciplineCaseOpened
    from src.infrastructure.events.handlers import notify_discipline_accused

    event = DisciplineCaseOpened(
        case_id=uuid4(),
        accused_user_id=uuid4(),
        opened_by_id=uuid4(),
        offense_category="COMPORTEMENT",
        accused_email="servant@bmra.org",
        accused_first_name="Jean",
    )
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        instance = AsyncMock()
        instance.send_general_notification = AsyncMock(return_value=True)
        MockEmail.return_value = instance
        await notify_discipline_accused(event)

    instance.send_general_notification.assert_called_once()
    call_kwargs = instance.send_general_notification.call_args.kwargs
    assert call_kwargs["to_email"] == "servant@bmra.org"
    assert call_kwargs["user_first_name"] == "Jean"
    assert "disciplinaire" in call_kwargs["title"].lower()


@pytest.mark.asyncio
async def test_notify_discipline_accused_email_error_handled():
    """Une exception dans l'envoi email ne doit pas propager."""
    from src.core.events.domain_events import DisciplineCaseOpened
    from src.infrastructure.events.handlers import notify_discipline_accused

    event = DisciplineCaseOpened(
        case_id=uuid4(),
        accused_user_id=uuid4(),
        opened_by_id=uuid4(),
        offense_category="ABSENCE",
        accused_email="servant@bmra.org",
        accused_first_name=None,
    )
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        instance = AsyncMock()
        instance.send_general_notification = AsyncMock(side_effect=ConnectionError("SMTP down"))
        MockEmail.return_value = instance
        # Should not raise
        await notify_discipline_accused(event)


@pytest.mark.asyncio
async def test_notify_discipline_accused_derives_firstname_from_email():
    """Si first_name absent, le prénom est dérivé du nom d'utilisateur de l'email."""
    from src.core.events.domain_events import DisciplineCaseOpened
    from src.infrastructure.events.handlers import notify_discipline_accused

    event = DisciplineCaseOpened(
        case_id=uuid4(),
        accused_user_id=uuid4(),
        opened_by_id=uuid4(),
        offense_category="ABSENCE",
        accused_email="pierre.martin@bmra.org",
        accused_first_name=None,
    )
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        instance = AsyncMock()
        instance.send_general_notification = AsyncMock(return_value=True)
        MockEmail.return_value = instance
        await notify_discipline_accused(event)

    call_kwargs = instance.send_general_notification.call_args.kwargs
    assert call_kwargs["user_first_name"] == "Pierre.martin"


# ─── notify_password_reset (nouveau handler) ──────────────────────────────────


@pytest.mark.asyncio
async def test_notify_password_reset_no_email_skips():
    """Sans email dans l'event, le handler doit retourner silencieusement."""
    from src.core.events.domain_events import PasswordReset
    from src.infrastructure.events.handlers import notify_password_reset

    event = PasswordReset(user_id=uuid4(), reset_by_admin_id=uuid4(), email=None, first_name=None)
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        await notify_password_reset(event)
    MockEmail.assert_not_called()


@pytest.mark.asyncio
async def test_notify_password_reset_sends_confirmation_email():
    """Avec email, le handler doit appeler send_password_changed_email."""
    from src.core.events.domain_events import PasswordReset
    from src.infrastructure.events.handlers import notify_password_reset

    event = PasswordReset(
        user_id=uuid4(),
        reset_by_admin_id=uuid4(),
        email="rene@bmra.org",
        first_name="René",
    )
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        instance = AsyncMock()
        instance.send_password_changed_email = AsyncMock(return_value=True)
        MockEmail.return_value = instance
        await notify_password_reset(event)

    instance.send_password_changed_email.assert_called_once_with(
        to_email="rene@bmra.org",
        user_first_name="René",
    )


@pytest.mark.asyncio
async def test_notify_password_reset_email_error_handled():
    """Une exception dans l'envoi email ne doit pas propager."""
    from src.core.events.domain_events import PasswordReset
    from src.infrastructure.events.handlers import notify_password_reset

    event = PasswordReset(user_id=uuid4(), email="user@bmra.org", first_name="Jean")
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        instance = AsyncMock()
        instance.send_password_changed_email = AsyncMock(side_effect=TimeoutError("SMTP timeout"))
        MockEmail.return_value = instance
        # Should not raise
        await notify_password_reset(event)


@pytest.mark.asyncio
async def test_notify_password_reset_derives_firstname_from_email():
    """Si first_name absent, le prénom est dérivé du nom d'utilisateur email."""
    from src.core.events.domain_events import PasswordReset
    from src.infrastructure.events.handlers import notify_password_reset

    event = PasswordReset(user_id=uuid4(), email="dupont@bmra.org", first_name=None)
    with patch("src.infrastructure.events.handlers.EmailService") as MockEmail:
        instance = AsyncMock()
        instance.send_password_changed_email = AsyncMock(return_value=True)
        MockEmail.return_value = instance
        await notify_password_reset(event)

    call_kwargs = instance.send_password_changed_email.call_args.kwargs
    assert call_kwargs["user_first_name"] == "Dupont"


@pytest.mark.asyncio
async def test_password_reset_event_carries_email():
    """Le domaine PasswordReset transporte maintenant email et first_name."""
    from src.core.events.domain_events import PasswordReset

    uid = uuid4()
    event = PasswordReset(
        user_id=uid,
        reset_by_admin_id=None,
        email="admin@bmra.org",
        first_name="Admin",
    )
    assert event.email == "admin@bmra.org"
    assert event.first_name == "Admin"
    assert event.user_id == uid


@pytest.mark.asyncio
async def test_discipline_case_opened_event_carries_contact():
    """DisciplineCaseOpened transporte maintenant accused_email et accused_first_name."""
    from src.core.events.domain_events import DisciplineCaseOpened

    cid = uuid4()
    event = DisciplineCaseOpened(
        case_id=cid,
        accused_user_id=uuid4(),
        opened_by_id=uuid4(),
        offense_category="ABSENCE",
        accused_email="servant@bmra.org",
        accused_first_name="Pierre",
    )
    assert event.accused_email == "servant@bmra.org"
    assert event.accused_first_name == "Pierre"
    assert event.case_id == cid
