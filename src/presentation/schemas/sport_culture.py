"""
Schémas Pydantic pour le module CHARGE_SPORT_CULTURE.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.sport_culture import (
    EventStatus,
    EventType,
    ParticipationStatus,
    ResultType,
    SportType,
)


# ── Schémas de création - Événements ─────────────────────────────
class SportCultureEventCreate(BaseModel):
    """Schéma pour créer un événement."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    event_type: EventType
    sport_type: Optional[SportType] = None
    date: datetime
    start_time: str = Field(pattern=r"^\d{2}h\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}h\d{2}$")
    location: str = Field(min_length=1, max_length=200)
    max_participants: int = Field(ge=0)
    cost: Optional[float] = Field(None, ge=0)
    registration_deadline: Optional[datetime] = None
    notes: Optional[str] = None
    broadcast_notification: bool = True


class SportCultureEventUpdate(BaseModel):
    """Schéma pour modifier un événement."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    event_type: Optional[EventType] = None
    sport_type: Optional[SportType] = None
    date: Optional[datetime] = None
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}h\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}h\d{2}$")
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    max_participants: Optional[int] = Field(None, ge=0)
    cost: Optional[float] = Field(None, ge=0)
    status: Optional[EventStatus] = None
    registration_deadline: Optional[datetime] = None
    notes: Optional[str] = None


class SportCultureEventResponse(BaseModel):
    """Schéma de réponse pour un événement."""

    id: UUID
    title: str
    description: str
    event_type: EventType
    sport_type: Optional[SportType]
    date: datetime
    start_time: str
    end_time: str
    location: str
    max_participants: int
    cost: Optional[float]
    status: EventStatus
    registration_deadline: Optional[datetime]
    notes: Optional[str]
    photos: List[str]
    broadcast_notification: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    # Enrichi
    participants_count: int = 0
    confirmed_count: int = 0

    class Config:
        from_attributes = True


class SportCultureEventListResponse(BaseModel):
    """Schéma de réponse pour une liste d'événements."""

    items: List[SportCultureEventResponse]
    total: int
    skip: int
    limit: int


# ── Schémas de création - Participations ─────────────────────────
class EventParticipationCreate(BaseModel):
    """Schéma pour inscrire un participant."""

    servant_id: UUID
    notes: Optional[str] = None


class EventParticipationBatchCreate(BaseModel):
    """Schéma pour inscrire plusieurs participants."""

    servant_ids: List[UUID] = Field(min_length=1)
    notes: Optional[str] = None


class EventParticipationMarkAttendance(BaseModel):
    """Schéma pour marquer la présence."""

    status: ParticipationStatus
    notes: Optional[str] = None


class EventParticipationMarkPayment(BaseModel):
    """Schéma pour marquer le paiement."""

    payment_status: bool
    notes: Optional[str] = None


class EventParticipationResponse(BaseModel):
    """Schéma de réponse pour une participation."""

    id: UUID
    event_id: UUID
    servant_id: UUID
    servant_name: Optional[str]
    status: ParticipationStatus
    registration_date: datetime
    attendance_marked_at: Optional[datetime]
    payment_status: bool
    payment_date: Optional[datetime]
    notes: Optional[str]
    registered_by: UUID
    marked_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventParticipationListResponse(BaseModel):
    """Schéma de réponse pour une liste de participations."""

    items: List[EventParticipationResponse]
    total: int


# ── Schémas de création - Résultats ──────────────────────────────
class EventResultCreate(BaseModel):
    """Schéma pour créer un résultat."""

    result_type: ResultType
    team_name: Optional[str] = None
    score: Optional[int] = Field(None, ge=0)
    opponent_name: Optional[str] = None
    opponent_score: Optional[int] = Field(None, ge=0)
    ranking: Optional[int] = Field(None, ge=1)
    description: str = Field(min_length=1)
    notes: Optional[str] = None


class EventResultResponse(BaseModel):
    """Schéma de réponse pour un résultat."""

    id: UUID
    event_id: UUID
    result_type: ResultType
    team_name: Optional[str]
    score: Optional[int]
    opponent_name: Optional[str]
    opponent_score: Optional[int]
    ranking: Optional[int]
    description: str
    notes: Optional[str]
    recorded_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ── Schémas de création - Équipes ────────────────────────────────
class EventTeamCreate(BaseModel):
    """Schéma pour créer une équipe."""

    team_name: str = Field(min_length=1, max_length=100)
    captain_id: UUID
    members: List[UUID] = Field(default_factory=list)


class EventTeamUpdate(BaseModel):
    """Schéma pour modifier une équipe."""

    team_name: Optional[str] = Field(None, min_length=1, max_length=100)
    captain_id: Optional[UUID] = None
    members: Optional[List[UUID]] = None


class EventTeamResponse(BaseModel):
    """Schéma de réponse pour une équipe."""

    id: UUID
    event_id: UUID
    team_name: str
    captain_id: UUID
    members: List[UUID]
    created_by: UUID
    created_at: datetime
    # Enrichi
    captain_name: Optional[str] = None
    members_names: List[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ── Schémas pour rapports ────────────────────────────────────────
class SportCultureReportRequest(BaseModel):
    """Schéma pour demander un rapport."""

    start_date: datetime
    end_date: datetime
    event_type: Optional[EventType] = None


class SportCultureReportResponse(BaseModel):
    """Schéma de réponse pour un rapport."""

    id: UUID
    start_date: datetime
    end_date: datetime
    total_events: int
    events_by_type: dict
    total_participants: int
    average_participation_rate: float
    total_cost: float
    total_revenue: float
    events_summary: List[dict]
    top_participants: List[dict]
    generated_by: UUID
    watermark_logo: str
    generated_at: datetime

    class Config:
        from_attributes = True


# ── Schémas pour statistiques ────────────────────────────────────
class SportCultureStatsResponse(BaseModel):
    """Schéma de réponse pour les statistiques."""

    total_events: int
    events_by_type: dict
    events_by_status: dict
    total_participants: int
    average_participation_rate: float
    upcoming_events: int
    completed_events: int


class ServantParticipationStatsResponse(BaseModel):
    """Schéma de réponse pour les statistiques d'un servant."""

    servant_id: UUID
    total_participations: int
    events_attended: int
    events_missed: int
    attendance_rate: float
    total_paid: float
    events_by_type: dict
