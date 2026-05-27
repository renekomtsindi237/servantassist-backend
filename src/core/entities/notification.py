"""
Entites du module Communication — notifications et preferences.

Types de notifications :
- AFFECTATION : servant affecte a un evenement
- RAPPEL_EVENEMENT : rappel 24h avant un evenement
- ABSENCE_PARENT : informer le parent si son enfant est absent
- DISCIPLINE : notification liee a un dossier disciplinaire
- COTISATION : rappel de cotisation en retard
- NOMINATION : notification de nomination a un poste
- GENERAL : message personnalise envoye par l'admin/aumonier

Canaux de diffusion :
- EMAIL : envoi par SMTP
- WHATSAPP : envoi par Twilio WhatsApp
- IN_APP : notification interne (consultable via l'API)

Les preferences de canal sont configurables par utilisateur.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now

# ═══════════════════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════════════════


class NotificationType(str, Enum):
    """Types de notifications envoyees par le systeme."""

    AFFECTATION = "AFFECTATION"  # Servant affecte a un evenement
    RAPPEL_EVENEMENT = "RAPPEL_EVENEMENT"  # Rappel 24h avant un evenement
    ABSENCE_PARENT = "ABSENCE_PARENT"  # Parent informe d'une absence
    DISCIPLINE = "DISCIPLINE"  # Notification disciplinaire
    COTISATION = "COTISATION"  # Rappel cotisation
    NOMINATION = "NOMINATION"  # Nomination / revocation
    GENERAL = "GENERAL"  # Message personnalise admin
    AVERTISSEMENT_ABSENCE = "AVERTISSEMENT_ABSENCE"  # Alerte 3 absences → servant
    CONVOCATION_PARENT = "CONVOCATION_PARENT"  # Convocation 5 absences → parent


class NotificationChannel(str, Enum):
    """Canaux de diffusion disponibles."""

    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    IN_APP = "IN_APP"


class NotificationStatus(str, Enum):
    """Statut de la notification."""

    PENDING = "PENDING"  # En attente d'envoi
    SENT = "SENT"  # Envoyee avec succes
    DELIVERED = "DELIVERED"  # Delivree (confirmation WhatsApp)
    READ = "READ"  # Lue par le destinataire (IN_APP)
    FAILED = "FAILED"  # Echec d'envoi


class NotificationPriority(str, Enum):
    """Priorite de la notification."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


# ═══════════════════════════════════════════════════════════════════════════
#  Table : Notifications
# ═══════════════════════════════════════════════════════════════════════════


class Notification(SQLModel, table=True):
    """
    Notification envoyee a un utilisateur.

    Chaque notification est un message unique envoye via un canal specifique.
    Un broadcast (message a plusieurs destinataires) genere autant de
    Notification que de destinataires.
    """

    __tablename__ = "notifications"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Destinataire
    recipient_id: UUID = Field(foreign_key="users.id", index=True)
    # Type et canal
    notification_type: NotificationType = Field(index=True)
    channel: NotificationChannel = Field(default=NotificationChannel.IN_APP)
    priority: NotificationPriority = Field(default=NotificationPriority.NORMAL)
    # Contenu
    title: str = Field(max_length=300)
    body: str = Field(max_length=5000)
    # Ressource liee (optionnel — pour navigation deep link)
    # "event", "assignment", ...
    related_entity_type: Optional[str] = Field(default=None, max_length=50)
    related_entity_id: Optional[UUID] = Field(default=None)
    # Statut
    status: NotificationStatus = Field(default=NotificationStatus.PENDING, index=True)
    error_message: Optional[str] = Field(default=None, max_length=1000)
    # Envoyeur
    sent_by: Optional[UUID] = Field(default=None, foreign_key="users.id")  # None = systeme
    # Dates
    sent_at: Optional[datetime] = Field(default=None)
    read_at: Optional[datetime] = Field(default=None)
    # Identifiant du broadcast parent (si notification groupee)
    broadcast_id: Optional[UUID] = Field(default=None, index=True)
    # Metadata
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ═══════════════════════════════════════════════════════════════════════════
#  Table : Preferences de notification par utilisateur
# ═══════════════════════════════════════════════════════════════════════════


class NotificationPreference(SQLModel, table=True):
    """
    Preferences de canal de notification pour un utilisateur.

    Par defaut, toutes les notifications sont envoyees IN_APP.
    L'utilisateur peut activer EMAIL et/ou WHATSAPP pour chaque type.
    """

    __tablename__ = "notification_preferences"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    notification_type: NotificationType = Field(index=True)
    # Canaux actives pour ce type
    email_enabled: bool = Field(default=False)
    whatsapp_enabled: bool = Field(default=False)
    in_app_enabled: bool = Field(default=True)
    # Metadata
    updated_at: datetime = Field(default_factory=utc_now)
