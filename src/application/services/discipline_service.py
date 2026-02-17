"""
Service metier pour le module Discipline.

Regles du reglement interieur :
- Le Censeur ouvre les dossiers disciplinaires
- Le conseil de discipline (Delegue, Vice-Delegue, Censeur, Censeur adjoint)
  rend les verdicts sous la supervision de l'Aumonier
- Les sanctions sont graduelles : verbal → ecrit → suspension → exclusion
- L'Aumonier a le dernier mot sur toute sanction
"""
import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.attendance import AttendanceStatus, AttendanceType
from src.core.entities.discipline import (
    OFFENSE_DEFAULT_SEVERITY,
    SEVERITY_RECOMMENDED_SANCTION,
    DisciplineCase,
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
    SanctionType,
)
from src.core.entities.user import User, UserRole
from src.infrastructure.repositories.attendance_repository import AttendanceRepository
from src.infrastructure.repositories.discipline_repository import DisciplineCaseRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.schemas.discipline import (
    DisciplineCaseCreate,
    DisciplineCaseResponse,
    DisciplineCaseUpdate,
    DisciplineConvocation,
    DisciplineStatsResponse,
    DisciplineVerdict,
)
from src.presentation.schemas.user import PaginatedResponse


class DisciplineService:
    """Logique metier du module disciplinaire."""

    def __init__(
        self,
        case_repo: DisciplineCaseRepository,
        user_repo: UserRepository,
        attendance_repo: AttendanceRepository,
    ):
        self.case_repo = case_repo
        self.user_repo = user_repo
        self.attendance_repo = attendance_repo

    # ══════════════════════════════════════════════════════════════════
    #  OUVRIR UN DOSSIER
    # ══════════════════════════════════════════════════════════════════

    async def open_case(self, data: DisciplineCaseCreate, reported_by: UUID) -> DisciplineCaseResponse:
        """Ouvrir un dossier disciplinaire."""
        user = await self.user_repo.get(data.accused_user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur accuse introuvable.",
            )
        if user.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les servants peuvent faire l'objet d'un dossier disciplinaire.",
            )

        severity = data.severity or OFFENSE_DEFAULT_SEVERITY.get(data.offense_category, SanctionSeverity.MINEUR)

        case = DisciplineCase(
            accused_user_id=data.accused_user_id,
            reported_by=reported_by,
            offense_category=data.offense_category,
            offense_description=data.offense_description,
            offense_date=data.offense_date or datetime.now(timezone.utc),
            severity=severity,
            status=DisciplineCaseStatus.SIGNALE,
        )
        created = await self.case_repo.create(case)
        enriched = await self.case_repo.enrich_case(created)
        return DisciplineCaseResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  CONVOQUER AU CONSEIL DE DISCIPLINE
    # ══════════════════════════════════════════════════════════════════

    async def convoke(self, case_id: UUID, data: DisciplineConvocation) -> DisciplineCaseResponse:
        """Convoquer un servant au conseil de discipline."""
        case = await self.case_repo.get(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable.",
            )
        if case.status != DisciplineCaseStatus.SIGNALE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Impossible de convoquer : statut actuel = {case.status.value}.",
            )

        case.status = DisciplineCaseStatus.CONVOQUE
        case.convocation_date = data.convocation_date
        case.convocation_notes = data.convocation_notes
        case.updated_at = datetime.now(timezone.utc)

        updated = await self.case_repo.update(case)
        enriched = await self.case_repo.enrich_case(updated)
        return DisciplineCaseResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  OUVRIR L'AUDIENCE
    # ══════════════════════════════════════════════════════════════════

    async def start_hearing(self, case_id: UUID) -> DisciplineCaseResponse:
        """Marquer l'audience comme en cours."""
        case = await self.case_repo.get(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable.",
            )
        if case.status != DisciplineCaseStatus.CONVOQUE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Impossible d'ouvrir l'audience : statut actuel = {case.status.value}.",
            )

        case.status = DisciplineCaseStatus.EN_AUDIENCE
        case.updated_at = datetime.now(timezone.utc)

        updated = await self.case_repo.update(case)
        enriched = await self.case_repo.enrich_case(updated)
        return DisciplineCaseResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  RENDRE LE VERDICT
    # ══════════════════════════════════════════════════════════════════

    async def render_verdict(self, case_id: UUID, data: DisciplineVerdict, verdict_by: UUID) -> DisciplineCaseResponse:
        """Rendre le verdict du conseil de discipline."""
        case = await self.case_repo.get(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable.",
            )
        if case.status not in (
            DisciplineCaseStatus.EN_AUDIENCE,
            DisciplineCaseStatus.CONVOQUE,
            DisciplineCaseStatus.SIGNALE,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Impossible de rendre un verdict : statut actuel = {case.status.value}.",
            )

        case.status = DisciplineCaseStatus.VERDICT_RENDU
        case.sanction_type = data.sanction_type
        case.verdict_notes = data.verdict_notes
        case.verdict_date = datetime.now(timezone.utc)
        case.verdict_by = verdict_by

        if data.sanction_type == SanctionType.SUSPENSION_TEMPORAIRE:
            days = data.suspension_days or 30
            case.suspension_days = days
            case.suspension_start = datetime.now(timezone.utc)
            case.suspension_end = datetime.now(timezone.utc) + timedelta(days=days)

        case.updated_at = datetime.now(timezone.utc)

        updated = await self.case_repo.update(case)
        enriched = await self.case_repo.enrich_case(updated)
        return DisciplineCaseResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  EXECUTER LA SANCTION
    # ══════════════════════════════════════════════════════════════════

    async def execute_sanction(self, case_id: UUID) -> DisciplineCaseResponse:
        """Marquer la sanction comme executee."""
        case = await self.case_repo.get(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable.",
            )
        if case.status != DisciplineCaseStatus.VERDICT_RENDU:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Impossible d'executer : verdict non rendu (statut = {case.status.value}).",
            )

        case.status = DisciplineCaseStatus.EXECUTE

        # En cas d'exclusion definitive, desactiver le compte du servant
        if case.sanction_type == SanctionType.EXCLUSION_DEFINITIVE:
            user = await self.user_repo.get(case.accused_user_id)
            if user:
                user.is_active = False
                user.updated_at = datetime.now(timezone.utc)
                await self.user_repo.update(user.id, user)

        case.updated_at = datetime.now(timezone.utc)
        updated = await self.case_repo.update(case)
        enriched = await self.case_repo.enrich_case(updated)
        return DisciplineCaseResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  CLASSER SANS SUITE
    # ══════════════════════════════════════════════════════════════════

    async def dismiss_case(self, case_id: UUID, notes: Optional[str] = None) -> DisciplineCaseResponse:
        """Classer un dossier sans suite."""
        case = await self.case_repo.get(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable.",
            )
        if case.status in (
            DisciplineCaseStatus.EXECUTE,
            DisciplineCaseStatus.CLASSE,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dossier deja termine (statut = {case.status.value}).",
            )

        case.status = DisciplineCaseStatus.CLASSE
        case.sanction_type = SanctionType.AUCUNE
        if notes:
            case.verdict_notes = notes
        case.verdict_date = datetime.now(timezone.utc)
        case.updated_at = datetime.now(timezone.utc)

        updated = await self.case_repo.update(case)
        enriched = await self.case_repo.enrich_case(updated)
        return DisciplineCaseResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  LECTURE
    # ══════════════════════════════════════════════════════════════════

    async def get_case(self, case_id: UUID) -> DisciplineCaseResponse:
        case = await self.case_repo.get(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable.",
            )
        enriched = await self.case_repo.enrich_case(case)
        return DisciplineCaseResponse(**enriched)

    async def list_cases(
        self,
        *,
        accused_user_id: Optional[UUID] = None,
        case_status: Optional[DisciplineCaseStatus] = None,
        severity: Optional[SanctionSeverity] = None,
        offense_category: Optional[OffenseCategory] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[DisciplineCaseResponse]:
        cases, total = await self.case_repo.list_paginated(
            accused_user_id=accused_user_id,
            status=case_status,
            severity=severity,
            offense_category=offense_category,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        enriched = await self.case_repo.enrich_cases(cases)
        items = [DisciplineCaseResponse(**e) for e in enriched]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_user_discipline_stats(self, user_id: UUID) -> DisciplineStatsResponse:
        counts = await self.case_repo.count_sanctions_by_user(user_id)
        active = await self.case_repo.count_active_cases(user_id)

        return DisciplineStatsResponse(
            user_id=user_id,
            total_cases=sum(counts.values()) + active,
            avertissements_verbaux=counts.get(SanctionType.AVERTISSEMENT_VERBAL.value, 0),
            avertissements_ecrits=counts.get(SanctionType.AVERTISSEMENT_ECRIT.value, 0),
            suspensions=counts.get(SanctionType.SUSPENSION_TEMPORAIRE.value, 0),
            cases_en_cours=active,
        )

    async def check_attendance_compliance(self, user_id: UUID) -> dict:
        """
        Vérifie l'assiduité (Art 42, 50) :
        - 2 absences consécutives aux réunions -> Suspension 1 semaine.
        - 6 mois d'absence continue -> Radiation.
        """
        # Récupérer les 2 dernières réunions hebdomadaires
        attendances, _ = await self.attendance_repo.list_paginated(
            user_id=user_id, attendance_type=AttendanceType.WEEKLY, page_size=2
        )

        consecutive_absences = (
            all(a.status == AttendanceStatus.ABSENT for a in attendances) if len(attendances) >= 2 else False
        )

        # Vérifier l'absence continue sur 6 mois
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
        recent_activity, _ = await self.attendance_repo.list_paginated(
            user_id=user_id, start_date=six_months_ago, page_size=1
        )

        continuous_absence = len(recent_activity) == 0  # Aucune présence enregistrée en 6 mois

        return {
            "user_id": user_id,
            "two_consecutive_absences": consecutive_absences,
            "six_months_continuous_absence": continuous_absence,
            "suggested_sanction": (
                SanctionType.EXCLUSION_DEFINITIVE
                if continuous_absence
                else SanctionType.SUSPENSION_TEMPORAIRE
                if consecutive_absences
                else SanctionType.AUCUNE
            ),
        }
