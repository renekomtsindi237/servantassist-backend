"""
Schémas Pydantic pour le module INTENDANTS - Gestion du matériel.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.material import MaterialCategory, MaterialCondition, TaskStatus, TaskType


# ── Schémas de création - Articles ───────────────────────────────────
class MaterialItemCreate(BaseModel):
    """Schéma pour créer un article."""

    name: str = Field(min_length=1, max_length=200)
    category: MaterialCategory
    description: Optional[str] = None
    quantity: int = Field(ge=0)
    size: Optional[str] = None
    condition: MaterialCondition = MaterialCondition.BON
    location: str = Field(min_length=1, max_length=200)
    purchase_date: Optional[datetime] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None


class MaterialItemUpdate(BaseModel):
    """Schéma pour modifier un article."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    category: Optional[MaterialCategory] = None
    description: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    size: Optional[str] = None
    condition: Optional[MaterialCondition] = None
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    purchase_date: Optional[datetime] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None


class MaterialItemResponse(BaseModel):
    """Schéma de réponse pour un article."""

    id: UUID
    name: str
    category: MaterialCategory
    description: Optional[str]
    quantity: int
    size: Optional[str]
    condition: MaterialCondition
    location: str
    purchase_date: Optional[datetime]
    last_maintenance_date: Optional[datetime]
    next_maintenance_date: Optional[datetime]
    notes: Optional[str]
    photo_url: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MaterialItemListResponse(BaseModel):
    """Schéma de réponse pour une liste d'articles."""

    items: List[MaterialItemResponse]
    total: int
    skip: int
    limit: int


# ── Schémas de création - Tâches de nettoyage ────────────────────────
class CleaningTaskCreate(BaseModel):
    """Schéma pour créer une tâche de nettoyage."""

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    task_type: TaskType
    scheduled_date: datetime
    scheduled_time: str = Field(pattern=r"^\d{2}h\d{2}$")
    location: str = Field(min_length=1, max_length=200)
    items: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class CleaningTaskUpdate(BaseModel):
    """Schéma pour modifier une tâche."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, min_length=1)
    task_type: Optional[TaskType] = None
    scheduled_date: Optional[datetime] = None
    scheduled_time: Optional[str] = Field(None, pattern=r"^\d{2}h\d{2}$")
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    items: Optional[List[str]] = None
    status: Optional[TaskStatus] = None
    notes: Optional[str] = None


class CleaningTaskComplete(BaseModel):
    """Schéma pour marquer une tâche comme terminée."""

    photos_after: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class CleaningTaskValidate(BaseModel):
    """Schéma pour valider une tâche."""

    notes: Optional[str] = None


class CleaningTaskResponse(BaseModel):
    """Schéma de réponse pour une tâche."""

    id: UUID
    title: str
    description: str
    task_type: TaskType
    scheduled_date: datetime
    scheduled_time: str
    location: str
    items: List[str]
    status: TaskStatus
    completed_at: Optional[datetime]
    validated_at: Optional[datetime]
    validated_by: Optional[UUID]
    photos_before: List[str]
    photos_after: List[str]
    notes: Optional[str]
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    # Enrichi
    assigned_servants: List[dict] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CleaningTaskListResponse(BaseModel):
    """Schéma de réponse pour une liste de tâches."""

    items: List[CleaningTaskResponse]
    total: int
    skip: int
    limit: int


# ── Schémas de création - Assignations ───────────────────────────────
class TaskAssignmentCreate(BaseModel):
    """Schéma pour assigner un servant."""

    servant_id: UUID


class TaskAssignmentBatchCreate(BaseModel):
    """Schéma pour assigner plusieurs servants."""

    servant_ids: List[UUID] = Field(min_length=1)


class TaskAssignmentResponse(BaseModel):
    """Schéma de réponse pour une assignation."""

    id: UUID
    task_id: UUID
    servant_id: UUID
    servant_name: Optional[str]
    assigned_by: UUID
    assigned_at: datetime
    notified: bool
    notified_at: Optional[datetime]

    class Config:
        from_attributes = True


# ── Schémas de création - Tâches aubes ───────────────────────────────
class AubeTaskCreate(BaseModel):
    """Schéma pour créer une tâche d'aubes."""

    title: str = Field(min_length=1, max_length=200)
    task_type: TaskType  # LAVAGE ou REPASSAGE
    scheduled_date: datetime
    scheduled_time: str = Field(pattern=r"^\d{2}h\d{2}$")
    location: str = Field(min_length=1, max_length=200)
    aube_count: int = Field(gt=0)
    aube_sizes: List[str] = Field(default_factory=list)
    notes: Optional[str] = None
    broadcast_notification: bool = True


class AubeTaskUpdate(BaseModel):
    """Schéma pour modifier une tâche d'aubes."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    task_type: Optional[TaskType] = None
    scheduled_date: Optional[datetime] = None
    scheduled_time: Optional[str] = Field(None, pattern=r"^\d{2}h\d{2}$")
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    aube_count: Optional[int] = Field(None, gt=0)
    aube_sizes: Optional[List[str]] = None
    status: Optional[TaskStatus] = None
    notes: Optional[str] = None


class AubeTaskComplete(BaseModel):
    """Schéma pour marquer une tâche d'aubes comme terminée."""

    photos_after: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class AubeTaskResponse(BaseModel):
    """Schéma de réponse pour une tâche d'aubes."""

    id: UUID
    title: str
    task_type: TaskType
    scheduled_date: datetime
    scheduled_time: str
    location: str
    aube_count: int
    aube_sizes: List[str]
    status: TaskStatus
    completed_at: Optional[datetime]
    validated_at: Optional[datetime]
    validated_by: Optional[UUID]
    photos_before: List[str]
    photos_after: List[str]
    notes: Optional[str]
    broadcast_notification: bool
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    # Enrichi
    assigned_servants: List[dict] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AubeTaskListResponse(BaseModel):
    """Schéma de réponse pour une liste de tâches d'aubes."""

    items: List[AubeTaskResponse]
    total: int
    skip: int
    limit: int


# ── Schémas pour historique de maintenance ───────────────────────────
class MaintenanceHistoryCreate(BaseModel):
    """Schéma pour créer un historique de maintenance."""

    maintenance_type: TaskType
    description: str = Field(min_length=1)
    performed_date: datetime
    cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None


class MaintenanceHistoryResponse(BaseModel):
    """Schéma de réponse pour un historique."""

    id: UUID
    item_id: UUID
    maintenance_type: TaskType
    description: str
    performed_date: datetime
    performed_by: UUID
    cost: Optional[float]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Schémas pour rapports ────────────────────────────────────────────
class MaterialReportRequest(BaseModel):
    """Schéma pour demander un rapport."""

    start_date: datetime
    end_date: datetime
    include_maintenance_history: bool = True


class MaterialReportResponse(BaseModel):
    """Schéma de réponse pour un rapport."""

    id: UUID
    start_date: datetime
    end_date: datetime
    total_items: int
    items_by_category: dict
    items_by_condition: dict
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    total_maintenance_cost: float
    items_needing_attention: List[dict]
    generated_by: UUID
    watermark_logo: str
    generated_at: datetime

    class Config:
        from_attributes = True


# ── Schémas pour statistiques ────────────────────────────────────────
class MaterialStatsResponse(BaseModel):
    """Schéma de réponse pour les statistiques."""

    total_items: int
    items_by_category: dict
    items_by_condition: dict
    items_needing_maintenance: int
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    completion_rate: float
