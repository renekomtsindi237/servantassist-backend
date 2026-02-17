"""
Repository pour la gestion des modèles de classement hebdomadaire.
"""
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.user import User
from src.core.entities.weekly_schedule import (
    ScheduleStatus,
    SlotServantAssignment,
    WeeklyScheduleSlot,
    WeeklyScheduleTemplate,
)


class WeeklyScheduleRepository:
    """Repository pour les modèles de classement hebdomadaire."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ══════════════════════════════════════════════════════════════════
    #  TEMPLATES
    # ══════════════════════════════════════════════════════════════════

    async def create_template(
        self, template: WeeklyScheduleTemplate
    ) -> WeeklyScheduleTemplate:
        """Crée un nouveau modèle de classement."""
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def get_template(self, template_id: UUID) -> Optional[WeeklyScheduleTemplate]:
        """Récupère un modèle par son ID."""
        result = await self.session.execute(
            select(WeeklyScheduleTemplate).where(
                WeeklyScheduleTemplate.id == template_id
            )
        )
        return result.scalar_one_or_none()

    async def update_template(
        self, template_id: UUID, template: WeeklyScheduleTemplate
    ) -> WeeklyScheduleTemplate:
        """Met à jour un modèle."""
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def delete_template(self, template_id: UUID) -> bool:
        """Supprime un modèle et tous ses créneaux."""
        template = await self.get_template(template_id)
        if not template:
            return False

        # Supprimer d'abord toutes les assignations
        slots_result = await self.session.execute(
            select(WeeklyScheduleSlot).where(
                WeeklyScheduleSlot.template_id == template_id
            )
        )
        slots = slots_result.scalars().all()

        for slot in slots:
            # Supprimer les assignations du créneau
            assignments_result = await self.session.execute(
                select(SlotServantAssignment).where(
                    SlotServantAssignment.slot_id == slot.id
                )
            )
            assignments = assignments_result.scalars().all()
            for assignment in assignments:
                await self.session.delete(assignment)

            # Supprimer le créneau
            await self.session.delete(slot)

        await self.session.delete(template)
        await self.session.commit()
        return True

    async def list_templates(
        self,
        status: Optional[ScheduleStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[WeeklyScheduleTemplate], int]:
        """Liste paginée des modèles avec filtres."""
        query = select(WeeklyScheduleTemplate)

        if status:
            query = query.where(WeeklyScheduleTemplate.status == status)
        if start_date:
            query = query.where(WeeklyScheduleTemplate.start_date >= start_date)
        if end_date:
            query = query.where(WeeklyScheduleTemplate.end_date <= end_date)

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # Pagination
        query = query.order_by(WeeklyScheduleTemplate.start_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        templates = result.scalars().all()
        return list(templates), total

    async def get_published_templates(self) -> List[WeeklyScheduleTemplate]:
        """Récupère tous les modèles publiés."""
        result = await self.session.execute(
            select(WeeklyScheduleTemplate)
            .where(WeeklyScheduleTemplate.status == ScheduleStatus.PUBLISHED)
            .order_by(WeeklyScheduleTemplate.start_date.desc())
        )
        return list(result.scalars().all())

    # ══════════════════════════════════════════════════════════════════
    #  SLOTS
    # ══════════════════════════════════════════════════════════════════

    async def create_slot(self, slot: WeeklyScheduleSlot) -> WeeklyScheduleSlot:
        """Crée un nouveau créneau."""
        self.session.add(slot)
        await self.session.commit()
        await self.session.refresh(slot)
        return slot

    async def create_slots_batch(
        self, slots: List[WeeklyScheduleSlot]
    ) -> List[WeeklyScheduleSlot]:
        """Crée plusieurs créneaux en une seule transaction."""
        self.session.add_all(slots)
        await self.session.commit()
        for slot in slots:
            await self.session.refresh(slot)
        return slots

    async def get_slot(self, slot_id: UUID) -> Optional[WeeklyScheduleSlot]:
        """Récupère un créneau par son ID."""
        result = await self.session.execute(
            select(WeeklyScheduleSlot).where(WeeklyScheduleSlot.id == slot_id)
        )
        return result.scalar_one_or_none()

    async def update_slot(
        self, slot_id: UUID, slot: WeeklyScheduleSlot
    ) -> WeeklyScheduleSlot:
        """Met à jour un créneau."""
        await self.session.commit()
        await self.session.refresh(slot)
        return slot

    async def delete_slot(self, slot_id: UUID) -> bool:
        """Supprime un créneau et ses assignations."""
        slot = await self.get_slot(slot_id)
        if not slot:
            return False

        # Supprimer d'abord les assignations
        assignments_result = await self.session.execute(
            select(SlotServantAssignment).where(
                SlotServantAssignment.slot_id == slot_id
            )
        )
        assignments = assignments_result.scalars().all()
        for assignment in assignments:
            await self.session.delete(assignment)

        await self.session.delete(slot)
        await self.session.commit()
        return True

    async def get_template_slots(self, template_id: UUID) -> List[WeeklyScheduleSlot]:
        """Récupère tous les créneaux d'un modèle."""
        result = await self.session.execute(
            select(WeeklyScheduleSlot)
            .where(WeeklyScheduleSlot.template_id == template_id)
            .order_by(WeeklyScheduleSlot.day, WeeklyScheduleSlot.mass_time)
        )
        return list(result.scalars().all())

    # ══════════════════════════════════════════════════════════════════
    #  SERVANT ASSIGNMENTS
    # ══════════════════════════════════════════════════════════════════

    async def create_assignment(
        self, assignment: SlotServantAssignment
    ) -> SlotServantAssignment:
        """Crée une nouvelle assignation de servant à un créneau."""
        self.session.add(assignment)
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def create_assignments_batch(
        self, assignments: List[SlotServantAssignment]
    ) -> List[SlotServantAssignment]:
        """Crée plusieurs assignations en une seule transaction."""
        self.session.add_all(assignments)
        await self.session.commit()
        for assignment in assignments:
            await self.session.refresh(assignment)
        return assignments

    async def get_assignment(
        self, assignment_id: UUID
    ) -> Optional[SlotServantAssignment]:
        """Récupère une assignation par son ID."""
        result = await self.session.execute(
            select(SlotServantAssignment).where(
                SlotServantAssignment.id == assignment_id
            )
        )
        return result.scalar_one_or_none()

    async def get_slot_assignments(self, slot_id: UUID) -> List[SlotServantAssignment]:
        """Récupère toutes les assignations d'un créneau."""
        result = await self.session.execute(
            select(SlotServantAssignment)
            .where(SlotServantAssignment.slot_id == slot_id)
            .order_by(SlotServantAssignment.created_at)
        )
        return list(result.scalars().all())

    async def delete_assignment(self, assignment_id: UUID) -> bool:
        """Supprime une assignation."""
        assignment = await self.get_assignment(assignment_id)
        if not assignment:
            return False
        await self.session.delete(assignment)
        await self.session.commit()
        return True

    # ══════════════════════════════════════════════════════════════════
    #  ENRICHISSEMENT
    # ══════════════════════════════════════════════════════════════════

    async def enrich_template(self, template: WeeklyScheduleTemplate) -> dict:
        """Enrichit un modèle avec les infos du créateur et les créneaux."""
        # Récupérer le créateur
        creator_result = await self.session.execute(
            select(User).where(User.id == template.created_by)
        )
        creator = creator_result.scalar_one_or_none()

        # Récupérer les créneaux
        slots = await self.get_template_slots(template.id)
        enriched_slots = await self.enrich_slots(slots)

        return {
            **template.model_dump(),
            "creator_first_name": creator.first_name if creator else None,
            "creator_last_name": creator.last_name if creator else None,
            "slots": enriched_slots,
        }

    async def enrich_slot(self, slot: WeeklyScheduleSlot) -> dict:
        """Enrichit un créneau avec ses assignations de servants."""
        enriched = slot.model_dump()

        # Récupérer les assignations
        assignments = await self.get_slot_assignments(slot.id)
        enriched_assignments = await self.enrich_assignments(assignments)
        enriched["servants"] = enriched_assignments

        return enriched

    async def enrich_slots(self, slots: List[WeeklyScheduleSlot]) -> List[dict]:
        """Enrichit plusieurs créneaux."""
        return [await self.enrich_slot(slot) for slot in slots]

    async def enrich_assignment(self, assignment: SlotServantAssignment) -> dict:
        """Enrichit une assignation avec les infos du servant."""
        enriched = assignment.model_dump()

        if assignment.servant_id:
            servant_result = await self.session.execute(
                select(User).where(User.id == assignment.servant_id)
            )
            servant = servant_result.scalar_one_or_none()
            if servant:
                enriched["servant_first_name"] = servant.first_name
                enriched["servant_last_name"] = servant.last_name

        return enriched

    async def enrich_assignments(
        self, assignments: List[SlotServantAssignment]
    ) -> List[dict]:
        """Enrichit plusieurs assignations."""
        return [await self.enrich_assignment(a) for a in assignments]

    async def get_template_summary(self, template: WeeklyScheduleTemplate) -> dict:
        """Crée un résumé d'un modèle avec statistiques."""
        # Récupérer le créateur
        creator_result = await self.session.execute(
            select(User).where(User.id == template.created_by)
        )
        creator = creator_result.scalar_one_or_none()

        # Compter les créneaux et servants
        slots = await self.get_template_slots(template.id)
        total_slots = len(slots)

        filled_slots = 0
        total_servants = 0
        for slot in slots:
            assignments = await self.get_slot_assignments(slot.id)
            if assignments:
                filled_slots += 1
                total_servants += len(assignments)

        return {
            **template.model_dump(),
            "creator_first_name": creator.first_name if creator else None,
            "creator_last_name": creator.last_name if creator else None,
            "total_slots": total_slots,
            "filled_slots": filled_slots,
            "total_servants": total_servants,
        }
