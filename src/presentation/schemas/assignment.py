"""
Schemas Pydantic pour le module Affectations.

Gere la creation, la modification, la lecture et la gestion du cycle de vie
des affectations liturgiques des servants.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.assignment import AssignmentStatus, LiturgicalRole
from src.core.entities.event import EventType

# ═══════════════════════════════════════════════════════════════════════════
#  Creation
# ═══════════════════════════════════════════════════════════════════════════


class AssignmentCreate(BaseModel):
    """Schema de creation d'une affectation liturgique."""

    event_id: UUID
    user_id: UUID
    liturgical_role: LiturgicalRole = LiturgicalRole.SERVANT_GENERAL
    notes: Optional[str] = Field(None, max_length=500)


class AssignmentBatchItem(BaseModel):
    """Un element d'une creation par lot."""

    user_id: UUID
    liturgical_role: LiturgicalRole = LiturgicalRole.SERVANT_GENERAL
    notes: Optional[str] = Field(None, max_length=500)


class AssignmentBatchCreate(BaseModel):
    """Schema pour creer plusieurs affectations en une seule requete."""

    event_id: UUID
    assignments: List[AssignmentBatchItem] = Field(
        ..., min_length=1, description="Au moins une affectation"
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Modification
# ═══════════════════════════════════════════════════════════════════════════


class AssignmentUpdate(BaseModel):
    """Modification partielle d'une affectation (PATCH) — Aumonier/Admin."""

    liturgical_role: Optional[LiturgicalRole] = None
    status: Optional[AssignmentStatus] = None
    notes: Optional[str] = Field(None, max_length=500)


class AssignmentStatusUpdate(BaseModel):
    """Mise a jour du statut par le servant lui-meme (self-service)."""

    status: AssignmentStatus = Field(..., description="ACCEPTED ou DECLINED uniquement")


# ═══════════════════════════════════════════════════════════════════════════
#  Reponses
# ═══════════════════════════════════════════════════════════════════════════


class AssignmentResponse(BaseModel):
    """Reponse pour une affectation avec infos utilisateur et evenement."""

    id: UUID
    event_id: UUID
    user_id: UUID
    liturgical_role: LiturgicalRole
    status: AssignmentStatus
    notes: Optional[str] = None
    assigned_by: UUID
    # Infos utilisateur
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[str] = None
    # Infos evenement
    event_title: Optional[str] = None
    event_type: Optional[EventType] = None
    event_start_time: Optional[datetime] = None
    event_location: Optional[str] = None
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AssignmentBatchResponse(BaseModel):
    """Reponse pour une creation par lot."""

    created: List[AssignmentResponse]
    errors: List[str] = []
    total_created: int = 0
    total_errors: int = 0
