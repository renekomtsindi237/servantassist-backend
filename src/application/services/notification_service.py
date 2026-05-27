"""
Service metier du module Communication / Notifications.

Responsabilites :
- Envoi de notifications individuelles (email, WhatsApp, in-app)
- Broadcast a un groupe de destinataires
- Gestion des preferences de canal
- Marquage comme lu
- Statistiques
"""

from datetime import datetime, timezone
import logging
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col, select

from src.core.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from src.core.entities.user import User, UserRole
from src.infrastructure.repositories.notification_repository import (
    NotificationPreferenceRepository,
    NotificationRepository,
)
from src.infrastructure.services.email_service import EmailService
from src.infrastructure.services.whatsapp_service import WhatsAppService

logger = logging.getLogger(__name__)


class NotificationService:
    """Service de gestion des notifications."""

    def __init__(self, session: AsyncSession, ws_manager=None):
        self.session = session
        self.repo = NotificationRepository(session)
        self.pref_repo = NotificationPreferenceRepository(session)
        self.email_service = EmailService()
        self.whatsapp_service = WhatsAppService()
        # Gestionnaire WebSocket optionnel (injecté depuis la requête FastAPI)
        self._ws_manager = ws_manager

    # ══════════════════════════════════════════════════════════════════════
    #  Envoi individuel
    # ══════════════════════════════════════════════════════════════════════

    async def send_notification(
        self,
        *,
        recipient_id: UUID,
        notification_type: NotificationType,
        channel: NotificationChannel,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        title: str,
        body: str,
        sent_by: Optional[UUID] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[UUID] = None,
        broadcast_id: Optional[UUID] = None,
    ) -> Notification:
        """
        Cree et envoie une notification via le canal specifie.

        Pour EMAIL et WHATSAPP, effectue l'envoi reel.
        Pour IN_APP, marque directement comme SENT.
        """
        notification = Notification(
            recipient_id=recipient_id,
            notification_type=notification_type,
            channel=channel,
            priority=priority,
            title=title,
            body=body,
            sent_by=sent_by,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            broadcast_id=broadcast_id,
        )
        notification = await self.repo.create(notification)

        # Push WebSocket temps réel si le gestionnaire est disponible
        if self._ws_manager is not None and channel == NotificationChannel.IN_APP:
            try:
                await self._ws_manager.send_to_user(
                    str(recipient_id),
                    {
                        "id": str(notification.id),
                        "type": notification_type.value,
                        "title": title,
                        "body": body,
                        "created_at": notification.created_at.isoformat() if notification.created_at else None,
                    },
                )
            except Exception as exc:
                logger.debug("WebSocket push failed (non-fatal): %s", exc)

        # Envoi effectif selon le canal
        error = None
        if channel == NotificationChannel.IN_APP:
            # Les notifications in-app sont directement marquees comme envoyees
            error = None
        elif channel == NotificationChannel.EMAIL:
            error = await self._send_email(notification)
        elif channel == NotificationChannel.WHATSAPP:
            error = await self._send_whatsapp(notification)

        # Mise a jour du statut
        await self.repo.mark_sent(notification.id, error_message=error)
        # Rafraichir pour renvoyer le bon statut
        notification = await self.repo.get_by_id(notification.id)
        return notification

    async def _send_email(self, notification: Notification) -> Optional[str]:
        """Envoie la notification par email. Retourne le message d'erreur si echec."""
        # Recuperer le destinataire
        stmt = select(User).where(User.id == notification.recipient_id)
        result = await self.session.exec(stmt)
        user = result.first()
        if not user:
            return "Destinataire introuvable"

        try:
            sent = await self._dispatch_email(notification, user)
            return None if sent else "SMTP non configure ou envoi echoue"
        except Exception as exc:
            logger.warning(
                "Notification email send failed | notification_id=%s | recipient_id=%s | error=%s",
                str(notification.id),
                str(notification.recipient_id),
                str(exc),
            )
            return str(exc)[:500]

    async def _dispatch_email(self, notification: Notification, user: User) -> bool:
        """Selectionne le template email selon le type de notification."""
        nt = notification.notification_type

        if nt == NotificationType.AFFECTATION:
            return await self.email_service.send_assignment_notification(
                to_email=user.email,
                user_first_name=user.first_name,
                event_title=notification.title,
                event_date="",  # enrichi par l'appelant si besoin
                liturgical_role=notification.body,
            )

        if nt == NotificationType.RAPPEL_EVENEMENT:
            return await self.email_service.send_event_reminder(
                to_email=user.email,
                user_first_name=user.first_name,
                event_title=notification.title,
                event_date="",
                liturgical_role="",
            )

        if nt == NotificationType.ABSENCE_PARENT:
            return await self.email_service.send_absence_parent_notification(
                to_email=user.email,
                parent_first_name=user.first_name,
                child_first_name="",
                child_last_name="",
                event_title=notification.title,
                event_date="",
            )

        if nt == NotificationType.AVERTISSEMENT_ABSENCE:
            return await self.email_service.send_general_notification(
                to_email=user.email,
                user_first_name=user.first_name,
                title=notification.title,
                body=notification.body,
            )

        if nt == NotificationType.CONVOCATION_PARENT:
            return await self.email_service.send_general_notification(
                to_email=user.email,
                user_first_name=user.first_name,
                title=notification.title,
                body=notification.body,
            )

        # DISCIPLINE, COTISATION, NOMINATION, GENERAL → template general
        return await self.email_service.send_general_notification(
            to_email=user.email,
            user_first_name=user.first_name,
            title=notification.title,
            body=notification.body,
        )

    async def _send_whatsapp(self, notification: Notification) -> Optional[str]:
        """Envoie la notification par WhatsApp. Retourne le message d'erreur si echec."""
        stmt = select(User).where(User.id == notification.recipient_id)
        result = await self.session.exec(stmt)
        user = result.first()
        if not user:
            return "Destinataire introuvable"
        if not user.phone_number:
            return "Pas de numero de telephone"

        try:
            sent = await self.whatsapp_service.send_admin_notification(
                phone_number=user.phone_number,
                admin_name="ServantAssist",
                message_text=f"*{notification.title}*\n\n{notification.body}",
            )
            return None if sent else "WhatsApp non configure ou envoi echoue"
        except Exception as exc:
            logger.warning(
                "Notification WhatsApp send failed | notification_id=%s | recipient_id=%s | error=%s",
                str(notification.id),
                str(notification.recipient_id),
                str(exc),
            )
            return str(exc)[:500]

    # ══════════════════════════════════════════════════════════════════════
    #  Broadcast
    # ══════════════════════════════════════════════════════════════════════

    async def broadcast(
        self,
        *,
        target: str,
        notification_type: NotificationType,
        channel: NotificationChannel,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        title: str,
        body: str,
        sent_by: Optional[UUID] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[UUID] = None,
    ) -> dict:
        """
        Envoie une notification a un groupe de destinataires.

        Targets supportes :
        - "all" : tous les utilisateurs actifs
        - "servants" : tous les servants actifs
        - "parents" : tous les parents actifs
        - "responsables" : servants avec nomination active
        - "subgroup:<uuid>" : membres d'un sous-groupe
        """
        recipients = await self._resolve_recipients(target)

        broadcast_id = uuid4()
        total_sent = 0
        total_failed = 0

        for user in recipients:
            notif = await self.send_notification(
                recipient_id=user.id,
                notification_type=notification_type,
                channel=channel,
                priority=priority,
                title=title,
                body=body,
                sent_by=sent_by,
                related_entity_type=related_entity_type,
                related_entity_id=related_entity_id,
                broadcast_id=broadcast_id,
            )
            if notif.status == NotificationStatus.FAILED:
                total_failed += 1
            else:
                total_sent += 1

        return {
            "broadcast_id": broadcast_id,
            "total_sent": total_sent,
            "total_failed": total_failed,
            "channel": channel,
            "target": target,
        }

    async def _resolve_recipients(self, target: str) -> list[User]:
        """Resout les destinataires selon la cible."""
        target_lower = target.lower().strip()

        if target_lower == "all":
            stmt = select(User).where(User.is_active == True)  # noqa: E712
        elif target_lower == "servants":
            stmt = select(User).where(
                User.is_active == True,  # noqa: E712
                User.role == UserRole.SERVANT,
            )
        elif target_lower == "parents":
            stmt = select(User).where(
                User.is_active == True,  # noqa: E712
                User.role == UserRole.PARENT,
            )
        elif target_lower == "responsables":
            from src.core.entities.responsable import Nomination, NominationStatus

            stmt = (
                select(User)
                .join(Nomination, Nomination.user_id == User.id)
                .where(
                    User.is_active == True,  # noqa: E712
                    Nomination.status == NominationStatus.ACTIVE,
                )
            )
        elif target_lower.startswith("subgroup:"):
            from src.core.entities.subgroup import SubGroupMember

            sg_id = target_lower.split(":", 1)[1]
            stmt = (
                select(User)
                .join(SubGroupMember, SubGroupMember.user_id == User.id)
                .where(
                    User.is_active == True,  # noqa: E712
                    SubGroupMember.sub_group_id == sg_id,
                    SubGroupMember.is_active == True,  # noqa: E712
                )
            )
        else:
            return []

        result = await self.session.exec(stmt)
        return list(result.all())

    # ══════════════════════════════════════════════════════════════════════
    #  Lecture / Marquage
    # ══════════════════════════════════════════════════════════════════════

    async def get_user_notifications(
        self,
        user_id: UUID,
        *,
        notification_type: Optional[NotificationType] = None,
        status: Optional[NotificationStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Recupere les notifications d'un utilisateur (enrichies)."""
        notifications = await self.repo.get_by_user(
            user_id,
            notification_type=notification_type,
            status=status,
            channel=NotificationChannel.IN_APP,
            limit=limit,
            offset=offset,
        )
        return [await self.repo.enrich(n) for n in notifications]

    async def get_notification(
        self,
        notification_id: UUID,
        user_id: UUID,
    ) -> Optional[dict]:
        """Recupere une notification specifique (verifie le proprietaire)."""
        notification = await self.repo.get_by_id(notification_id)
        if not notification or notification.recipient_id != user_id:
            return None
        return await self.repo.enrich(notification)

    async def mark_as_read(
        self,
        notification_ids: list[UUID],
        user_id: UUID,
    ) -> int:
        """Marque des notifications comme lues."""
        return await self.repo.mark_read(notification_ids, user_id)

    async def get_user_stats(self, user_id: UUID) -> dict:
        """Statistiques de notifications pour un utilisateur."""
        return await self.repo.get_stats_by_user(user_id)

    # ══════════════════════════════════════════════════════════════════════
    #  Historique admin
    # ══════════════════════════════════════════════════════════════════════

    async def get_all_notifications(
        self,
        *,
        notification_type: Optional[NotificationType] = None,
        channel: Optional[NotificationChannel] = None,
        status: Optional[NotificationStatus] = None,
        broadcast_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Listing admin paginé de toutes les notifications."""
        items = await self.repo.get_all(
            notification_type=notification_type,
            channel=channel,
            status=status,
            broadcast_id=broadcast_id,
            limit=limit,
            offset=offset,
        )
        total = await self.repo.count_all(
            notification_type=notification_type,
            channel=channel,
            status=status,
        )
        enriched = [await self.repo.enrich(n) for n in items]
        return {
            "items": enriched,
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    # ══════════════════════════════════════════════════════════════════════
    #  Preferences
    # ══════════════════════════════════════════════════════════════════════

    async def get_preferences(self, user_id: UUID) -> list[dict]:
        """Recupere les preferences de notification d'un utilisateur."""
        prefs = await self.pref_repo.get_by_user(user_id)
        # Retourner aussi les types sans preference (defaults)
        result = []
        pref_map = {p.notification_type: p for p in prefs}
        for nt in NotificationType:
            if nt in pref_map:
                result.append(pref_map[nt].model_dump())
            else:
                result.append(
                    {
                        "notification_type": nt,
                        "email_enabled": False,
                        "whatsapp_enabled": False,
                        "in_app_enabled": True,
                    }
                )
        return result

    async def update_preference(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        *,
        email_enabled: Optional[bool] = None,
        whatsapp_enabled: Optional[bool] = None,
        in_app_enabled: Optional[bool] = None,
    ) -> dict:
        """Met a jour une preference de notification."""
        pref = await self.pref_repo.upsert(
            user_id,
            notification_type,
            email_enabled=email_enabled,
            whatsapp_enabled=whatsapp_enabled,
            in_app_enabled=in_app_enabled,
        )
        return pref.model_dump()
