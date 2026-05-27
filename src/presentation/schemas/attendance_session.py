"""
Schémas Pydantic pour le module de gestion des appels (CENSEUR).
"""
import html
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.core.entities.attendance_session import AttendanceStatus, SessionType

# ══════════════════════════════════════════════════════════════════
#  CRÉATION
# ══════════════════════════════════════════════════════════════════


class AttendanceSessionCreate(BaseModel):
    """Schéma pour créer une session d'appel."""

    session_date: datetime = Field(description="Date de la session (samedi)")
    session_time: str = Field(default="07h30", description="Heure de la session")
    location: str = Field(default="Sacristie", description="Lieu de l'appel")
    session_type: SessionType = Field(default=SessionType.REUNION_HEBDOMADAIRE)
    notes: Optional[str] = None

    @field_validator("notes", mode="before")
    @classmethod
    def sanitize_notes(cls, v):
        """Échappe les caractères HTML/JS dans les notes pour prévenir les XSS."""
        if v is None:
            return v
        if isinstance(v, str):
            return html.escape(v)
        return v


class AttendanceRecordCreate(BaseModel):
    """Schéma pour marquer la présence d'un servant."""

    servant_id: UUID
    status: AttendanceStatus
    arrival_time: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("notes", mode="before")
    @classmethod
    def sanitize_notes(cls, v):
        """Échappe les caractères HTML/JS dans les notes pour prévenir les XSS."""
        if v is None:
            return v
        if isinstance(v, str):
            return html.escape(v)
        return v


class AttendanceRecordUpdate(BaseModel):
    """Schéma pour modifier un enregistrement de présence."""

    status: Optional[AttendanceStatus] = None
    arrival_time: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("notes", mode="before")
    @classmethod
    def sanitize_notes(cls, v):
        """Échappe les caractères HTML/JS dans les notes pour prévenir les XSS."""
        if v is None:
            return v
        if isinstance(v, str):
            return html.escape(v)
        return v


# ══════════════════════════════════════════════════════════════════
#  RÉPONSES
# ══════════════════════════════════════════════════════════════════


class AttendanceRecordResponse(BaseModel):
    """Schéma de réponse pour un enregistrement de présence."""

    id: UUID
    session_id: UUID
    servant_id: UUID
    servant_name: str  # Enrichi
    status: AttendanceStatus
    arrival_time: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: UUID
    recorded_by_name: str  # Enrichi
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AttendanceSessionResponse(BaseModel):
    """Schéma de réponse pour une session d'appel."""

    id: UUID
    session_date: datetime
    session_time: str
    location: str
    session_type: SessionType = SessionType.REUNION_HEBDOMADAIRE
    conducted_by: UUID
    conducted_by_name: str  # Enrichi
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    records: List[AttendanceRecordResponse] = []  # Enrichi
    total_servants: int = 0  # Enrichi
    present_count: int = 0  # Enrichi
    absent_count: int = 0  # Enrichi
    late_count: int = 0  # Enrichi
    excused_count: int = 0  # Enrichi

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════
#  STATISTIQUES
# ══════════════════════════════════════════════════════════════════


class ServantAttendanceStatsResponse(BaseModel):
    """Schéma de réponse pour les statistiques de présence d'un servant."""

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


class AttendanceReportRequest(BaseModel):
    """Paramètres pour générer un rapport de présence."""

    start_date: datetime
    end_date: datetime
    # Filtrer par servants spécifiques
    servant_ids: Optional[list[UUID]] = None


class AttendanceReportResponse(BaseModel):
    """Schéma de réponse pour un rapport de présence."""

    start_date: datetime
    end_date: datetime
    total_sessions: int
    total_servants: int
    average_attendance_rate: float
    servants_stats: List[ServantAttendanceStatsResponse]
    generated_by: UUID
    generated_by_name: str  # Enrichi
    generated_at: datetime
    watermark_logo: str = "logo_servant.jpeg"

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════
#  LISTE DES SERVANTS
# ══════════════════════════════════════════════════════════════════


class ServantListItem(BaseModel):
    """Item de la liste des servants pour l'appel."""

    id: UUID
    first_name: str
    last_name: str
    full_name: str
    phone_number: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True
