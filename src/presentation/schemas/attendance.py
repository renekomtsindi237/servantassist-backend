"""
Schemas Pydantic pour le module Presence.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.attendance import AttendanceStatus, AttendanceType


# ═══════════════════════════════════════════════════════════════════════════
#  Enregistrement de presence
# ═══════════════════════════════════════════════════════════════════════════

class AttendanceCreate(BaseModel):
    """Enregistrer une presence individuelle."""
    user_id: UUID
    attendance_type: AttendanceType
    attendance_date: datetime
    title: Optional[str] = Field(None, max_length=200)
    status: AttendanceStatus = AttendanceStatus.PRESENT
    event_id: Optional[UUID] = None
    justification: Optional[str] = Field(None, max_length=1000)


class AttendanceBatchItem(BaseModel):
    """Element d'un enregistrement par lot (appel nominal)."""
    user_id: UUID
    status: AttendanceStatus = AttendanceStatus.PRESENT
    justification: Optional[str] = Field(None, max_length=1000)


class AttendanceBatchCreate(BaseModel):
    """Enregistrer la presence de plusieurs servants en une fois (appel)."""
    attendance_type: AttendanceType
    attendance_date: datetime
    title: Optional[str] = Field(None, max_length=200)
    event_id: Optional[UUID] = None
    entries: List[AttendanceBatchItem]


class AttendanceUpdate(BaseModel):
    """Modifier un enregistrement de presence."""
    status: Optional[AttendanceStatus] = None
    justification: Optional[str] = Field(None, max_length=1000)


class AttendanceResponse(BaseModel):
    """Reponse pour un enregistrement de presence."""
    id: UUID
    user_id: UUID
    event_id: Optional[UUID] = None
    attendance_type: AttendanceType
    attendance_date: datetime
    title: Optional[str] = None
    status: AttendanceStatus
    justification: Optional[str] = None
    justified_at: Optional[datetime] = None
    recorded_by: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Enrichissement
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None

    class Config:
        from_attributes = True


class AttendanceBatchResponse(BaseModel):
    """Reponse pour un enregistrement par lot."""
    created: List[AttendanceResponse]
    errors: List[str] = []
    total_created: int = 0
    total_errors: int = 0


class AttendanceStatsResponse(BaseModel):
    """Statistiques de presence d'un servant."""
    user_id: UUID
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    total_entries: int = 0
    presents: int = 0
    absents: int = 0
    absents_justifies: int = 0
    retards: int = 0
    excuses: int = 0
    taux_presence: float = 0  # Pourcentage

