"""
Entites du module Responsable — postes de direction du groupe.

Un **poste de responsable** est une nomination permanente (ou semi-permanente)
d'un servant a un role de leadership au sein du groupe. C'est different
des affectations liturgiques (per-evenement).

Cycle de vie d'une nomination :
    Aumonier nomme  →  ACTIVE  →  Aumonier revoque  →  REVOQUEE

Actions de poste :
    Chaque responsable peut creer des actions (decisions, rapports, classements,
    sanctions, collectes, etc.) liees a son poste.

Postes definis :
    CONSEILLER, DELEGUE, VICE_DELEGUE, SECRETAIRE_GENERAL,
    SECRETAIRE_GENERAL_ADJOINT, CENSEUR, CENSEUR_ADJOINT, ECONOME,
    COMMISSAIRE_AUX_COMPTES, CHARGE_LITURGIE, CHARGE_LITURGIE_ADJOINT,
    CEREMONIAIRE, CHARGE_CLASSEMENT_DIMANCHE, CHARGE_CLASSEMENT_SEMAINE,
    INTENDANT, CHARGE_SPORT_CULTURE
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

class PosteResponsable(str, Enum):
    """Les 19 postes de responsable au sein du groupe de servants."""
    CONSEILLER = "CONSEILLER"
    DELEGUE = "DELEGUE"
    VICE_DELEGUE = "VICE_DELEGUE"
    SECRETAIRE_GENERAL = "SECRETAIRE_GENERAL"
    SECRETAIRE_GENERAL_ADJOINT = "SECRETAIRE_GENERAL_ADJOINT"
    SECRETAIRE = "SECRETAIRE"  # Alias pour SECRETAIRE_GENERAL
    SECRETAIRE_ADJOINT = "SECRETAIRE_ADJOINT"  # Alias pour SECRETAIRE_GENERAL_ADJOINT
    CENSEUR = "CENSEUR"
    CENSEUR_ADJOINT = "CENSEUR_ADJOINT"
    ECONOME = "ECONOME"
    COMMISSAIRE_AUX_COMPTES = "COMMISSAIRE_AUX_COMPTES"
    CHARGE_LITURGIE = "CHARGE_LITURGIE"
    CHARGE_LITURGIE_ADJOINT = "CHARGE_LITURGIE_ADJOINT"
    CEREMONIAIRE = "CEREMONIAIRE"
    CHARGE_CLASSEMENT_DIMANCHE = "CHARGE_CLASSEMENT_DIMANCHE"
    CHARGE_CLASSEMENT_SEMAINE = "CHARGE_CLASSEMENT_SEMAINE"
    INTENDANT = "INTENDANT"
    INTENDANT_ADJOINT = "INTENDANT_ADJOINT"
    CHARGE_SPORT_CULTURE = "CHARGE_SPORT_CULTURE"
    CHARGE_SPORT_CULTURE_ADJOINT = "CHARGE_SPORT_CULTURE_ADJOINT"


class NominationStatus(str, Enum):
    """Statut d'une nomination a un poste."""
    ACTIVE = "ACTIVE"
    REVOQUEE = "REVOQUEE"


class ActionCategory(str, Enum):
    """Categories d'actions realisables par les responsables."""
    DECISION = "DECISION"                    # Delegue : decisions du conseil
    RAPPORT = "RAPPORT"                      # Secretariat : PV, rapports
    COMMUNICATION = "COMMUNICATION"          # Secretariat : informations transmises
    DISCIPLINE = "DISCIPLINE"                # Censeur : dossiers disciplinaires
    SANCTION = "SANCTION"                    # Censeur : sanctions prononcees
    CLASSEMENT = "CLASSEMENT"                # Classement : planning des messes
    FORMATION = "FORMATION"                  # Liturgie : formations et enseignements
    RECOLLECTION = "RECOLLECTION"            # Liturgie adj. : recollections mensuelles
    REPETITION = "REPETITION"                # Ceremoniaire : repetitions
    COLLECTE = "COLLECTE"                    # Econome : collectes financieres
    DEPENSE = "DEPENSE"                      # Econome : sorties de fonds
    BILAN_FINANCIER = "BILAN_FINANCIER"      # Commissaires : bilans hebdo/mensuels
    MATERIEL = "MATERIEL"                    # Intendants : gestion du materiel
    LAVAGE = "LAVAGE"                        # Intendants : planning lavage aubes
    ACTIVITE_SPORTIVE = "ACTIVITE_SPORTIVE"  # Sport : activites sportives
    ACTIVITE_CULTURELLE = "ACTIVITE_CULTURELLE"  # Sport : activites culturelles
    AUTRE = "AUTRE"


