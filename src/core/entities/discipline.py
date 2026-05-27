"""
Entites du module Discipline — Conseil de discipline & Sanctions.

Implemente le reglement interieur du groupe des enfants de choeur :
- Avertissement verbal (1ere faute)
- Avertissement ecrit (2eme faute)
- Suspension temporaire (faute grave ou recidive)
- Exclusion definitive (faute tres grave)

Workflow d'un dossier disciplinaire :
    SIGNALE → CONVOQUE → EN_AUDIENCE → VERDICT_RENDU → EXECUTE
                                       → CLASSE (sans suite)
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


class SanctionType(str, Enum):
    """Types de sanctions prevus par le reglement interieur."""

    AUCUNE = "AUCUNE"  # Classe sans suite
    AVERTISSEMENT_VERBAL = "AVERTISSEMENT_VERBAL"  # 1er manquement
    AVERTISSEMENT_ECRIT = "AVERTISSEMENT_ECRIT"  # 2eme manquement
    SUSPENSION_TEMPORAIRE = "SUSPENSION_TEMPORAIRE"  # Manquement grave / recidive
    EXCLUSION_DEFINITIVE = "EXCLUSION_DEFINITIVE"  # Faute tres grave
    LETTRE_EXCUSE = "LETTRE_EXCUSE"  # Article 44
    CORVEE_INTENSIVE = "CORVEE_INTENSIVE"  # Article 43
    RECYCLAGE_SERVICE = "RECYCLAGE_SERVICE"  # Article 46


class SanctionSeverity(str, Enum):
    """Gravite de la faute."""

    MINEUR = "MINEUR"  # Retard, oubli materiel
    MOYEN = "MOYEN"  # Absence non justifiee, manque de discipline
    GRAVE = "GRAVE"  # Insubordination, vol, violence verbale
    TRES_GRAVE = "TRES_GRAVE"  # Violence physique, comportement immoral


class DisciplineCaseStatus(str, Enum):
    """Statut d'un dossier disciplinaire."""

    SIGNALE = "SIGNALE"  # Faute signalee
    CONVOQUE = "CONVOQUE"  # Servant convoque au conseil de discipline
    EN_AUDIENCE = "EN_AUDIENCE"  # Audience en cours
    VERDICT_RENDU = "VERDICT_RENDU"  # Verdict prononce
    EXECUTE = "EXECUTE"  # Sanction appliquee
    CLASSE = "CLASSE"  # Classe sans suite


class OffenseCategory(str, Enum):
    """Categories de fautes prevues par le reglement interieur."""

    ABSENCE_NON_JUSTIFIEE = "ABSENCE_NON_JUSTIFIEE"
    RETARD_REPETE = "RETARD_REPETE"
    INSUBORDINATION = "INSUBORDINATION"
    MANQUE_DE_RESPECT = "MANQUE_DE_RESPECT"
    NON_RESPECT_TENUE = "NON_RESPECT_TENUE"
    UTILISATION_TELEPHONE = "UTILISATION_TELEPHONE"
    BAGARRE_VIOLENCE = "BAGARRE_VIOLENCE"
    VOL = "VOL"
    COMPORTEMENT_IMMORAL = "COMPORTEMENT_IMMORAL"
    NON_PAIEMENT_COTISATION = "NON_PAIEMENT_COTISATION"
    NEGLIGENCE_MATERIEL = "NEGLIGENCE_MATERIEL"
    BAVARDAGE_PENDANT_SERVICE = "BAVARDAGE_PENDANT_SERVICE"
    RELATION_AMOUREUSE = "RELATION_AMOUREUSE"
    CONSOMMATION_STUPEFIANTS = "CONSOMMATION_STUPEFIANTS"
    AGRESSION_PHYSIQUE_RESPONSABLE = "AGRESSION_PHYSIQUE_RESPONSABLE"
    MENSONGE = "MENSONGE"
    INFLUENCE_PARENTALE_INAPPROPRIEE = "INFLUENCE_PARENTALE_INAPPROPRIEE"
    AUTRE = "AUTRE"


# ═══════════════════════════════════════════════════════════════════════════
#  Table : Dossiers disciplinaires
# ═══════════════════════════════════════════════════════════════════════════


