"""
Schémas Pydantic pour le module Classements.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.classement import ClassementStatus, ClassementType


class PosteRowSchema(BaseModel):
    label: str
    col1: str = ""
    col2: str = ""


class ClassementCreate(BaseModel):
    type: ClassementType
    date: datetime
    heure: str = Field(..., max_length=10)
    lieu: str = Field(..., max_length=200)
    solennite: Optional[str] = Field(None, max_length=200)
    couleur_liturgique: Optional[str] = Field(None, max_length=20)
    semaine: Optional[int] = None
    annee: Optional[int] = None
    horaire: Optional[str] = Field(None, max_length=10)
    type_extra: Optional[str] = Field(None, max_length=30)
    participants: Optional[str] = None
    postes: List[PosteRowSchema] = Field(default_factory=list)


class ClassementUpdate(BaseModel):
    date: Optional[datetime] = None
    heure: Optional[str] = Field(None, max_length=10)
    lieu: Optional[str] = Field(None, max_length=200)
    solennite: Optional[str] = Field(None, max_length=200)
    couleur_liturgique: Optional[str] = Field(None, max_length=20)
    semaine: Optional[int] = None
    annee: Optional[int] = None
    horaire: Optional[str] = Field(None, max_length=10)
    type_extra: Optional[str] = Field(None, max_length=30)
    participants: Optional[str] = None
    postes: Optional[List[PosteRowSchema]] = None


class ClassementResponse(BaseModel):
    id: UUID
    type: ClassementType
    status: ClassementStatus
    date: datetime
    heure: str
    lieu: str
    solennite: Optional[str]
    couleur_liturgique: Optional[str]
    semaine: Optional[int]
    annee: Optional[int]
    horaire: Optional[str]
    type_extra: Optional[str]
    participants: Optional[str]
    postes: List[Dict[str, Any]]
    created_by: UUID
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClassementListResponse(BaseModel):
    items: List[ClassementResponse]
    total: int
