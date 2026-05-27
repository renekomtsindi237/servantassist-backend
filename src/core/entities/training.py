"""
Entités pour le module CHARGE_LITURGIE - Formations liturgiques.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlmodel import JSON, Field, SQLModel


class TrainingLevel(str, Enum):
    """Niveau de formation."""

    DEBUTANT = "DEBUTANT"  # Nouveaux servants
    INTERMEDIAIRE = "INTERMEDIAIRE"  # Servants confirmés
    AVANCE = "AVANCE"  # Servants expérimentés
    TOUS = "TOUS"  # Tous niveaux


class TrainingStatus(str, Enum):
    """Statut de la session de formation."""

    PLANIFIEE = "PLANIFIEE"  # Session planifiée
    EN_COURS = "EN_COURS"  # Session en cours
    TERMINEE = "TERMINEE"  # Session terminée
    ANNULEE = "ANNULEE"  # Session annulée


class MaterialType(str, Enum):
    """Type de matériel pédagogique."""

    DOCUMENT = "DOCUMENT"  # Document PDF, Word, etc.
    VIDEO = "VIDEO"  # Vidéo de démonstration
    QUIZ = "QUIZ"  # Quiz d'évaluation
    IMAGE = "IMAGE"  # Image, schéma
    AUTRE = "AUTRE"  # Autre type


class ParticipationStatus(str, Enum):
    """Statut de participation."""

    INSCRIT = "INSCRIT"  # Inscrit à la session
    PRESENT = "PRESENT"  # Présent à la session
    ABSENT = "ABSENT"  # Absent à la session
    EXCUSE = "EXCUSE"  # Absent excusé


class TrainingSession(SQLModel, table=True):
    """
    Session de formation liturgique.
    """

    __tablename__ = "training_sessions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=200)
    description: str
    objectives: Optional[str] = None
    date: datetime
    start_time: str  # Format HH:MM
    end_time: str  # Format HH:MM
    duration_minutes: int = Field(gt=0)
    location: str = Field(min_length=1, max_length=200)
    trainer_id: UUID = Field(foreign_key="users.id")
    trainer_name: Optional[str] = None  # Enrichi
    max_participants: int = Field(ge=0, default=0)  # 0 = illimité
    current_participants: int = 0  # Enrichi
    level: TrainingLevel = Field(
        default=TrainingLevel.TOUS,
        sa_column=Column(String(50), nullable=False, server_default="TOUS"),
    )
    status: TrainingStatus = Field(
        default=TrainingStatus.PLANIFIEE,
        sa_column=Column(String(50), nullable=False, server_default="PLANIFIEE"),
    )
    materials_url: Optional[str] = None
    notes: Optional[str] = None
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TrainingParticipation(SQLModel, table=True):
    """
    Participation d'un servant à une session de formation.
    """

    __tablename__ = "training_participations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="training_sessions.id")
    servant_id: UUID = Field(foreign_key="users.id")
    servant_name: Optional[str] = None  # Enrichi
    status: ParticipationStatus = Field(
        default=ParticipationStatus.INSCRIT,
        sa_column=Column(String(50), nullable=False, server_default="INSCRIT"),
    )
    registration_date: datetime = Field(default_factory=datetime.utcnow)
    attendance_marked_at: Optional[datetime] = None
    evaluation_score: Optional[int] = Field(None, ge=0, le=100)
    evaluation_comments: Optional[str] = None
    certificate_issued: bool = False
    certificate_url: Optional[str] = None
    notes: Optional[str] = None
    registered_by: UUID = Field(foreign_key="users.id")
    marked_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TrainingMaterial(SQLModel, table=True):
    """
    Matériel pédagogique pour les formations.
    """

    __tablename__ = "training_materials"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=200)
    description: str
    type: MaterialType = Field(sa_column=Column(String(50), nullable=False))
    file_url: str
    file_type: str  # MIME type
    file_size: int = Field(gt=0)
    thumbnail_url: Optional[str] = None
    level: TrainingLevel = Field(
        default=TrainingLevel.TOUS,
        sa_column=Column(String(50), nullable=False, server_default="TOUS"),
    )
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    is_public: bool = True  # Accessible à tous par défaut
    view_count: int = 0
    uploaded_by: UUID = Field(foreign_key="users.id")
    uploaded_by_name: Optional[str] = None  # Enrichi
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SessionMaterial(SQLModel, table=True):
    """
    Association entre une session et un matériel.
    """

    __tablename__ = "training_session_materials"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    session_id: UUID = Field(foreign_key="training_sessions.id")
    material_id: UUID = Field(foreign_key="training_materials.id")
    order: int = 0
    is_required: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TrainingStats(BaseModel):
    """
    Statistiques de formation d'un servant.

    Attributes:
        servant_id: ID du servant
        servant_name: Nom du servant
        total_sessions: Nombre total de sessions
        attended_sessions: Nombre de sessions suivies
        absent_sessions: Nombre d'absences
        attendance_rate: Taux de présence (%)
        average_score: Note moyenne
        certificates_earned: Nombre de certificats obtenus
        last_training_date: Date de la dernière formation
    """

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


class TrainingReport(BaseModel):
    """
    Rapport de formation.

    Attributes:
        id: Identifiant unique
        start_date: Date de début de la période
        end_date: Date de fin de la période
        total_sessions: Nombre total de sessions
        completed_sessions: Nombre de sessions terminées
        total_participants: Nombre total de participants
        average_attendance_rate: Taux de présence moyen (%)
        average_evaluation_score: Note moyenne
        certificates_issued: Nombre de certificats délivrés
        top_performers: Meilleurs participants
        sessions_by_level: Répartition par niveau
        generated_by: ID du générateur
        watermark_logo: Logo en filigrane
        generated_at: Date de génération
    """

    id: UUID = Field(default_factory=uuid4)
    start_date: datetime
    end_date: datetime
    total_sessions: int
    completed_sessions: int
    total_participants: int
    average_attendance_rate: float
    average_evaluation_score: Optional[float]
    certificates_issued: int
    top_performers: List[dict] = Field(default_factory=list)
    sessions_by_level: dict = Field(default_factory=dict)
    generated_by: UUID
    watermark_logo: str = "logo_servant.jpeg"
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
