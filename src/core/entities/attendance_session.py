"""
Entités pour le module de gestion des appels (CENSEUR).

Gère les appels hebdomadaires des servants chaque samedi après la messe de 06h15.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel


class AttendanceStatus(str, Enum):
    """Statut de présence lors d'un appel."""

    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    LATE = "LATE"
    EXCUSED = "EXCUSED"


class SessionType(str, Enum):
    """Type de session d'appel."""

    REUNION_HEBDOMADAIRE = "REUNION_HEBDOMADAIRE"
    LITURGIQUE = "LITURGIQUE"
    AUTRE = "AUTRE"


class AttendanceSession(SQLModel, table=True):
    """
    Session d'appel hebdomadaire.
    """

    __tablename__ = "attendance_sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_date: datetime
    session_time: str = "07h30"  # Après la messe de 06h15
    location: str = "Sacristie"
    session_type: SessionType = Field(
        default=SessionType.REUNION_HEBDOMADAIRE,
        sa_column=Column(String(30), nullable=False, server_default="REUNION_HEBDOMADAIRE"),
    )
    conducted_by: UUID = Field(foreign_key="users.id")
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class AttendanceRecord(SQLModel, table=True):
    """
    Enregistrement de présence d'un servant lors d'une session.
    """

    __tablename__ = "attendance_records"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="attendance_sessions.id")
    servant_id: UUID = Field(foreign_key="users.id")
    status: AttendanceStatus = Field(sa_column=Column(String(50), nullable=False))
    arrival_time: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ServantAttendanceStats(BaseModel):
    """
    Statistiques de présence d'un servant.

    Attributes:
        servant_id: ID du servant
        servant_name: Nom complet
        total_sessions: Nombre total de sessions
        present_count: Nombre de présences
        absent_count: Nombre d'absences
        late_count: Nombre de retards
        excused_count: Nombre d'absences excusées
        attendance_rate: Taux de présence (%)
        consecutive_absences: Absences consécutives
    """

    servant_id: UUID
    servant_name: str
    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    excused_count: int
    attendance_rate: float  # Pourcentage
    consecutive_absences: int

    class Config:
        from_attributes = True


class AttendanceReport(BaseModel):
    """
    Rapport de présence pour une période.

    Attributes:
        start_date: Date de début
        end_date: Date de fin
        total_sessions: Nombre de sessions
        total_servants: Nombre de servants
        average_attendance_rate: Taux moyen de présence
        servants_stats: Statistiques par servant
        generated_by: ID du CENSEUR
        generated_at: Date de génération
        watermark_logo: Logo en filigrane
    """

    start_date: datetime
    end_date: datetime
    total_sessions: int
    total_servants: int
    average_attendance_rate: float
    servants_stats: list[ServantAttendanceStats]
    generated_by: UUID
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    watermark_logo: str = "logo_servant.jpeg"

    class Config:
        from_attributes = True
