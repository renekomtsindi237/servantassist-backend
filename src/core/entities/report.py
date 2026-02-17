"""
Entités pour le module de gestion des rapports (SECRETAIRE).
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import Column
from sqlmodel import JSON, Field, SQLModel


class ReportType(str, Enum):
    """Type de rapport."""

    MEETING = "REUNION"  # Réunion hebdomadaire
    ACTIVITY = "ACTIVITE"  # Activité du groupe


class ReportStatus(str, Enum):
    """Statut du rapport."""

    DRAFT = "BROUILLON"
    PUBLISHED = "PUBLIE"
    ARCHIVED = "ARCHIVE"


class Report(SQLModel, table=True):
    """
    Rapport (réunion ou activité).
    """

    __tablename__ = "reports"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    type: ReportType
    title: str
    content: str
    report_date: datetime
    location: str
    participants: list[str] = Field(
        default_factory=list, sa_column=Column(JSON)
    )  # Liste des noms
    decisions: Optional[str] = None
    action_items: Optional[str] = None
    status: ReportStatus = ReportStatus.DRAFT
    created_by: UUID = Field(foreign_key="users.id")
    published_at: Optional[datetime] = None
    watermark_logo: str = "logo_servant.jpeg"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ReportAttachment(SQLModel, table=True):
    """
    Pièce jointe d'un rapport.
    """

    __tablename__ = "report_attachments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    report_id: UUID = Field(foreign_key="reports.id")
    filename: str
    file_url: str
    file_type: str
    file_size: int
    uploaded_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
