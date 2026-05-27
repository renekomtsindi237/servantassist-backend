"""
Schemas Pydantic pour le module Discipline.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.discipline import (
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
    SanctionType,
)

# ═══════════════════════════════════════════════════════════════════════════
#  Dossiers disciplinaires
# ═══════════════════════════════════════════════════════════════════════════


class DisciplineCaseCreate(BaseModel):
    """Ouvrir un dossier disciplinaire."""

    accused_user_id: UUID
    offense_category: OffenseCategory
    offense_description: str = Field(..., min_length=10, max_length=2000)
    offense_date: Optional[datetime] = None
    severity: Optional[SanctionSeverity] = None  # Auto-determine si absent


class DisciplineConvocation(BaseModel):
    """Convoquer un servant au conseil de discipline."""

    convocation_date: datetime
    convocation_notes: Optional[str] = Field(None, max_length=1000)


class DisciplineVerdict(BaseModel):
    """Rendre un verdict dans un dossier disciplinaire."""

    sanction_type: SanctionType
    verdict_notes: Optional[str] = Field(None, max_length=2000)
    suspension_days: Optional[int] = Field(None, ge=1, le=365)


class DisciplineCaseUpdate(BaseModel):
    """Mise a jour d'un dossier (notes, gravite)."""

    offense_description: Optional[str] = Field(None, max_length=2000)
    severity: Optional[SanctionSeverity] = None
    status: Optional[DisciplineCaseStatus] = None


class DisciplineCaseResponse(BaseModel):
    """Reponse complete d'un dossier disciplinaire."""

    id: UUID
    accused_user_id: UUID
    reported_by: UUID
    offense_category: OffenseCategory
    offense_description: str
    offense_date: Optional[datetime] = None
    severity: SanctionSeverity
    status: DisciplineCaseStatus
    # Convocation
    convocation_date: Optional[datetime] = None
    convocation_notes: Optional[str] = None
    # Verdict
    sanction_type: SanctionType
    verdict_notes: Optional[str] = None
    verdict_date: Optional[datetime] = None
    verdict_by: Optional[UUID] = None
    # Suspension
    suspension_start: Optional[datetime] = None
    suspension_end: Optional[datetime] = None
    suspension_days: Optional[int] = None
    # Enrichissement
    accused_first_name: Optional[str] = None
    accused_last_name: Optional[str] = None
    reporter_first_name: Optional[str] = None
    reporter_last_name: Optional[str] = None
    verdict_by_name: Optional[str] = None
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DisciplineStatsResponse(BaseModel):
    """Statistiques disciplinaires d'un servant."""

    user_id: UUID
    total_cases: int = 0
    avertissements_verbaux: int = 0
    avertissements_ecrits: int = 0
    suspensions: int = 0
    cases_en_cours: int = 0
