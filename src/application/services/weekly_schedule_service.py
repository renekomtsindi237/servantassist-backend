"""
Service métier pour la gestion des modèles de classement hebdomadaire.

Règles métier :
- Seul le CHARGE_CLASSEMENT_SEMAINE peut créer/modifier/supprimer des modèles.
- Les modèles publiés sont visibles par tous les utilisateurs authentifiés.
- Un modèle peut être créé avec des créneaux pré-remplis ou vides.
- Chaque créneau peut avoir 0 ou plusieurs servants assignés.
- Les servants peuvent être référencés par ID (servant existant) ou par nom libre.
- Validation temporelle stricte : modifications autorisées 1h avant → 1h après la messe.
"""

import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.user import UserRole
from src.core.entities.weekly_schedule import (
    ScheduleStatus,
    SlotServantAssignment,
    WeeklyScheduleSlot,
    WeeklyScheduleTemplate,
)
from src.core.interfaces.repositories import IUserRepository, IWeeklyScheduleRepository
from src.core.utils import utc_now
from src.presentation.schemas.user import PaginatedResponse
from src.presentation.schemas.weekly_schedule import (
    SlotServantCreate,
    SlotServantResponse,
    WeeklyScheduleSlotResponse,
    WeeklyScheduleSlotUpdate,
    WeeklyScheduleTemplateCreate,
    WeeklyScheduleTemplateResponse,
    WeeklyScheduleTemplateSummary,
    WeeklyScheduleTemplateUpdate,
)


def parse_mass_time(mass_time: str) -> tuple[int, int]:
    """
    Parse une heure de messe (ex: "06h15", "12h00", "18h00") en heures et minutes.

    Returns:
        tuple[int, int]: (heures, minutes)
    """
    # Format attendu : "06h15", "12h00", "18h00", etc.
    parts = mass_time.lower().replace("h", ":").split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    return hours, minutes


def is_within_mass_window(slot_date: datetime, mass_time: str, current_time: Optional[datetime] = None) -> bool:
    """
    Vérifie si l'heure actuelle est dans la fenêtre de modification autorisée.

    Fenêtre : 1 heure avant la messe → 1 heure après la fin de la messe.
    Durée estimée d'une messe : 1 heure.

    Args:
        slot_date: Date du créneau (jour de la semaine)
        mass_time: Heure de la messe (ex: "06h15", "12h00", "18h00" ou enum "MATIN", "MIDI", "SOIR")
        current_time: Heure actuelle (None = maintenant)

    Returns:
        bool: True si dans la fenêtre autorisée
    """
    if current_time is None:
        current_time = utc_now()

    # Mapping des enums (si c'est une chaîne, on compare à la valeur de l'enum)
    # On supporte les valeurs brutes ("06h15") ou les clés d'enum ("MATIN")
    time_str = mass_time
    if hasattr(mass_time, "value"):
        time_str = mass_time.value

    time_upper = str(time_str).upper()
    if time_upper == "MATIN":
        time_str = "06h15"
    elif time_upper == "MIDI":
        time_str = "12h00"
    elif time_upper == "SOIR":
        time_str = "18h00"

    # Parser l'heure de la messe
    hours, minutes = parse_mass_time(time_str)

    # Normaliser slot_date en naif UTC (utc_now() est toujours naif)
    naive_date = slot_date.replace(tzinfo=None) if slot_date.tzinfo else slot_date
    if current_time.tzinfo:
        current_time = current_time.replace(tzinfo=None)

    # Créer le datetime de début de la messe
    mass_start = naive_date.replace(
        hour=hours,
        minute=minutes,
        second=0,
        microsecond=0,
    )

    # Fenêtre : 1h avant → 2h après le début (1h de messe + 1h après)
    window_start = mass_start - timedelta(hours=1)
    window_end = mass_start + timedelta(hours=2)

    return window_start <= current_time <= window_end


