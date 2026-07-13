"""
Entités pour le module CHARGE_SPORT_CULTURE - Activités sportives et culturelles.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Column, String
from sqlmodel import JSON, Field, SQLModel


class EventType(str, Enum):
    """Type d'événement."""

    JOURNEE_SPORTIVE = "JOURNEE_SPORTIVE"  # Journée sportive mensuelle
    TOURNOI = "TOURNOI"  # Tournoi sportif
    MATCH = "MATCH"  # Match amical
    SORTIE_CULTURELLE = "SORTIE_CULTURELLE"  # Sortie culturelle
    SPECTACLE = "SPECTACLE"  # Spectacle, théâtre
    VISITE = "VISITE"  # Visite de musée, monument
    AUTRE = "AUTRE"  # Autre activité


class EventStatus(str, Enum):
    """Statut de l'événement."""

    PLANIFIE = "PLANIFIE"  # Événement planifié
    OUVERT = "OUVERT"  # Inscriptions ouvertes
    COMPLET = "COMPLET"  # Inscriptions complètes
    EN_COURS = "EN_COURS"  # Événement en cours
    TERMINE = "TERMINE"  # Événement terminé
    ANNULE = "ANNULE"  # Événement annulé


class SportType(str, Enum):
    """Type de sport."""

    FOOTBALL = "FOOTBALL"
    BASKETBALL = "BASKETBALL"
    VOLLEYBALL = "VOLLEYBALL"
    HANDBALL = "HANDBALL"
    ATHLETISME = "ATHLETISME"
    NATATION = "NATATION"
    TENNIS = "TENNIS"
    AUTRE = "AUTRE"


class ParticipationStatus(str, Enum):
    """Statut de participation."""

    INSCRIT = "INSCRIT"  # Inscrit
    CONFIRME = "CONFIRME"  # Présence confirmée
    PRESENT = "PRESENT"  # Présent
    ABSENT = "ABSENT"  # Absent
    EXCUSE = "EXCUSE"  # Excusé


class ResultType(str, Enum):
    """Type de résultat."""

    VICTOIRE = "VICTOIRE"
    DEFAITE = "DEFAITE"
    NUL = "NUL"
    CLASSEMENT = "CLASSEMENT"  # Pour les tournois
    PARTICIPATION = "PARTICIPATION"  # Pour les activités culturelles


class SportCultureEvent(SQLModel, table=True):
    """
    Événement sportif ou culturel.
    """

    __tablename__ = "sport_culture_events"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(min_length=1, max_length=200)
    description: str
    event_type: EventType = Field(sa_column=Column(String(50), nullable=False))
    sport_type: Optional[SportType] = Field(default=None, sa_column=Column(String(50), nullable=True))
    date: datetime
    start_time: str  # Format HHhMM
    end_time: str  # Format HHhMM
    location: str = Field(min_length=1, max_length=200)
    max_participants: int = Field(ge=0)
    cost: Optional[float] = Field(None, ge=0)
    status: EventStatus = Field(
        default=EventStatus.PLANIFIE,
        sa_column=Column(String(50), nullable=False, server_default="PLANIFIE"),
    )
    registration_deadline: Optional[datetime] = None
    notes: Optional[str] = None
    photos: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    broadcast_notification: bool = True
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EventParticipation(SQLModel, table=True):
    """
    Participation à un événement.
    """

    __tablename__ = "sport_culture_participations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="sport_culture_events.id")
    servant_id: UUID = Field(foreign_key="users.id")
    servant_name: Optional[str] = None  # Enrichi
    status: ParticipationStatus = Field(
        default=ParticipationStatus.INSCRIT,
        sa_column=Column(String(50), nullable=False, server_default="INSCRIT"),
    )
    registration_date: datetime = Field(default_factory=datetime.utcnow)
    attendance_marked_at: Optional[datetime] = None
    payment_status: bool = False
    payment_date: Optional[datetime] = None
    notes: Optional[str] = None
    registered_by: UUID = Field(foreign_key="users.id")
    marked_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EventResult(SQLModel, table=True):
    """
    Résultat d'un événement sportif.
    """

    __tablename__ = "sport_culture_results"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="sport_culture_events.id")
    result_type: ResultType = Field(sa_column=Column(String(50), nullable=False))
    team_name: Optional[str] = None
    score: Optional[int] = Field(None, ge=0)
    opponent_name: Optional[str] = None
    opponent_score: Optional[int] = Field(None, ge=0)
    ranking: Optional[int] = Field(None, ge=1)
    description: str
    notes: Optional[str] = None
    recorded_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EventTeam(SQLModel, table=True):
    """
    Équipe pour un événement sportif.
    """

    __tablename__ = "sport_culture_teams"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_id: UUID = Field(foreign_key="sport_culture_events.id")
    team_name: str = Field(min_length=1, max_length=100)
    captain_id: UUID = Field(foreign_key="users.id")
    captain_name: Optional[str] = None  # Enrichi
    members: List[str] = Field(
        default_factory=list, sa_column=Column(JSON)
    )  # Changed to List[str] for JSON serialization
    members_names: List[str] = Field(default_factory=list, sa_column=Column(JSON))  # Enrichi
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SportCultureReport(BaseModel):
    """
    Rapport d'activités sportives et culturelles.

    Attributes:
        id: Identifiant unique
        start_date: Date de début de la période
        end_date: Date de fin de la période
        total_events: Nombre total d'événements
        events_by_type: Répartition par type
        total_participants: Nombre total de participants
        average_participation_rate: Taux de participation moyen
        total_cost: Coût total
        total_revenue: Revenu total
        events_summary: Résumé des événements
        top_participants: Participants les plus actifs
        generated_by: ID du générateur
        watermark_logo: Logo en filigrane
        generated_at: Date de génération
    """

    id: UUID = Field(default_factory=uuid4)
    start_date: datetime
    end_date: datetime
    total_events: int
    events_by_type: dict = Field(default_factory=dict)
    total_participants: int
    average_participation_rate: float
    total_cost: float
    total_revenue: float
    events_summary: List[dict] = Field(default_factory=list)
    top_participants: List[dict] = Field(default_factory=list)
    generated_by: UUID
    watermark_logo: str = "logo_servant.jpeg"
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True
