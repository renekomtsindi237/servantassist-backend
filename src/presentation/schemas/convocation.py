"""
Schemas Pydantic pour le module Convocation (Art. 48-49 du reglement interieur).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.core.entities.convocation import ConvocationMotif, ConvocationStatus


class ConvocationCreate(BaseModel):
    """Convoquer manuellement les parents d'un servant."""

    servant_id: UUID
    motif: ConvocationMotif
    details: Optional[str] = Field(None, max_length=1000)


class ConvocationHonor(BaseModel):
    """Marquer une convocation comme honoree (presentation d'un parent, Art. 49)."""

    notes: Optional[str] = Field(None, max_length=1000)


class ConvocationResponse(BaseModel):
    """Reponse pour une convocation."""

    id: UUID
    servant_id: UUID
    motif: ConvocationMotif
    details: Optional[str] = None
    convocation_date: datetime
    response_deadline: datetime
    status: ConvocationStatus
    convened_by: UUID
    honored_at: Optional[datetime] = None
    honored_by: Optional[UUID] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
