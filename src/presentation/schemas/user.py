"""
Schemas pour le module Users (gestion des profils et administration).
"""

import re
from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from src.core.entities.user import ServantPosition, UserRole

# PaginatedResponse est défini une seule fois dans common.py et
# ré-exporté ici pour la compatibilité descendante de tous les imports existants.
from src.presentation.schemas.common import (  # noqa: F401
    PageLinks,
    PaginatedResponse,
    ResourceLink,
    build_paginated_response,
)


# ── Profil utilisateur (lecture) ─────────────────────────────────────────
class UserProfileResponse(BaseModel):
    """Profil complet d'un utilisateur (lecture)."""

    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    position: Optional[ServantPosition] = None
    # Poste actif issu de la table nominations (PosteResponsable.value).
    # Prend le dessus sur position pour le calcul des permissions côté client.
    active_poste: Optional[str] = None
    is_active: bool
    phone_number: Optional[str] = None
    profile_photo_url: Optional[str] = None
    parent_id: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    links: Optional[Dict[str, ResourceLink]] = Field(
        default=None,
        description="Liens vers les ressources liées (HATEOAS léger)",
    )

    model_config = {"from_attributes": True, "populate_by_name": True}


# ── Mise a jour du profil (self-service) ─────────────────────────────────
class UserProfileUpdate(BaseModel):
    """Champs modifiables par l'utilisateur lui-meme."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != "":
            if not re.match(r"^\+\d{1,3}\d{6,14}$", v):
                raise ValueError(
                    "Le numero de telephone doit etre au format +237xxxxxxxxx"
                )
        return v


# ── Changement de mot de passe ───────────────────────────────────────────
class ChangePasswordRequest(BaseModel):
    """Requete de changement de mot de passe (l'utilisateur doit fournir l'ancien)."""

    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not re.search(r"[a-z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not re.search(r"\d", v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v


# ── Administration des utilisateurs ──────────────────────────────────────
class UserAdminUpdate(BaseModel):
    """Champs modifiables par un administrateur."""

    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    phone_number: Optional[str] = None
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    position: Optional[ServantPosition] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_format(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v != "":
            if not re.match(r"^\+\d{1,3}\d{6,14}$", v):
                raise ValueError(
                    "Le numero de telephone doit etre au format +237xxxxxxxxx"
                )
        return v


class UserAdminResetPassword(BaseModel):
    """Reinitialisation forcee du mot de passe par l'admin."""

    new_password: str = Field(..., min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Le mot de passe doit contenir au moins 8 caracteres")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une majuscule")
        if not re.search(r"[a-z]", v):
            raise ValueError("Le mot de passe doit contenir au moins une minuscule")
        if not re.search(r"\d", v):
            raise ValueError("Le mot de passe doit contenir au moins un chiffre")
        return v


# ── Filtres de listing ───────────────────────────────────────────────────
class UserListFilters(BaseModel):
    """Parametres de filtre et pagination pour la liste des utilisateurs."""

    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    search: Optional[str] = Field(
        None, max_length=100, description="Recherche par nom ou email"
    )
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)
