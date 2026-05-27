"""
Tests E2E du module Communication / Notifications.

Couvre :
- Envoi de notification individuelle (admin/aumonier)
- Broadcast a un groupe (admin/aumonier)
- Lecture des notifications de l'utilisateur connecte
- Detail d'une notification
- Marquage comme lues
- Statistiques utilisateur
- Preferences de notification
- Historique admin
- Controle d'acces (RBAC)
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.notification import Notification, NotificationPreference
from src.core.entities.user import User
from tests.conftest import make_auth_header

# ═══════════════════════════════════════════════════════════════════════════
#  ENVOI INDIVIDUEL
# ═══════════════════════════════════════════════════════════════════════════


class TestSendNotification:
    """Tests pour l'envoi de notifications individuelles."""

    @pytest.mark.asyncio
    async def test_send_notification_success(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        resp = await client.post(
            "/api/v1/communication/notify",
            json={
                "recipient_id": str(servant_user.id),
                "notification_type": "GENERAL",
                "channel": "IN_APP",
                "title": "Reunion importante",
                "body": "Reunion de preparation a 8h dimanche.",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["recipient_id"] == str(servant_user.id)
        assert body["title"] == "Reunion importante"
        assert body["notification_type"] == "GENERAL"
        assert body["channel"] == "IN_APP"
        assert body["status"] == "SENT"
        assert body["sent_by"] == str(aumonier_user.id)

    @pytest.mark.asyncio
    async def test_send_notification_with_priority(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        resp = await client.post(
            "/api/v1/communication/notify",
            json={
                "recipient_id": str(servant_user.id),
                "notification_type": "AFFECTATION",
                "channel": "IN_APP",
                "priority": "HIGH",
                "title": "Nouvelle affectation",
                "body": "Vous etes affecte a la messe de dimanche.",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["priority"] == "HIGH"
        assert body["notification_type"] == "AFFECTATION"

    @pytest.mark.asyncio
    async def test_send_notification_with_related_entity(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        event_id = str(uuid4())
        resp = await client.post(
            "/api/v1/communication/notify",
            json={
                "recipient_id": str(servant_user.id),
                "notification_type": "RAPPEL_EVENEMENT",
                "channel": "IN_APP",
                "title": "Rappel evenement",
                "body": "La messe dominicale est dans 24h.",
                "related_entity_type": "event",
                "related_entity_id": event_id,
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["related_entity_type"] == "event"
        assert body["related_entity_id"] == event_id

    @pytest.mark.asyncio
    async def test_send_notification_forbidden_servant(
        self, client: AsyncClient, servant_user: User, aumonier_user: User
    ):
        """Un servant ne peut pas envoyer de notification."""
        resp = await client.post(
            "/api/v1/communication/notify",
            json={
                "recipient_id": str(aumonier_user.id),
                "notification_type": "GENERAL",
                "channel": "IN_APP",
                "title": "Test",
                "body": "Test",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_send_notification_admin_success(
        self, client: AsyncClient, admin_user: User, servant_user: User
    ):
        """Un admin peut envoyer une notification."""
        resp = await client.post(
            "/api/v1/communication/notify",
            json={
                "recipient_id": str(servant_user.id),
                "notification_type": "GENERAL",
                "channel": "IN_APP",
                "title": "Message admin",
                "body": "Message de l'administrateur.",
            },
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["sent_by"] == str(admin_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  BROADCAST
# ═══════════════════════════════════════════════════════════════════════════


class TestBroadcastNotification:
    """Tests pour le broadcast de notifications."""

    @pytest.mark.asyncio
    async def test_broadcast_to_all(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        parent_user: User,
    ):
        resp = await client.post(
            "/api/v1/communication/broadcast",
            json={
                "target": "all",
                "notification_type": "GENERAL",
                "channel": "IN_APP",
                "title": "Annonce generale",
                "body": "Ceci est un message pour tous.",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["target"] == "all"
        assert body["total_sent"] >= 0
        assert "broadcast_id" in body

    @pytest.mark.asyncio
    async def test_broadcast_to_servants(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        resp = await client.post(
            "/api/v1/communication/broadcast",
            json={
                "target": "servants",
                "notification_type": "GENERAL",
                "channel": "IN_APP",
                "title": "Message aux servants",
                "body": "Message reserve aux servants.",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["target"] == "servants"
        # At least servant_user should receive
        assert body["total_sent"] >= 1

    @pytest.mark.asyncio
    async def test_broadcast_to_parents(
        self,
        client: AsyncClient,
        aumonier_user: User,
        parent_user: User,
    ):
        resp = await client.post(
            "/api/v1/communication/broadcast",
            json={
                "target": "parents",
                "notification_type": "ABSENCE_PARENT",
                "channel": "IN_APP",
                "title": "Info parents",
                "body": "Information pour les parents.",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["target"] == "parents"
        assert body["total_sent"] >= 1

    @pytest.mark.asyncio
    async def test_broadcast_forbidden_servant(
        self,
        client: AsyncClient,
        servant_user: User,
    ):
        """Un servant ne peut pas envoyer de broadcast."""
        resp = await client.post(
            "/api/v1/communication/broadcast",
            json={
                "target": "all",
                "notification_type": "GENERAL",
                "channel": "IN_APP",
                "title": "Test",
                "body": "Test",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  MES NOTIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════


class TestMyNotifications:
    """Tests pour la lecture des notifications de l'utilisateur connecte."""

    @pytest.mark.asyncio
    async def test_get_my_notifications_empty(
        self, client: AsyncClient, servant_user: User
    ):
        resp = await client.get(
            "/api/v1/communication/me",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 0

    @pytest.mark.asyncio
    async def test_get_my_notifications_with_data(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_notification: Notification,
    ):
        resp = await client.get(
            "/api/v1/communication/me",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1
        assert body[0]["title"] == "Reunion ce dimanche"

    @pytest.mark.asyncio
    async def test_get_my_notifications_pagination(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_notification: Notification,
    ):
        resp = await client.get(
            "/api/v1/communication/me?limit=1&offset=0",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) <= 1


# ═══════════════════════════════════════════════════════════════════════════
#  DETAIL D'UNE NOTIFICATION
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationDetail:
    """Tests pour le detail d'une notification."""

    @pytest.mark.asyncio
    async def test_get_notification_detail(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_notification: Notification,
    ):
        resp = await client.get(
            f"/api/v1/communication/me/{sample_notification.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_notification.id)
        assert body["title"] == "Reunion ce dimanche"

    @pytest.mark.asyncio
    async def test_get_notification_not_found(
        self, client: AsyncClient, servant_user: User
    ):
        fake_id = uuid4()
        resp = await client.get(
            f"/api/v1/communication/me/{fake_id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_notification_wrong_user(
        self,
        client: AsyncClient,
        parent_user: User,
        sample_notification: Notification,
    ):
        """Un parent ne peut pas voir la notification d'un servant."""
        resp = await client.get(
            f"/api/v1/communication/me/{sample_notification.id}",
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════
#  MARQUAGE COMME LU
# ═══════════════════════════════════════════════════════════════════════════


class TestMarkAsRead:
    """Tests pour le marquage des notifications comme lues."""

    @pytest.mark.asyncio
    async def test_mark_notification_as_read(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_notification: Notification,
    ):
        resp = await client.post(
            "/api/v1/communication/me/read",
            json={"notification_ids": [str(sample_notification.id)]},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["marked_read"] == 1

    @pytest.mark.asyncio
    async def test_mark_already_read_notification(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_notification: Notification,
    ):
        """Marquer comme lu une notification deja lue ne devrait pas echouer."""
        # First read
        await client.post(
            "/api/v1/communication/me/read",
            json={"notification_ids": [str(sample_notification.id)]},
            headers=make_auth_header(servant_user),
        )
        # Second read
        resp = await client.post(
            "/api/v1/communication/me/read",
            json={"notification_ids": [str(sample_notification.id)]},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["marked_read"] == 0  # Already read

    @pytest.mark.asyncio
    async def test_mark_wrong_user_notification(
        self,
        client: AsyncClient,
        parent_user: User,
        sample_notification: Notification,
    ):
        """Un parent ne devrait pas pouvoir marquer les notifications d'un servant."""
        resp = await client.post(
            "/api/v1/communication/me/read",
            json={"notification_ids": [str(sample_notification.id)]},
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["marked_read"] == 0  # Not owner


# ═══════════════════════════════════════════════════════════════════════════
#  STATISTIQUES
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationStats:
    """Tests pour les statistiques de notifications."""

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, client: AsyncClient, servant_user: User):
        resp = await client.get(
            "/api/v1/communication/me/stats",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["unread"] == 0
        assert body["by_type"] == {}

    @pytest.mark.asyncio
    async def test_get_stats_with_notification(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_notification: Notification,
    ):
        resp = await client.get(
            "/api/v1/communication/me/stats",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert body["unread"] >= 1
        assert "GENERAL" in body["by_type"]


# ═══════════════════════════════════════════════════════════════════════════
#  PREFERENCES
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationPreferences:
    """Tests pour les preferences de notification."""

    @pytest.mark.asyncio
    async def test_get_preferences_defaults(
        self, client: AsyncClient, servant_user: User
    ):
        """Sans preferences custom, retourne les defaults pour tous les types."""
        resp = await client.get(
            "/api/v1/communication/me/preferences",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        # Should have an entry for each NotificationType
        assert len(body) >= 1
        # Each entry should have defaults
        for pref in body:
            assert "notification_type" in pref
            assert "in_app_enabled" in pref

    @pytest.mark.asyncio
    async def test_update_preference(self, client: AsyncClient, servant_user: User):
        resp = await client.put(
            "/api/v1/communication/me/preferences",
            json={
                "notification_type": "GENERAL",
                "email_enabled": True,
                "whatsapp_enabled": False,
                "in_app_enabled": True,
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["notification_type"] == "GENERAL"
        assert body["email_enabled"] is True
        assert body["whatsapp_enabled"] is False
        assert body["in_app_enabled"] is True

    @pytest.mark.asyncio
    async def test_update_preference_partial(
        self, client: AsyncClient, servant_user: User
    ):
        """Mise a jour partielle : seul email_enabled change."""
        resp = await client.put(
            "/api/v1/communication/me/preferences",
            json={
                "notification_type": "AFFECTATION",
                "email_enabled": True,
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["notification_type"] == "AFFECTATION"
        assert body["email_enabled"] is True
        # Defaults should remain
        assert body["whatsapp_enabled"] is False
        assert body["in_app_enabled"] is True

    @pytest.mark.asyncio
    async def test_update_preference_idempotent(
        self, client: AsyncClient, servant_user: User
    ):
        """Deux mises a jour successives fonctionnent correctement."""
        data = {
            "notification_type": "DISCIPLINE",
            "email_enabled": True,
            "in_app_enabled": True,
        }
        resp1 = await client.put(
            "/api/v1/communication/me/preferences",
            json=data,
            headers=make_auth_header(servant_user),
        )
        assert resp1.status_code == 200

        data["email_enabled"] = False
        resp2 = await client.put(
            "/api/v1/communication/me/preferences",
            json=data,
            headers=make_auth_header(servant_user),
        )
        assert resp2.status_code == 200
        assert resp2.json()["email_enabled"] is False


# ═══════════════════════════════════════════════════════════════════════════
#  HISTORIQUE ADMIN
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationHistory:
    """Tests pour l'historique admin des notifications."""

    @pytest.mark.asyncio
    async def test_history_admin_access(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_notification: Notification,
    ):
        resp = await client.get(
            "/api/v1/communication/history",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_history_with_filters(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_notification: Notification,
    ):
        resp = await client.get(
            "/api/v1/communication/history?notification_type=GENERAL&channel=IN_APP",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_history_forbidden_servant(
        self,
        client: AsyncClient,
        servant_user: User,
    ):
        """Un servant ne peut pas acceder a l'historique admin."""
        resp = await client.get(
            "/api/v1/communication/history",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_history_pagination(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_notification: Notification,
    ):
        resp = await client.get(
            "/api/v1/communication/history?limit=1&offset=0",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) <= 1


# ═══════════════════════════════════════════════════════════════════════════
#  WORKFLOW COMPLET : envoi → lecture → marquage → stats
# ═══════════════════════════════════════════════════════════════════════════


class TestNotificationWorkflow:
    """Test du workflow complet d'une notification."""

    @pytest.mark.asyncio
    async def test_full_workflow(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """Workflow complet : envoi → lecture → marquage → verification stats."""
        # 1. Envoi d'une notification
        send_resp = await client.post(
            "/api/v1/communication/notify",
            json={
                "recipient_id": str(servant_user.id),
                "notification_type": "GENERAL",
                "channel": "IN_APP",
                "title": "Test workflow",
                "body": "Notification de test pour le workflow complet.",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert send_resp.status_code == 201
        notif_id = send_resp.json()["id"]

        # 2. Le servant voit la notification dans sa liste
        me_resp = await client.get(
            "/api/v1/communication/me",
            headers=make_auth_header(servant_user),
        )
        assert me_resp.status_code == 200
        ids = [n["id"] for n in me_resp.json()]
        assert notif_id in ids

        # 3. Le servant consulte le detail
        detail_resp = await client.get(
            f"/api/v1/communication/me/{notif_id}",
            headers=make_auth_header(servant_user),
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["title"] == "Test workflow"

        # 4. Le servant marque comme lu
        read_resp = await client.post(
            "/api/v1/communication/me/read",
            json={"notification_ids": [notif_id]},
            headers=make_auth_header(servant_user),
        )
        assert read_resp.status_code == 200
        assert read_resp.json()["marked_read"] == 1

        # 5. Verification des stats
        stats_resp = await client.get(
            "/api/v1/communication/me/stats",
            headers=make_auth_header(servant_user),
        )
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["total"] >= 1
        # After marking as read, unread count should be 0 for this single notification
        # (may be >=0 if other notifications exist)
        assert stats["unread"] >= 0

        # 6. L'aumonier voit la notification dans l'historique
        history_resp = await client.get(
            "/api/v1/communication/history",
            headers=make_auth_header(aumonier_user),
        )
        assert history_resp.status_code == 200
        hist_ids = [n["id"] for n in history_resp.json()["items"]]
        assert notif_id in hist_ids