class DisciplineCase(SQLModel, table=True):
    """
    Dossier disciplinaire ouvert a l'encontre d'un servant.

    Cycle de vie :
        Le censeur ouvre un dossier → Convocation → Audience devant le conseil
        → Verdict rendu → Sanction executee (ou classement sans suite).

    Le conseil de discipline est compose du Delegue, du Vice-Delegue, du Censeur
    et du Censeur adjoint, sous la supervision de l'Aumonier.
    """

    __tablename__ = "discipline_cases"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Qui est concerne
    accused_user_id: UUID = Field(foreign_key="users.id", index=True)
    # Qui a signale la faute
    reported_by: UUID = Field(foreign_key="users.id")
    # Description de la faute
    offense_category: OffenseCategory = Field(index=True)
    offense_description: str = Field(max_length=2000)
    offense_date: datetime = Field(default_factory=utc_now)
    severity: SanctionSeverity = Field(default=SanctionSeverity.MINEUR)
    # Statut du dossier
    status: DisciplineCaseStatus = Field(
        default=DisciplineCaseStatus.SIGNALE, index=True
    )
    # Convocation
    convocation_date: Optional[datetime] = Field(default=None)
    convocation_notes: Optional[str] = Field(default=None, max_length=1000)
    # Verdict
    sanction_type: SanctionType = Field(default=SanctionType.AUCUNE)
    verdict_notes: Optional[str] = Field(default=None, max_length=2000)
    verdict_date: Optional[datetime] = Field(default=None)
    verdict_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    # Suspension
    suspension_start: Optional[datetime] = Field(default=None)
    suspension_end: Optional[datetime] = Field(default=None)
    suspension_days: Optional[int] = Field(default=None)
    # Metadata
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ═══════════════════════════════════════════════════════════════════════════
#  Regles de gravite et sanctions recommandees
# ═══════════════════════════════════════════════════════════════════════════

OFFENSE_DEFAULT_SEVERITY: dict[OffenseCategory, SanctionSeverity] = {
    OffenseCategory.ABSENCE_NON_JUSTIFIEE: SanctionSeverity.MOYEN,
    OffenseCategory.RETARD_REPETE: SanctionSeverity.MINEUR,
    OffenseCategory.INSUBORDINATION: SanctionSeverity.GRAVE,
    OffenseCategory.MANQUE_DE_RESPECT: SanctionSeverity.MOYEN,
    OffenseCategory.NON_RESPECT_TENUE: SanctionSeverity.MINEUR,
    OffenseCategory.UTILISATION_TELEPHONE: SanctionSeverity.MINEUR,
    OffenseCategory.BAGARRE_VIOLENCE: SanctionSeverity.TRES_GRAVE,
    OffenseCategory.VOL: SanctionSeverity.TRES_GRAVE,
    OffenseCategory.COMPORTEMENT_IMMORAL: SanctionSeverity.TRES_GRAVE,
    OffenseCategory.NON_PAIEMENT_COTISATION: SanctionSeverity.MINEUR,
    OffenseCategory.NEGLIGENCE_MATERIEL: SanctionSeverity.MOYEN,
    OffenseCategory.BAVARDAGE_PENDANT_SERVICE: SanctionSeverity.MINEUR,
    OffenseCategory.RELATION_AMOUREUSE: SanctionSeverity.TRES_GRAVE,
    OffenseCategory.CONSOMMATION_STUPEFIANTS: SanctionSeverity.TRES_GRAVE,
    OffenseCategory.AGRESSION_PHYSIQUE_RESPONSABLE: SanctionSeverity.TRES_GRAVE,
    OffenseCategory.MENSONGE: SanctionSeverity.MOYEN,
    OffenseCategory.INFLUENCE_PARENTALE_INAPPROPRIEE: SanctionSeverity.MINEUR,
    OffenseCategory.AUTRE: SanctionSeverity.MINEUR,
}

SEVERITY_RECOMMENDED_SANCTION: dict[SanctionSeverity, SanctionType] = {
    SanctionSeverity.MINEUR: SanctionType.AVERTISSEMENT_VERBAL,
    SanctionSeverity.MOYEN: SanctionType.AVERTISSEMENT_ECRIT,
    SanctionSeverity.GRAVE: SanctionType.SUSPENSION_TEMPORAIRE,
    SanctionSeverity.TRES_GRAVE: SanctionType.EXCLUSION_DEFINITIVE,
}
