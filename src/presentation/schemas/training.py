"""
Schémas Pydantic pour le module CHARGE_LITURGIE - Formations liturgiques.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.training import MaterialType, ParticipationStatus, TrainingLevel, TrainingStatus


# ── Schémas de création - Sessions ───────────────────────────────────
class TrainingSessionCreate(BaseModel):
    """Schéma pour créer une session de formation."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    objectives: Optional[str] = None
    level: TrainingLevel = TrainingLevel.TOUS
    date: datetime
    start_time: str = Field(pattern=r"^\d{2}h\d{2}$")  # Format HHhMM
    end_time: str = Field(pattern=r"^\d{2}h\d{2}$")
    duration_minutes: int = Field(gt=0, le=480)  # Max 8h
    location: str = Field(min_length=1, max_length=200)
    trainer_id: UUID
    max_participants: int = Field(ge=0, default=0)
    materials_url: Optional[str] = None
    notes: Optional[str] = None


class TrainingSessionUpdate(BaseModel):
    """Schéma pour modifier une session."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    objectives: Optional[str] = None
    level: Optional[TrainingLevel] = None
    date: Optional[datetime] = None
    start_time: Optional[str] = Field(None, pattern=r"^\d{2}h\d{2}$")
    end_time: Optional[str] = Field(None, pattern=r"^\d{2}h\d{2}$")
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    trainer_id: Optional[UUID] = None
    max_participants: Optional[int] = Field(None, ge=0)
    status: Optional[TrainingStatus] = None
    materials_url: Optional[str] = None
    notes: Optional[str] = None


class TrainingSessionResponse(BaseModel):
    """Schéma de réponse pour une session."""

    id: UUID
    title: str
    description: str
    objectives: Optional[str]
    level: TrainingLevel
    date: datetime
    start_time: str
    end_time: str
    duration_minutes: int
    location: str
    trainer_id: UUID
    trainer_name: Optional[str]
    max_participants: int
    current_participants: int
    status: TrainingStatus
    materials_url: Optional[str]
    notes: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingSessionListResponse(BaseModel):
    """Schéma de réponse pour une liste de sessions."""

    items: List[TrainingSessionResponse]
    total: int
    skip: int
    limit: int


# ── Schémas de création - Participations ─────────────────────────────
class TrainingParticipationCreate(BaseModel):
    """Schéma pour inscrire un servant."""

    servant_id: UUID
    notes: Optional[str] = None


class TrainingParticipationBatchCreate(BaseModel):
    """Schéma pour inscrire plusieurs servants."""

    servant_ids: List[UUID] = Field(min_length=1)
    notes: Optional[str] = None


class TrainingParticipationMarkAttendance(BaseModel):
    """Schéma pour marquer la présence."""

    status: ParticipationStatus
    notes: Optional[str] = None


class TrainingParticipationEvaluate(BaseModel):
    """Schéma pour évaluer un participant."""

    evaluation_score: int = Field(ge=0, le=100)
    evaluation_comments: Optional[str] = None
    certificate_issued: bool = False


class TrainingParticipationResponse(BaseModel):
    """Schéma de réponse pour une participation."""

    id: UUID
    session_id: UUID
    servant_id: UUID
    servant_name: Optional[str]
    status: ParticipationStatus
    registration_date: datetime
    attendance_marked_at: Optional[datetime]
    evaluation_score: Optional[int]
    evaluation_comments: Optional[str]
    certificate_issued: bool
    certificate_url: Optional[str]
    notes: Optional[str]
    registered_by: UUID
    marked_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingParticipationListResponse(BaseModel):
    """Schéma de réponse pour une liste de participations."""

    items: List[TrainingParticipationResponse]
    total: int


# ── Schémas de création - Matériels ──────────────────────────────────
class TrainingMaterialCreate(BaseModel):
    """Schéma pour créer un matériel."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    type: MaterialType
    file_url: str
    file_type: str
    file_size: int = Field(gt=0)
    thumbnail_url: Optional[str] = None
    level: TrainingLevel = TrainingLevel.TOUS
    tags: List[str] = Field(default_factory=list)
    is_public: bool = True


class TrainingMaterialUpdate(BaseModel):
    """Schéma pour modifier un matériel."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    type: Optional[MaterialType] = None
    thumbnail_url: Optional[str] = None
    level: Optional[TrainingLevel] = None
    tags: Optional[List[str]] = None
    is_public: Optional[bool] = None


class TrainingMaterialResponse(BaseModel):
    """Schéma de réponse pour un matériel."""

    id: UUID
    title: str
    description: str
    type: MaterialType
    file_url: str
    file_type: str
    file_size: int
    thumbnail_url: Optional[str]
    level: TrainingLevel
    tags: List[str]
    is_public: bool
    view_count: int
    uploaded_by: UUID
    uploaded_by_name: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingMaterialListResponse(BaseModel):
    """Schéma de réponse pour une liste de matériels."""

    items: List[TrainingMaterialResponse]
    total: int
    skip: int
    limit: int


# ── Schémas pour statistiques ────────────────────────────────────────
class TrainingStatsResponse(BaseModel):
    """Schéma de réponse pour les statistiques d'un servant."""

    servant_id: UUID
    servant_name: str
    total_sessions: int
    attended_sessions: int
    absent_sessions: int
    attendance_rate: float
    average_score: Optional[float]
    certificates_earned: int
    last_training_date: Optional[datetime]

    class Config:
        from_attributes = True


class TrainingReportRequest(BaseModel):
    """Schéma pour demander un rapport de formation."""

    start_date: datetime
    end_date: datetime
    level: Optional[TrainingLevel] = None
    include_stats: bool = True


class TrainingReportResponse(BaseModel):
    """Schéma de réponse pour un rapport de formation."""

    id: UUID
    start_date: datetime
    end_date: datetime
    total_sessions: int
    completed_sessions: int
    total_participants: int
    average_attendance_rate: float
    average_evaluation_score: Optional[float]
    certificates_issued: int
    top_performers: List[dict]
    sessions_by_level: dict
    generated_by: UUID
    watermark_logo: str
    generated_at: datetime

    class Config:
        from_attributes = True


# ── Schémas pour association session-matériel ────────────────────────
class SessionMaterialAdd(BaseModel):
    """Schéma pour ajouter un matériel à une session."""

    material_id: UUID
    order: int = 0
    is_required: bool = False


class SessionMaterialResponse(BaseModel):
    """Schéma de réponse pour un matériel de session."""

    id: UUID
    session_id: UUID
    material_id: UUID
    material: TrainingMaterialResponse
    order: int
    is_required: bool
    created_at: datetime

    class Config:
        from_attributes = True
