"""
Schemas Pydantic pour le module Sous-groupes.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

# ═══════════════════════════════════════════════════════════════════════════
#  Sous-groupes
# ═══════════════════════════════════════════════════════════════════════════


class SubGroupCreate(BaseModel):
    """Creer un sous-groupe."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    service_schedule: Optional[str] = Field(None, max_length=500)
    max_members: Optional[int] = Field(None, ge=1)


class SubGroupUpdate(BaseModel):
    """Modifier un sous-groupe."""

    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    service_schedule: Optional[str] = Field(None, max_length=500)
    max_members: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None


class SubGroupMemberAdd(BaseModel):
    """Ajouter un servant a un sous-groupe."""

    user_id: UUID


class SubGroupMemberResponse(BaseModel):
    """Info d'un membre de sous-groupe."""

    id: UUID
    user_id: UUID
    sub_group_id: UUID
    is_active: bool
    joined_at: Optional[datetime] = None
    left_at: Optional[datetime] = None
    # Enrichissement
    user_first_name: Optional[str] = None
    user_last_name: Optional[str] = None
    user_email: Optional[str] = None
    user_phone: Optional[str] = None

    class Config:
        from_attributes = True


class SubGroupResponse(BaseModel):
    """Reponse pour un sous-groupe."""

    id: UUID
    name: str
    description: Optional[str] = None
    service_schedule: Optional[str] = None
    is_active: bool
    max_members: Optional[int] = None
    created_by: UUID
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # Stats
    member_count: int = 0
    members: List[SubGroupMemberResponse] = []

    class Config:
        from_attributes = True
