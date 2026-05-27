"""
Service métier pour la gestion des modèles de classement dominical.

Règles métier :
- Seul le CHARGE_CLASSEMENT_DIMANCHE peut créer/modifier/supprimer des modèles.
- Les modèles publiés sont visibles par tous les utilisateurs authentifiés.
- Support des horaires ordinaires et exceptionnels.
- Support des messes solennelles avec postes liturgiques supplémentaires.
- Validation temporelle stricte : modifications autorisées 1h avant → 1h après la messe.
"""
import math
from datetime import datetime, timedelta, timezone
from src.core.utils import utc_now
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.sunday_schedule import (
    EXCEPTIONAL_MASS_TIMES,
    ORDINARY_MASS_TIMES,
    ORDINARY_POSITIONS,
    SOLEMN_POSITIONS,
    MassType,
    SundayMassAssignment,
    SundayMassSlot,
    SundayScheduleStatus,
    SundayScheduleTemplate,
)
from src.core.entities.user import UserRole
from src.core.interfaces.repositories import ISundayScheduleRepository
from src.core.interfaces.repositories import IUserRepository
from src.presentation.schemas.sunday_schedule import (
    GenerateExceptionalScheduleRequest,
    GenerateOrdinaryScheduleRequest,
    SundayMassAssignmentCreate,
    SundayMassAssignmentResponse,
    SundayMassSlotResponse,
    SundayMassSlotUpdate,
    SundayScheduleTemplateCreate,
    SundayScheduleTemplateResponse,
    SundayScheduleTemplateSummary,
    SundayScheduleTemplateUpdate,
)
from src.presentation.schemas.user import PaginatedResponse


def parse_mass_time(mass_time: str) -> tuple[int, int]:
    """
    Parse une heure de messe (ex: "06h30", "08h30") en heures et minutes.

    Returns:
        tuple[int, int]: (heures, minutes)
    """
    # Format attendu : "06h30", "08h30", etc.
    parts = mass_time.lower().replace("h", ":").split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    return hours, minutes


def is_within_mass_window(
    schedule_date: datetime, mass_time: str, current_time: Optional[datetime] = None
) -> bool:
    """
    Vérifie si l'heure actuelle est dans la fenêtre de modification autorisée.

    Fenêtre : 1 heure avant la messe → 1 heure après la fin de la messe.
    Durée estimée d'une messe : 1 heure.

    Args:
        schedule_date: Date du dimanche
        mass_time: Heure de la messe (ex: "06h30")
        current_time: Heure actuelle (None = maintenant)

    Returns:
        bool: True si dans la fenêtre autorisée
    """
    if current_time is None:
        current_time = utc_now()

    # Parser l'heure de la messe
    hours, minutes = parse_mass_time(mass_time)

    # Normaliser en naif UTC (utc_now() est toujours naif)
    naive_date = (
        schedule_date.replace(tzinfo=None) if schedule_date.tzinfo else schedule_date
    )
    if current_time.tzinfo:
        current_time = current_time.replace(tzinfo=None)

    # Créer le datetime de début de la messe
    mass_start = naive_date.replace(hour=hours, minute=minutes, second=0, microsecond=0)

    # Fenêtre : 1h avant → 2h après le début (1h de messe + 1h après)
    window_start = mass_start - timedelta(hours=1)
    window_end = mass_start + timedelta(hours=2)

    return window_start <= current_time <= window_end


