"""
Entites du module Presence — suivi d'assiduite des membres.

Le reglement interieur prevoit un suivi strict de l'assiduite :
- Presence aux reunions ordinaires (obligatoire)
- Presence aux messes de classement (obligatoire)
- Presence aux recollections (obligatoire)
- Presence aux activites du groupe

Le censeur adjoint veille a l'assiduite des servants.
Le charge du classement peut utiliser ces donnees pour le planning.
Les absences non justifiees repetees entrainent des sanctions disciplinaires.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


# ═══════════════════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════════════════

class AttendanceType(str, Enum):
    """Type de presence attendue."""
    REUNION_ORDINAIRE = "REUNION_ORDINAIRE"      # Reunion hebdomadaire
    MESSE_CLASSEMENT = "MESSE_CLASSEMENT"        # Messe ou le servant est classe
    MESSE_VOLONTAIRE = "MESSE_VOLONTAIRE"        # Messe sans classement
    RECOLLECTION = "RECOLLECTION"                # Recollection mensuelle
    CAMP = "CAMP"                                # Camp spirituel
    FORMATION = "FORMATION"                      # Formation / enseignement
    REPETITION = "REPETITION"                    # Repetition de ceremonie
    ACTIVITE = "ACTIVITE"                        # Activite sportive/culturelle
    CONSEIL = "CONSEIL"                          # Conseil des responsables
    AUTRE = "AUTRE"


class AttendanceStatus(str, Enum):
    """Statut de presence d'un servant."""
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    ABSENT_JUSTIFIE = "ABSENT_JUSTIFIE"
    EN_RETARD = "EN_RETARD"
    EXCUSE = "EXCUSE"                            # Excuse acceptee a l'avance


# ═══════════════════════════════════════════════════════════════════════════
#  Table : Presences
# ═══════════════════════════════════════════════════════════════════════════

class Attendance(SQLModel, table=True):
    """
    Enregistrement de presence/absence d'un servant.

    Peut etre lie a un evenement (via event_id) ou independant
    (ex: reunion ordinaire sans evenement formel).

    La justification d'absence doit etre fournie dans les 48h suivant
    l'absence, conformement au reglement interieur.
    """
    __tablename__ = "attendances"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    # Evenement associe (optionnel)
    event_id: Optional[UUID] = Field(default=None, foreign_key="events.id", index=True)
    # Type et date
    attendance_type: AttendanceType = Field(index=True)
    attendance_date: datetime = Field(index=True)
    title: Optional[str] = Field(default=None, max_length=200)
    # Statut
    status: AttendanceStatus = Field(default=AttendanceStatus.PRESENT, index=True)
    # Justification
    justification: Optional[str] = Field(default=None, max_length=1000)
    justified_at: Optional[datetime] = Field(default=None)
    # Qui a enregistre
    recorded_by: UUID = Field(foreign_key="users.id")
    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

