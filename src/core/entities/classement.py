"""
Entités pour le module de gestion des classements (CHARGE_CLASSEMENT).
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String
from sqlmodel import JSON, Field, SQLModel

from src.core.utils import utc_now


class ClassementType(str, Enum):
    DIMANCHE = "DIMANCHE"
    SEMAINE = "SEMAINE"
    EXTRAORDINAIRE = "EXTRAORDINAIRE"


class ClassementStatus(str, Enum):
    BROUILLON = "BROUILLON"
    FINALISE = "FINALISE"
    PUBLIE = "PUBLIE"


class Classement(SQLModel, table=True):
    """Classement de messe (dimanche, semaine ou extraordinaire)."""

    __tablename__ = "classements"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: ClassementType = Field(sa_column=Column(String(20), nullable=False))
    status: ClassementStatus = Field(
        default=ClassementStatus.BROUILLON,
        sa_column=Column(String(20), nullable=False, server_default="BROUILLON"),
    )

    # Champs communs
    date: datetime
    heure: str = Field(max_length=10)
    lieu: str = Field(max_length=200)

    # Dimanche uniquement
    solennite: Optional[str] = Field(default=None, max_length=200)
    couleur_liturgique: Optional[str] = Field(default=None, max_length=20)

    # Semaine uniquement
    semaine: Optional[int] = None
    annee: Optional[int] = None
    horaire: Optional[str] = Field(default=None, max_length=10)

    # Extraordinaire uniquement
    type_extra: Optional[str] = Field(default=None, max_length=30)
    participants: Optional[str] = None

    # Tableau des postes : [{label, col1, col2}, ...]
    postes: List[Dict[str, Any]] = Field(default_factory=list, sa_column=Column(JSON))

    created_by: UUID = Field(foreign_key="users.id")
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
