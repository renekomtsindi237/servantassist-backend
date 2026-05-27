"""
Schémas pour le dossier unique d'un servant (agrégation multi-modules).
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class DossierAttendanceStat(BaseModel):
    total_sessions: int
    present_count: int
    absent_count: int
    late_count: int
    excused_count: int
    attendance_rate: float


class DossierNomination(BaseModel):
    id: UUID
    poste: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True


class DossierCotisation(BaseModel):
    id: UUID
    period_label: str
    amount_due: float
    amount_paid: float
    status: str
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class DossierTraining(BaseModel):
    id: UUID
    title: str
    training_date: Optional[datetime]
    status: str

    class Config:
        from_attributes = True


class DossierDiscipline(BaseModel):
    id: UUID
    incident_type: str
    incident_date: Optional[datetime]
    sanction: Optional[str]
    status: str

    class Config:
        from_attributes = True


class DossierSportCulture(BaseModel):
    id: UUID
    event_title: str
    event_date: Optional[datetime]
    role: Optional[str]
    result: Optional[str]

    class Config:
        from_attributes = True


class DossierUserInfo(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    email: str
    role: str
    phone_number: Optional[str]
    profile_photo_url: Optional[str]
    is_active: bool
    birth_date: Optional[datetime]
    baptism_date: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class DossierResponse(BaseModel):
    user: DossierUserInfo
    attendance_stats: DossierAttendanceStat
    nominations: List[DossierNomination]
    cotisations: List[DossierCotisation]
    trainings: List[DossierTraining]
    discipline_cases: List[DossierDiscipline]
    sport_culture: List[DossierSportCulture]
    generated_at: datetime