class SundayScheduleService:
    """Logique métier des modèles de classement dominical."""

    def __init__(
        self,
        schedule_repository: ISundayScheduleRepository,
        user_repository: IUserRepository,
    ):
        self.schedule_repo = schedule_repository
        self.user_repo = user_repository

    # ══════════════════════════════════════════════════════════════════
    #  CRÉATION
    # ══════════════════════════════════════════════════════════════════

    async def create_template(
        self, data: SundayScheduleTemplateCreate, created_by: UUID
    ) -> SundayScheduleTemplateResponse:
        """Crée un nouveau modèle de classement dominical."""
        # Créer le modèle
        template = SundayScheduleTemplate(
            title=data.title,
            schedule_date=data.schedule_date,
            mass_type=data.mass_type,
            is_exceptional=data.is_exceptional,
            notes=data.notes,
            created_by=created_by,
        )
        created_template = await self.schedule_repo.create_template(template)

        # Créer les messes si fournies
        if data.masses:
            for mass_data in data.masses:
                # Créer la messe
                mass = SundayMassSlot(
                    template_id=created_template.id,
                    mass_time=mass_data.mass_time,
                    language=mass_data.language,
                    notes=mass_data.notes,
                )
                created_mass = await self.schedule_repo.create_mass(mass)

                # Créer les assignations
                if mass_data.assignments:
                    assignments = []
                    for assignment_data in mass_data.assignments:
                        # Valider le servant si fourni
                        if assignment_data.servant_id:
                            user = await self.user_repo.get(assignment_data.servant_id)
                            if not user:
                                raise HTTPException(
                                    status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f"Utilisateur {assignment_data.servant_id} introuvable.",
                                )
                            if user.role != UserRole.SERVANT:
                                raise HTTPException(
                                    status_code=status.HTTP_400_BAD_REQUEST,
                                    detail=f"{user.first_name} {user.last_name} n'est pas un servant.",
                                )

                        assignment = SundayMassAssignment(
                            mass_slot_id=created_mass.id,
                            position=assignment_data.position,
                            servant_id=assignment_data.servant_id,
                            servant_name=assignment_data.servant_name,
                            notes=assignment_data.notes,
                            assigned_by=created_by,
                        )
                        assignments.append(assignment)

                    await self.schedule_repo.create_assignments_batch(assignments)

        # Retourner le modèle enrichi
        enriched = await self.schedule_repo.enrich_template(created_template)
        return SundayScheduleTemplateResponse(**enriched)

    async def generate_ordinary_template(
        self, data: GenerateOrdinaryScheduleRequest, created_by: UUID
    ) -> SundayScheduleTemplateResponse:
        """Génère un modèle avec les horaires ordinaires pré-remplis."""
        # Créer le modèle
        template = SundayScheduleTemplate(
            title=data.title,
            schedule_date=data.schedule_date,
            mass_type=MassType.ORDINAIRE,
            is_exceptional=False,
            notes=data.notes,
            created_by=created_by,
        )
        created_template = await self.schedule_repo.create_template(template)

        # Créer les messes avec horaires ordinaires
        masses = []
        for mass_time in ORDINARY_MASS_TIMES:
            mass = SundayMassSlot(
                template_id=created_template.id,
                mass_time=mass_time["time"],
                language=mass_time["language"],
            )
            masses.append(mass)

        await self.schedule_repo.create_masses_batch(masses)

        # Retourner le modèle enrichi
        enriched = await self.schedule_repo.enrich_template(created_template)
        return SundayScheduleTemplateResponse(**enriched)

    async def generate_exceptional_template(
        self, data: GenerateExceptionalScheduleRequest, created_by: UUID
    ) -> SundayScheduleTemplateResponse:
        """Génère un modèle avec des horaires exceptionnels."""
        # Créer le modèle
        template = SundayScheduleTemplate(
            title=data.title,
            schedule_date=data.schedule_date,
            mass_type=MassType.ORDINAIRE,
            is_exceptional=True,
            notes=data.notes,
            created_by=created_by,
        )
        created_template = await self.schedule_repo.create_template(template)

        # Créer les messes avec horaires personnalisés
        masses = []
        for mass_time in data.mass_times:
            mass = SundayMassSlot(
                template_id=created_template.id,
                mass_time=mass_time.time,
                language=mass_time.language,
            )
            masses.append(mass)

        await self.schedule_repo.create_masses_batch(masses)

        # Retourner le modèle enrichi
        enriched = await self.schedule_repo.enrich_template(created_template)
        return SundayScheduleTemplateResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  LECTURE
    # ══════════════════════════════════════════════════════════════════

    async def get_template(self, template_id: UUID) -> SundayScheduleTemplateResponse:
        """Récupère un modèle par son ID avec toutes ses messes."""
        template = await self.schedule_repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )
        enriched = await self.schedule_repo.enrich_template(template)
        return SundayScheduleTemplateResponse(**enriched)

    async def list_templates(
        self,
        status_filter: Optional[SundayScheduleStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[SundayScheduleTemplateSummary]:
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
            summaries.append(SundayScheduleTemplateSummary(**summary_data))

        return PaginatedResponse(
            items=summaries,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_published_templates(
        self,
    ) -> List[SundayScheduleTemplateSummary]:
        """Récupère tous les modèles publiés (visible par tous)."""
        templates = await self.schedule_repo.get_published_templates()
        summaries = []
        for template in templates:
            summary_data = await self.schedule_repo.get_template_summary(template)
            summaries.append(SundayScheduleTemplateSummary(**summary_data))
        return summaries

    # ══════════════════════════════════════════════════════════════════
    #  MODIFICATION
    # ══════════════════════════════════════════════════════════════════

    async def update_template(
        self,
        template_id: UUID,
        data: SundayScheduleTemplateUpdate,
        updated_by: UUID,
    ) -> SundayScheduleTemplateResponse:
        """Met à jour un modèle de classement."""
        template = await self.schedule_repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )

        if data.title is not None:
            template.title = data.title
        if data.schedule_date is not None:
            template.schedule_date = data.schedule_date
        if data.mass_type is not None:
            template.mass_type = data.mass_type
        if data.is_exceptional is not None:
            template.is_exceptional = data.is_exceptional
        if data.status is not None:
            template.status = data.status
        if data.notes is not None:
            template.notes = data.notes

        template.updated_by = updated_by
        template.updated_at = utc_now()

        updated = await self.schedule_repo.update_template(template_id, template)
        enriched = await self.schedule_repo.enrich_template(updated)
        return SundayScheduleTemplateResponse(**enriched)

    async def publish_template(
        self, template_id: UUID, published_by: UUID
    ) -> SundayScheduleTemplateResponse:
        """Publie un modèle (le rend visible par tous)."""
        template = await self.schedule_repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )

        if template.status == SundayScheduleStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ce modèle est déjà publié.",
            )

        template.status = SundayScheduleStatus.PUBLISHED
        template.updated_by = published_by
        template.updated_at = utc_now()

        updated = await self.schedule_repo.update_template(template_id, template)
        enriched = await self.schedule_repo.enrich_template(updated)
        return SundayScheduleTemplateResponse(**enriched)

    async def archive_template(
        self, template_id: UUID, archived_by: UUID
    ) -> SundayScheduleTemplateResponse:
        """Archive un modèle."""
        template = await self.schedule_repo.get_template(template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )

        template.status = SundayScheduleStatus.ARCHIVED
        template.updated_by = archived_by
        template.updated_at = utc_now()

        updated = await self.schedule_repo.update_template(template_id, template)
        enriched = await self.schedule_repo.enrich_template(updated)
        return SundayScheduleTemplateResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  SUPPRESSION
    # ══════════════════════════════════════════════════════════════════

    async def delete_template(self, template_id: UUID) -> None:
        """Supprime un modèle et toutes ses messes."""
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
    #  GESTION DES MESSES
    # ══════════════════════════════════════════════════════════════════

    async def update_mass(
        self,
        mass_id: UUID,
        data: SundayMassSlotUpdate,
    ) -> SundayMassSlotResponse:
        """Met à jour une messe."""
        mass = await self.schedule_repo.get_mass(mass_id)
        if not mass:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Messe introuvable.",
            )

        if data.mass_time is not None:
            mass.mass_time = data.mass_time
        if data.language is not None:
            mass.language = data.language
        if data.notes is not None:
            mass.notes = data.notes

        mass.updated_at = utc_now()

        updated = await self.schedule_repo.update_mass(mass_id, mass)
        enriched = await self.schedule_repo.enrich_mass(updated)
        return SundayMassSlotResponse(**enriched)

    async def delete_mass(self, mass_id: UUID) -> None:
        """Supprime une messe."""
        mass = await self.schedule_repo.get_mass(mass_id)
        if not mass:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Messe introuvable.",
            )
        deleted = await self.schedule_repo.delete_mass(mass_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de la messe.",
            )

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES ASSIGNATIONS
    # ══════════════════════════════════════════════════════════════════

    async def add_assignment_to_mass(
        self,
        mass_id: UUID,
        data: SundayMassAssignmentCreate,
        assigned_by: UUID,
    ) -> SundayMassAssignmentResponse:
        """Ajoute une assignation à une messe."""
        mass = await self.schedule_repo.get_mass(mass_id)
        if not mass:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Messe introuvable.",
            )

        # Récupérer le template pour vérifier la date
        template = await self.schedule_repo.get_template(mass.template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )

        # Validation temporelle stricte : 1h avant → 1h après la messe
        if not is_within_mass_window(template.schedule_date, mass.mass_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"L'ajout de servants n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de {mass.mass_time}.",
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

        assignment = SundayMassAssignment(
            mass_slot_id=mass_id,
            position=data.position,
            servant_id=data.servant_id,
            servant_name=data.servant_name,
            notes=data.notes,
            assigned_by=assigned_by,
        )
        created = await self.schedule_repo.create_assignment(assignment)
        enriched = await self.schedule_repo.enrich_assignment(created)
        return SundayMassAssignmentResponse(**enriched)

    async def remove_assignment(self, assignment_id: UUID) -> None:
        """Retire une assignation."""
        assignment = await self.schedule_repo.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignation introuvable.",
            )

        # Récupérer la messe et le template pour vérifier la date
        mass = await self.schedule_repo.get_mass(assignment.mass_slot_id)
        if mass:
            template = await self.schedule_repo.get_template(mass.template_id)
            if template:
                # Validation temporelle stricte : 1h avant → 1h après la messe
                if not is_within_mass_window(template.schedule_date, mass.mass_time):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Le retrait de servants n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de {mass.mass_time}.",
                    )

        deleted = await self.schedule_repo.delete_assignment(assignment_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de l'assignation.",
            )

    # ══════════════════════════════════════════════════════════════════
    #  MARQUAGE DE PRÉSENCE
    # ══════════════════════════════════════════════════════════════════

    async def mark_presence(
        self,
        assignment_id: UUID,
        is_present: bool,
        marked_by: UUID,
        ip_address: Optional[str] = None,
    ) -> SundayMassAssignmentResponse:
        """Marque la présence ou l'absence d'un servant."""
        from src.core.entities.sunday_schedule import (
            ModificationAction,
            SundayScheduleModificationLog,
        )

        assignment = await self.schedule_repo.get_assignment(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignation introuvable.",
            )

        # Récupérer la messe pour avoir le template_id et l'heure
        mass = await self.schedule_repo.get_mass(assignment.mass_slot_id)
        if not mass:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Messe introuvable.",
            )

        # Récupérer le template pour avoir la date
        template = await self.schedule_repo.get_template(mass.template_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Modèle de classement introuvable.",
            )

        # Validation temporelle stricte : 1h avant → 1h après la messe
        if not is_within_mass_window(template.schedule_date, mass.mass_time):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Le marquage de présence n'est autorisé que dans la fenêtre de 1h avant à 1h après la messe de {mass.mass_time}.",
            )

        # Récupérer l'utilisateur qui marque
        user = await self.user_repo.get(marked_by)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable.",
            )

        # Sauvegarder l'ancienne valeur
        old_value = f"is_present={assignment.is_present}"

        # Mettre à jour
        assignment.is_present = is_present
        assignment.presence_marked_by = marked_by
        assignment.presence_marked_at = utc_now()
        assignment.last_modified_by = marked_by
        assignment.updated_at = utc_now()

        updated = await self.schedule_repo.update_assignment(assignment_id, assignment)

        # Créer le log
        servant_name = assignment.servant_name or "Servant inconnu"
        if assignment.servant_id:
            servant = await self.user_repo.get(assignment.servant_id)
            if servant:
                servant_name = f"{servant.first_name} {servant.last_name}"

        log = SundayScheduleModificationLog(
            template_id=mass.template_id,
            mass_slot_id=mass.id,
            assignment_id=assignment_id,
            action=ModificationAction.PRESENCE_MARKED
            if is_present
            else ModificationAction.ABSENCE_MARKED,
            description=f"Présence {'confirmée' if is_present else 'marquée absente'} pour {servant_name} ({assignment.position.value}) à la messe de {mass.mass_time}",
            modified_by=marked_by,
            modified_by_name=f"{user.first_name} {user.last_name}",
            ip_address=ip_address,
            old_value=old_value,
            new_value=f"is_present={is_present}",
        )
        await self.schedule_repo.create_modification_log(log)

        enriched = await self.schedule_repo.enrich_assignment(updated)
        return SundayMassAssignmentResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  HISTORIQUE
    # ══════════════════════════════════════════════════════════════════

    async def get_modification_history(
        self, template_id: UUID, limit: int = 100
    ) -> List:
        """Récupère l'historique des modifications d'un classement."""
        from src.presentation.schemas.sunday_schedule import ModificationLogResponse

        logs = await self.schedule_repo.get_template_modification_logs(
            template_id, limit
        )
        return [ModificationLogResponse(**log.model_dump()) for log in logs]
