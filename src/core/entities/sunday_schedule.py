"""
Entité Modèle de Classement Dominical.

Gère les modèles de planification des messes dominicales et solennelles avec :
- Horaires ordinaires et exceptionnels
- Rôles liturgiques spécifiques (Cérémoniaires, Crucifère, Acolytes, Thuriféraire, etc.)
- Support des messes solennelles
- Langues des messes (Ewondo, Français, Anglais)

Horaires ordinaires :
- 06h30 : Messe en Ewondo
- 08h30 : Messe en Français
- 10h00 : Messe en Ewondo
- 11h30 : Messe en Anglais
- 17h00 : Messe en Français

Horaires exceptionnels (variables selon les besoins)
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class MassLanguage(str, Enum):
    """Langues des messes."""
    EWONDO = "EWONDO"
    FRANCAIS = "FRANCAIS"
    ANGLAIS = "ANGLAIS"
    BILINGUE = "BILINGUE"  # Pour les messes mixtes


class MassType(str, Enum):
    """Types de messe."""
    ORDINAIRE = "ORDINAIRE"           # Messe dominicale normale
    SOLENNELLE = "SOLENNELLE"         # Messe solennelle
    PONTIFICALE = "PONTIFICALE"       # Messe pontificale


class LiturgicalPosition(str, Enum):
    """Postes liturgiques pour les messes dominicales."""
    CEREMONIAIRE_1 = "CEREMONIAIRE_1"
    CEREMONIAIRE_2 = "CEREMONIAIRE_2"
    CEREMONIAIRE_3 = "CEREMONIAIRE_3"
    CEREMONIAIRE_4 = "CEREMONIAIRE_4"
    RESPONSABLE = "RESPONSABLE"
    CRUCIFERE = "CRUCIFERE"
    ACOLYTE_1 = "ACOLYTE_1"
    ACOLYTE_2 = "ACOLYTE_2"
    ACOLYTE_3 = "ACOLYTE_3"
    ACOLYTE_4 = "ACOLYTE_4"
    ACOLYTE_5 = "ACOLYTE_5"
    ACOLYTE_6 = "ACOLYTE_6"
    THURIFERAIRE = "THURIFERAIRE"
    PORTE_INSIGNES = "PORTE_INSIGNES"
    CEROFERERAIRE = "CEROFERERAIRE"  # Nombre indéterminé (au moins 1)
    MARMITIER_GARCON_1 = "MARMITIER_GARCON_1"
    MARMITIER_GARCON_2 = "MARMITIER_GARCON_2"
    MARMITIER_GARCON_3 = "MARMITIER_GARCON_3"
    MARMITIER_GARCON_4 = "MARMITIER_GARCON_4"
    MARMITIER_FILLE_1 = "MARMITIER_FILLE_1"
    MARMITIER_FILLE_2 = "MARMITIER_FILLE_2"


# Note: CEROFERERAIRE peut avoir plusieurs servants assignés au même poste
# contrairement aux autres postes qui sont uniques


class SundayScheduleStatus(str, Enum):
    """Statut du modèle de classement dominical."""
    DRAFT = "DRAFT"          # Brouillon
    PUBLISHED = "PUBLISHED"  # Publié et visible par tous
    ARCHIVED = "ARCHIVED"    # Archivé


class SundayScheduleTemplateBase(SQLModel):
    """Champs communs du modèle de classement dominical."""
    title: str = Field(max_length=200, description="Titre du classement (ex: Dimanche du temps ordinaire - 16/02/2026)")
    schedule_date: datetime = Field(description="Date du dimanche ou de la solennité")
    mass_type: MassType = Field(default=MassType.ORDINAIRE)
    is_exceptional: bool = Field(default=False, description="Horaires exceptionnels")
    status: SundayScheduleStatus = Field(default=SundayScheduleStatus.DRAFT)
    watermark_logo_url: str = Field(default="logo_servant.jpeg", max_length=500, description="URL du logo en filigrane")
    notes: Optional[str] = Field(default=None, max_length=1000)


class SundayScheduleTemplate(SundayScheduleTemplateBase, table=True):
    """Table des modèles de classement dominical."""
    __tablename__ = "sunday_schedule_templates"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_by: UUID = Field(foreign_key="users.id")
    updated_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SundayMassSlotBase(SQLModel):
    """Champs communs d'une messe dans le classement dominical."""
    template_id: UUID = Field(foreign_key="sunday_schedule_templates.id", index=True)
    mass_time: str = Field(max_length=10, description="Heure de la messe (ex: 06h30, 08h30, 10h00)")
    language: MassLanguage
    notes: Optional[str] = Field(default=None, max_length=500)


class SundayMassSlot(SundayMassSlotBase, table=True):
    """Table des messes dans un classement dominical."""
    __tablename__ = "sunday_mass_slots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════
#  Table de liaison : servants assignés à un poste liturgique pour une messe
# ══════════════════════════════════════════════════════════════════════════

