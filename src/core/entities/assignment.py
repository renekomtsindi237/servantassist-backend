"""
Entite Affectation — planification liturgique.

Une **affectation** est le lien formel entre :
- Un **evenement** (messe, ceremonie, camp…)
- Un **servant** (utilisateur avec le role SERVANT)
- Un **role liturgique** (crucifer, thurifer, acolyte…)

Cycle de vie :
    PENDING  →  ACCEPTED  →  PRESENT
             →  DECLINED      ABSENT
             →  CANCELLED

Differences avec EventParticipant :
- EventParticipant = participation generale (tout role y compris PARENT)
- Assignment = affectation formelle de service liturgique (SERVANT uniquement)
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


class AssignmentStatus(str, Enum):
    """Statut d'une affectation dans son cycle de vie."""

    PENDING = "PENDING"  # En attente de reponse du servant
    ACCEPTED = "ACCEPTED"  # Servant a accepte
    DECLINED = "DECLINED"  # Servant a refuse
    PRESENT = "PRESENT"  # Presence constatee le jour J
    ABSENT = "ABSENT"  # Absent le jour J
    CANCELLED = "CANCELLED"  # Annulee par l'aumonier/admin


class LiturgicalRole(str, Enum):
    """Roles liturgiques attribuables a un servant."""

    CRUCIFER = "CRUCIFER"  # Porte-croix
    THURIFER = "THURIFER"  # Porte-encens (thuriferaire)
    ACOLYTE = "ACOLYTE"  # Acolyte (porte-cierge)
    CEROMONIAIRE = "CEROMONIAIRE"  # Ceremoniaire
    NAVETTIER = "NAVETTIER"  # Porte-navette
    PORTE_MITRE = "PORTE_MITRE"  # Porte-mitre (messes pontificales)
    PORTE_CROSSE = "PORTE_CROSSE"  # Porte-crosse
    PORTE_BOUGEOIR = "PORTE_BOUGEOIR"  # Porte-bougeoir
    LECTEUR = "LECTEUR"  # Lecteur
    SERVANT_GENERAL = "SERVANT_GENERAL"  # Servant sans role specifique
    AUTRE = "AUTRE"  # Autre


class AssignmentBase(SQLModel):
    """Champs communs a toutes les variantes de l'affectation."""

    event_id: UUID = Field(foreign_key="events.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    liturgical_role: LiturgicalRole = Field(default=LiturgicalRole.SERVANT_GENERAL)
    status: AssignmentStatus = Field(default=AssignmentStatus.PENDING)
    notes: Optional[str] = Field(default=None, max_length=500)


class Assignment(AssignmentBase, table=True):
    """Table des affectations liturgiques."""

    __tablename__ = "assignments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Qui a cree l'affectation
    assigned_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
