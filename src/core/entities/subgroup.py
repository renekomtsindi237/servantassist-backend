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
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now

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
