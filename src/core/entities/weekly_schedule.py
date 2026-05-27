"""
Entité Modèle de Classement Hebdomadaire.

Gère les modèles de planification des messes en semaine avec les horaires fixes :
- Matin : 6h15 (Lundi à Samedi)
- Midi : 12h00 (Lundi à Vendredi)
- Soir : 18h00 (Lundi à Vendredi)

Chaque créneau peut avoir 0 ou plusieurs servants assignés.
"""
from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String
from sqlmodel import Field, SQLModel


class MassTime(str, Enum):
    """Horaires des messes en semaine."""

    MATIN = "MATIN"  # 6h15
    MIDI = "MIDI"  # 12h00
    SOIR = "SOIR"  # 18h00


class WeekDay(str, Enum):
    """Jours de la semaine."""

    LUNDI = "LUNDI"
    MARDI = "MARDI"
    MERCREDI = "MERCREDI"
    JEUDI = "JEUDI"
    VENDREDI = "VENDREDI"
    SAMEDI = "SAMEDI"


class ScheduleStatus(str, Enum):
    """Statut du modèle de classement."""

    DRAFT = "DRAFT"  # Brouillon
    PUBLISHED = "PUBLISHED"  # Publié et visible par tous
    ARCHIVED = "ARCHIVED"  # Archivé


class WeeklyScheduleTemplateBase(SQLModel):
    """Champs communs du modèle de classement hebdomadaire."""

    title: str = Field(
        max_length=200,
        description="Titre du classement (ex: Semaine du 07/02 au 14/02/2026)",
    )
    start_date: datetime = Field(description="Date de début de la semaine")
    end_date: datetime = Field(description="Date de fin de la semaine")
    status: ScheduleStatus = Field(default=ScheduleStatus.DRAFT)
    watermark_logo_url: str = Field(
        default="logo_servant.jpeg",
        max_length=500,
        description="URL du logo en filigrane",
    )
    notes: Optional[str] = Field(default=None, max_length=1000)


class WeeklyScheduleTemplate(WeeklyScheduleTemplateBase, table=True):
    """Table des modèles de classement hebdomadaire."""

    __tablename__ = "weekly_schedule_templates"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    status: ScheduleStatus = Field(
        default=ScheduleStatus.DRAFT,
        sa_column=Column(String(20), nullable=False, server_default="DRAFT"),
    )
    created_by: UUID = Field(foreign_key="users.id")
    updated_by: Optional[UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WeeklyScheduleSlotBase(SQLModel):
    """Champs communs d'un créneau de messe dans le classement."""

    template_id: UUID = Field(
    foreign_key="weekly_schedule_templates.id",
     index=True)
    day: WeekDay = Field(sa_column=Column(String(20), nullable=False))
    mass_time: MassTime = Field(sa_column=Column(String(10), nullable=False))
    notes: Optional[str] = Field(default=None, max_length=500)


class WeeklyScheduleSlot(WeeklyScheduleSlotBase, table=True):
    """Table des créneaux de messe dans un classement hebdomadaire."""

    __tablename__ = "weekly_schedule_slots"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════
#  Table de liaison : servants assignés à un créneau (many-to-many)
# ══════════════════════════════════════════════════════════════════════════


class SlotServantAssignmentBase(SQLModel):
    """Assignation d'un servant à un créneau."""

    slot_id: UUID = Field(foreign_key="weekly_schedule_slots.id", index=True)
    servant_id: Optional[UUID] = Field(
    default=None, foreign_key="users.id", index=True)
    servant_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Nom du servant (si non encore dans le système)",
    )
    notes: Optional[str] = Field(default=None, max_length=500)


class SlotServantAssignment(SlotServantAssignmentBase, table=True):
    """Table de liaison entre créneaux et servants."""

    __tablename__ = "slot_servant_assignments"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    assigned_by: UUID = Field(foreign_key="users.id")
    # Traçabilité des modifications
    last_modified_by: Optional[UUID] = Field(
        default=None, foreign_key="users.id")
    presence_marked_by: Optional[UUID] = Field(
        default=None, foreign_key="users.id")
    presence_marked_at: Optional[datetime] = Field(default=None)
    is_present: Optional[bool] = Field(
    default=None, description="Présence constatée")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ══════════════════════════════════════════════════════════════════════════
#  Table d'historique des modifications (classement hebdomadaire)
# ══════════════════════════════════════════════════════════════════════════


class WeeklyModificationAction(str, Enum):
    """Types d'actions de modification."""

    CREATED = "CREATED"
    ASSIGNED = "ASSIGNED"
    REASSIGNED = "REASSIGNED"
    REMOVED = "REMOVED"
    PRESENCE_MARKED = "PRESENCE_MARKED"
    ABSENCE_MARKED = "ABSENCE_MARKED"
    UPDATED = "UPDATED"


class WeeklyScheduleModificationLog(SQLModel, table=True):
    """Historique de toutes les modifications sur les classements hebdomadaires."""

    __tablename__ = "weekly_schedule_modification_logs"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    template_id: UUID = Field(
    foreign_key="weekly_schedule_templates.id",
     index=True)
    slot_id: Optional[UUID] = Field(
    default=None, foreign_key="weekly_schedule_slots.id")
    assignment_id: Optional[UUID] = Field(
    default=None, foreign_key="slot_servant_assignments.id")

    action: WeeklyModificationAction = Field(sa_column=Column(String(30), nullable=False))
    description: str = Field(max_length=500,
     description="Description de la modification")

    # Qui a fait la modification
    modified_by: UUID = Field(foreign_key="users.id", index=True)
    modified_by_name: str = Field(max_length=200,
     description="Nom complet de la personne")

    # Quand et où
    modified_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)

    # Données avant/après (JSON)
    old_value: Optional[str] = Field(default=None, max_length=1000)
    new_value: Optional[str] = Field(default=None, max_length=1000)