class SundayMassAssignmentBase(SQLModel):
    """Assignation d'un servant à un poste liturgique pour une messe."""
    mass_slot_id: UUID = Field(foreign_key="sunday_mass_slots.id", index=True)
    position: LiturgicalPosition
    servant_id: Optional[UUID] = Field(default=None, foreign_key="users.id", index=True)
    servant_name: Optional[str] = Field(default=None, max_length=200, description="Nom du servant (si non encore dans le système)")
    is_present: Optional[bool] = Field(default=None, description="Présence constatée (None=pas encore vérifié)")
    notes: Optional[str] = Field(default=None, max_length=500)


class SundayMassAssignment(SundayMassAssignmentBase, table=True):
    """Table de liaison entre messes et servants avec leurs postes."""
    __tablename__ = "sunday_mass_assignments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    assigned_by: UUID = Field(foreign_key="users.id")
    # Traçabilité des modifications
    last_modified_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    presence_marked_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    presence_marked_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════
#  Table d'historique des modifications
# ══════════════════════════════════════════════════════════════════════════

class ModificationAction(str, Enum):
    """Types d'actions de modification."""
    CREATED = "CREATED"                    # Création initiale
    ASSIGNED = "ASSIGNED"                  # Assignation d'un servant
    REASSIGNED = "REASSIGNED"              # Réassignation à un autre servant
    REMOVED = "REMOVED"                    # Retrait d'un servant
    PRESENCE_MARKED = "PRESENCE_MARKED"    # Marquage de présence
    ABSENCE_MARKED = "ABSENCE_MARKED"      # Marquage d'absence
    UPDATED = "UPDATED"                    # Autre modification


class SundayScheduleModificationLog(SQLModel, table=True):
    """Historique de toutes les modifications sur les classements dominicaux."""
    __tablename__ = "sunday_schedule_modification_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    template_id: UUID = Field(foreign_key="sunday_schedule_templates.id", index=True)
    mass_slot_id: Optional[UUID] = Field(default=None, foreign_key="sunday_mass_slots.id")
    assignment_id: Optional[UUID] = Field(default=None, foreign_key="sunday_mass_assignments.id")
    
    action: ModificationAction
    description: str = Field(max_length=500, description="Description de la modification")
    
    # Qui a fait la modification
    modified_by: UUID = Field(foreign_key="users.id", index=True)
    modified_by_name: str = Field(max_length=200, description="Nom complet de la personne")
    
    # Quand et où
    modified_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    
    # Données avant/après (JSON)
    old_value: Optional[str] = Field(default=None, max_length=1000)
    new_value: Optional[str] = Field(default=None, max_length=1000)


# ══════════════════════════════════════════════════════════════════════════
#  Horaires prédéfinis
# ══════════════════════════════════════════════════════════════════════════

ORDINARY_MASS_TIMES = [
    {"time": "06h30", "language": MassLanguage.EWONDO},
    {"time": "08h30", "language": MassLanguage.FRANCAIS},
    {"time": "10h00", "language": MassLanguage.EWONDO},
    {"time": "11h30", "language": MassLanguage.ANGLAIS},
    {"time": "17h00", "language": MassLanguage.FRANCAIS},
]

EXCEPTIONAL_MASS_TIMES = [
    {"time": "06h30", "language": MassLanguage.EWONDO},
    {"time": "09h00", "language": MassLanguage.BILINGUE},
    {"time": "11h30", "language": MassLanguage.ANGLAIS},
    {"time": "17h00", "language": MassLanguage.FRANCAIS},
]

# Postes liturgiques par type de messe
ORDINARY_POSITIONS = [
    LiturgicalPosition.CEREMONIAIRE_1,
    LiturgicalPosition.CEREMONIAIRE_2,
    LiturgicalPosition.CEREMONIAIRE_3,
    LiturgicalPosition.CEREMONIAIRE_4,
    LiturgicalPosition.RESPONSABLE,
    LiturgicalPosition.CRUCIFERE,
    LiturgicalPosition.ACOLYTE_1,
    LiturgicalPosition.ACOLYTE_2,
    LiturgicalPosition.ACOLYTE_3,
    LiturgicalPosition.ACOLYTE_4,
    LiturgicalPosition.ACOLYTE_5,
    LiturgicalPosition.ACOLYTE_6,
    LiturgicalPosition.THURIFERAIRE,
    LiturgicalPosition.PORTE_INSIGNES,
    LiturgicalPosition.CEROFERERAIRE,  # Toujours présent dans les messes dominicales
    LiturgicalPosition.MARMITIER_GARCON_1,
    LiturgicalPosition.MARMITIER_GARCON_2,
    LiturgicalPosition.MARMITIER_GARCON_3,
    LiturgicalPosition.MARMITIER_GARCON_4,
    LiturgicalPosition.MARMITIER_FILLE_1,
    LiturgicalPosition.MARMITIER_FILLE_2,
]

SOLEMN_POSITIONS = ORDINARY_POSITIONS  # Même postes pour les messes solennelles
