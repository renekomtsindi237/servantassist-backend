"""
Schémas Pydantic pour le module Classement Dominical.

Gère la création, modification et consultation des modèles de classement
des messes dominicales et solennelles.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.core.entities.sunday_schedule import (
    LiturgicalPosition,
    MassLanguage,
    MassType,
    SundayScheduleStatus,
)

# ═══════════════════════════════════════════════════════════════════════════
#  Assignation de servants à un poste liturgique
# ═══════════════════════════════════════════════════════════════════════════


class SundayMassAssignmentCreate(BaseModel):
    """Assignation d'un servant à un poste liturgique."""

    position: LiturgicalPosition
    servant_id: Optional[UUID] = None
    servant_name: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator("servant_name")
    @classmethod
    def validate_servant_info(cls, v: Optional[str], info) -> Optional[str]:
        """Valide qu'au moins servant_id ou servant_name est fourni."""
        servant_id = info.data.get("servant_id")
        if not servant_id and not v:
            raise ValueError("Au moins servant_id ou servant_name doit être fourni")
        return v


class SundayMassAssignmentResponse(BaseModel):
    """Réponse pour un servant assigné à un poste."""

    id: UUID
    mass_slot_id: UUID
    position: LiturgicalPosition
    servant_id: Optional[UUID] = None
    servant_name: Optional[str] = None
    # Infos enrichies du servant
    servant_first_name: Optional[str] = None
    servant_last_name: Optional[str] = None
    # Présence
    is_present: Optional[bool] = None
    presence_marked_by: Optional[UUID] = None
    presence_marked_by_name: Optional[str] = None
    presence_marked_at: Optional[datetime] = None
    # Traçabilité
    notes: Optional[str] = None
    assigned_by: UUID
    assigned_by_name: Optional[str] = None
    last_modified_by: Optional[UUID] = None
    last_modified_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
#  Création de messes
# ═══════════════════════════════════════════════════════════════════════════


class SundayMassSlotCreate(BaseModel):
    """Création d'une messe."""

    mass_time: str = Field(..., max_length=10, description="Heure (ex: 06h30, 08h30)")
    language: MassLanguage
    notes: Optional[str] = Field(None, max_length=500)
    assignments: List[SundayMassAssignmentCreate] = Field(default_factory=list)


class SundayScheduleTemplateCreate(BaseModel):
    """Création d'un modèle de classement dominical."""

    title: str = Field(..., max_length=200)
    schedule_date: datetime
    mass_type: MassType = MassType.ORDINAIRE
    is_exceptional: bool = False
    notes: Optional[str] = Field(None, max_length=1000)
    masses: List[SundayMassSlotCreate] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
#  Modification
# ═══════════════════════════════════════════════════════════════════════════


class SundayMassSlotUpdate(BaseModel):
    """Modification d'une messe."""

    mass_time: Optional[str] = Field(None, max_length=10)
    language: Optional[MassLanguage] = None
    notes: Optional[str] = Field(None, max_length=500)


class SundayScheduleTemplateUpdate(BaseModel):
    """Modification d'un modèle de classement."""

    title: Optional[str] = Field(None, max_length=200)
    schedule_date: Optional[datetime] = None
    mass_type: Optional[MassType] = None
    is_exceptional: Optional[bool] = None
    status: Optional[SundayScheduleStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)


# ═══════════════════════════════════════════════════════════════════════════
#  Réponses
# ═══════════════════════════════════════════════════════════════════════════


class SundayMassSlotResponse(BaseModel):
    """Réponse pour une messe avec ses assignations."""

    id: UUID
    template_id: UUID
    mass_time: str
    language: MassLanguage
    notes: Optional[str] = None
    assignments: List[SundayMassAssignmentResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SundayScheduleTemplateResponse(BaseModel):
    """Réponse pour un modèle de classement avec ses messes."""

    id: UUID
    title: str
    schedule_date: datetime
    mass_type: MassType
    is_exceptional: bool
    status: SundayScheduleStatus
    notes: Optional[str] = None
    created_by: UUID
    updated_by: Optional[UUID] = None
    # Infos enrichies du créateur
    creator_first_name: Optional[str] = None
    creator_last_name: Optional[str] = None
    # Messes
    masses: List[SundayMassSlotResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SundayScheduleTemplateSummary(BaseModel):
    """Résumé d'un modèle de classement (pour les listes)."""

    id: UUID
    title: str
    schedule_date: datetime
    mass_type: MassType
    is_exceptional: bool
    status: SundayScheduleStatus
    total_masses: int = 0
    total_positions: int = 0
    filled_positions: int = 0
    created_by: UUID
    creator_first_name: Optional[str] = None
    creator_last_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers pour génération automatique
# ═══════════════════════════════════════════════════════════════════════════


class MassTimePreset(BaseModel):
    """Preset d'horaires de messe."""

    time: str
    language: MassLanguage


class GenerateOrdinaryScheduleRequest(BaseModel):
    """Requête pour générer un classement ordinaire."""

    title: str = Field(..., max_length=200)
    schedule_date: datetime
    notes: Optional[str] = Field(None, max_length=1000)


class GenerateExceptionalScheduleRequest(BaseModel):
    """Requête pour générer un classement exceptionnel."""

    title: str = Field(..., max_length=200)
    schedule_date: datetime
    mass_times: List[MassTimePreset]
    notes: Optional[str] = Field(None, max_length=1000)


# ═══════════════════════════════════════════════════════════════════════════
#  Marquage de présence
# ═══════════════════════════════════════════════════════════════════════════


class MarkPresenceRequest(BaseModel):
    """Requête pour marquer la présence d'un servant."""

    is_present: bool = Field(..., description="True=présent, False=absent")


# ═══════════════════════════════════════════════════════════════════════════
#  Historique des modifications
# ═══════════════════════════════════════════════════════════════════════════


class ModificationLogResponse(BaseModel):
    """Réponse pour un log de modification."""

    id: UUID
    template_id: UUID
    mass_slot_id: Optional[UUID] = None
    assignment_id: Optional[UUID] = None
    action: str
    description: str
    modified_by: UUID
    modified_by_name: str
    modified_at: datetime
    ip_address: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None

    class Config:
        from_attributes = True
