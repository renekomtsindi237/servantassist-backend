"""
Service metier pour la gestion des affectations liturgiques.

Regles metier :
- Seuls l'Aumonier et l'Admin peuvent creer/modifier/supprimer des affectations.
- Le servant affecte peut accepter ou decliner (self-service).
- L'Aumonier/Admin peut marquer la presence (PRESENT/ABSENT).
- Un servant ne peut pas etre affecte deux fois au meme evenement
  avec le meme role liturgique.
- L'utilisateur affecte doit exister, etre actif et etre SERVANT.
- L'evenement doit exister.
- La creation par lot (batch) gere les erreurs individuellement
  et retourne un rapport detaille.
"""
import math
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.assignment import Assignment, AssignmentStatus, LiturgicalRole
from src.core.entities.event import Event
from src.core.entities.user import User, UserRole
from src.infrastructure.repositories.assignment_repository import AssignmentRepository
from src.infrastructure.repositories.event_repository import EventRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.schemas.assignment import (
    AssignmentBatchCreate,
    AssignmentBatchResponse,
    AssignmentCreate,
    AssignmentResponse,
    AssignmentStatusUpdate,
    AssignmentUpdate,
)
from src.presentation.schemas.user import PaginatedResponse


class AssignmentService:
    """Logique metier des affectations liturgiques."""

    def __init__(
        self,
        assignment_repository: AssignmentRepository,
        event_repository: EventRepository,
        user_repository: UserRepository,
    ):
        self.assignment_repo = assignment_repository
        self.event_repo = event_repository
        self.user_repo = user_repository

    # ══════════════════════════════════════════════════════════════════
    #  CREATION
    # ══════════════════════════════════════════════════════════════════

    async def create_assignment(
        self, data: AssignmentCreate, assigned_by: UUID
    ) -> AssignmentResponse:
        """
        Cree une affectation unique.

        Validations :
        - L'evenement existe
        - L'utilisateur existe, est actif et est SERVANT
        - Pas de doublon (meme user + meme event + meme role actif)
        """
        # Verifier l'evenement
        event = await self.event_repo.get(data.event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evenement introuvable.",
            )

        # Verifier l'utilisateur
        user = await self.user_repo.get(data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Utilisateur {data.user_id} introuvable.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'utilisateur n'est pas actif.",
            )
        if user.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les servants peuvent recevoir des affectations liturgiques.",
            )

        # Verifier doublon
        existing = await self.assignment_repo.get_by_event_user_role(
            data.event_id, data.user_id, data.liturgical_role
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ce servant est deja affecte comme {data.liturgical_role.value} "
                    f"a cet evenement."
                ),
            )

        assignment = Assignment(
            event_id=data.event_id,
            user_id=data.user_id,
            liturgical_role=data.liturgical_role,
            notes=data.notes,
            assigned_by=assigned_by,
        )
        created = await self.assignment_repo.create(assignment)
        enriched = await self.assignment_repo.enrich_assignment(created)
        return AssignmentResponse(**enriched)

    async def create_batch(
        self, data: AssignmentBatchCreate, assigned_by: UUID
    ) -> AssignmentBatchResponse:
        """
        Cree plusieurs affectations pour un meme evenement en une seule requete.

        Chaque affectation est traitee independamment : une erreur sur l'une
        n'empeche pas la creation des autres.
        """
        # Verifier l'evenement
        event = await self.event_repo.get(data.event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evenement introuvable.",
            )

        created_list: List[AssignmentResponse] = []
        errors: List[str] = []

        for item in data.assignments:
            try:
                # Verifier l'utilisateur
                user = await self.user_repo.get(item.user_id)
                if not user:
                    errors.append(f"Utilisateur {item.user_id} introuvable.")
                    continue
                if not user.is_active:
                    errors.append(
                        f"Utilisateur {user.first_name} {user.last_name} inactif."
                    )
                    continue
                if user.role != UserRole.SERVANT:
                    errors.append(
                        f"{user.first_name} {user.last_name} n'est pas un servant."
                    )
                    continue

                # Verifier doublon
                existing = await self.assignment_repo.get_by_event_user_role(
                    data.event_id, item.user_id, item.liturgical_role
                )
                if existing:
                    errors.append(
                        f"{user.first_name} {user.last_name} est deja "
                        f"{item.liturgical_role.value} pour cet evenement."
                    )
                    continue

                assignment = Assignment(
                    event_id=data.event_id,
                    user_id=item.user_id,
                    liturgical_role=item.liturgical_role,
                    notes=item.notes,
                    assigned_by=assigned_by,
                )
                created = await self.assignment_repo.create(assignment)
                enriched = await self.assignment_repo.enrich_assignment(created)
                created_list.append(AssignmentResponse(**enriched))

            except Exception as exc:
                errors.append(f"Erreur pour l'utilisateur {item.user_id}: {str(exc)}")

        return AssignmentBatchResponse(
            created=created_list,
            errors=errors,
            total_created=len(created_list),
            total_errors=len(errors),
        )

    # ══════════════════════════════════════════════════════════════════
    #  LECTURE
    # ══════════════════════════════════════════════════════════════════

    async def get_assignment(self, assignment_id: UUID) -> AssignmentResponse:
        """Recupere une affectation par son ID."""
        assignment = await self.assignment_repo.get(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affectation introuvable.",
            )
        enriched = await self.assignment_repo.enrich_assignment(assignment)
        return AssignmentResponse(**enriched)

    async def list_assignments(
        self,
        *,
        event_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        assignment_status: Optional[AssignmentStatus] = None,
        liturgical_role: Optional[LiturgicalRole] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[AssignmentResponse]:
        """Liste paginee de toutes les affectations avec filtres."""
        assignments, total = await self.assignment_repo.list_paginated(
            event_id=event_id,
            user_id=user_id,
            status=assignment_status,
            liturgical_role=liturgical_role,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        enriched = await self.assignment_repo.enrich_assignments(assignments)
        items = [AssignmentResponse(**e) for e in enriched]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_event_assignments(self, event_id: UUID) -> List[AssignmentResponse]:
        """Toutes les affectations actives d'un evenement."""
        event = await self.event_repo.get(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evenement introuvable.",
            )
        assignments = await self.assignment_repo.list_by_event(event_id)
        # Filtrer les annulees
        active = [a for a in assignments if a.status != AssignmentStatus.CANCELLED]
        enriched = await self.assignment_repo.enrich_assignments(active)
        return [AssignmentResponse(**e) for e in enriched]

    async def get_my_assignments(self, user_id: UUID) -> List[AssignmentResponse]:
        """Toutes les affectations du servant connecte."""
        assignments = await self.assignment_repo.list_by_user(user_id)
        enriched = await self.assignment_repo.enrich_assignments(assignments)
        return [AssignmentResponse(**e) for e in enriched]

    async def get_my_upcoming(self, user_id: UUID) -> List[AssignmentResponse]:
        """Affectations a venir du servant (evenements futurs, statut PENDING ou ACCEPTED)."""
        assignments = await self.assignment_repo.get_upcoming_for_user(user_id)
        enriched = await self.assignment_repo.enrich_assignments(assignments)
        return [AssignmentResponse(**e) for e in enriched]

    # ══════════════════════════════════════════════════════════════════
    #  MODIFICATION
    # ══════════════════════════════════════════════════════════════════

    async def update_assignment(
        self,
        assignment_id: UUID,
        data: AssignmentUpdate,
        updated_by: UUID,
    ) -> AssignmentResponse:
        """
        Modification partielle d'une affectation (Aumonier/Admin).
        Peut modifier le role, le statut (y compris PRESENT/ABSENT/CANCELLED)
        et les notes.
        """
        assignment = await self.assignment_repo.get(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affectation introuvable.",
            )

        if data.liturgical_role is not None:
            # Verifier pas de doublon avec le nouveau role
            if data.liturgical_role != assignment.liturgical_role:
                existing = await self.assignment_repo.get_by_event_user_role(
                    assignment.event_id, assignment.user_id, data.liturgical_role
                )
                if existing and existing.id != assignment.id:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Ce servant a deja une affectation "
                            f"{data.liturgical_role.value} pour cet evenement."
                        ),
                    )
            assignment.liturgical_role = data.liturgical_role

        if data.status is not None:
            assignment.status = data.status

        if data.notes is not None:
            assignment.notes = data.notes

        assignment.updated_at = datetime.now(timezone.utc)
        updated = await self.assignment_repo.update(assignment_id, assignment)
        enriched = await self.assignment_repo.enrich_assignment(updated)
        return AssignmentResponse(**enriched)

    async def update_my_status(
        self,
        assignment_id: UUID,
        data: AssignmentStatusUpdate,
        user_id: UUID,
    ) -> AssignmentResponse:
        """
        Self-service : le servant accepte ou decline son affectation.

        Seules les transitions PENDING → ACCEPTED ou PENDING → DECLINED
        sont autorisees.
        """
        assignment = await self.assignment_repo.get(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affectation introuvable.",
            )

        # Verifier que c'est bien l'affectation du servant
        if assignment.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez modifier que vos propres affectations.",
            )

        # Verifier le statut actuel
        if assignment.status != AssignmentStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Impossible de changer le statut. "
                    f"Statut actuel : {assignment.status.value}. "
                    f"Seules les affectations en attente peuvent etre acceptees ou declinees."
                ),
            )

        # Verifier la transition
        allowed = {AssignmentStatus.ACCEPTED, AssignmentStatus.DECLINED}
        if data.status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Vous ne pouvez qu'accepter ou decliner. "
                    f"Statuts autorises : {[s.value for s in allowed]}"
                ),
            )

        assignment.status = data.status
        assignment.updated_at = datetime.now(timezone.utc)
        updated = await self.assignment_repo.update(assignment_id, assignment)
        enriched = await self.assignment_repo.enrich_assignment(updated)
        return AssignmentResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  SUPPRESSION
    # ══════════════════════════════════════════════════════════════════

    async def delete_assignment(self, assignment_id: UUID) -> None:
        """Supprime une affectation."""
        assignment = await self.assignment_repo.get(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affectation introuvable.",
            )
        deleted = await self.assignment_repo.delete(assignment_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de l'affectation.",
            )

    async def cancel_assignment(
        self, assignment_id: UUID, cancelled_by: UUID
    ) -> AssignmentResponse:
        """
        Annule une affectation (soft-delete : passe le statut a CANCELLED).
        L'affectation reste en BDD pour l'historique.
        """
        assignment = await self.assignment_repo.get(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affectation introuvable.",
            )

        if assignment.status == AssignmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cette affectation est deja annulee.",
            )

        assignment.status = AssignmentStatus.CANCELLED
        assignment.updated_at = datetime.now(timezone.utc)
        updated = await self.assignment_repo.update(assignment_id, assignment)
        enriched = await self.assignment_repo.enrich_assignment(updated)
        return AssignmentResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  PRESENCE
    # ══════════════════════════════════════════════════════════════════

    async def mark_presence(
        self,
        assignment_id: UUID,
        present: bool,
        marked_by: UUID,
    ) -> AssignmentResponse:
        """
        Marque la presence ou l'absence d'un servant le jour J.
        Seuls l'Aumonier et l'Admin peuvent appeler cette methode.
        """
        assignment = await self.assignment_repo.get(assignment_id)
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affectation introuvable.",
            )

        if assignment.status == AssignmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de marquer la presence d'une affectation annulee.",
            )

        assignment.status = (
            AssignmentStatus.PRESENT if present else AssignmentStatus.ABSENT
        )
        assignment.updated_at = datetime.now(timezone.utc)
        updated = await self.assignment_repo.update(assignment_id, assignment)
        enriched = await self.assignment_repo.enrich_assignment(updated)
        return AssignmentResponse(**enriched)
