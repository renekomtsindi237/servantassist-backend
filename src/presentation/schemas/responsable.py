"""
Schemas Pydantic pour le module Responsables.

Gere les nominations aux postes de responsable et les actions
effectuees par chaque responsable dans le cadre de son poste.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.responsable import (
    ActionCategory,
    ActionStatus,
    NominationStatus,
    PosteResponsable,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Nominations
# ═══════════════════════════════════════════════════════════════════════════

class NominationCreate(BaseModel):
    """Schema pour nommer un servant a un poste de responsable."""
    user_id: UUID
    poste: PosteResponsable
    notes: Optional[str] = Field(None, max_length=500)


class NominationResponse(BaseModel):
    """Reponse pour une nomination avec infos utilisateur."""
    id: UUID
    user_id: UUID
    poste: PosteResponsable
    poste_titre: Optional[str] = None
    poste_slug: Optional[str] = None
    status: NominationStatus
    nominated_by: UUID
    notes: Optional[str] = None
    nominated_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_by: Optional[UUID] = None
    # Infos enrichies
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[str] = None

    class Config:
        from_attributes = True


class PosteDetailResponse(BaseModel):
    """Detail d'un poste avec son titulaire et ses missions."""
    poste: PosteResponsable
    slug: str
    titre: str
    description: str
    missions: List[str]
    categories_autorisees: List[ActionCategory]
    titulaire: Optional[NominationResponse] = None


class PosteListResponse(BaseModel):
    """Liste de tous les postes avec statut d'occupation."""
    postes: List[PosteDetailResponse]
    total_postes: int
    postes_pourvus: int
    postes_vacants: int


# ═══════════════════════════════════════════════════════════════════════════
#  Actions de poste
# ═══════════════════════════════════════════════════════════════════════════

class PosteActionCreate(BaseModel):
    """Schema pour creer une action de responsable."""
    category: ActionCategory
    title: str = Field(..., min_length=1, max_length=300)
    content: Optional[str] = Field(default=None, max_length=5000)
    target_user_id: Optional[UUID] = None
    target_event_id: Optional[UUID] = None
    amount: Optional[float] = Field(default=None, ge=0)
    action_date: Optional[datetime] = None
    status: Optional[ActionStatus] = Field(default=ActionStatus.BROUILLON)
    extra_data: Optional[str] = Field(default=None, max_length=10000)


class PosteActionUpdate(BaseModel):
    """Modification partielle d'une action de responsable."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    content: Optional[str] = Field(default=None, max_length=5000)
    target_user_id: Optional[UUID] = None
    target_event_id: Optional[UUID] = None
    amount: Optional[float] = Field(default=None, ge=0)
    action_date: Optional[datetime] = None
    status: Optional[ActionStatus] = None
    extra_data: Optional[str] = Field(default=None, max_length=10000)


class PosteActionPublish(BaseModel):
    """Schema pour publier une action."""
    pass  # Pas de paramètres requis


class PosteActionResponse(BaseModel):
    """Reponse pour une action de responsable."""
    id: UUID
    poste: PosteResponsable
    category: ActionCategory
    title: str
    content: Optional[str] = None
    target_user_id: Optional[UUID] = None
    target_event_id: Optional[UUID] = None
    amount: Optional[float] = None
    action_date: Optional[datetime] = None
    status: ActionStatus
    extra_data: Optional[str] = None
    created_by: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Enrichissement
    author_first_name: Optional[str] = None
    author_last_name: Optional[str] = None
    target_user_name: Optional[str] = None
    target_event_title: Optional[str] = None

    class Config:
        from_attributes = True


class PosteActionListResponse(BaseModel):
    """Liste des actions avec pagination."""
    items: List[PosteActionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    updated_at: Optional[datetime] = None
    # Enrichissement
    author_first_name: Optional[str] = None
    author_last_name: Optional[str] = None
    target_user_name: Optional[str] = None
    target_event_title: Optional[str] = None

    class Config:
        from_attributes = True


class PosteDashboardResponse(BaseModel):
    """Tableau de bord d'un poste de responsable."""
    poste: PosteResponsable
    slug: str
    titre: str
    description: str
    missions: List[str]
    total_actions: int
    actions_brouillon: int
    actions_publiees: int
    actions_en_cours: int
    actions_terminees: int
    recent_actions: List[PosteActionResponse]


# ═══════════════════════════════════════════════════════════════════════════
#  Conseil des Responsables
# ═══════════════════════════════════════════════════════════════════════════

class CouncilMeetingCreate(BaseModel):
    """Schema pour creer une reunion du conseil."""
    meeting_date: datetime
    location: str = Field(..., max_length=200)
    agenda: Optional[str] = Field(None, max_length=1000)


class CouncilAttendanceRecord(BaseModel):
    """Schema pour enregistrer une presence au conseil."""
    responsable_id: UUID
    is_present: bool = True
    excuse: Optional[str] = Field(None, max_length=500)


class CouncilAttendanceRecordList(BaseModel):
    """Liste des presences a enregistrer."""
    attendances: List[CouncilAttendanceRecord]


class CouncilMeetingResponse(BaseModel):
    """Reponse pour une reunion du conseil."""
    id: UUID
    meeting_date: datetime
    location: str
    agenda: Optional[str] = None
    created_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True

