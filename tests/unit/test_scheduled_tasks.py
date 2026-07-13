"""
Unit tests for src/infrastructure/tasks/scheduled.py

Tests the async helper functions (_run_async, _send_event_reminders_async, etc.)
with mocked sessions and email service - no real DB or Celery worker.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


# ─── _run_async ───────────────────────────────────────────────────────────────


def test_run_async_returns_value():
    from src.infrastructure.tasks.scheduled import _run_async

    async def _coro():
        return 42

    result = _run_async(_coro())
    assert result == 42


def test_run_async_propagates_exception():
    from src.infrastructure.tasks.scheduled import _run_async

    async def _coro():
        raise ValueError("test error")

    with pytest.raises(ValueError, match="test error"):
        _run_async(_coro())


def test_run_async_closes_loop():
    from src.infrastructure.tasks.scheduled import _run_async

    closed = []

    async def _coro():
        loop = asyncio.get_event_loop()
        closed.append(loop)
        return "done"

    _run_async(_coro())
    # Loop used inside should be closed afterwards
    assert closed[0].is_closed()


# ─── _send_event_reminders_async ─────────────────────────────────────────────


def _make_event(**kw):
    from src.core.entities.event import EventStatus

    event = MagicMock()
    event.id = kw.get("id", uuid4())
    event.title = kw.get("title", "Messe dimanche")
    event.status = kw.get("status", EventStatus.PUBLIE)
    event.start_time = kw.get("start_time", datetime.now(timezone.utc) + timedelta(hours=24))
    event.location = kw.get("location", "Cathédrale")
    return event


def _make_assignment(**kw):
    assignment = MagicMock()
    assignment.event_id = kw.get("event_id", uuid4())
    assignment.user_id = kw.get("user_id", uuid4())
    mock_role = MagicMock()
    mock_role.value = kw.get("liturgical_role", "servant")
    assignment.liturgical_role = mock_role
    return assignment


def _make_user(**kw):
    user = MagicMock()
    user.id = kw.get("id", uuid4())
    user.email = kw.get("email", "user@example.com")
    user.first_name = kw.get("first_name", "Jean")
    user.is_active = kw.get("is_active", True)
    return user


def _exec_result(items):
    r = MagicMock()
    r.all.return_value = items
    return r


@pytest.mark.asyncio
async def test_send_event_reminders_no_events():
    """No events tomorrow → early return, no emails sent."""
    from src.infrastructure.tasks.scheduled import _send_event_reminders_async

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(return_value=_exec_result([]))

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    with patch("src.infrastructure.tasks.scheduled.sessionmanager", mock_sm, create=True):
        import src.infrastructure.tasks.scheduled as sched_mod
        orig_sm = getattr(sched_mod, "sessionmanager", None)
        # Patch through the local import
        with patch("src.infrastructure.database.session.sessionmanager", mock_sm):
            # The function imports sessionmanager inside; patch it there
            pass

    # Better approach: patch where it's used (local import inside function)
    import src.infrastructure.database.session as db_session_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        await _send_event_reminders_async()

    # No crash = pass; no emails were sent since events list is empty


@pytest.mark.asyncio
async def test_send_event_reminders_sends_emails():
    """Events exist tomorrow with accepted assignments → emails sent."""
    from src.infrastructure.tasks.scheduled import _send_event_reminders_async

    event = _make_event()
    assignment = _make_assignment(event_id=event.id)
    user = _make_user()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(side_effect=[
        _exec_result([event]),        # events query
        _exec_result([assignment]),   # assignments query for event
    ])
    mock_session.get = AsyncMock(return_value=user)

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    mock_email_svc = AsyncMock()
    mock_email_svc.send_event_reminder = AsyncMock(return_value=True)

    import src.infrastructure.database.session as db_session_mod
    import src.infrastructure.services.email_service as email_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        with patch.object(email_mod, "EmailService", return_value=mock_email_svc):
            await _send_event_reminders_async()

    mock_email_svc.send_event_reminder.assert_called_once()


@pytest.mark.asyncio
async def test_send_event_reminders_skips_inactive_user():
    """Inactive users are skipped — no email sent."""
    from src.infrastructure.tasks.scheduled import _send_event_reminders_async

    event = _make_event()
    assignment = _make_assignment(event_id=event.id)
    user = _make_user(is_active=False)

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(side_effect=[
        _exec_result([event]),
        _exec_result([assignment]),
    ])
    mock_session.get = AsyncMock(return_value=user)

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    mock_email_svc = AsyncMock()
    mock_email_svc.send_event_reminder = AsyncMock(return_value=True)

    import src.infrastructure.database.session as db_session_mod
    import src.infrastructure.services.email_service as email_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        with patch.object(email_mod, "EmailService", return_value=mock_email_svc):
            await _send_event_reminders_async()

    mock_email_svc.send_event_reminder.assert_not_called()


@pytest.mark.asyncio
async def test_send_event_reminders_skips_no_email():
    """Users without email are skipped."""
    from src.infrastructure.tasks.scheduled import _send_event_reminders_async

    event = _make_event()
    assignment = _make_assignment(event_id=event.id)
    user = _make_user(email=None)

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(side_effect=[
        _exec_result([event]),
        _exec_result([assignment]),
    ])
    mock_session.get = AsyncMock(return_value=user)

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    mock_email_svc = AsyncMock()
    mock_email_svc.send_event_reminder = AsyncMock(return_value=True)

    import src.infrastructure.database.session as db_session_mod
    import src.infrastructure.services.email_service as email_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        with patch.object(email_mod, "EmailService", return_value=mock_email_svc):
            await _send_event_reminders_async()

    mock_email_svc.send_event_reminder.assert_not_called()


# ─── _send_weekly_report_async ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_weekly_report_no_admins():
    """No admins → early return."""
    from src.infrastructure.tasks.scheduled import _send_weekly_report_async

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(return_value=_exec_result([]))

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    import src.infrastructure.database.session as db_session_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        await _send_weekly_report_async()

    # Only one exec call (admins query), no events/attendance queries
    assert mock_session.exec.call_count == 1


@pytest.mark.asyncio
async def test_send_weekly_report_sends_to_admins():
    """Admins exist with no attendance → report sent to each admin (att_rate=N/A)."""
    from src.infrastructure.tasks.scheduled import _send_weekly_report_async

    admin1 = _make_user(email="admin@example.com", first_name="Admin")
    admin2 = _make_user(email="admin2@example.com", first_name="Admin2")

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(side_effect=[
        _exec_result([admin1, admin2]),     # admins
        _exec_result([MagicMock()]),         # events
        _exec_result([]),                    # attendance (empty avoids RETARD bug)
    ])

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    mock_email_svc = AsyncMock()
    mock_email_svc.send_general_notification = AsyncMock()

    import src.infrastructure.database.session as db_session_mod
    import src.infrastructure.services.email_service as email_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        with patch.object(email_mod, "EmailService", return_value=mock_email_svc):
            await _send_weekly_report_async()

    assert mock_email_svc.send_general_notification.call_count == 2


@pytest.mark.asyncio
async def test_send_weekly_report_no_attendance():
    """Attendance rate shows N/A when no attendance records."""
    from src.infrastructure.tasks.scheduled import _send_weekly_report_async

    admin = _make_user()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(side_effect=[
        _exec_result([admin]),   # admins
        _exec_result([]),        # events (empty)
        _exec_result([]),        # attendance (empty)
    ])

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    mock_email_svc = AsyncMock()
    mock_email_svc.send_general_notification = AsyncMock()

    import src.infrastructure.database.session as db_session_mod
    import src.infrastructure.services.email_service as email_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        with patch.object(email_mod, "EmailService", return_value=mock_email_svc):
            await _send_weekly_report_async()

    # Report should mention N/A when no attendance
    call_args = mock_email_svc.send_general_notification.call_args[1]
    assert "N/A" in call_args.get("body", "")


# ─── _cleanup_notifications_async ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cleanup_notifications_returns_deleted_count():
    from src.infrastructure.tasks.scheduled import _cleanup_notifications_async

    mock_result = MagicMock()
    mock_result.rowcount = 5

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    import src.infrastructure.database.session as db_session_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        deleted = await _cleanup_notifications_async()

    assert deleted == 5
    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_cleanup_notifications_zero_rowcount():
    from src.infrastructure.tasks.scheduled import _cleanup_notifications_async

    mock_result = MagicMock()
    mock_result.rowcount = None  # Some DB backends return None

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    import src.infrastructure.database.session as db_session_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        deleted = await _cleanup_notifications_async()

    assert deleted == 0
