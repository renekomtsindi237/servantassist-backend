"""
Repository pour le module Communication / Notifications.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, func, select

from src.core.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationStatus,
    NotificationType,
)
from src.core.entities.user import User
from src.core.utils import utc_now


class NotificationRepository:
    """CRUD pour les notifications."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Create ────────────────────────────────────────────────────────────

    async def create(self, notification: Notification) -> Notification:
        self.session.add(notification)
        await self.session.commit()
        await self.session.refresh(notification)
        return notification

    async def create_many(self, notifications: list[Notification]) -> list[Notification]:
        """Insere un lot de notifications (broadcast)."""
        for n in notifications:
            self.session.add(n)
        await self.session.commit()
        for n in notifications:
            await self.session.refresh(n)
        return notifications

    # ── Read ──────────────────────────────────────────────────────────────

    async def get_by_id(self, notification_id: UUID) -> Optional[Notification]:
        stmt = select(Notification).where(Notification.id == notification_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def get_by_user(
        self,
        user_id: UUID,
        *,
        notification_type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        channel: Optional[NotificationChannel] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Notifications d'un utilisateur avec filtres optionnels."""
        stmt = select(Notification).where(Notification.recipient_id == user_id)

        if notification_type:
            stmt = stmt.where(Notification.notification_type == notification_type)
        if status:
            stmt = stmt.where(Notification.status == status)
        if channel:
            stmt = stmt.where(Notification.channel == channel)

        stmt = stmt.order_by(col(Notification.created_at).desc()).offset(offset).limit(limit)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def count_by_user(
        self,
        user_id: UUID,
        *,
        status: Optional[NotificationStatus] = None,
    ) -> int:
        stmt = select(func.count()).select_from(Notification).where(Notification.recipient_id == user_id)
        if status:
            stmt = stmt.where(Notification.status == status)
        result = await self.session.exec(stmt)
        return result.one()

    async def count_unread_by_user(self, user_id: UUID) -> int:
        """Nombre de notifications non lues (IN_APP, statut SENT ou DELIVERED)."""
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.channel == NotificationChannel.IN_APP,
                Notification.status.in_(
                    [
                        NotificationStatus.SENT,
                        NotificationStatus.DELIVERED,
                    ]
                ),
            )
        )
        result = await self.session.exec(stmt)
        return result.one()

    async def get_all(
        self,
        *,
        notification_type: Optional[NotificationType] = None,
        channel: Optional[NotificationChannel] = None,
        status: Optional[NotificationStatus] = None,
        broadcast_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Listing admin de toutes les notifications."""
        stmt = select(Notification)

        if notification_type:
            stmt = stmt.where(Notification.notification_type == notification_type)
        if channel:
            stmt = stmt.where(Notification.channel == channel)
        if status:
            stmt = stmt.where(Notification.status == status)
        if broadcast_id:
            stmt = stmt.where(Notification.broadcast_id == broadcast_id)

        stmt = stmt.order_by(col(Notification.created_at).desc()).offset(offset).limit(limit)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def count_all(
        self,
        *,
        notification_type: Optional[NotificationType] = None,
        channel: Optional[NotificationChannel] = None,
        status: Optional[NotificationStatus] = None,
    ) -> int:
        stmt = select(func.count()).select_from(Notification)
        if notification_type:
            stmt = stmt.where(Notification.notification_type == notification_type)
        if channel:
            stmt = stmt.where(Notification.channel == channel)
        if status:
            stmt = stmt.where(Notification.status == status)
        result = await self.session.exec(stmt)
        return result.one()

    # ── Update ────────────────────────────────────────────────────────────

    async def mark_sent(
        self,
        notification_id: UUID,
        *,
        error_message: Optional[str] = None,
    ) -> Optional[Notification]:
        notification = await self.get_by_id(notification_id)
        if not notification:
            return None
        if error_message:
            notification.status = NotificationStatus.FAILED
            notification.error_message = error_message
        else:
            notification.status = NotificationStatus.SENT
            notification.sent_at = utc_now()
        notification.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(notification)
        return notification

    async def mark_read(self, notification_ids: list[UUID], user_id: UUID) -> int:
        """Marque des notifications IN_APP comme lues. Retourne le nombre mis a jour."""
        count = 0
        now = utc_now()
        for nid in notification_ids:
            notification = await self.get_by_id(nid)
            if notification and notification.recipient_id == user_id and notification.status != NotificationStatus.READ:
                notification.status = NotificationStatus.READ
                notification.read_at = now
                notification.updated_at = now
                count += 1
        await self.session.commit()
        return count

    # ── Stats ─────────────────────────────────────────────────────────────

    async def get_stats_by_user(self, user_id: UUID) -> dict:
        """Statistiques de notifications pour un utilisateur."""
        total = await self.count_by_user(user_id)
        unread = await self.count_unread_by_user(user_id)

        # Compte par type
        by_type: dict[str, int] = {}
        for nt in NotificationType:
            stmt = (
                select(func.count())
                .select_from(Notification)
                .where(
                    Notification.recipient_id == user_id,
                    Notification.notification_type == nt,
                )
            )
            result = await self.session.exec(stmt)
            c = result.one()
            if c > 0:
                by_type[nt.value] = c

        return {"total": total, "unread": unread, "by_type": by_type}

    # ── Enrichment ────────────────────────────────────────────────────────

    async def enrich(self, notification: Notification) -> dict:
        """Enrichit une notification avec le nom de l'envoyeur."""
        data = notification.model_dump()
        if notification.sent_by:
            stmt = select(User.first_name, User.last_name).where(User.id == notification.sent_by)
            result = await self.session.exec(stmt)
            row = result.first()
            if row:
                data["sender_name"] = f"{row.first_name} {row.last_name}"
        return data


# ═══════════════════════════════════════════════════════════════════════════
#  Preferences
# ═══════════════════════════════════════════════════════════════════════════


class NotificationPreferenceRepository:
    """CRUD pour les preferences de notification."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_user(self, user_id: UUID) -> list[NotificationPreference]:
        stmt = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        result = await self.session.exec(stmt)
        return list(result.all())

    async def get_by_user_and_type(
        self,
        user_id: UUID,
        notification_type: NotificationType,
    ) -> Optional[NotificationPreference]:
        stmt = select(NotificationPreference).where(
            NotificationPreference.user_id == user_id,
            NotificationPreference.notification_type == notification_type,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def upsert(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        *,
        email_enabled: Optional[bool] = None,
        whatsapp_enabled: Optional[bool] = None,
        in_app_enabled: Optional[bool] = None,
    ) -> NotificationPreference:
        """Cree ou met a jour une preference."""
        pref = await self.get_by_user_and_type(user_id, notification_type)
        if pref is None:
            pref = NotificationPreference(
                user_id=user_id,
                notification_type=notification_type,
                email_enabled=email_enabled if email_enabled is not None else False,
                whatsapp_enabled=whatsapp_enabled if whatsapp_enabled is not None else False,
                in_app_enabled=in_app_enabled if in_app_enabled is not None else True,
            )
            self.session.add(pref)
        else:
            if email_enabled is not None:
                pref.email_enabled = email_enabled
            if whatsapp_enabled is not None:
                pref.whatsapp_enabled = whatsapp_enabled
            if in_app_enabled is not None:
                pref.in_app_enabled = in_app_enabled
            pref.updated_at = utc_now()

        await self.session.commit()
        await self.session.refresh(pref)
        return pref
