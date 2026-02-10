"""
Entites du module Cotisations — contributions financieres des membres.

Le reglement interieur prevoit :
- Cotisation ordinaire : contribution reguliere (mensuelle ou par reunion)
- Cotisation speciale : pour un evenement particulier (camp, recollection, etc.)
- Amende : penalite financiere liee a une infraction
- Autre : contribution volontaire ou exceptionnelle

Cycle de vie d'une cotisation :
    Periode creee par l'Aumonier/Econome → Membres paient → Bilan financier

L'Econome collecte les fonds et les depose aupres de l'Aumonier (tresorier).
Les Commissaires aux comptes enregistrent les entrees/sorties et elaborent
le bilan financier hebdomadaire et mensuel.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel

from src.core.utils import utc_now


# ═══════════════════════════════════════════════════════════════════════════
#  Enums
# ═══════════════════════════════════════════════════════════════════════════

class CotisationType(str, Enum):
    """Types de cotisation prevus par le reglement."""
    ORDINAIRE = "ORDINAIRE"            # Cotisation reguliere
    SPECIALE = "SPECIALE"              # Pour un evenement specifique
    AMENDE = "AMENDE"                  # Penalite financiere
    AUTRE = "AUTRE"                    # Contribution volontaire


class CotisationStatus(str, Enum):
    """Statut de paiement d'un membre pour une periode."""
    EN_ATTENTE = "EN_ATTENTE"          # Pas encore paye
    PAYE = "PAYE"                      # Paiement complet
    PAYE_PARTIELLEMENT = "PAYE_PARTIELLEMENT"  # Paiement partiel
    EXONERE = "EXONERE"                # Dispense de paiement
    EN_RETARD = "EN_RETARD"            # Paiement en retard


class PeriodType(str, Enum):
    """Type de periode de collecte."""
    HEBDOMADAIRE = "HEBDOMADAIRE"      # Chaque semaine (reunion)
    MENSUEL = "MENSUEL"                # Chaque mois
    EVENEMENT = "EVENEMENT"            # Lie a un evenement specifique
    ANNUEL = "ANNUEL"                  # Cotisation annuelle
    PONCTUEL = "PONCTUEL"              # Ponctuel (amende, etc.)


# ═══════════════════════════════════════════════════════════════════════════
#  Table : Periodes de cotisation
# ═══════════════════════════════════════════════════════════════════════════

class CotisationPeriod(SQLModel, table=True):
    """
    Periode de collecte de cotisations.

    L'Aumonier ou l'Econome cree une periode avec un montant attendu,
    puis les paiements des membres sont enregistres.
    """
    __tablename__ = "cotisation_periods"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    title: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    cotisation_type: CotisationType = Field(default=CotisationType.ORDINAIRE, index=True)
    period_type: PeriodType = Field(default=PeriodType.MENSUEL)
    amount_expected: float = Field(ge=0)
    # Periode
    start_date: datetime
    end_date: datetime
    # Evenement associe (optionnel)
    event_id: Optional[UUID] = Field(default=None, foreign_key="events.id")
    # Statut
    is_active: bool = Field(default=True)
    # Metadata
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ═══════════════════════════════════════════════════════════════════════════
#  Table : Paiements individuels
# ═══════════════════════════════════════════════════════════════════════════

class MemberCotisation(SQLModel, table=True):
    """
    Paiement d'un membre pour une periode de cotisation.

    L'Econome enregistre chaque paiement au moment de la collecte.
    Les Commissaires aux comptes verifient les ecritures.
    """
    __tablename__ = "member_cotisations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    period_id: UUID = Field(foreign_key="cotisation_periods.id", index=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    # Montants
    amount_paid: float = Field(default=0, ge=0)
    status: CotisationStatus = Field(default=CotisationStatus.EN_ATTENTE)
    # Details
    payment_date: Optional[datetime] = Field(default=None)
    payment_method: Optional[str] = Field(default=None, max_length=100)
    notes: Optional[str] = Field(default=None, max_length=500)
    # Qui a enregistre le paiement
    recorded_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    # Metadata
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

