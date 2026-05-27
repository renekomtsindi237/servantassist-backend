"""
Entites du module Evenements.

Types d'evenements liturgiques et paroissiaux geres par ServantAssist.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


class EventType(str, Enum):
    """Types d'evenements geres par ServantAssist."""

    # ── Messes ────────────────────────────────────────────────────────
    MESSE_DOMINICALE = "MESSE_DOMINICALE"
    MESSE_SEMAINE = "MESSE_SEMAINE"
    MESSE_PONTIFICALE = "MESSE_PONTIFICALE"
    MESSE_SOLENNELLE_PONTIFICALE = "MESSE_SOLENNELLE_PONTIFICALE"
    MESSE_ACTION_GRACE = "MESSE_ACTION_GRACE"
    MARIAGE = "MARIAGE"
    REQUIEM = "REQUIEM"
    # ── Activites spirituelles ────────────────────────────────────────
    RECOLLECTION = "RECOLLECTION"
    CAMP_SPIRITUEL = "CAMP_SPIRITUEL"
    # ── Activites communautaires ──────────────────────────────────────
    JOURNEE_AMITIE = "JOURNEE_AMITIE"
    JOURNEE_SPORTIVE = "JOURNEE_SPORTIVE"
    CAMP = "CAMP"
    # ── Divers ────────────────────────────────────────────────────────
    REPETITION = "REPETITION"
    AUTRE = "AUTRE"


class EventStatus(str, Enum):
    """Statut d'un evenement dans son cycle de vie."""

    BROUILLON = "BROUILLON"  # Cree mais pas publie
    PUBLIE = "PUBLIE"  # Visible par tous
    EN_COURS = "EN_COURS"  # L'evenement est en cours
    TERMINE = "TERMINE"  # Passe
    ANNULE = "ANNULE"  # Annule


class EventBase(SQLModel):
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    start_time: datetime
    end_time: datetime
    location: str = Field(max_length=300)
    event_type: EventType = Field(default=EventType.MESSE_DOMINICALE)
    status: EventStatus = Field(default=EventStatus.BROUILLON)


class Event(EventBase, table=True):
    __tablename__ = "events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_by: UUID = Field(foreign_key="users.id")  # Aumonier ou Admin
    updated_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ══════════════════════════════════════════════════════════════════════════
#  Table de liaison : participants a un evenement
# ══════════════════════════════════════════════════════════════════════════


class ParticipantRole(str, Enum):
    """Role liturgique d'un participant dans un evenement."""

    CRUCIFER = "CRUCIFER"  # Porte-croix
    THURIFER = "THURIFER"  # Porte-encens
    ACOLYTE = "ACOLYTE"  # Acolyte (porte-cierge)
    CEROMONIAIRE = "CEROMONIAIRE"  # Ceremoniaire
    NAVETTIER = "NAVETTIER"  # Porte-navette
    PORTE_MITRE = "PORTE_MITRE"  # Porte-mitre
    PORTE_CROSSE = "PORTE_CROSSE"  # Porte-crosse
    PORTE_BOUGEOIR = "PORTE_BOUGEOIR"
    LECTEUR = "LECTEUR"  # Lecteur
    SERVANT = "SERVANT"  # Servant general
    PARTICIPANT = "PARTICIPANT"  # Simple participant (parent, invite)
    AUTRE = "AUTRE"


class ParticipantStatus(str, Enum):
    """Statut de participation a un evenement."""

    INVITE = "INVITE"  # Invite, en attente de reponse
    CONFIRME = "CONFIRME"  # A confirme sa presence
    DECLINE = "DECLINE"  # A decline
    PRESENT = "PRESENT"  # Presence constatee le jour J
    ABSENT = "ABSENT"  # Absent le jour J


class EventParticipant(SQLModel, table=True):
    """Table de liaison entre un evenement et ses participants."""

    __tablename__ = "event_participants"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="events.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    participant_role: ParticipantRole = Field(default=ParticipantRole.SERVANT)
    status: ParticipantStatus = Field(default=ParticipantStatus.INVITE)
    notes: Optional[str] = Field(default=None, max_length=500)
    # Qui a ajoute ce participant
    added_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
