"""
Repository pour la gestion des modèles de classement dominical.

Chiffrement PII (Loi 2024/017 Cameroun) :
  - SundayMassAssignment.servant_name : nom en clair d'un servant chiffré
  - SundayScheduleModificationLog : modified_by_name, ip_address, user_agent
    (une adresse IP est une donnée personnelle per Art. 5)
  Les User chargés directement sont déchiffrés via decrypt_str_fields().
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional, Tuple
from uuid import UUID

if TYPE_CHECKING:
    from src.core.entities.sunday_schedule import SundayScheduleModificationLog

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.sunday_schedule import (
    SundayMassAssignment,
    SundayMassSlot,
    SundayScheduleStatus,
    SundayScheduleTemplate,
)
from src.core.entities.user import User
from src.infrastructure.security.field_encryption import (
    decrypt_str_fields,
    get_encryptor,
)

_USER_PII = ("first_name", "last_name")
_ASSIGN_PII = ("servant_name",)
_LOG_PII = ("modified_by_name", "ip_address", "user_agent")


def _enc_fields(model, fields):
    enc = get_encryptor()
    for f in fields:
        v = getattr(model, f, None)
        if v:
            setattr(model, f, enc.encrypt(str(v)))


def _dec_fields(model, fields):
    enc = get_encryptor()
    for f in fields:
        v = getattr(model, f, None)
        if v:
            try:
                setattr(model, f, enc.decrypt(v))
            except (ValueError, Exception):
                pass


class SundayScheduleRepository:
    """Repository pour les modèles de classement dominical."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ══════════════════════════════════════════════════════════════════
    #  TEMPLATES
    # ══════════════════════════════════════════════════════════════════

    async def create_template(self, template: SundayScheduleTemplate) -> SundayScheduleTemplate:
        """Crée un nouveau modèle de classement."""
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def get_template(self, template_id: UUID) -> Optional[SundayScheduleTemplate]:
        """Récupère un modèle par son ID."""
        result = await self.session.execute(
            select(SundayScheduleTemplate).where(SundayScheduleTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def update_template(self, template_id: UUID, template: SundayScheduleTemplate) -> SundayScheduleTemplate:
        """Met à jour un modèle."""
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def delete_template(self, template_id: UUID) -> bool:
        """Supprime un modèle et toutes ses messes."""
        template = await self.get_template(template_id)
        if not template:
            return False

        # Supprimer d'abord toutes les assignations
        masses_result = await self.session.execute(
            select(SundayMassSlot).where(SundayMassSlot.template_id == template_id)
        )
        masses = masses_result.scalars().all()

        for mass in masses:
            # Supprimer les assignations de la messe
            assignments_result = await self.session.execute(
                select(SundayMassAssignment).where(SundayMassAssignment.mass_slot_id == mass.id)
            )
            assignments = assignments_result.scalars().all()
            for assignment in assignments:
                await self.session.delete(assignment)

            # Supprimer la messe
            await self.session.delete(mass)

        await self.session.delete(template)
        await self.session.commit()
        return True

    async def list_templates(
        self,
        status: Optional[SundayScheduleStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[SundayScheduleTemplate], int]:
        """Liste paginée des modèles avec filtres."""
        query = select(SundayScheduleTemplate)

        if status:
            query = query.where(SundayScheduleTemplate.status == status)
        if start_date:
            query = query.where(SundayScheduleTemplate.schedule_date >= start_date)
        if end_date:
            query = query.where(SundayScheduleTemplate.schedule_date <= end_date)

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Pagination
        query = query.order_by(SundayScheduleTemplate.schedule_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        templates = result.scalars().all()
        return list(templates), total

    async def get_published_templates(self) -> List[SundayScheduleTemplate]:
        """Récupère tous les modèles publiés."""
        result = await self.session.execute(
            select(SundayScheduleTemplate)
            .where(SundayScheduleTemplate.status == SundayScheduleStatus.PUBLISHED)
            .order_by(SundayScheduleTemplate.schedule_date.desc())
        )
        return list(result.scalars().all())

    # ══════════════════════════════════════════════════════════════════
    #  MASS SLOTS
    # ══════════════════════════════════════════════════════════════════

    async def create_mass(self, mass: SundayMassSlot) -> SundayMassSlot:
        """Crée une nouvelle messe."""
        self.session.add(mass)
        await self.session.commit()
        await self.session.refresh(mass)
        return mass

    async def create_masses_batch(self, masses: List[SundayMassSlot]) -> List[SundayMassSlot]:
        """Crée plusieurs messes en une seule transaction."""
        self.session.add_all(masses)
        await self.session.commit()
        for mass in masses:
            await self.session.refresh(mass)
        return masses

    async def get_mass(self, mass_id: UUID) -> Optional[SundayMassSlot]:
        """Récupère une messe par son ID."""
        result = await self.session.execute(select(SundayMassSlot).where(SundayMassSlot.id == mass_id))
        return result.scalar_one_or_none()

    async def update_mass(self, mass_id: UUID, mass: SundayMassSlot) -> SundayMassSlot:
        """Met à jour une messe."""
        await self.session.commit()
        await self.session.refresh(mass)
        return mass

    async def delete_mass(self, mass_id: UUID) -> bool:
        """Supprime une messe et ses assignations."""
        mass = await self.get_mass(mass_id)
        if not mass:
            return False

        # Supprimer d'abord les assignations
        assignments_result = await self.session.execute(
            select(SundayMassAssignment).where(SundayMassAssignment.mass_slot_id == mass_id)
        )
        assignments = assignments_result.scalars().all()
        for assignment in assignments:
            await self.session.delete(assignment)

        await self.session.delete(mass)
        await self.session.commit()
        return True

    async def get_template_masses(self, template_id: UUID) -> List[SundayMassSlot]:
        """Récupère toutes les messes d'un modèle."""
        result = await self.session.execute(
            select(SundayMassSlot).where(SundayMassSlot.template_id == template_id).order_by(SundayMassSlot.mass_time)
        )
        return list(result.scalars().all())

    # ══════════════════════════════════════════════════════════════════
    #  ASSIGNMENTS
    # ══════════════════════════════════════════════════════════════════

    async def create_assignment(self, assignment: SundayMassAssignment) -> SundayMassAssignment:
        """Crée une nouvelle assignation."""
        _enc_fields(assignment, _ASSIGN_PII)
        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)
        _dec_fields(assignment, _ASSIGN_PII)
        return assignment

    async def create_assignments_batch(self, assignments: List[SundayMassAssignment]) -> List[SundayMassAssignment]:
        """Crée plusieurs assignations en une seule transaction."""
        for a in assignments:
            _enc_fields(a, _ASSIGN_PII)
        self.session.add_all(assignments)
        await self.session.commit()
        for assignment in assignments:
            await self.session.refresh(assignment)
            _dec_fields(assignment, _ASSIGN_PII)
        return assignments

    async def get_assignment(self, assignment_id: UUID) -> Optional[SundayMassAssignment]:
        """Récupère une assignation par son ID."""
        result = await self.session.execute(
            select(SundayMassAssignment).where(SundayMassAssignment.id == assignment_id)
        )
        a = result.scalar_one_or_none()
        if a:
            _dec_fields(a, _ASSIGN_PII)
        return a

    async def get_mass_assignments(self, mass_id: UUID) -> List[SundayMassAssignment]:
        """Récupère toutes les assignations d'une messe."""
        result = await self.session.execute(
            select(SundayMassAssignment)
            .where(SundayMassAssignment.mass_slot_id == mass_id)
            .order_by(SundayMassAssignment.position)
        )
        assignments = list(result.scalars().all())
        for a in assignments:
            _dec_fields(a, _ASSIGN_PII)
        return assignments

    async def delete_assignment(self, assignment_id: UUID) -> bool:
        """Supprime une assignation."""
        assignment = await self.get_assignment(assignment_id)
        if not assignment:
            return False
        await self.session.delete(assignment)
        await self.session.commit()
        return True

    async def update_assignment(self, assignment_id: UUID, assignment: SundayMassAssignment) -> SundayMassAssignment:
        """Met à jour une assignation."""
        _enc_fields(assignment, _ASSIGN_PII)
        await self.session.commit()
        await self.session.refresh(assignment)
        _dec_fields(assignment, _ASSIGN_PII)
        return assignment

    # ══════════════════════════════════════════════════════════════════
    #  ENRICHISSEMENT
    # ══════════════════════════════════════════════════════════════════

    async def enrich_template(self, template: SundayScheduleTemplate) -> dict:
        """Enrichit un modèle avec les infos du créateur et les messes."""
        creator_result = await self.session.execute(select(User).where(User.id == template.created_by))
        creator = creator_result.scalar_one_or_none()
        if creator:
            decrypt_str_fields(creator, _USER_PII)

        # Récupérer les messes
        masses = await self.get_template_masses(template.id)
        enriched_masses = await self.enrich_masses(masses)

        return {
            **template.model_dump(),
            "creator_first_name": creator.first_name if creator else None,
            "creator_last_name": creator.last_name if creator else None,
            "masses": enriched_masses,
        }

    async def enrich_mass(self, mass: SundayMassSlot) -> dict:
        """Enrichit une messe avec ses assignations."""
        enriched = mass.model_dump()

        # Récupérer les assignations
        assignments = await self.get_mass_assignments(mass.id)
        enriched_assignments = await self.enrich_assignments(assignments)
        enriched["assignments"] = enriched_assignments

        return enriched

    async def enrich_masses(self, masses: List[SundayMassSlot]) -> List[dict]:
        """Enrichit plusieurs messes."""
        return [await self.enrich_mass(mass) for mass in masses]

    async def enrich_assignment(self, assignment: SundayMassAssignment) -> dict:
        """Enrichit une assignation avec les infos du servant et traçabilité."""
        enriched = assignment.model_dump()

        # Infos du servant
        if assignment.servant_id:
            servant_result = await self.session.execute(select(User).where(User.id == assignment.servant_id))
            servant = servant_result.scalar_one_or_none()
            if servant:
                decrypt_str_fields(servant, _USER_PII)
                enriched["servant_first_name"] = servant.first_name
                enriched["servant_last_name"] = servant.last_name

        # Infos de la personne qui a assigné
        assigned_by_result = await self.session.execute(select(User).where(User.id == assignment.assigned_by))
        assigned_by = assigned_by_result.scalar_one_or_none()
        if assigned_by:
            decrypt_str_fields(assigned_by, _USER_PII)
            enriched["assigned_by_name"] = f"{assigned_by.first_name} {assigned_by.last_name}"

        # Infos de la dernière modification
        if assignment.last_modified_by:
            modified_by_result = await self.session.execute(select(User).where(User.id == assignment.last_modified_by))
            modified_by = modified_by_result.scalar_one_or_none()
            if modified_by:
                decrypt_str_fields(modified_by, _USER_PII)
                enriched["last_modified_by_name"] = f"{modified_by.first_name} {modified_by.last_name}"

        # Infos du marquage de présence
        if assignment.presence_marked_by:
            presence_by_result = await self.session.execute(
                select(User).where(User.id == assignment.presence_marked_by)
            )
            presence_by = presence_by_result.scalar_one_or_none()
            if presence_by:
                decrypt_str_fields(presence_by, _USER_PII)
                enriched["presence_marked_by_name"] = f"{presence_by.first_name} {presence_by.last_name}"

        return enriched

    async def enrich_assignments(self, assignments: List[SundayMassAssignment]) -> List[dict]:
        """Enrichit plusieurs assignations."""
        return [await self.enrich_assignment(a) for a in assignments]

    async def get_template_summary(self, template: SundayScheduleTemplate) -> dict:
        """Crée un résumé d'un modèle avec statistiques."""
        creator_result = await self.session.execute(select(User).where(User.id == template.created_by))
        creator = creator_result.scalar_one_or_none()
        if creator:
            decrypt_str_fields(creator, _USER_PII)

        # Compter les messes et assignations
        masses = await self.get_template_masses(template.id)
        total_masses = len(masses)

        total_positions = 0
        filled_positions = 0
        for mass in masses:
            assignments = await self.get_mass_assignments(mass.id)
            total_positions += len(assignments)
            filled_positions += sum(1 for a in assignments if a.servant_id is not None or a.servant_name is not None)

        return {
            **template.model_dump(),
            "creator_first_name": creator.first_name if creator else None,
            "creator_last_name": creator.last_name if creator else None,
            "total_masses": total_masses,
            "total_positions": total_positions,
            "filled_positions": filled_positions,
        }

    # ══════════════════════════════════════════════════════════════════
    #  HISTORIQUE DES MODIFICATIONS
    # ══════════════════════════════════════════════════════════════════

    async def create_modification_log(self, log: "SundayScheduleModificationLog") -> "SundayScheduleModificationLog":
        """Crée une entrée dans l'historique des modifications (champs PII chiffrés)."""
        from src.core.entities.sunday_schedule import SundayScheduleModificationLog

        _enc_fields(log, _LOG_PII)
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        _dec_fields(log, _LOG_PII)
        return log

    async def get_template_modification_logs(
        self, template_id: UUID, limit: int = 100
    ) -> List["SundayScheduleModificationLog"]:
        """Récupère l'historique des modifications d'un modèle (déchiffré)."""
        from src.core.entities.sunday_schedule import SundayScheduleModificationLog

        result = await self.session.execute(
            select(SundayScheduleModificationLog)
            .where(SundayScheduleModificationLog.template_id == template_id)
            .order_by(SundayScheduleModificationLog.modified_at.desc())
            .limit(limit)
        )
        logs = list(result.scalars().all())
        for log in logs:
            _dec_fields(log, _LOG_PII)
        return logs