class ActionStatus(str, Enum):
    """Statut d'une action de responsable."""
    BROUILLON = "BROUILLON"
    PUBLIE = "PUBLIE"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    ANNULE = "ANNULE"


# ═══════════════════════════════════════════════════════════════════════════
#  Table : Nominations aux postes de responsable
# ═══════════════════════════════════════════════════════════════════════════

class Nomination(SQLModel, table=True):
    """
    Nomination d'un servant a un poste de responsable.

    Un servant ne peut occuper qu'un seul poste actif a la fois.
    L'aumonier est le seul a pouvoir nommer et revoquer.
    """
    __tablename__ = "nominations"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)
    poste: PosteResponsable = Field(index=True)
    status: NominationStatus = Field(default=NominationStatus.ACTIVE)
    nominated_by: UUID = Field(foreign_key="users.id")  # Aumonier qui a nomme
    notes: Optional[str] = Field(default=None, max_length=500)
    nominated_at: datetime = Field(default_factory=utc_now)
    revoked_at: Optional[datetime] = Field(default=None)
    revoked_by: Optional[UUID] = Field(default=None, foreign_key="users.id")


# ═══════════════════════════════════════════════════════════════════════════
#  Table : Actions des responsables
# ═══════════════════════════════════════════════════════════════════════════

class PosteAction(SQLModel, table=True):
    """
    Action ou document cree par un responsable dans le cadre de son poste.

    Exemples :
    - Le delegue enregistre une decision du conseil
    - Le secretaire redige un rapport de reunion
    - Le censeur prononce une sanction
    - Le charge du classement publie le planning du dimanche
    - L'econome enregistre une collecte
    - Les commissaires publient un bilan financier
    - Les intendants planifient un lavage d'aubes
    """
    __tablename__ = "poste_actions"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    poste: PosteResponsable = Field(index=True)
    category: ActionCategory = Field(index=True)
    title: str = Field(max_length=300)
    content: Optional[str] = Field(default=None, max_length=5000)
    # Cibles optionnelles
    target_user_id: Optional[UUID] = Field(default=None, foreign_key="users.id")
    target_event_id: Optional[UUID] = Field(default=None, foreign_key="events.id")
    # Champs financiers (econome, commissaires)
    amount: Optional[float] = Field(default=None)
    # Date d'effet de l'action
    action_date: Optional[datetime] = Field(default=None)
    status: ActionStatus = Field(default=ActionStatus.BROUILLON)
    # Donnees supplementaires au format JSON
    extra_data: Optional[str] = Field(default=None, max_length=10000)
    # Auteur
    created_by: UUID = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


# ═══════════════════════════════════════════════════════════════════════════
#  Mapping : categories autorisees par poste
# ═══════════════════════════════════════════════════════════════════════════

