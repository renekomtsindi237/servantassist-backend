"""
Schémas Pydantic pour le module SECRETAIRE - Rapports.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.report import ReportStatus, ReportType


# ── Schémas de création ──────────────────────────────────────────────────
class ReportCreate(BaseModel):
    """Schéma pour créer un rapport."""

    type: ReportType
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    report_date: datetime
    location: str = Field(..., min_length=1, max_length=200)
    participants: List[str] = Field(default_factory=list)
    decisions: Optional[str] = None
    action_items: Optional[str] = None


class ReportUpdate(BaseModel):
    """Schéma pour modifier un rapport."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    report_date: Optional[datetime] = None
    location: Optional[str] = Field(None, min_length=1, max_length=200)
    participants: Optional[list[str]] = None
    decisions: Optional[str] = None
    action_items: Optional[str] = None


class ReportPublish(BaseModel):
    """Schéma pour publier un rapport."""

    publish: bool = True


# ── Schémas de réponse ───────────────────────────────────────────────────
class ReportResponse(BaseModel):
    """Schéma de réponse pour un rapport."""

    id: UUID
    type: ReportType
    title: str
    content: str
    report_date: datetime
    location: str
    participants: List[str]
    decisions: Optional[str]
    action_items: Optional[str]
    status: ReportStatus
    created_by: UUID
    published_at: Optional[datetime]
    watermark_logo: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Schéma de réponse pour une liste de rapports."""

    items: List[ReportResponse]
    total: int
    skip: int
    limit: int


# ── Schémas pour pièces jointes ──────────────────────────────────────────
class AttachmentCreate(BaseModel):
    """Schéma pour ajouter une pièce jointe."""

    filename: str = Field(..., min_length=1, max_length=255)
    file_url: str = Field(..., min_length=1)
    file_type: str = Field(..., min_length=1, max_length=100)
    file_size: int = Field(..., gt=0)


class AttachmentResponse(BaseModel):
    """Schéma de réponse pour une pièce jointe."""

    id: UUID
    report_id: UUID
    filename: str
    file_url: str
    file_type: str
    file_size: int
    uploaded_by: UUID
    created_at: datetime

    class Config:
        from_attributes = True


# ── Schémas pour export ──────────────────────────────────────────────────
class ReportExportRequest(BaseModel):
    """Schéma pour demander l'export d'un rapport."""

    format: str = Field(default="pdf", pattern="^(pdf|docx)$")
    include_attachments: bool = False


class ReportExportResponse(BaseModel):
    """Schéma de réponse pour l'export d'un rapport."""

    report_id: UUID
    export_url: str
    format: str
    generated_at: datetime
    expires_at: datetime
