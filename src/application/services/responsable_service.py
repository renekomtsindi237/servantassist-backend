"""
Service metier pour le module Responsables.

Regles metier :
- Seul l'Aumonier (ou l'Admin) peut nommer / revoquer un responsable.
- Un poste ne peut etre occupe que par un seul servant actif a la fois.
- Un servant ne peut occuper qu'un seul poste actif a la fois.
- Seul un SERVANT authentifie et ayant une nomination active peut
  creer des actions pour son poste.
- Chaque poste n'a acces qu'a ses categories d'actions autorisees.
- L'Aumonier/Admin peut consulter toutes les actions de tous les postes.
"""

import math
from datetime import datetime, timezone
from src.core.utils import utc_now
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.council_meeting import (
    CouncilAttendance,
    CouncilAttendanceStatus,
    CouncilMeeting,
)
from src.core.entities.responsable import (
    POSTE_ALLOWED_CATEGORIES,
    POSTE_MISSIONS,
    POSTE_TO_SLUG,
    SLUG_TO_POSTE,
    ActionCategory,
    ActionStatus,
    Nomination,
    NominationStatus,
    PosteAction,
    PosteResponsable,
)
from src.core.entities.user import User, UserRole
from src.core.interfaces.repositories import ICouncilMeetingRepository
from src.core.interfaces.repositories import (
    INominationRepository,
    IPosteActionRepository,
)
from src.core.interfaces.repositories import IUserRepository
from src.presentation.schemas.responsable import (
    CouncilAttendanceRecordList,
    CouncilMeetingCreate,
    CouncilMeetingResponse,
    NominationCreate,
    NominationResponse,
    PosteActionCreate,
    PosteActionResponse,
    PosteActionUpdate,
    PosteDashboardResponse,
    PosteDetailResponse,
    PosteListResponse,
)
from src.presentation.schemas.user import PaginatedResponse


