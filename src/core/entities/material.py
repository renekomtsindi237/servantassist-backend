"""
Entités pour le module INTENDANTS - Gestion du matériel.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlmodel import JSON, Field, Relationship, SQLModel


class MaterialCategory(str, Enum):
    """Catégorie de matériel."""

    AUBE = "AUBE"  # Aubes des servants
    ENCENSOIR = "ENCENSOIR"  # Encensoirs
    CIERGE = "CIERGE"  # Cierges et bougies
    NAPPE = "NAPPE"  # Nappes d'autel
    CALICE = "CALICE"  # Calices
    PATENE = "PATENE"  # Patènes
    CIBOIRE = "CIBOIRE"  # Ciboires
    OSTENSOIR = "OSTENSOIR"  # Ostensoirs
    CROIX = "CROIX"  # Croix processionnelles
    AUTRE = "AUTRE"  # Autre matériel


class MaterialCondition(str, Enum):
    """État du matériel."""

    BON = "BON"  # Bon état
    A_NETTOYER = "A_NETTOYER"  # À nettoyer
    A_REPARER = "A_REPARER"  # À réparer
    HORS_SERVICE = "HORS_SERVICE"  # Hors service


class TaskType(str, Enum):
    """Type de tâche."""

    NETTOYAGE = "NETTOYAGE"  # Nettoyage du matériel
    LAVAGE = "LAVAGE"  # Lavage des aubes
    REPASSAGE = "REPASSAGE"  # Repassage des aubes
    REPARATION = "REPARATION"  # Réparation
    MAINTENANCE = "MAINTENANCE"  # Maintenance


class TaskStatus(str, Enum):
    """Statut de la tâche."""

    PLANIFIEE = "PLANIFIEE"  # Tâche planifiée
    EN_COURS = "EN_COURS"  # En cours
    TERMINEE = "TERMINEE"  # Terminée
    VALIDEE = "VALIDEE"  # Validée par l'intendant
    ANNULEE = "ANNULEE"  # Annulée


class MaterialItem(SQLModel, table=True):
    """
    Article de matériel liturgique.
    """

    __tablename__ = "material_items"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(min_length=1, max_length=200)
    category: MaterialCategory = Field(sa_column=Column(String(50), nullable=False))
    description: Optional[str] = None
    quantity: int = Field(ge=0)
    size: Optional[str] = None  # Pour les aubes : S, M, L, XL
    condition: MaterialCondition = Field(
        default=MaterialCondition.BON,
        sa_column=Column(String(50), nullable=False, server_default="BON"),
    )
    location: str = Field(min_length=1, max_length=200)
    purchase_date: Optional[datetime] = None
    last_maintenance_date: Optional[datetime] = None
    next_maintenance_date: Optional[datetime] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class CleaningTask(SQLModel, table=True):
    """
    Tâche de nettoyage du matériel.
    """

    __tablename__ = "cleaning_tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=200)
    description: str
    task_type: TaskType = Field(sa_column=Column(String(50), nullable=False))
    scheduled_date: datetime
    scheduled_time: str  # Format HH:MM
    location: str = Field(min_length=1, max_length=200)
    items: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # Liste des noms d'articles
    status: TaskStatus = Field(
        default=TaskStatus.PLANIFIEE,
        sa_column=Column(String(50), nullable=False, server_default="PLANIFIEE"),
    )
    completed_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    validated_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    photos_before: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    photos_after: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    notes: Optional[str] = None
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TaskAssignment(SQLModel, table=True):
    """
    Assignation d'un servant à une tâche.
    """

    __tablename__ = "task_assignments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    task_id: UUID = Field(foreign_key="cleaning_tasks.id")
    servant_id: UUID = Field(foreign_key="users.id")
    servant_name: Optional[str] = None  # Enrichi
    assigned_by: UUID = Field(foreign_key="users.id")
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    notified: bool = False
    notified_at: Optional[datetime] = None


class AubeTask(SQLModel, table=True):
    """
    Tâche de lavage/repassage des aubes.
    """

    __tablename__ = "aube_tasks"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=200)
    task_type: TaskType = Field(sa_column=Column(String(50), nullable=False))  # LAVAGE ou REPASSAGE
    scheduled_date: datetime
    scheduled_time: str  # Format HH:MM
    location: str = Field(min_length=1, max_length=200)
    aube_count: int = Field(gt=0)
    aube_sizes: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    status: TaskStatus = Field(
        default=TaskStatus.PLANIFIEE,
        sa_column=Column(String(50), nullable=False, server_default="PLANIFIEE"),
    )
    completed_at: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    validated_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    photos_before: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    photos_after: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    notes: Optional[str] = None
    broadcast_notification: bool = True  # Notification à tous par défaut
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class MaintenanceHistory(SQLModel, table=True):
    """
    Historique de maintenance d'un article.
    """

    __tablename__ = "maintenance_history"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    item_id: UUID = Field(foreign_key="material_items.id")
    maintenance_type: TaskType = Field(sa_column=Column(String(50), nullable=False))
    description: str
    performed_date: datetime
    performed_by: UUID = Field(foreign_key="users.id")
    cost: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MaterialReport(BaseModel):
    """
    Rapport de gestion du matériel.

    Attributes:
        id: Identifiant unique
        start_date: Date de début de la période
        end_date: Date de fin de la période
        total_items: Nombre total d'articles
        items_by_category: Répartition par catégorie
        items_by_condition: Répartition par état
        total_tasks: Nombre total de tâches
        completed_tasks: Nombre de tâches terminées
        pending_tasks: Nombre de tâches en attente
        total_maintenance_cost: Coût total de maintenance
        items_needing_attention: Articles nécessitant attention
        generated_by: ID du générateur
        watermark_logo: Logo en filigrane
        generated_at: Date de génération
    """

    id: UUID = Field(default_factory=uuid4)
    start_date: datetime
    end_date: datetime
    total_items: int
    items_by_category: dict = Field(default_factory=dict)
    items_by_condition: dict = Field(default_factory=dict)
    total_tasks: int
    completed_tasks: int
    pending_tasks: int
    total_maintenance_cost: float
    items_needing_attention: List[dict] = Field(default_factory=list)
    generated_by: UUID
    watermark_logo: str = "logo_servant.jpeg"
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
