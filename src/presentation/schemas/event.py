"""
Schemas Pydantic pour le module Evenements.

Gere la creation, modification, lecture et gestion des participants.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.entities.event import (
    EventStatus,
    EventType,
    ParticipantRole,
    ParticipantStatus,
)
from src.core.utils import maybe_to_naive_utc, to_naive_utc

# ═══════════════════════════════════════════════════════════════════════════
#  Participants
# ═══════════════════════════════════════════════════════════════════════════


class ParticipantAdd(BaseModel):
    """Schema pour ajouter un participant a un evenement."""

    user_id: UUID
    participant_role: ParticipantRole = ParticipantRole.SERVANT
    notes: Optional[str] = Field(None, max_length=500)


class ParticipantUpdate(BaseModel):
    """Schema pour modifier un participant."""

    participant_role: Optional[ParticipantRole] = None
    status: Optional[ParticipantStatus] = None
    notes: Optional[str] = Field(None, max_length=500)


class ParticipantResponse(BaseModel):
    """Schema de reponse pour un participant."""

    id: UUID
    event_id: UUID
    user_id: UUID
    participant_role: ParticipantRole
    status: ParticipantStatus
    notes: Optional[str] = None
    added_by: UUID
    # Informations utilisateur pour l'affichage
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
#  Evenements
# ═══════════════════════════════════════════════════════════════════════════


class EventCreate(BaseModel):
    """Creation d'un evenement avec participants optionnels."""

    title: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: datetime
    end_time: datetime
    location: str = Field(..., min_length=2, max_length=300)
    event_type: EventType = EventType.MESSE_DOMINICALE
    status: EventStatus = EventStatus.BROUILLON
    # Participants a ajouter directement a la creation
    participants: Optional[List[ParticipantAdd]] = Field(
        default=None, description="Liste des participants a ajouter lors de la creation"
    )

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_datetimes(cls, v: datetime) -> datetime:
        return to_naive_utc(v)

    @model_validator(mode="after")
    def validate_end_after_start(self):
        if self.end_time <= self.start_time:
            raise ValueError("La date de fin doit etre apres la date de debut")
        return self


class EventUpdate(BaseModel):
    """Modification partielle d'un evenement (PATCH)."""

    title: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, min_length=2, max_length=300)
    event_type: Optional[EventType] = None
    status: Optional[EventStatus] = None

    @field_validator("start_time", "end_time")
    @classmethod
    def normalize_optional_datetimes(cls, v: Optional[datetime]) -> Optional[datetime]:
        return maybe_to_naive_utc(v)


class EventResponse(BaseModel):
    """Reponse pour un evenement (sans participants detailles)."""

    id: UUID
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: str
    event_type: EventType
    status: EventStatus
    created_by: UUID
    updated_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    participant_count: int = 0

    class Config:
        from_attributes = True


class EventDetailResponse(BaseModel):
    """Reponse detaillee pour un evenement avec ses participants."""

    id: UUID
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: str
    event_type: EventType
    status: EventStatus
    created_by: UUID
    updated_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    participants: List[ParticipantResponse] = []

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
#  Filtres de listing
# ═══════════════════════════════════════════════════════════════════════════


class EventListFilters(BaseModel):
    """Parametres de filtre et pagination pour la liste des evenements."""

    event_type: Optional[EventType] = None
    status: Optional[EventStatus] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = Field(None, max_length=100)
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    @field_validator("start_date", "end_date")
    @classmethod
    def normalize_filter_datetimes(cls, v: Optional[datetime]) -> Optional[datetime]:
        return maybe_to_naive_utc(v)
