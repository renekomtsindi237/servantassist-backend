"""
Événements de domaine ServantAssist.

Chaque événement documente quelque chose qui s'est passé dans le système.
Les handlers (notification, audit, etc.) réagissent à ces événements sans
modifier les services émetteurs.
"""

from dataclasses import dataclass, field
from typing import Optional
from uuid import UUID

from .base import DomainEvent

# ── Utilisateurs ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """Un nouvel utilisateur s'est inscrit ou a été créé par l'admin."""

    user_id: UUID = field(default=None)
    email: Optional[str] = field(default=None)
    first_name: Optional[str] = field(default=None)
    role: str = field(default="")
    created_by_admin: bool = field(default=False)


@dataclass(frozen=True)
class UserInvited(DomainEvent):
    """Un code d'invitation a été envoyé."""

    invitation_id: UUID = field(default=None)
    created_by_id: UUID = field(default=None)
    email: Optional[str] = field(default=None)
    phone_number: Optional[str] = field(default=None)
    role: str = field(default="")


@dataclass(frozen=True)
class PasswordReset(DomainEvent):
    """Un mot de passe a été réinitialisé (par l'admin)."""

    user_id: UUID = field(default=None)
    reset_by_admin_id: Optional[UUID] = field(default=None)
    email: Optional[str] = field(default=None)
    first_name: Optional[str] = field(default=None)


@dataclass(frozen=True)
class UserDeactivated(DomainEvent):
    """Un compte utilisateur a été désactivé."""

    user_id: UUID = field(default=None)
    deactivated_by_id: UUID = field(default=None)


@dataclass(frozen=True)
class UserActivated(DomainEvent):
    """Un compte utilisateur a été réactivé."""

    user_id: UUID = field(default=None)


@dataclass(frozen=True)
class UserDeleted(DomainEvent):
    """Un compte utilisateur a été supprimé."""

    user_id: UUID = field(default=None)
    deleted_by_id: UUID = field(default=None)


# ── Discipline ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class DisciplineCaseOpened(DomainEvent):
    """Un dossier disciplinaire a été ouvert."""

    case_id: UUID = field(default=None)
    accused_user_id: UUID = field(default=None)
    opened_by_id: UUID = field(default=None)
    offense_category: str = field(default="")
    accused_email: Optional[str] = field(default=None)
    accused_first_name: Optional[str] = field(default=None)


@dataclass(frozen=True)
class DisciplineSanctionIssued(DomainEvent):
    """Une sanction disciplinaire a été prononcée."""

    case_id: UUID = field(default=None)
    accused_user_id: UUID = field(default=None)
    sanction_type: str = field(default="")
    issued_by_id: UUID = field(default=None)


# ── Présence ──────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AttendanceRecorded(DomainEvent):
    """Une présence/absence a été enregistrée."""

    attendance_id: UUID = field(default=None)
    user_id: UUID = field(default=None)
    attendance_type: str = field(default="")
    status: str = field(default="")
