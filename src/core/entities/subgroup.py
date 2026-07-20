"""
Entites du module Sous-groupes — organisation interne.

Le reglement interieur prevoit l'organisation des servants en sous-groupes :
- Faciliter la gestion des classements
- Organiser les tours de service
- Repartir les responsabilites

L'Aumonier et le Delegue gerent la creation des sous-groupes.
Le Charge du classement utilise les sous-groupes pour planifier les tours.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy import String as SAString
from sqlalchemy import types
from sqlmodel import Field, SQLModel

from src.core.utils import utc_now

# ═══════════════════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════════════════


class SubGroupCategory(str, Enum):
    """
    Categorie structuree d'un sous-groupe (Art. 26, 33-34 du reglement).

    - ASPIRANTS : servants de moins de 12 ans et nouveaux servants
    - CONFIRMES : servants de 12 ans et plus
    - AINES : servants aptes au service, moyenne >= 14/20 (max 7 membres,
      eligibles a la fonction de responsable)
    - CHORALE : organe ouvert a tout servant (Art. 33-34)
    - AUTRE : sous-groupe libre (ex. equipes de service)
    """

    ASPIRANTS = "ASPIRANTS"
    CONFIRMES = "CONFIRMES"
    AINES = "AINES"
    CHORALE = "CHORALE"
    AUTRE = "AUTRE"


# Nombre maximum de membres du sous-groupe des Aines (Art. 26.4) — regle
# metier dediee, independante du max_members generique configurable.
AINES_MAX_MEMBERS = 7


class _SubGroupCategoryType(types.TypeDecorator):
    """VARCHAR(32) column that transparently converts to/from SubGroupCategory enum."""

    impl = SAString(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, SubGroupCategory):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return SubGroupCategory(value)
            except ValueError:
                return value
        return value


# ═══════════════════════════════════════════════════════════════════════════
#  Table : Sous-groupes
# ═══════════════════════════════════════════════════════════════════════════


class SubGroup(SQLModel, table=True):
    """
    Sous-groupe au sein du groupe des enfants de choeur.

    Exemples : Groupe A, Groupe B, Equipe 1, Equipe 2, etc.
    Utilise pour organiser les tours de service aux messes.
    """

    __tablename__ = "sub_groups"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    description: Optional[str] = Field(default=None, max_length=500)
    # Tour de service (ex: "Dimanche 1er et 3eme du mois")
    service_schedule: Optional[str] = Field(default=None, max_length=500)
    is_active: bool = Field(default=True)
    max_members: Optional[int] = Field(default=None, ge=1)
    category: SubGroupCategory = Field(
        default=SubGroupCategory.AUTRE,
        sa_column=Column(_SubGroupCategoryType(), nullable=False, server_default="AUTRE"),
    )
    # Metadata
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ═══════════════════════════════════════════════════════════════════════════
#  Table de liaison : Membres des sous-groupes
# ═══════════════════════════════════════════════════════════════════════════


class SubGroupMember(SQLModel, table=True):
    """
    Appartenance d'un servant a un sous-groupe.

    Un servant peut appartenir a un seul sous-groupe actif a la fois.
    """

    __tablename__ = "sub_group_members"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    sub_group_id: UUID = Field(foreign_key="sub_groups.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    is_active: bool = Field(default=True)
    # Qui a ajoute ce membre
    added_by: UUID = Field(foreign_key="users.id")
    joined_at: datetime = Field(default_factory=utc_now)
    left_at: Optional[datetime] = Field(default=None)