POSTE_ALLOWED_CATEGORIES: dict[PosteResponsable, list[ActionCategory]] = {
    PosteResponsable.CONSEILLER: [
        ActionCategory.DECISION, ActionCategory.RAPPORT, ActionCategory.AUTRE,
    ],
    PosteResponsable.DELEGUE: [
        ActionCategory.DECISION, ActionCategory.RAPPORT,
        ActionCategory.COMMUNICATION, ActionCategory.AUTRE,
    ],
    PosteResponsable.VICE_DELEGUE: [
        ActionCategory.DECISION, ActionCategory.RAPPORT,
        ActionCategory.COMMUNICATION, ActionCategory.MATERIEL, ActionCategory.AUTRE,
    ],
    PosteResponsable.SECRETAIRE_GENERAL: [
        ActionCategory.RAPPORT, ActionCategory.COMMUNICATION, ActionCategory.AUTRE,
    ],
    PosteResponsable.SECRETAIRE_GENERAL_ADJOINT: [
        ActionCategory.RAPPORT, ActionCategory.COMMUNICATION, ActionCategory.AUTRE,
    ],
    PosteResponsable.SECRETAIRE: [
        ActionCategory.RAPPORT, ActionCategory.COMMUNICATION, ActionCategory.AUTRE,
    ],
    PosteResponsable.SECRETAIRE_ADJOINT: [
        ActionCategory.RAPPORT, ActionCategory.COMMUNICATION, ActionCategory.AUTRE,
    ],
    PosteResponsable.CENSEUR: [
        ActionCategory.DISCIPLINE, ActionCategory.SANCTION, ActionCategory.AUTRE,
    ],
    PosteResponsable.CENSEUR_ADJOINT: [
        ActionCategory.DISCIPLINE, ActionCategory.SANCTION, ActionCategory.AUTRE,
    ],
    PosteResponsable.ECONOME: [
        ActionCategory.COLLECTE, ActionCategory.DEPENSE, ActionCategory.AUTRE,
    ],
    PosteResponsable.COMMISSAIRE_AUX_COMPTES: [
        ActionCategory.BILAN_FINANCIER, ActionCategory.COLLECTE,
        ActionCategory.DEPENSE, ActionCategory.AUTRE,
    ],
    PosteResponsable.CHARGE_LITURGIE: [
        ActionCategory.FORMATION, ActionCategory.AUTRE,
    ],
    PosteResponsable.CHARGE_LITURGIE_ADJOINT: [
        ActionCategory.FORMATION, ActionCategory.RECOLLECTION, ActionCategory.AUTRE,
    ],
    PosteResponsable.CEREMONIAIRE: [
        ActionCategory.REPETITION, ActionCategory.FORMATION, ActionCategory.AUTRE,
    ],
    PosteResponsable.CHARGE_CLASSEMENT_DIMANCHE: [
        ActionCategory.CLASSEMENT, ActionCategory.AUTRE,
    ],
    PosteResponsable.CHARGE_CLASSEMENT_SEMAINE: [
        ActionCategory.CLASSEMENT, ActionCategory.AUTRE,
    ],
    PosteResponsable.INTENDANT: [
        ActionCategory.MATERIEL, ActionCategory.LAVAGE, ActionCategory.AUTRE,
    ],
    PosteResponsable.INTENDANT_ADJOINT: [
        ActionCategory.MATERIEL, ActionCategory.LAVAGE, ActionCategory.AUTRE,
    ],
    PosteResponsable.CHARGE_SPORT_CULTURE: [
        ActionCategory.ACTIVITE_SPORTIVE, ActionCategory.ACTIVITE_CULTURELLE,
        ActionCategory.AUTRE,
    ],
    PosteResponsable.CHARGE_SPORT_CULTURE_ADJOINT: [
        ActionCategory.ACTIVITE_SPORTIVE, ActionCategory.ACTIVITE_CULTURELLE,
        ActionCategory.AUTRE,
    ],
}


# ═══════════════════════════════════════════════════════════════════════════
#  Mapping : slug URL -> PosteResponsable
# ═══════════════════════════════════════════════════════════════════════════

