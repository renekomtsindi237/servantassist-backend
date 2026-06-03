"""
Unit tests for NotificationService.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.services.notification_service import NotificationService
from src.core.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from src.core.entities.user import User, UserRole

NOW = datetime(2026, 6, 1, 10, 0, 0)


# ─── Factories ────────────────────────────────────────────────────────────────


def _make_notification(
    channel=NotificationChannel.IN_APP,
    notification_type=NotificationType.GENERAL,
    status=NotificationStatus.SENT,
    **kwargs,
) -> Notification:
    return Notification(
        id=kwargs.pop("id", uuid4()),
        recipient_id=kwargs.pop("recipient_id", uuid4()),
        notification_type=notification_type,
        channel=channel,
        priority=kwargs.pop("priority", NotificationPriority.NORMAL),
        title=kwargs.pop("title", "Test Titre"),
        body=kwargs.pop("body", "Corps de la notification"),
        status=status,
        sent_by=kwargs.pop("sent_by", None),
        created_at=kwargs.pop("created_at", NOW),
        **kwargs,
    )


def _make_user(role=UserRole.SERVANT, phone=None) -> User:
    u = User(
        id=uuid4(),
        first_name="Marie",
        last_name="Kone",
        email=f"marie_{uuid4().hex[:6]}@test.com",
        role=role,
        is_active=True,
    )
    if phone:
        u.phone_number = phone
    return u


def _make_svc(session=None) -> NotificationService:
    if session is None:
        session = AsyncMock()
    svc = NotificationService(session=session)
    svc.repo = AsyncMock()
    svc.pref_repo = AsyncMock()
    svc.email_service = AsyncMock()
    svc.whatsapp_service = AsyncMock()
    return svc


# ─── send_notification — IN_APP ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_notification_in_app_no_ws():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.IN_APP)
    svc.repo.create.return_value = notif
    svc.repo.mark_sent.return_value = None
    svc.repo.get_by_id.return_value = notif

    result = await svc.send_notification(
        recipient_id=notif.recipient_id,
        notification_type=NotificationType.GENERAL,
        channel=NotificationChannel.IN_APP,
        title="Test",
        body="Corps",
    )

    assert result.id == notif.id
    svc.repo.create.assert_called_once()
    svc.repo.mark_sent.assert_called_once_with(notif.id, error_message=None)


@pytest.mark.asyncio
async def test_send_notification_in_app_with_ws_manager():
    ws_manager = AsyncMock()

    session = AsyncMock()
    svc = NotificationService(session=session, ws_manager=ws_manager)
    svc.repo = AsyncMock()
    svc.pref_repo = AsyncMock()

    notif = _make_notification(channel=NotificationChannel.IN_APP)
    notif.created_at = NOW
    svc.repo.create.return_value = notif
    svc.repo.mark_sent.return_value = None
    svc.repo.get_by_id.return_value = notif

    await svc.send_notification(
        recipient_id=notif.recipient_id,
        notification_type=NotificationType.GENERAL,
        channel=NotificationChannel.IN_APP,
        title="Alert",
        body="Message",
    )

    ws_manager.send_to_user.assert_called_once()
    call_args = ws_manager.send_to_user.call_args
    assert call_args[0][0] == str(notif.recipient_id)


@pytest.mark.asyncio
async def test_send_notification_ws_failure_non_fatal():
    ws_manager = AsyncMock()
    ws_manager.send_to_user.side_effect = Exception("WS connection closed")

    session = AsyncMock()
    svc = NotificationService(session=session, ws_manager=ws_manager)
    svc.repo = AsyncMock()
    svc.pref_repo = AsyncMock()

    notif = _make_notification(channel=NotificationChannel.IN_APP)
    notif.created_at = NOW
    svc.repo.create.return_value = notif
    svc.repo.mark_sent.return_value = None
    svc.repo.get_by_id.return_value = notif

    result = await svc.send_notification(
        recipient_id=notif.recipient_id,
        notification_type=NotificationType.GENERAL,
        channel=NotificationChannel.IN_APP,
        title="Test",
        body="Corps",
    )

    assert result is not None
    svc.repo.mark_sent.assert_called_once()


@pytest.mark.asyncio
async def test_send_notification_email():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.EMAIL)
    svc.repo.create.return_value = notif
    svc.repo.mark_sent.return_value = None
    svc.repo.get_by_id.return_value = notif

    user = _make_user()
    result_mock = MagicMock()
    result_mock.first.return_value = user
    svc.session.exec = AsyncMock(return_value=result_mock)
    svc.email_service.send_general_notification = AsyncMock(return_value=True)

    result = await svc.send_notification(
        recipient_id=notif.recipient_id,
        notification_type=NotificationType.GENERAL,
        channel=NotificationChannel.EMAIL,
        title="Test Email",
        body="Corps email",
    )

    assert result.id == notif.id
    svc.repo.mark_sent.assert_called_once_with(notif.id, error_message=None)


@pytest.mark.asyncio
async def test_send_notification_whatsapp_no_phone():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.WHATSAPP)
    svc.repo.create.return_value = notif
    svc.repo.mark_sent.return_value = None
    svc.repo.get_by_id.return_value = notif

    user = _make_user()
    result_mock = MagicMock()
    result_mock.first.return_value = user
    svc.session.exec = AsyncMock(return_value=result_mock)

    result = await svc.send_notification(
        recipient_id=notif.recipient_id,
        notification_type=NotificationType.GENERAL,
        channel=NotificationChannel.WHATSAPP,
        title="Test WA",
        body="Corps WA",
    )

    assert result.id == notif.id
    svc.repo.mark_sent.assert_called_once_with(notif.id, error_message="Pas de numero de telephone")


# ─── _send_email ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_email_user_not_found():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.EMAIL)

    result_mock = MagicMock()
    result_mock.first.return_value = None
    svc.session.exec = AsyncMock(return_value=result_mock)

    error = await svc._send_email(notif)
    assert error == "Destinataire introuvable"


@pytest.mark.asyncio
async def test_send_email_success():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.EMAIL, notification_type=NotificationType.GENERAL)

    user = _make_user()
    result_mock = MagicMock()
    result_mock.first.return_value = user
    svc.session.exec = AsyncMock(return_value=result_mock)
    svc.email_service.send_general_notification = AsyncMock(return_value=True)

    error = await svc._send_email(notif)
    assert error is None


@pytest.mark.asyncio
async def test_send_email_smtp_not_configured():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.EMAIL, notification_type=NotificationType.GENERAL)

    user = _make_user()
    result_mock = MagicMock()
    result_mock.first.return_value = user
    svc.session.exec = AsyncMock(return_value=result_mock)
    svc.email_service.send_general_notification = AsyncMock(return_value=False)

    error = await svc._send_email(notif)
    assert "SMTP" in error or "envoi echoue" in error


@pytest.mark.asyncio
async def test_send_email_exception():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.EMAIL, notification_type=NotificationType.GENERAL)

    user = _make_user()
    result_mock = MagicMock()
    result_mock.first.return_value = user
    svc.session.exec = AsyncMock(return_value=result_mock)
    svc.email_service.send_general_notification = AsyncMock(side_effect=Exception("SMTP error"))

    error = await svc._send_email(notif)
    assert "SMTP error" in error


# ─── _dispatch_email ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dispatch_email_affectation():
    svc = _make_svc()
    notif = _make_notification(notification_type=NotificationType.AFFECTATION)
    user = _make_user()
    svc.email_service.send_assignment_notification = AsyncMock(return_value=True)

    result = await svc._dispatch_email(notif, user)
    assert result is True
    svc.email_service.send_assignment_notification.assert_called_once()


@pytest.mark.asyncio
async def test_dispatch_email_rappel_evenement():
    svc = _make_svc()
    notif = _make_notification(notification_type=NotificationType.RAPPEL_EVENEMENT)
    user = _make_user()
    svc.email_service.send_event_reminder = AsyncMock(return_value=True)

    result = await svc._dispatch_email(notif, user)
    assert result is True


@pytest.mark.asyncio
async def test_dispatch_email_absence_parent():
    svc = _make_svc()
    notif = _make_notification(notification_type=NotificationType.ABSENCE_PARENT)
    user = _make_user()
    svc.email_service.send_absence_parent_notification = AsyncMock(return_value=True)

    result = await svc._dispatch_email(notif, user)
    assert result is True


@pytest.mark.asyncio
async def test_dispatch_email_avertissement_absence():
    svc = _make_svc()
    notif = _make_notification(notification_type=NotificationType.AVERTISSEMENT_ABSENCE)
    user = _make_user()
    svc.email_service.send_general_notification = AsyncMock(return_value=True)

    result = await svc._dispatch_email(notif, user)
    assert result is True


@pytest.mark.asyncio
async def test_dispatch_email_convocation_parent():
    svc = _make_svc()
    notif = _make_notification(notification_type=NotificationType.CONVOCATION_PARENT)
    user = _make_user()
    svc.email_service.send_general_notification = AsyncMock(return_value=True)

    result = await svc._dispatch_email(notif, user)
    assert result is True


@pytest.mark.asyncio
async def test_dispatch_email_discipline_general():
    svc = _make_svc()
    notif = _make_notification(notification_type=NotificationType.DISCIPLINE)
    user = _make_user()
    svc.email_service.send_general_notification = AsyncMock(return_value=True)

    result = await svc._dispatch_email(notif, user)
    assert result is True


# ─── _send_whatsapp ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_whatsapp_user_not_found():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.WHATSAPP)

    result_mock = MagicMock()
    result_mock.first.return_value = None
    svc.session.exec = AsyncMock(return_value=result_mock)

    error = await svc._send_whatsapp(notif)
    assert error == "Destinataire introuvable"


@pytest.mark.asyncio
async def test_send_whatsapp_no_phone_number():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.WHATSAPP)

    user = _make_user()
    result_mock = MagicMock()
    result_mock.first.return_value = user
    svc.session.exec = AsyncMock(return_value=result_mock)

    error = await svc._send_whatsapp(notif)
    assert error == "Pas de numero de telephone"


@pytest.mark.asyncio
async def test_send_whatsapp_success():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.WHATSAPP)

    user = _make_user(phone="+22500000000")
    result_mock = MagicMock()
    result_mock.first.return_value = user
    svc.session.exec = AsyncMock(return_value=result_mock)
    svc.whatsapp_service.send_admin_notification = AsyncMock(return_value=True)

    error = await svc._send_whatsapp(notif)
    assert error is None


@pytest.mark.asyncio
async def test_send_whatsapp_not_configured():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.WHATSAPP)

    user = _make_user(phone="+22500000000")
    result_mock = MagicMock()
    result_mock.first.return_value = user
    svc.session.exec = AsyncMock(return_value=result_mock)
    svc.whatsapp_service.send_admin_notification = AsyncMock(return_value=False)

    error = await svc._send_whatsapp(notif)
    assert error is not None
    assert "WhatsApp" in error


@pytest.mark.asyncio
async def test_send_whatsapp_exception():
    svc = _make_svc()
    notif = _make_notification(channel=NotificationChannel.WHATSAPP)

    user = _make_user(phone="+22500000000")
    result_mock = MagicMock()
    result_mock.first.return_value = user
    svc.session.exec = AsyncMock(return_value=result_mock)
    svc.whatsapp_service.send_admin_notification = AsyncMock(side_effect=Exception("WA timeout"))

    error = await svc._send_whatsapp(notif)
    assert "WA timeout" in error


# ─── broadcast ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_broadcast_to_unknown_target():
    svc = _make_svc()
    result_mock = MagicMock()
    result_mock.all.return_value = []
    svc.session.exec = AsyncMock(return_value=result_mock)

    result = await svc.broadcast(
        target="unknown_target",
        notification_type=NotificationType.GENERAL,
        channel=NotificationChannel.IN_APP,
        title="Test",
        body="Corps",
    )

    assert result["total_sent"] == 0
    assert result["total_failed"] == 0


@pytest.mark.asyncio
async def test_broadcast_success_two_recipients():
    svc = _make_svc()

    user1 = _make_user()
    user2 = _make_user()
    notif_sent = _make_notification(status=NotificationStatus.SENT)
    notif_failed = _make_notification(status=NotificationStatus.FAILED)

    result_mock = MagicMock()
    result_mock.all.return_value = [user1, user2]
    svc.session.exec = AsyncMock(return_value=result_mock)

    call_count = 0

    async def mock_send_notification(**kwargs):
        nonlocal call_count
        call_count += 1
        return notif_sent if call_count == 1 else notif_failed

    svc.send_notification = mock_send_notification

    result = await svc.broadcast(
        target="all",
        notification_type=NotificationType.GENERAL,
        channel=NotificationChannel.IN_APP,
        title="Broadcast",
        body="Message",
    )

    assert result["total_sent"] == 1
    assert result["total_failed"] == 1
    assert "broadcast_id" in result


# ─── _resolve_recipients ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_recipients_unknown_returns_empty():
    svc = _make_svc()
    result = await svc._resolve_recipients("foobar")
    assert result == []


@pytest.mark.asyncio
async def test_resolve_recipients_all():
    svc = _make_svc()
    users = [_make_user(), _make_user()]
    result_mock = MagicMock()
    result_mock.all.return_value = users
    svc.session.exec = AsyncMock(return_value=result_mock)

    result = await svc._resolve_recipients("all")
    assert result == users


@pytest.mark.asyncio
async def test_resolve_recipients_servants():
    svc = _make_svc()
    servants = [_make_user(role=UserRole.SERVANT)]
    result_mock = MagicMock()
    result_mock.all.return_value = servants
    svc.session.exec = AsyncMock(return_value=result_mock)

    result = await svc._resolve_recipients("servants")
    assert result == servants


@pytest.mark.asyncio
async def test_resolve_recipients_parents():
    svc = _make_svc()
    parents = [_make_user(role=UserRole.PARENT)]
    result_mock = MagicMock()
    result_mock.all.return_value = parents
    svc.session.exec = AsyncMock(return_value=result_mock)

    result = await svc._resolve_recipients("parents")
    assert result == parents


@pytest.mark.asyncio
async def test_resolve_recipients_responsables():
    svc = _make_svc()
    responsables = [_make_user()]
    result_mock = MagicMock()
    result_mock.all.return_value = responsables
    svc.session.exec = AsyncMock(return_value=result_mock)

    result = await svc._resolve_recipients("responsables")
    assert result == responsables


@pytest.mark.asyncio
async def test_resolve_recipients_subgroup():
    svc = _make_svc()
    members = [_make_user()]
    result_mock = MagicMock()
    result_mock.all.return_value = members
    svc.session.exec = AsyncMock(return_value=result_mock)

    result = await svc._resolve_recipients(f"subgroup:{uuid4()}")
    assert result == members


# ─── get_user_notifications ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_user_notifications():
    svc = _make_svc()
    user_id = uuid4()
    notif = _make_notification()
    svc.repo.get_by_user = AsyncMock(return_value=[notif])
    svc.repo.enrich = AsyncMock(return_value={"id": str(notif.id), "title": notif.title})

    result = await svc.get_user_notifications(user_id)

    assert len(result) == 1
    assert result[0]["title"] == notif.title
    svc.repo.get_by_user.assert_called_once_with(
        user_id,
        notification_type=None,
        status=None,
        channel=NotificationChannel.IN_APP,
        limit=50,
        offset=0,
    )


# ─── get_notification ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_notification_not_found():
    svc = _make_svc()
    svc.repo.get_by_id = AsyncMock(return_value=None)

    result = await svc.get_notification(uuid4(), uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_notification_wrong_user():
    svc = _make_svc()
    notif = _make_notification(recipient_id=uuid4())
    svc.repo.get_by_id = AsyncMock(return_value=notif)

    result = await svc.get_notification(notif.id, uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_notification_success():
    svc = _make_svc()
    user_id = uuid4()
    notif = _make_notification(recipient_id=user_id)
    enriched = {"id": str(notif.id), "title": notif.title}
    svc.repo.get_by_id = AsyncMock(return_value=notif)
    svc.repo.enrich = AsyncMock(return_value=enriched)

    result = await svc.get_notification(notif.id, user_id)
    assert result == enriched


# ─── mark_as_read / get_user_stats ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_mark_as_read():
    svc = _make_svc()
    svc.repo.mark_read = AsyncMock(return_value=3)

    ids = [uuid4(), uuid4(), uuid4()]
    user_id = uuid4()
    count = await svc.mark_as_read(ids, user_id)

    assert count == 3
    svc.repo.mark_read.assert_called_once_with(ids, user_id)


@pytest.mark.asyncio
async def test_get_user_stats():
    svc = _make_svc()
    user_id = uuid4()
    stats = {"total": 10, "unread": 3}
    svc.repo.get_stats_by_user = AsyncMock(return_value=stats)

    result = await svc.get_user_stats(user_id)
    assert result == stats


# ─── get_all_notifications ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_all_notifications():
    svc = _make_svc()
    notif = _make_notification()
    enriched = {"id": str(notif.id)}
    svc.repo.get_all = AsyncMock(return_value=[notif])
    svc.repo.count_all = AsyncMock(return_value=1)
    svc.repo.enrich = AsyncMock(return_value=enriched)

    result = await svc.get_all_notifications()

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["limit"] == 50
    assert result["offset"] == 0


# ─── get_preferences ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_preferences_no_existing():
    svc = _make_svc()
    svc.pref_repo.get_by_user = AsyncMock(return_value=[])

    result = await svc.get_preferences(uuid4())

    nt_count = len(list(NotificationType))
    assert len(result) == nt_count
    for pref in result:
        assert pref["in_app_enabled"] is True
        assert pref["email_enabled"] is False


@pytest.mark.asyncio
async def test_get_preferences_with_existing():
    svc = _make_svc()
    user_id = uuid4()

    pref = MagicMock()
    pref.notification_type = NotificationType.GENERAL
    pref.model_dump.return_value = {
        "notification_type": NotificationType.GENERAL,
        "email_enabled": True,
        "whatsapp_enabled": False,
        "in_app_enabled": True,
    }
    svc.pref_repo.get_by_user = AsyncMock(return_value=[pref])

    result = await svc.get_preferences(user_id)

    general_pref = next(r for r in result if r["notification_type"] == NotificationType.GENERAL)
    assert general_pref["email_enabled"] is True


# ─── update_preference ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_preference():
    svc = _make_svc()
    user_id = uuid4()

    updated_pref = MagicMock()
    updated_pref.model_dump.return_value = {
        "notification_type": NotificationType.AFFECTATION,
        "email_enabled": True,
        "whatsapp_enabled": True,
        "in_app_enabled": True,
    }
    svc.pref_repo.upsert = AsyncMock(return_value=updated_pref)

    result = await svc.update_preference(
        user_id,
        NotificationType.AFFECTATION,
        email_enabled=True,
        whatsapp_enabled=True,
    )

    assert result["email_enabled"] is True
    svc.pref_repo.upsert.assert_called_once_with(
        user_id,
        NotificationType.AFFECTATION,
        email_enabled=True,
        whatsapp_enabled=True,
        in_app_enabled=None,
    )
