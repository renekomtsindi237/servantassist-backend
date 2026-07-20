"""
Entites du module Convocation — convocation formelle des parents.

Le reglement interieur (Art. 48-49) prevoit une convocation des parents pour
trois motifs precis :
- Non-paiement de la cotisation 2 mois consecutifs
- 2 mois d'absence non justifiee
- Tenue incorrecte 3 fois de suite

Apres un mois sans reponse (Art. 49), le servant est suspendu de service
jusqu'a presentation d'un de ses parents.

Avant ce module, le systeme ne faisait que calculer un indicateur
(`needs_parent_convocation`) sans jamais creer d'enregistrement structure ni
suivre de delai de reponse — cette entite comble cet ecart.
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column
from sqlalchemy import String as SAString
from sqlalchemy import types
from sqlmodel import Field, SQLModel

from src.core.utils import utc_now

# Delai de reponse accorde aux parents avant suspension automatique (Art. 49).
CONVOCATION_RESPONSE_DELAY_DAYS = 30


class ConvocationMotif(str, Enum):
    """Motifs de convocation des parents prevus par le reglement (Art. 48)."""

    NON_COTISATION = "NON_COTISATION"  # 2 mois consecutifs sans cotisation
    ABSENCES_REPETEES = "ABSENCES_REPETEES"  # 2 mois d'absence non justifiee
    TENUE_INCORRECTE = "TENUE_INCORRECTE"  # Tenue incorrecte 3 fois de suite
    AUTRE = "AUTRE"


class ConvocationStatus(str, Enum):
    """Statut d'une convocation."""

    EN_ATTENTE = "EN_ATTENTE"  # Convocation envoyee, en attente de reponse
    HONOREE = "HONOREE"  # Un parent s'est presente
    SANS_REPONSE = "SANS_REPONSE"  # Delai de 30 jours ecoule sans reponse (Art. 49)
    ANNULEE = "ANNULEE"  # Convocation annulee (ex. erreur, regularisation entre-temps)


class _ConvocationMotifType(types.TypeDecorator):
    """VARCHAR(32) column that transparently converts to/from ConvocationMotif enum."""

    impl = SAString(32)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, ConvocationMotif):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return ConvocationMotif(value)
            except ValueError:
                return value
        return value


class _ConvocationStatusType(types.TypeDecorator):
    """VARCHAR(16) column that transparently converts to/from ConvocationStatus enum."""

    impl = SAString(16)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, ConvocationStatus):
            return value.value
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            try:
                return ConvocationStatus(value)
            except ValueError:
                return value
        return value


class Convocation(SQLModel, table=True):
    """
    Convocation formelle d'un parent (Art. 48-49 du reglement interieur).
    """

    __tablename__ = "convocations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    servant_id: UUID = Field(foreign_key="users.id", index=True)
    motif: ConvocationMotif = Field(sa_column=Column(_ConvocationMotifType(), nullable=False))
    details: Optional[str] = Field(default=None, max_length=1000)
    convocation_date: datetime = Field(default_factory=utc_now)
    response_deadline: datetime = Field(
        default_factory=lambda: utc_now() + timedelta(days=CONVOCATION_RESPONSE_DELAY_DAYS)
    )
    status: ConvocationStatus = Field(
        default=ConvocationStatus.EN_ATTENTE,
        sa_column=Column(_ConvocationStatusType(), nullable=False, server_default="EN_ATTENTE"),
    )
    convened_by: UUID = Field(foreign_key="users.id")
    honored_at: Optional[datetime] = Field(default=None)
    honored_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    notes: Optional[str] = Field(default=None, max_length=1000)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