class WeeklyScheduleService:
    """Logique métier des modèles de classement hebdomadaire."""

    def __init__(
        self,
        schedule_repository: IWeeklyScheduleRepository,
        user_repository: IUserRepository,
    ):
        self.schedule_repo = schedule_repository
        self.user_repo = user_repository

    # ══════════════════════════════════════════════════════════════════
    #  CRÉATION
    # ══════════════════════════════════════════════════════════════════

    async def create_template(
        self, data: WeeklyScheduleTemplateCreate, created_by: UUID
    ) -> WeeklyScheduleTemplateResponse:
        """
        Crée un nouveau modèle de classement hebdomadaire.

        Peut être créé avec des créneaux pré-remplis ou vide.
        """
        # Créer le modèle
        template = WeeklyScheduleTemplate(
            title=data.title,
            start_date=data.start_date,
            end_date=data.end_date,
            notes=data.notes,
            created_by=created_by,
        )
        created_template = await self.schedule_repo.create_template(template)

        # Créer les créneaux si fournis
        if data.slots:
            for slot_data in data.slots:
                # Créer le créneau
                slot = WeeklyScheduleSlot(
                    template_id=created_template.id,
                    day=slot_data.day,
                    mass_time=slot_data.mass_time,
                    notes=slot_data.notes,
                )
                created_slot = await self.schedule_repo.create_slot(slot)

                # Créer les assignations de servants
                if slot_data.servants:
                    assignments = []
                    for servant_data in slot_data.servants:
                        # Valider le servant si fourni
                        if servant_data.servant_id:
                            user = await self.user_repo.get(servant_data.servant_id)
                            if not user:
                                raise HTTPException(
                                    status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Utilisateur {servant_data.servant_id} introuvable.",
                                )
                            if user.role != UserRole.SERVANT:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"{user.first_name} {user.last_name} n'est pas un servant.",
                                )

                        assignment = SlotServantAssignment(
                            slot_id=created_slot.id,
                            servant_id=servant_data.servant_id,
                            servant_name=servant_data.servant_name,
                            notes=servant_data.notes,
                            assigned_by=created_by,
                        )
                        assignments.append(assignment)

                    await self.schedule_repo.create_assignments_batch(assignments)

        # Retourner le modèle enrichi
        enriched = await self.schedule_repo.enrich_template(created_template)
        return WeeklyScheduleTemplateResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  LECTURE
    # ══════════════════════════════════════════════════════════════════

    async def get_template(self, template_id: UUID) -> WeeklyScheduleTemplateResponse:
        """Récupère un modèle par son ID avec tous ses créneaux."""
        template = await self.schedule_repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )
        enriched = await self.schedule_repo.enrich_template(template)
        return WeeklyScheduleTemplateResponse(**enriched)

    async def list_templates(
        self,
        status_filter: Optional[ScheduleStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[WeeklyScheduleTemplateSummary]:
        """Liste paginée des modèles avec filtres."""
        templates, total = await self.schedule_repo.list_templates(
            status=status_filter,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        # Créer les résumés
        summaries = []
        for template in templates:
            summary_data = await self.schedule_repo.get_template_summary(template)
            summaries.append(WeeklyScheduleTemplateSummary(**summary_data))

        return PaginatedResponse(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_published_templates(
        self,
    ) -> List[WeeklyScheduleTemplateSummary]:
        """Récupère tous les modèles publiés (visible par tous)."""
        templates = await self.schedule_repo.get_published_templates()
        summaries = []
        for template in templates:
            summary_data = await self.schedule_repo.get_template_summary(template)
            summaries.append(WeeklyScheduleTemplateSummary(**summary_data))
        return summaries

    # ══════════════════════════════════════════════════════════════════
    #  MODIFICATION
    # ══════════════════════════════════════════════════════════════════

    async def update_template(
        self,
        template_id: UUID,
        data: WeeklyScheduleTemplateUpdate,
        updated_by: UUID,
    ) -> WeeklyScheduleTemplateResponse:
        """Met à jour un modèle de classement."""
        template = await self.schedule_repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )

        if data.title is not None:
            template.title = data.title
        if data.start_date is not None:
            template.start_date = data.start_date
        if data.end_date is not None:
            template.end_date = data.end_date
        if data.status is not None:
            template.status = data.status
        if data.notes is not None:
            template.notes = data.notes

        template.updated_by = updated_by
        template.updated_at = utc_now()

        updated = await self.schedule_repo.update_template(template_id, template)
        enriched = await self.schedule_repo.enrich_template(updated)
        return WeeklyScheduleTemplateResponse(**enriched)

    async def publish_template(self, template_id: UUID, published_by: UUID) -> WeeklyScheduleTemplateResponse:
        """Publie un modèle (le rend visible par tous)."""
        template = await self.schedule_repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )

        if template.status == ScheduleStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce modèle est déjà publié.",
            )

        template.status = ScheduleStatus.PUBLISHED
        template.updated_by = published_by
        template.updated_at = utc_now()

        updated = await self.schedule_repo.update_template(template_id, template)
        enriched = await self.schedule_repo.enrich_template(updated)
        return WeeklyScheduleTemplateResponse(**enriched)

    async def archive_template(self, template_id: UUID, archived_by: UUID) -> WeeklyScheduleTemplateResponse:
        """Archive un modèle."""
        template = await self.schedule_repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )

        template.status = ScheduleStatus.ARCHIVED
        template.updated_by = archived_by
        template.updated_at = utc_now()

        updated = await self.schedule_repo.update_template(template_id, template)
        enriched = await self.schedule_repo.enrich_template(updated)
        return WeeklyScheduleTemplateResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  SUPPRESSION
    # ══════════════════════════════════════════════════════════════════

    async def delete_template(self, template_id: UUID) -> None:
        """Supprime un modèle et tous ses créneaux."""
        template = await self.schedule_repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )
        deleted = await self.schedule_repo.delete_template(template_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression du modèle.",
            )

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES CRÉNEAUX
    # ══════════════════════════════════════════════════════════════════

    async def update_slot(
        self,
        slot_id: UUID,
        data: WeeklyScheduleSlotUpdate,
    ) -> WeeklyScheduleSlotResponse:
        """Met à jour un créneau."""
        slot = await self.schedule_repo.get_slot(slot_id)
        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Créneau introuvable.",
            )

        if data.notes is not None:
            slot.notes = data.notes

        slot.updated_at = utc_now()

        updated = await self.schedule_repo.update_slot(slot_id, slot)
        enriched = await self.schedule_repo.enrich_slot(updated)
        return WeeklyScheduleSlotResponse(**enriched)

    async def delete_slot(self, slot_id: UUID) -> None:
        """Supprime un créneau."""
        slot = await self.schedule_repo.get_slot(slot_id)
        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Créneau introuvable.",
            )
        deleted = await self.schedule_repo.delete_slot(slot_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression du créneau.",
            )

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES ASSIGNATIONS DE SERVANTS
    # ══════════════════════════════════════════════════════════════════

    async def add_servant_to_slot(
        self,
        slot_id: UUID,
        data: SlotServantCreate,
        assigned_by: UUID,
    ) -> SlotServantResponse:
        """Ajoute un servant à un créneau."""
        slot = await self.schedule_repo.get_slot(slot_id)
        if not slot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Créneau introuvable.",
            )

        # Récupérer le template pour vérifier la date
        template = await self.schedule_repo.get_template(slot.template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )

        # Calculer la date du créneau (jour de la semaine dans la période du template)
        # Le slot.day est un enum (LUNDI, MARDI, etc.)
        # On doit trouver le jour correspondant dans la période start_date ->
        # end_date
        from src.core.entities.weekly_schedule import WeekDay

        # Mapping des jours
        day_mapping = {
            WeekDay.LUNDI: 0,
            WeekDay.MARDI: 1,
            WeekDay.MERCREDI: 2,
            WeekDay.JEUDI: 3,
            WeekDay.VENDREDI: 4,
            WeekDay.SAMEDI: 5,
        }

        # Trouver le jour dans la période
        target_weekday = day_mapping[slot.day]
        current_date = template.start_date
        slot_date = None

        while current_date <= template.end_date:
            if current_date.weekday() == target_weekday:
                slot_date = current_date
                break
            current_date += timedelta(days=1)

        if not slot_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le jour {getattr(slot.day, 'value', slot.day)} n'existe pas dans la période du classement.",
            )

        # Validation temporelle stricte : 1h avant → 1h après la messe
        if not is_within_mass_window(slot_date, slot.mass_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"L'ajout de servants n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de {getattr(slot.mass_time, 'value', slot.mass_time)} le {getattr(slot.day, 'value', slot.day)}.",  # noqa: E501
            )

        # Valider le servant si fourni
        if data.servant_id:
            user = await self.user_repo.get(data.servant_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Utilisateur {data.servant_id} introuvable.",
                )
            if user.role != UserRole.SERVANT:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{user.first_name} {user.last_name} n'est pas un servant.",
                )

        assignment = SlotServantAssignment(
            slot_id=slot_id,
            servant_id=data.servant_id,
            servant_name=data.servant_name,
            notes=data.notes,
            assigned_by=assigned_by,
        )
        created = await self.schedule_repo.create_assignment(assignment)
        enriched = await self.schedule_repo.enrich_assignment(created)
        return SlotServantResponse(**enriched)

    async def remove_servant_from_slot(self, assignment_id: UUID) -> None:
        """Retire un servant d'un créneau."""
        assignment = await self.schedule_repo.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignation introuvable.",
            )

        # Récupérer le slot et le template pour vérifier la date
        slot = await self.schedule_repo.get_slot(assignment.slot_id)
        if slot:
            template = await self.schedule_repo.get_template(slot.template_id)
            if template:
                # Calculer la date du créneau
                from src.core.entities.weekly_schedule import WeekDay

                day_mapping = {
                    WeekDay.LUNDI: 0,
                    WeekDay.MARDI: 1,
                    WeekDay.MERCREDI: 2,
                    WeekDay.JEUDI: 3,
                    WeekDay.VENDREDI: 4,
                    WeekDay.SAMEDI: 5,
                }

                target_weekday = day_mapping[slot.day]
                current_date = template.start_date
                slot_date = None

                while current_date <= template.end_date:
                    if current_date.weekday() == target_weekday:
                        slot_date = current_date
                        break
                    current_date += timedelta(days=1)

                if slot_date:
                    # Validation temporelle stricte : 1h avant → 1h après la
                    # messe
                    if not is_within_mass_window(slot_date, slot.mass_time):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Le retrait de servants n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de {getattr(slot.mass_time, 'value', slot.mass_time)} le {getattr(slot.day, 'value', slot.day)}.",  # noqa: E501
                        )

        deleted = await self.schedule_repo.delete_assignment(assignment_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de l'assignation.",
            )