SLUG_TO_POSTE: dict[str, PosteResponsable] = {
    "conseiller": PosteResponsable.CONSEILLER,
    "delegue": PosteResponsable.DELEGUE,
    "vice-delegue": PosteResponsable.VICE_DELEGUE,
    "secretariat": PosteResponsable.SECRETAIRE_GENERAL,
    "secretariat-adjoint": PosteResponsable.SECRETAIRE_GENERAL_ADJOINT,
    "censeur": PosteResponsable.CENSEUR,
    "censeur-adjoint": PosteResponsable.CENSEUR_ADJOINT,
    "economat": PosteResponsable.ECONOME,
    "finances": PosteResponsable.COMMISSAIRE_AUX_COMPTES,
    "liturgie": PosteResponsable.CHARGE_LITURGIE,
    "liturgie-adjoint": PosteResponsable.CHARGE_LITURGIE_ADJOINT,
    "ceremoniaire": PosteResponsable.CEREMONIAIRE,
    "classement-dimanche": PosteResponsable.CHARGE_CLASSEMENT_DIMANCHE,
    "classement-semaine": PosteResponsable.CHARGE_CLASSEMENT_SEMAINE,
    "intendance": PosteResponsable.INTENDANT,
    "sport-culture": PosteResponsable.CHARGE_SPORT_CULTURE,
}

POSTE_TO_SLUG: dict[PosteResponsable, str] = {v: k for k, v in SLUG_TO_POSTE.items()}


# ═══════════════════════════════════════════════════════════════════════════
#  Missions par poste (descriptions textuelles)
# ═══════════════════════════════════════════════════════════════════════════

