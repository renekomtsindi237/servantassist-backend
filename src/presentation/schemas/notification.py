"""
Schemas Pydantic pour le module Communication / Notifications.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.notification import (
    NotificationChannel,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)

# ═══════════════════════════════════════════════════════════════════════════
#  Envoi de notification individuelle
# ═══════════════════════════════════════════════════════════════════════════


class NotificationSend(BaseModel):
    """Schema pour envoyer une notification a un seul destinataire."""

    recipient_id: UUID
    notification_type: NotificationType = NotificationType.GENERAL
    channel: NotificationChannel = NotificationChannel.IN_APP
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = Field(max_length=300)
    body: str = Field(max_length=5000)
    related_entity_type: Optional[str] = Field(default=None, max_length=50)
    related_entity_id: Optional[UUID] = None


# ═══════════════════════════════════════════════════════════════════════════
#  Broadcast (envoi a un groupe)
# ═══════════════════════════════════════════════════════════════════════════


class NotificationBroadcast(BaseModel):
    """
    Schema pour envoyer une notification a plusieurs destinataires.

    ``target`` controle le groupe de destinataires :
    - ``all``          : tous les utilisateurs actifs
    - ``servants``     : tous les servants
    - ``parents``      : tous les parents
    - ``responsables`` : tous les servants avec une nomination active
    - ``subgroup:<id>`` : membres d'un sous-groupe
    """

    target: str = Field(max_length=200)
    notification_type: NotificationType = NotificationType.GENERAL
    channel: NotificationChannel = NotificationChannel.IN_APP
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = Field(max_length=300)
    body: str = Field(max_length=5000)
    related_entity_type: Optional[str] = Field(default=None, max_length=50)
    related_entity_id: Optional[UUID] = None


# ═══════════════════════════════════════════════════════════════════════════
#  Reponse
# ═══════════════════════════════════════════════════════════════════════════


class NotificationResponse(BaseModel):
    """Representation d'une notification dans les reponses API."""

    id: UUID
    recipient_id: UUID
    notification_type: NotificationType
    channel: NotificationChannel
    priority: NotificationPriority
    title: str
    body: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[UUID] = None
    status: NotificationStatus
    sent_by: Optional[UUID] = None
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    broadcast_id: Optional[UUID] = None
    created_at: datetime

    # Champs enrichis (remplis par le service)
    sender_name: Optional[str] = None

    class Config:
        from_attributes = True


class BroadcastResponse(BaseModel):
    """Reponse apres un broadcast."""

    broadcast_id: UUID
    total_sent: int
    total_failed: int
    channel: NotificationChannel
    target: str


# ═══════════════════════════════════════════════════════════════════════════
#  Marquage comme lu
# ═══════════════════════════════════════════════════════════════════════════


class NotificationMarkRead(BaseModel):
    """Schema pour marquer des notifications comme lues."""

    notification_ids: list[UUID] = Field(min_length=1, max_length=100)


# ═══════════════════════════════════════════════════════════════════════════
#  Preferences
# ═══════════════════════════════════════════════════════════════════════════


class NotificationPreferenceUpdate(BaseModel):
    """Schema pour mettre a jour les preferences de notification."""

    notification_type: NotificationType
    email_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None


class NotificationPreferenceResponse(BaseModel):
    """Preference de notification d'un utilisateur pour un type donne."""

    notification_type: NotificationType
    email_enabled: bool
    whatsapp_enabled: bool
    in_app_enabled: bool

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
#  Statistiques
# ═══════════════════════════════════════════════════════════════════════════


class NotificationStatsResponse(BaseModel):
    """Statistiques de notifications pour un utilisateur."""

    total: int = 0
    unread: int = 0
    by_type: dict[str, int] = {}
