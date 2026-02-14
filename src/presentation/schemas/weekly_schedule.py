"""
Schémas Pydantic pour le module Classement Hebdomadaire.

Gère la création, modification et consultation des modèles de classement
des messes en semaine. Chaque créneau peut avoir 0 ou plusieurs servants.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.core.entities.weekly_schedule import MassTime, ScheduleStatus, WeekDay


# ═══════════════════════════════════════════════════════════════════════════
#  Assignation de servants à un créneau
# ═══════════════════════════════════════════════════════════════════════════

class SlotServantCreate(BaseModel):
    """Assignation d'un servant à un créneau."""
    servant_id: Optional[UUID] = None
    servant_name: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator('servant_name')
    @classmethod
    def validate_servant_info(cls, v: Optional[str], info) -> Optional[str]:
        """Valide qu'au moins servant_id ou servant_name est fourni."""
        servant_id = info.data.get('servant_id')
        if not servant_id and not v:
            raise ValueError("Au moins servant_id ou servant_name doit être fourni")
        return v


class SlotServantResponse(BaseModel):
    """Réponse pour un servant assigné à un créneau."""
    id: UUID
    slot_id: UUID
    servant_id: Optional[UUID] = None
    servant_name: Optional[str] = None
    # Infos enrichies du servant
    servant_first_name: Optional[str] = None
    servant_last_name: Optional[str] = None
    notes: Optional[str] = None
    assigned_by: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════
#  Création de créneaux
# ═══════════════════════════════════════════════════════════════════════════

class WeeklyScheduleSlotCreate(BaseModel):
    """Création d'un créneau de messe."""
    day: WeekDay
    mass_time: MassTime
    notes: Optional[str] = Field(None, max_length=500)
    servants: List[SlotServantCreate] = Field(default_factory=list)

    @field_validator('mass_time')
    @classmethod
    def validate_mass_time_for_day(cls, v: MassTime, info) -> MassTime:
        """Valide que l'horaire de messe est disponible pour le jour donné."""
        day = info.data.get('day')
        if day == WeekDay.SAMEDI and v in [MassTime.MIDI, MassTime.SOIR]:
            raise ValueError("Le samedi, seule la messe du matin (6h15) est disponible")
        return v


class WeeklyScheduleTemplateCreate(BaseModel):
    """Création d'un modèle de classement hebdomadaire."""
    title: str = Field(..., max_length=200)
    start_date: datetime
    end_date: datetime
    notes: Optional[str] = Field(None, max_length=1000)
    slots: List[WeeklyScheduleSlotCreate] = Field(default_factory=list)

    @field_validator('end_date')
    @classmethod
    def validate_dates(cls, v: datetime, info) -> datetime:
        """Valide que la date de fin est après la date de début."""
        start_date = info.data.get('start_date')
        if start_date and v <= start_date:
            raise ValueError("La date de fin doit être après la date de début")
        return v


# ═══════════════════════════════════════════════════════════════════════════
#  Modification
# ═══════════════════════════════════════════════════════════════════════════

class WeeklyScheduleSlotUpdate(BaseModel):
    """Modification d'un créneau de messe."""
    notes: Optional[str] = Field(None, max_length=500)


class WeeklyScheduleTemplateUpdate(BaseModel):
    """Modification d'un modèle de classement."""
    title: Optional[str] = Field(None, max_length=200)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: Optional[ScheduleStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)


# ═══════════════════════════════════════════════════════════════════════════
#  Réponses
# ═══════════════════════════════════════════════════════════════════════════

class WeeklyScheduleSlotResponse(BaseModel):
    """Réponse pour un créneau de messe avec ses servants."""
    id: UUID
    template_id: UUID
    day: WeekDay
    mass_time: MassTime
    notes: Optional[str] = None
    servants: List[SlotServantResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WeeklyScheduleTemplateResponse(BaseModel):
    """Réponse pour un modèle de classement avec ses créneaux."""
    id: UUID
    title: str
    start_date: datetime
    end_date: datetime
    status: ScheduleStatus
    notes: Optional[str] = None
    created_by: UUID
    updated_by: Optional[UUID] = None
    # Infos enrichies du créateur
    creator_first_name: Optional[str] = None
    creator_last_name: Optional[str] = None
    # Créneaux
    slots: List[WeeklyScheduleSlotResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WeeklyScheduleTemplateSummary(BaseModel):
    """Résumé d'un modèle de classement (pour les listes)."""
    id: UUID
    title: str
    start_date: datetime
    end_date: datetime
    status: ScheduleStatus
    total_slots: int = 0
    filled_slots: int = 0
    total_servants: int = 0
    created_by: UUID
    creator_first_name: Optional[str] = None
    creator_last_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