POSTE_MISSIONS: dict[PosteResponsable, dict] = {
    PosteResponsable.CONSEILLER: {
        "titre": "Conseiller",
        "description": "Accompagne et conseille le groupe dans ses orientations.",
        "missions": [
            "Accompagne et conseille le groupe",
            "Participe aux decisions du conseil des responsables",
        ],
    },
    PosteResponsable.DELEGUE: {
        "titre": "Delegue",
        "description": "Representant principal du groupe, assure le fonctionnement general.",
        "missions": [
            "Assure la fonctionnalite des reunions ordinaires et des activites du groupe",
            "Organise les conseils des responsables en coordination avec son adjoint et le Secretariat",
            "Met en application les decisions prises par l'aumonier et le conseil des responsables",
            "Assure la politique de gestion du groupe administree par l'Aumonier",
            "Represente le groupe dans les reunions paroissiales (CPJ, Conseil Pastoral Paroissial)",
            "Veille a l'application du reglement interieur",
        ],
    },
    PosteResponsable.VICE_DELEGUE: {
        "titre": "Delegue Adjoint (Vice-Delegue)",
        "description": "Seconde le delegue et veille a la spiritualite et au materiel liturgique.",
        "missions": [
            "Veille a la gestion de la spiritualite du groupe",
            "Coordonne l'entretien du materiel liturgique",
            "Remplit les fonctions du Delegue en cas d'empechement de celui-ci",
        ],
    },
    PosteResponsable.SECRETAIRE_GENERAL: {
        "titre": "Secretaire",
        "description": "Organise les conseils et redige les rapports officiels du groupe.",
        "missions": [
            "Organise les conseils et les reunions en collaboration avec le Delegue et son adjoint",
            "Assiste aux reunions organisees en paroisse",
            "Redige les rapports des conseils des responsables et des reunions",
            "A la capacite de diriger la reunion ordinaire en l'absence du Delegue and de son adjoint",
            "Est le moderateur des conseils and des reunions",
        ],
    },
    PosteResponsable.SECRETAIRE_GENERAL_ADJOINT: {
        "titre": "Secretaire Adjoint",
        "description": "Assiste le SG, assure la promotion du bilinguisme et la transmission des informations.",
        "missions": [
            "Travaille en collaboration avec le Secretaire",
            "Assure la transmission des informations a la portee des servants de messe",
            "Assure la promotion du bilinguisme",
            "Redige les rapports des conseils and des reunions en langue anglaise",
            "Assure l'interim en cas d'absence du Secretaire",
        ],
    },
    PosteResponsable.CENSEUR: {
        "titre": "Censeur",
        "description": "Garant de la discipline et de l'application du reglement interieur.",
        "missions": [
            "Assure la discipline dans le groupe et l'application du reglement interieur",
            "Convoque le conseil de discipline sous la coordination du Delegue et de son adjoint",
            "Prononce les sanctions emanant du conseil des responsables",
        ],
    },
    PosteResponsable.CENSEUR_ADJOINT: {
        "titre": "Censeur Adjoint",
        "description": "Seconde le censeur et veille a l'assiduite des servants.",
        "missions": [
            "Assure l'interim en cas d'absence du Censeur",
            "Veille a l'assiduite des servants aux reunions et messes auxquelles ils sont classes",
        ],
    },
    PosteResponsable.CHARGE_CLASSEMENT_DIMANCHE: {
        "titre": "Responsable chargé du classement",
        "description": "Elabore et communique le classement des messes dominicales et solennites.",
        "missions": [
            "Elabore et communique le classement des differentes celebrations eucharistiques du Dimanche",
            "Elabore et communique le classement des solennites liturgiques",
        ],
    },
    PosteResponsable.CHARGE_CLASSEMENT_SEMAINE: {
        "titre": "Responsable adjoint chargé du classement",
        "description": "Elabore et communique le classement des messes du lundi au samedi.",
        "missions": [
            "Elabore et communique le classement des messes dominicales allant du lundi a samedi",
        ],
    },
    PosteResponsable.CHARGE_LITURGIE: {
        "titre": "Responsable chargé de la spiritualité",
        "description": "Organise les formations et veille aux bons services de la messe.",
        "missions": [
            "Organise et planifie les enseignements et formations pratiques et theoriques des servants",
            "Veille aux bons services de la messe",
        ],
    },
    PosteResponsable.CHARGE_LITURGIE_ADJOINT: {
        "titre": "Charge de la liturgie Adjoint",
        "description": "Met en valeur l'aspect spirituel et organise les recollections mensuelles.",
        "missions": [
            "Met en valeur l'aspect spirituel du groupe",
            "Organise et planifie les recollections mensuelles du groupe",
            "Assure l'interim en cas d'absence de son superieur",
        ],
    },
    PosteResponsable.CEREMONIAIRE: {
        "titre": "Ceremoniaire",
        "description": "Coordonne les repetitions et veille a la bonne organisation liturgique.",
        "missions": [
            "Coordonne les repetitions des enfants de choeur et la formation des ceremoniaires",
            "Est l'ambassadeur du groupe a la commission liturgique",
            "Travaille en collaboration avec l'Aumonier de la commission liturgique",
            "Veille a la bonne organisation liturgique lors des grandes celebrations eucharistiques",
        ],
    },
    PosteResponsable.ECONOME: {
        "titre": "Econome",
        "description": "Collecte et gere les fonds financiers du groupe sous le controle de l'Aumonier.",
        "missions": [
            "Est le collecteur des fonds financiers du groupe",
            "Depose les fonds a la fin de la reunion au tresorier du groupe (l'Aumonier)",
            "Opere des sorties sous le controle et l'accord de l'aumonier et du conseil",
        ],
    },
    PosteResponsable.COMMISSAIRE_AUX_COMPTES: {
        "titre": "Commissaire aux comptes",
        "description": "Controle la tracabilite et la transparence des flux financiers.",
        "missions": [
            "Enregistre les differentes entrees et les depenses du groupe",
            "Elabore le bilan financier hebdomadaire et mensuel",
            "Veille a la tracabilite et la transparence des flux financiers",
        ],
    },
    PosteResponsable.INTENDANT: {
        "titre": "Intendant",
        "description": "Veille a l'entretien des aubes et des objets liturgiques.",
        "missions": [
            "Veille a l'entretien des aubes et des objets liturgiques propres au service de messe",
            "Organise et veille au lavage des aubes et du repassage",
        ],
    },
    PosteResponsable.CHARGE_SPORT_CULTURE: {
        "titre": "Responsable chargé des sports et de divertissement",
        "description": "Organise les activites sportives et culturelles du groupe.",
        "missions": [
            "Organise les activites sportives et culturelles",
            "Assure la responsabilite de la chorale des enfants de choeur",
        ],
    },
}

