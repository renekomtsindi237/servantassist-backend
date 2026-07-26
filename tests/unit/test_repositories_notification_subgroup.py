"""
Unit tests for NotificationRepository, NotificationPreferenceRepository,
and SubGroupRepository.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _exec_result(first=None, all_=None, one=None):
    r = MagicMock()
    r.first = MagicMock(return_value=first)
    r.all = MagicMock(return_value=all_ if all_ is not None else [])
    r.one = MagicMock(return_value=one)
    return r


# ═══════════════════════════════════════════════════════════════════════════════
#  NotificationRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_notification(**kw):
    from src.core.entities.notification import (
        Notification,
        NotificationChannel,
        NotificationStatus,
        NotificationType,
    )

    n = MagicMock(spec=Notification)
    n.id = kw.get("id", uuid4())
    n.recipient_id = kw.get("recipient_id", uuid4())
    n.sent_by = kw.get("sent_by", None)
    n.status = kw.get("status", NotificationStatus.PENDING)
    n.channel = kw.get("channel", NotificationChannel.IN_APP)
    n.notification_type = kw.get("notification_type", NotificationType.RAPPEL_EVENEMENT)
    n.updated_at = kw.get("updated_at", datetime.utcnow())
    n.broadcast_id = kw.get("broadcast_id", None)
    n.model_dump = MagicMock(return_value={"id": str(n.id)})
    return n


@pytest.mark.asyncio
async def test_notification_create():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    n = _make_notification()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(n)
    assert result is n
    session.add.assert_called_once_with(n)


@pytest.mark.asyncio
async def test_notification_create_many():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    notifs = [_make_notification(), _make_notification()]
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_many(notifs)
    assert len(result) == 2
    assert session.add.call_count == 2


@pytest.mark.asyncio
async def test_notification_get_by_id_found():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    n = _make_notification()
    session.exec = AsyncMock(return_value=_exec_result(first=n))

    result = await repo.get_by_id(n.id)
    assert result is n


@pytest.mark.asyncio
async def test_notification_get_by_id_not_found():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_notification_get_by_user():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    notifs = [_make_notification(), _make_notification()]
    session.exec = AsyncMock(return_value=_exec_result(all_=notifs))

    result = await repo.get_by_user(uuid4())
    assert len(result) == 2


@pytest.mark.asyncio
async def test_notification_get_by_user_with_filters():
    from src.core.entities.notification import NotificationChannel, NotificationStatus, NotificationType
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(all_=[]))

    result = await repo.get_by_user(
        uuid4(),
        notification_type=NotificationType.RAPPEL_EVENEMENT,
        status=NotificationStatus.PENDING,
        channel=NotificationChannel.IN_APP,
    )
    assert result == []


@pytest.mark.asyncio
async def test_notification_count_by_user():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(one=5))

    result = await repo.count_by_user(uuid4())
    assert result == 5


@pytest.mark.asyncio
async def test_notification_count_unread_by_user():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(one=3))

    result = await repo.count_unread_by_user(uuid4())
    assert result == 3


@pytest.mark.asyncio
async def test_notification_get_all():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    notifs = [_make_notification()]
    session.exec = AsyncMock(return_value=_exec_result(all_=notifs))

    result = await repo.get_all()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_notification_get_all_with_filters():
    from src.core.entities.notification import NotificationChannel, NotificationStatus, NotificationType
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(all_=[]))
    bcast_id = uuid4()

    result = await repo.get_all(
        notification_type=NotificationType.RAPPEL_EVENEMENT,
        channel=NotificationChannel.EMAIL,
        status=NotificationStatus.SENT,
        broadcast_id=bcast_id,
    )
    assert result == []


@pytest.mark.asyncio
async def test_notification_count_all():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(one=10))

    result = await repo.count_all()
    assert result == 10


@pytest.mark.asyncio
async def test_notification_mark_sent_found():
    from src.core.entities.notification import NotificationStatus
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    n = _make_notification(status=NotificationStatus.PENDING)

    session.exec = AsyncMock(return_value=_exec_result(first=n))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.mark_sent(n.id)
    assert result is n
    assert n.status == NotificationStatus.SENT


@pytest.mark.asyncio
async def test_notification_mark_sent_with_error():
    from src.core.entities.notification import NotificationStatus
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    n = _make_notification(status=NotificationStatus.PENDING)

    session.exec = AsyncMock(return_value=_exec_result(first=n))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    await repo.mark_sent(n.id, error_message="SMTP error")
    assert n.status == NotificationStatus.FAILED


@pytest.mark.asyncio
async def test_notification_mark_sent_not_found():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.mark_sent(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_notification_mark_read():
    from src.core.entities.notification import NotificationStatus
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    user_id = uuid4()

    n1 = _make_notification(recipient_id=user_id, status=NotificationStatus.SENT)
    n2 = _make_notification(recipient_id=user_id, status=NotificationStatus.SENT)

    session.exec = AsyncMock(
        side_effect=[
            _exec_result(first=n1),
            _exec_result(first=n2),
        ]
    )
    session.commit = AsyncMock()

    count = await repo.mark_read([n1.id, n2.id], user_id)
    assert count == 2
    assert n1.status == NotificationStatus.READ
    assert n2.status == NotificationStatus.READ


@pytest.mark.asyncio
async def test_notification_mark_read_wrong_user():
    """If notification belongs to a different user, it is NOT marked read."""
    from src.core.entities.notification import NotificationStatus
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    user_id = uuid4()
    other_id = uuid4()

    n = _make_notification(recipient_id=other_id, status=NotificationStatus.SENT)

    session.exec = AsyncMock(return_value=_exec_result(first=n))
    session.commit = AsyncMock()

    count = await repo.mark_read([n.id], user_id)
    assert count == 0


@pytest.mark.asyncio
async def test_notification_enrich_without_sender():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    n = _make_notification(sent_by=None)

    result = await repo.enrich(n)
    assert "id" in result
    # No sender_name key since sent_by is None
    assert "sender_name" not in result


@pytest.mark.asyncio
async def test_notification_enrich_with_sender():
    from src.infrastructure.repositories.notification_repository import NotificationRepository

    session = _mock_session()
    repo = NotificationRepository(session)
    n = _make_notification(sent_by=uuid4())

    row = MagicMock()
    row.first_name = "Pierre"
    row.last_name = "Dupont"
    session.exec = AsyncMock(return_value=_exec_result(first=row))

    result = await repo.enrich(n)
    assert result.get("sender_name") == "Pierre Dupont"


# ─── NotificationPreferenceRepository ────────────────────────────────────────


def _make_pref(**kw):
    from src.core.entities.notification import NotificationPreference, NotificationType

    p = MagicMock()
    p.id = kw.get("id", uuid4())
    p.user_id = kw.get("user_id", uuid4())
    p.notification_type = kw.get("notification_type", NotificationType.RAPPEL_EVENEMENT)
    p.email_enabled = kw.get("email_enabled", False)
    p.whatsapp_enabled = kw.get("whatsapp_enabled", False)
    p.in_app_enabled = kw.get("in_app_enabled", True)
    p.updated_at = kw.get("updated_at", datetime.utcnow())
    return p


@pytest.mark.asyncio
async def test_notif_pref_get_by_user():
    from src.infrastructure.repositories.notification_repository import NotificationPreferenceRepository

    session = _mock_session()
    repo = NotificationPreferenceRepository(session)
    prefs = [_make_pref()]
    session.exec = AsyncMock(return_value=_exec_result(all_=prefs))

    result = await repo.get_by_user(uuid4())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_notif_pref_get_by_user_and_type_found():
    from src.core.entities.notification import NotificationType
    from src.infrastructure.repositories.notification_repository import NotificationPreferenceRepository

    session = _mock_session()
    repo = NotificationPreferenceRepository(session)
    pref = _make_pref()
    session.exec = AsyncMock(return_value=_exec_result(first=pref))

    result = await repo.get_by_user_and_type(uuid4(), NotificationType.RAPPEL_EVENEMENT)
    assert result is pref


@pytest.mark.asyncio
async def test_notif_pref_upsert_creates_new():
    from src.core.entities.notification import NotificationType
    from src.infrastructure.repositories.notification_repository import NotificationPreferenceRepository

    session = _mock_session()
    repo = NotificationPreferenceRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    await repo.upsert(uuid4(), NotificationType.RAPPEL_EVENEMENT, email_enabled=True)
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_notif_pref_upsert_updates_existing():
    from src.core.entities.notification import NotificationType
    from src.infrastructure.repositories.notification_repository import NotificationPreferenceRepository

    session = _mock_session()
    repo = NotificationPreferenceRepository(session)
    pref = _make_pref()
    session.exec = AsyncMock(return_value=_exec_result(first=pref))
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    await repo.upsert(pref.user_id, NotificationType.RAPPEL_EVENEMENT, email_enabled=True, in_app_enabled=False)
    assert pref.email_enabled is True
    assert pref.in_app_enabled is False


# ═══════════════════════════════════════════════════════════════════════════════
#  SubGroupRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_subgroup(**kw):
    from src.core.entities.subgroup import SubGroup

    g = MagicMock(spec=SubGroup)
    g.id = kw.get("id", uuid4())
    g.name = kw.get("name", "Groupe Alpha")
    g.is_active = kw.get("is_active", True)
    return g


def _make_membership(**kw):
    from src.core.entities.subgroup import SubGroupMember

    m = MagicMock(spec=SubGroupMember)
    m.id = kw.get("id", uuid4())
    m.sub_group_id = kw.get("sub_group_id", uuid4())
    m.user_id = kw.get("user_id", uuid4())
    m.is_active = kw.get("is_active", True)
    m.joined_at = kw.get("joined_at", datetime.utcnow())
    m.left_at = kw.get("left_at", None)
    return m


@pytest.mark.asyncio
async def test_subgroup_get_found():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    group = _make_subgroup()
    session.exec = AsyncMock(return_value=_exec_result(first=group))

    result = await repo.get(group.id)
    assert result is group


@pytest.mark.asyncio
async def test_subgroup_get_not_found():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_subgroup_get_by_name():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    group = _make_subgroup(name="Beta")
    session.exec = AsyncMock(return_value=_exec_result(first=group))

    result = await repo.get_by_name("Beta")
    assert result is group


@pytest.mark.asyncio
async def test_subgroup_list_all_active():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    groups = [_make_subgroup(), _make_subgroup()]
    session.exec = AsyncMock(return_value=_exec_result(all_=groups))

    result = await repo.list_all(active_only=True)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_subgroup_list_all_including_inactive():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(all_=[]))

    result = await repo.list_all(active_only=False)
    assert result == []


@pytest.mark.asyncio
async def test_subgroup_create():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    group = _make_subgroup()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(group)
    assert result is group


@pytest.mark.asyncio
async def test_subgroup_update():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    group = _make_subgroup()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(group)
    assert result is group


@pytest.mark.asyncio
async def test_subgroup_delete_found():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    group = _make_subgroup()
    session.exec = AsyncMock(return_value=_exec_result(first=group))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(group.id)
    assert result is True


@pytest.mark.asyncio
async def test_subgroup_delete_not_found():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_subgroup_get_member_count():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    session.exec = AsyncMock(return_value=_exec_result(one=3))

    count = await repo.get_member_count(uuid4())
    assert count == 3


@pytest.mark.asyncio
async def test_subgroup_get_members():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    members = [_make_membership(), _make_membership()]
    session.exec = AsyncMock(return_value=_exec_result(all_=members))

    result = await repo.get_members(uuid4())
    assert len(result) == 2


@pytest.mark.asyncio
async def test_subgroup_get_active_membership():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    m = _make_membership()
    session.exec = AsyncMock(return_value=_exec_result(first=m))

    result = await repo.get_active_membership(uuid4())
    assert result is m


@pytest.mark.asyncio
async def test_subgroup_add_member():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    m = _make_membership()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.add_member(m)
    assert result is m


@pytest.mark.asyncio
async def test_subgroup_remove_member():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    m = _make_membership(is_active=True)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.remove_member(m)
    assert result is m
    assert m.is_active is False


@pytest.mark.asyncio
async def test_subgroup_get_membership():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    m = _make_membership()
    session.exec = AsyncMock(return_value=_exec_result(first=m))

    result = await repo.get_membership(m.sub_group_id, m.user_id)
    assert result is m


@pytest.mark.asyncio
async def test_subgroup_enrich_member():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    m = _make_membership()

    user = MagicMock()
    user.first_name = "Marie"
    user.last_name = "Nkemelu"
    user.email = "marie@example.com"
    user.phone_number = "+237600000000"
    session.exec = AsyncMock(return_value=_exec_result(first=user))

    with patch("src.infrastructure.repositories.subgroup_repository.decrypt_str_fields"):
        result = await repo.enrich_member(m)

    assert result["user_first_name"] == "Marie"
    assert result["user_last_name"] == "Nkemelu"


@pytest.mark.asyncio
async def test_subgroup_enrich_member_no_user():
    from src.infrastructure.repositories.subgroup_repository import SubGroupRepository

    session = _mock_session()
    repo = SubGroupRepository(session)
    m = _make_membership()
    session.exec = AsyncMock(return_value=_exec_result(first=None))

    result = await repo.enrich_member(m)
    assert result["user_first_name"] is None