class ResponsableService:
    """Logique metier des nominations et des actions de poste."""

    def __init__(
        self,
        nomination_repo: INominationRepository,
        action_repo: IPosteActionRepository,
        user_repo: IUserRepository,
        council_repo: ICouncilMeetingRepository,
    ):
        self.nomination_repo = nomination_repo
        self.action_repo = action_repo
        self.user_repo = user_repo
        self.council_repo = council_repo

    # ══════════════════════════════════════════════════════════════════
    #  NOMINATIONS (Aumonier / Admin)
    # ══════════════════════════════════════════════════════════════════

    async def nominate(self, data: NominationCreate, nominated_by: UUID) -> NominationResponse:
        """
        Nommer un servant a un poste de responsable.

        Validations :
        - L'utilisateur doit exister, etre actif et etre SERVANT
        - Le poste ne doit pas etre deja occupe
        - Le servant ne doit pas deja occuper un autre poste
        """
        # Verifier l'utilisateur
        user = await self.user_repo.get(data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable.",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="L'utilisateur n'est pas actif.",
            )
        if user.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les servants peuvent etre nommes responsables.",
            )

        # Verifier que le poste n'est pas deja occupe
        existing_poste = await self.nomination_repo.get_active_by_poste(data.poste)
        if existing_poste:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Le poste {data.poste.value} est deja occupe. "
                    f"Revoquez la nomination actuelle avant d'en creer une nouvelle."
                ),
            )

        # Verifier que le servant n'occupe pas deja un poste
        existing_nominations = await self.nomination_repo.get_active_by_user(data.user_id)
        if existing_nominations:
            postes_occupes = ", ".join(n.poste.value for n in existing_nominations)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Ce servant occupe deja le(s) poste(s) : {postes_occupes}. "
                    f"Un servant ne peut occuper qu'un seul poste a la fois."
                ),
            )

        nomination = Nomination(
            user_id=data.user_id,
            poste=data.poste,
            nominated_by=nominated_by,
            notes=data.notes,
        )
        created = await self.nomination_repo.create(nomination)
        enriched = await self.nomination_repo.enrich_nomination(created)
        return NominationResponse(**enriched)

    async def revoke(self, nomination_id: UUID, revoked_by: UUID) -> NominationResponse:
        """Revoquer une nomination (l'aumonier retire le poste)."""
        nomination = await self.nomination_repo.get(nomination_id)
        if not nomination:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nomination introuvable.",
            )
        if nomination.status == NominationStatus.REVOQUEE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cette nomination est deja revoquee.",
            )

        nomination.status = NominationStatus.REVOQUEE
        nomination.revoked_at = utc_now()
        nomination.revoked_by = revoked_by
        updated = await self.nomination_repo.update(nomination)
        enriched = await self.nomination_repo.enrich_nomination(updated)
        return NominationResponse(**enriched)

    async def list_active_nominations(self) -> List[NominationResponse]:
        """Liste toutes les nominations actives."""
        nominations = await self.nomination_repo.list_all_active()
        enriched = await self.nomination_repo.enrich_nominations(nominations)
        return [NominationResponse(**e) for e in enriched]

    async def get_my_nominations(self, user_id: UUID) -> List[NominationResponse]:
        """Mes nominations actives."""
        nominations = await self.nomination_repo.get_active_by_user(user_id)
        enriched = await self.nomination_repo.enrich_nominations(nominations)
        return [NominationResponse(**e) for e in enriched]

    async def get_nomination_history(
        self,
        user_id: Optional[UUID] = None,
        poste: Optional[PosteResponsable] = None,
    ) -> List[NominationResponse]:
        """Historique des nominations (actives + revoquees)."""
        nominations = await self.nomination_repo.list_history(user_id=user_id, poste=poste)
        enriched = await self.nomination_repo.enrich_nominations(nominations)
        return [NominationResponse(**e) for e in enriched]

    # ══════════════════════════════════════════════════════════════════
    #  POSTES (reference)
    # ══════════════════════════════════════════════════════════════════

    async def list_postes(self) -> PosteListResponse:
        """Liste tous les postes avec leur titulaire et missions."""
        postes = []
        postes_pourvus = 0

        for poste in PosteResponsable:
            missions_data = POSTE_MISSIONS.get(poste, {})
            slug = POSTE_TO_SLUG.get(poste, poste.value.lower())
            categories = POSTE_ALLOWED_CATEGORIES.get(poste, [])

            # Chercher le titulaire actif
            nomination = await self.nomination_repo.get_active_by_poste(poste)
            titulaire = None
            if nomination:
                postes_pourvus += 1
                enriched = await self.nomination_repo.enrich_nomination(nomination)
                titulaire = NominationResponse(**enriched)

            postes.append(
                PosteDetailResponse(
                    poste=poste,
                    slug=slug,
                    titre=missions_data.get("titre", poste.value),
                    description=missions_data.get("description", ""),
                    missions=missions_data.get("missions", []),
                    categories_autorisees=categories,
                    titulaire=titulaire,
                )
            )

        return PosteListResponse(
            postes=postes,
            total_postes=len(PosteResponsable),
            postes_pourvus=postes_pourvus,
            postes_vacants=len(PosteResponsable) - postes_pourvus,
        )

    async def get_poste_detail(self, poste: PosteResponsable) -> PosteDetailResponse:
        """Detail d'un poste avec titulaire et missions."""
        missions_data = POSTE_MISSIONS.get(poste, {})
        slug = POSTE_TO_SLUG.get(poste, poste.value.lower())
        categories = POSTE_ALLOWED_CATEGORIES.get(poste, [])

        nomination = await self.nomination_repo.get_active_by_poste(poste)
        titulaire = None
        if nomination:
            enriched = await self.nomination_repo.enrich_nomination(nomination)
            titulaire = NominationResponse(**enriched)

        return PosteDetailResponse(
            poste=poste,
            slug=slug,
            titre=missions_data.get("titre", poste.value),
            description=missions_data.get("description", ""),
            missions=missions_data.get("missions", []),
            categories_autorisees=categories,
            titulaire=titulaire,
        )

    # ══════════════════════════════════════════════════════════════════
    #  ACTIONS DE POSTE (Responsable)
    # ══════════════════════════════════════════════════════════════════

    async def _verify_responsable(self, user_id: UUID, poste: PosteResponsable) -> Nomination:
        """Verifie que l'utilisateur occupe le poste demande."""
        nomination = await self.nomination_repo.get_active_by_user_and_poste(user_id, poste)
        if not nomination:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Vous n'occupez pas le poste de {poste.value}.",
            )
        return nomination

    async def create_action(
        self,
        poste: PosteResponsable,
        data: PosteActionCreate,
        created_by: UUID,
    ) -> PosteActionResponse:
        """
        Creer une action pour un poste.

        Validations :
        - La categorie doit etre autorisee pour ce poste
        """
        # Verifier la categorie
        allowed = POSTE_ALLOWED_CATEGORIES.get(poste, [])
        if data.category not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"La categorie {data.category.value} n'est pas autorisee "
                    f"pour le poste {poste.value}. "
                    f"Categories autorisees : {[c.value for c in allowed]}"
                ),
            )

        # Appeler le repository avec les parametres individuels
        created = await self.action_repo.create(
            poste=poste,
            category=data.category,
            title=data.title,
            content=data.content,
            target_user_id=data.target_user_id,
            target_event_id=data.target_event_id,
            amount=data.amount,
            action_date=data.action_date,
            status=data.status,
            extra_data=data.extra_data,
            created_by=created_by,
        )
        enriched = await self.action_repo.enrich_action(created)
        return PosteActionResponse(**enriched)

    async def list_actions(
        self,
        poste: PosteResponsable,
        *,
        category: Optional[ActionCategory] = None,
        action_status: Optional[ActionStatus] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[PosteActionResponse]:
        """Liste paginee des actions d'un poste."""
        actions, total = await self.action_repo.list_by_poste(
            poste,
            category=category,
            status=action_status,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        enriched = await self.action_repo.enrich_actions(actions)
        items = [PosteActionResponse(**e) for e in enriched]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_action(self, action_id: UUID) -> PosteActionResponse:
        """Recupere une action par son ID."""
        action = await self.action_repo.get(action_id)
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action introuvable.",
            )
        enriched = await self.action_repo.enrich_action(action)
        return PosteActionResponse(**enriched)

    async def update_action(
        self,
        action_id: UUID,
        data: PosteActionUpdate,
        updated_by: UUID,
    ) -> PosteActionResponse:
        """Modifier une action existante."""
        action = await self.action_repo.get(action_id)
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action introuvable.",
            )

        # Seul le createur peut modifier (sauf Admin/Aumonier via autre route)
        if action.created_by != updated_by:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez modifier que vos propres actions.",
            )

        # Preparer les donnees a mettre a jour
        update_dict = {}
        if data.title is not None:
            update_dict["title"] = data.title
        if data.content is not None:
            update_dict["content"] = data.content
        if data.target_user_id is not None:
            update_dict["target_user_id"] = data.target_user_id
        if data.target_event_id is not None:
            update_dict["target_event_id"] = data.target_event_id
        if data.amount is not None:
            update_dict["amount"] = data.amount
        if data.action_date is not None:
            update_dict["action_date"] = data.action_date
        if data.status is not None:
            update_dict["status"] = data.status
        if data.extra_data is not None:
            update_dict["extra_data"] = data.extra_data

        # Appeler le repository avec l'ID et le dictionnaire
        updated = await self.action_repo.update(action_id, update_dict)
        enriched = await self.action_repo.enrich_action(updated)
        return PosteActionResponse(**enriched)

    async def delete_action(self, action_id: UUID, deleted_by: UUID) -> None:
        """Supprimer une action."""
        action = await self.action_repo.get(action_id)
        if not action:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action introuvable.",
            )

        if action.created_by != deleted_by:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous ne pouvez supprimer que vos propres actions.",
            )

        await self.action_repo.delete(action_id)

    async def get_dashboard(self, poste: PosteResponsable) -> PosteDashboardResponse:
        """Tableau de bord d'un poste."""
        missions_data = POSTE_MISSIONS.get(poste, {})
        slug = POSTE_TO_SLUG.get(poste, poste.value.lower())

        counts = await self.action_repo.count_by_poste_and_status(poste)
        recent = await self.action_repo.get_recent_by_poste(poste, limit=5)
        enriched_recent = await self.action_repo.enrich_actions(recent)

        total = sum(counts.values())

        return PosteDashboardResponse(
            poste=poste,
            slug=slug,
            titre=missions_data.get("titre", poste.value),
            description=missions_data.get("description", ""),
            missions=missions_data.get("missions", []),
            total_actions=total,
            actions_brouillon=counts.get(ActionStatus.BROUILLON.value, 0),
            actions_publiees=counts.get(ActionStatus.PUBLIE.value, 0),
            actions_en_cours=counts.get(ActionStatus.EN_COURS.value, 0),
            actions_terminees=counts.get(ActionStatus.TERMINE.value, 0),
            recent_actions=[PosteActionResponse(**e) for e in enriched_recent],
        )

    async def monitor_council_attendance(self, responsable_id: UUID) -> dict:
        """
        Vérifie l'assiduité d'un responsable au conseil (Art 15).
        Si 3 absences consécutives -> Destitution.
        """
        attendances = await self.council_repo.get_responsable_attendances(responsable_id, limit=3)

        if len(attendances) < 3:
            return {
                "responsable_id": responsable_id,
                "destituted": False,
                "reason": "Not enough data",
            }

        is_consecutive_absent = all(a.status == CouncilAttendanceStatus.ABSENT for a in attendances)

        if is_consecutive_absent:
            # Révoquer toutes les nominations actives
            active_nominations = await self.nomination_repo.get_active_by_user(responsable_id)
            for nom in active_nominations:
                nom.status = NominationStatus.REVOQUEE
                nom.revoked_at = utc_now()
                # System ID (Délégué d'office)
                nom.revoked_by = UUID("00000000-0000-0000-0000-000000000000")
                nom.notes = "Destitution automatique pour 3 absences consécutives au conseil (Art 15)"
                await self.nomination_repo.update(nom)

            return {
                "responsable_id": responsable_id,
                "destituted": True,
                "reason": "3 consecutive absences",
            }

        return {"responsable_id": responsable_id, "destituted": False}

    async def create_council_meeting(self, data: CouncilMeetingCreate, created_by: UUID) -> CouncilMeetingResponse:
        """Crée une nouvelle réunion du conseil (Délégué/SG)."""
        meeting = CouncilMeeting(
            meeting_date=data.meeting_date,
            location=data.location,
            agenda=data.agenda,
            created_by=created_by,
        )
        created = await self.council_repo.create_meeting(meeting)
        return CouncilMeetingResponse.from_orm(created)

    async def record_council_attendance(
        self,
        meeting_id: UUID,
        data: CouncilAttendanceRecordList,
        recorded_by: UUID = None,
    ) -> List[dict]:
        """Enregistre les présences pour une réunion (SG)."""
        meeting = await self.council_repo.get_meeting(meeting_id)
        if not meeting:
            raise HTTPException(404, "Réunion introuvable")

        results = []
        for att in data.attendances:
            status = CouncilAttendanceStatus.PRESENT if att.is_present else CouncilAttendanceStatus.ABSENT
            attendance = CouncilAttendance(
                meeting_id=meeting_id,
                responsable_id=att.responsable_id,
                status=status,
                excuse=att.excuse,
                recorded_by=recorded_by or meeting.created_by,
            )
            await self.council_repo.add_attendance(attendance)
            results.append({"responsable_id": str(att.responsable_id), "status": status.value})

        return results
