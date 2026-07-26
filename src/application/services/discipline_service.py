"""
Service metier pour le module Discipline.

Regles du reglement interieur :
- Le Censeur ouvre les dossiers disciplinaires
- Le conseil de discipline (Delegue, Vice-Delegue, Censeur, Censeur adjoint)
  rend les verdicts sous la supervision de l'Aumonier
- Les sanctions sont graduelles : verbal → ecrit → suspension → exclusion
- L'Aumonier a le dernier mot sur toute sanction
"""

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

from src.core.entities.attendance import AttendanceStatus, AttendanceType
from src.core.entities.discipline import (
    COUNCIL_POSTES,
    OFFENSE_DEFAULT_SEVERITY,
    SEVERITY_RECOMMENDED_SANCTION,
    DisciplineCase,
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
    SanctionType,
)
from src.core.entities.responsable import PosteResponsable
from src.core.entities.user import User, UserRole

# ═══════════════════════════════════════════════════════════════════════════
#  Portee des sanctions pouvant etre rendues directement par poste
#  (hors Aumonier, qui a toujours pouvoir sur tout type de sanction).
# ═══════════════════════════════════════════════════════════════════════════

# Sanctions "mineures/routinieres" (Art. 39-44) que le Censeur decide
# directement, sans passer par le vote collegial du conseil (Art. 16-17).
_MINOR_SANCTIONS = frozenset(
    {
        SanctionType.AVERTISSEMENT_VERBAL,
        SanctionType.AVERTISSEMENT_ECRIT,
        SanctionType.CORVEE_INTENSIVE,
        SanctionType.LETTRE_EXCUSE,
        SanctionType.RECYCLAGE_SERVICE,
        SanctionType.SUSPENSION_TEMPORAIRE,
    }
)

# None = tout type de sanction autorise. Un ensemble = uniquement ces types.
RENDER_VERDICT_SANCTION_SCOPE: dict[PosteResponsable, Optional[frozenset]] = {
    # Le Censeur decide les punitions courantes (Art. 39-44) ET peut
    # prononcer une radiation (Art. 51 : "prononcee par le Secretaire
    # General ou le Censeur").
    PosteResponsable.CENSEUR: None,
    # L'adjoint assure l'interim des punitions courantes (Art. 40), mais
    # l'Art. 51 ne nomme que le Censeur titulaire pour la radiation.
    PosteResponsable.CENSEUR_ADJOINT: _MINOR_SANCTIONS,
    # Seul pouvoir disciplinaire explicite du Secretaire General : la
    # radiation (Art. 51), apres avis du conseil et de l'Aumonier.
    PosteResponsable.SECRETAIRE_GENERAL: frozenset({SanctionType.EXCLUSION_DEFINITIVE}),
    # Le Cerémoniaire decide une punition pour trouble durant la
    # celebration eucharistique (Art. 41) — un motif mineur, pas de pouvoir
    # de suspension ou de radiation.
    PosteResponsable.CEREMONIAIRE: frozenset(
        {
            SanctionType.AVERTISSEMENT_VERBAL,
            SanctionType.AVERTISSEMENT_ECRIT,
            SanctionType.CORVEE_INTENSIVE,
            SanctionType.LETTRE_EXCUSE,
            SanctionType.RECYCLAGE_SERVICE,
        }
    ),
}
from src.core.events.domain_events import DisciplineCaseOpened, DisciplineSanctionIssued
from src.core.interfaces.repositories import (
    IAttendanceRepository,
    IDisciplineCaseRepository,
    INominationRepository,
    IUserRepository,
)
from src.core.utils import utc_now
from src.infrastructure.events.bus import event_bus
from src.presentation.schemas.discipline import (
    DisciplineCaseCreate,
    DisciplineCaseResponse,
    DisciplineCaseUpdate,
    DisciplineConvocation,
    DisciplineStatsResponse,
    DisciplineVerdict,
    DisciplineVoteCast,
    DisciplineVoteResponse,
    DisciplineVoteStatusResponse,
)
from src.presentation.schemas.user import PaginatedResponse


class DisciplineService:
    """Logique metier du module disciplinaire."""

    def __init__(
        self,
        case_repo: IDisciplineCaseRepository,
        user_repo: IUserRepository,
        attendance_repo: IAttendanceRepository,
        nomination_repo: Optional[INominationRepository] = None,
    ):
        self.case_repo = case_repo
        self.user_repo = user_repo
        self.attendance_repo = attendance_repo
        self.nomination_repo = nomination_repo

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
            offense_date=data.offense_date or utc_now(),
            severity=severity,
            status=DisciplineCaseStatus.SIGNALE,
        )
        created = await self.case_repo.create(case)
        await event_bus.publish(
            DisciplineCaseOpened(
                case_id=created.id,
                accused_user_id=data.accused_user_id,
                opened_by_id=reported_by,
                offense_category=data.offense_category.value,
                accused_email=user.email if user.email else None,
                accused_first_name=user.first_name if user.first_name else None,
            )
        )

        if data.offense_category == OffenseCategory.NON_RESPECT_TENUE:
            await self._check_tenue_incorrecte_convocation(data.accused_user_id, reported_by)

        enriched = await self.case_repo.enrich_case(created)
        return DisciplineCaseResponse(**enriched)

    async def _check_tenue_incorrecte_convocation(self, accused_user_id: UUID, reported_by: UUID) -> None:
        """
        Tenue incorrecte 3 fois de suite (Art. 48) -> convocation des parents.

        Ne doit jamais faire echouer l'ouverture du dossier disciplinaire.
        """
        try:
            since = utc_now() - timedelta(days=90)
            count = await self.case_repo.count_by_offense_category_since(
                accused_user_id, OffenseCategory.NON_RESPECT_TENUE, since
            )
            if count >= 3:
                from src.application.services.convocation_service import ConvocationService
                from src.core.entities.convocation import ConvocationMotif
                from src.infrastructure.repositories.convocation_repository import (
                    ConvocationRepository,
                )

                convocation_service = ConvocationService(
                    convocation_repo=ConvocationRepository(self.case_repo.session),
                    user_repo=self.user_repo,
                )
                await convocation_service.create_if_not_pending(
                    servant_id=accused_user_id,
                    motif=ConvocationMotif.TENUE_INCORRECTE,
                    details=f"{count} manquements a la tenue vestimentaire sur les 3 derniers mois.",
                    convened_by=reported_by,
                )
        except Exception as exc:
            logger.warning("Création de la convocation tenue incorrecte a échoué: %s", exc)

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
        case.updated_at = utc_now()

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
        case.updated_at = utc_now()

        updated = await self.case_repo.update(case)
        enriched = await self.case_repo.enrich_case(updated)
        return DisciplineCaseResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  RENDRE LE VERDICT
    # ══════════════════════════════════════════════════════════════════

    async def _check_verdict_authority(self, decider: User, sanction_type: SanctionType) -> None:
        """
        Verifie que `decider` peut rendre un verdict fixant `sanction_type`.

        L'Aumonier peut toujours tout faire. Pour les autres, le poste actif
        (Censeur, Censeur Adjoint, Secretaire General, Ceremoniaire) doit
        figurer dans RENDER_VERDICT_SANCTION_SCOPE avec ce type de sanction
        autorise (None = tous types). Leve 403 sinon.
        """
        if decider.role == UserRole.AUMÔNIER:
            return

        nominations = []
        if self.nomination_repo is not None:
            nominations = await self.nomination_repo.get_active_by_user(decider.id)

        for nomination in nominations:
            scope = RENDER_VERDICT_SANCTION_SCOPE.get(nomination.poste)
            if scope is None and nomination.poste in RENDER_VERDICT_SANCTION_SCOPE:
                return  # poste autorise sans restriction de type
            if scope is not None and sanction_type in scope:
                return

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(f"Votre poste ne vous autorise pas a prononcer une sanction de type " f"{sanction_type.value}."),
        )

    async def render_verdict(self, case_id: UUID, data: DisciplineVerdict, decider: User) -> DisciplineCaseResponse:
        """Rendre directement un verdict (Aumonier, ou poste habilite selon le type de sanction)."""
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

        await self._check_verdict_authority(decider, data.sanction_type)
        verdict_by = decider.id

        case.status = DisciplineCaseStatus.VERDICT_RENDU
        case.sanction_type = data.sanction_type
        case.verdict_notes = data.verdict_notes
        case.verdict_date = utc_now()
        case.verdict_by = verdict_by

        if data.sanction_type == SanctionType.SUSPENSION_TEMPORAIRE:
            days = data.suspension_days or 30
            case.suspension_days = days
            case.suspension_start = utc_now()
            case.suspension_end = datetime.now(timezone.utc) + timedelta(days=days)

        case.updated_at = utc_now()

        updated = await self.case_repo.update(case)
        await event_bus.publish(
            DisciplineSanctionIssued(
                case_id=case_id,
                accused_user_id=case.accused_user_id,
                sanction_type=data.sanction_type.value,
                issued_by_id=verdict_by,
            )
        )
        enriched = await self.case_repo.enrich_case(updated)
        return DisciplineCaseResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  CONSEIL DE DISCIPLINE — VOTE COLLEGIAL (Art. 16-17)
    # ══════════════════════════════════════════════════════════════════

    async def _council_quorum(self) -> tuple[list[PosteResponsable], int]:
        """Sieges du conseil actuellement pourvus + majorite requise parmi eux."""
        seats_filled: list[PosteResponsable] = []
        for poste in COUNCIL_POSTES:
            nomination = await self.nomination_repo.get_active_by_poste(poste)
            if nomination:
                seats_filled.append(poste)
        majority_required = len(seats_filled) // 2 + 1
        return seats_filled, majority_required

    async def cast_vote(self, case_id: UUID, voter: User, data: DisciplineVoteCast) -> DisciplineCaseResponse:
        """
        Enregistre le vote d'un siege du conseil de discipline.

        Le verdict est rendu automatiquement des qu'une majorite simple des
        sieges actuellement pourvus (parmi les 7 du conseil) se prononce pour
        la meme sanction. Un siege vacant ne bloque pas le quorum.
        """
        case = await self.case_repo.get(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable.",
            )
        if case.status not in (
            DisciplineCaseStatus.SIGNALE,
            DisciplineCaseStatus.CONVOQUE,
            DisciplineCaseStatus.EN_AUDIENCE,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Impossible de voter : statut actuel = {case.status.value}.",
            )

        nominations = await self.nomination_repo.get_active_by_user(voter.id)
        council_nomination = next((n for n in nominations if n.poste in COUNCIL_POSTES), None)
        if not council_nomination:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Vous n'occupez pas un siege du conseil de discipline.",
            )

        await self.case_repo.upsert_vote(
            case_id=case_id,
            poste=council_nomination.poste.value,
            voter_user_id=voter.id,
            sanction_type=data.sanction_type,
            notes=data.notes,
        )

        seats_filled, majority_required = await self._council_quorum()
        valid_poste_values = {p.value for p in seats_filled}
        votes = await self.case_repo.list_votes(case_id)

        tally: dict[str, int] = {}
        for v in votes:
            if v.poste in valid_poste_values:
                tally[v.sanction_type.value] = tally.get(v.sanction_type.value, 0) + 1

        decided_sanction: Optional[SanctionType] = None
        for sanction_value, count in tally.items():
            if count >= majority_required:
                decided_sanction = SanctionType(sanction_value)
                break

        if decided_sanction is None:
            enriched = await self.case_repo.enrich_case(case)
            return DisciplineCaseResponse(**enriched)

        case.status = DisciplineCaseStatus.VERDICT_RENDU
        case.sanction_type = decided_sanction
        case.verdict_notes = data.notes
        case.verdict_date = utc_now()
        case.verdict_by = voter.id

        if decided_sanction == SanctionType.SUSPENSION_TEMPORAIRE:
            days = 30
            case.suspension_days = days
            case.suspension_start = utc_now()
            case.suspension_end = datetime.now(timezone.utc) + timedelta(days=days)

        case.updated_at = utc_now()
        updated = await self.case_repo.update(case)
        await event_bus.publish(
            DisciplineSanctionIssued(
                case_id=case_id,
                accused_user_id=case.accused_user_id,
                sanction_type=decided_sanction.value,
                issued_by_id=voter.id,
            )
        )
        enriched = await self.case_repo.enrich_case(updated)
        return DisciplineCaseResponse(**enriched)

    async def get_vote_status(self, case_id: UUID) -> DisciplineVoteStatusResponse:
        """Etat d'avancement du vote collegial sur un dossier."""
        case = await self.case_repo.get(case_id)
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dossier introuvable.",
            )

        seats_filled, majority_required = await self._council_quorum()
        valid_poste_values = {p.value for p in seats_filled}
        votes = await self.case_repo.list_votes(case_id)

        vote_responses: list[DisciplineVoteResponse] = []
        tally: dict[str, int] = {}
        for v in votes:
            user = await self.user_repo.get(v.voter_user_id)
            voter_name = f"{user.first_name} {user.last_name}" if user else None
            vote_responses.append(
                DisciplineVoteResponse(
                    poste=v.poste,
                    voter_user_id=v.voter_user_id,
                    voter_name=voter_name,
                    sanction_type=v.sanction_type,
                    notes=v.notes,
                    voted_at=v.voted_at,
                )
            )
            if v.poste in valid_poste_values:
                tally[v.sanction_type.value] = tally.get(v.sanction_type.value, 0) + 1

        return DisciplineVoteStatusResponse(
            case_id=case_id,
            seats_filled=len(seats_filled),
            majority_required=majority_required,
            votes=vote_responses,
            tally=tally,
            is_decided=case.status in (DisciplineCaseStatus.VERDICT_RENDU, DisciplineCaseStatus.EXECUTE),
        )

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
                user.updated_at = utc_now()
                await self.user_repo.update(user.id, user)

        case.updated_at = utc_now()
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
        case.verdict_date = utc_now()
        case.updated_at = utc_now()

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
            user_id=user_id,
            attendance_type=AttendanceType.REUNION_ORDINAIRE,
            page_size=2,
        )

        consecutive_absences = (
            all(a.status == AttendanceStatus.ABSENT for a in attendances) if len(attendances) >= 2 else False
        )

        # Vérifier l'absence continue sur 6 mois
        six_months_ago = utc_now() - timedelta(days=180)
        recent_activity, _ = await self.attendance_repo.list_paginated(
            user_id=user_id, start_date=six_months_ago, page_size=1
        )

        # Aucune présence enregistrée en 6 mois
        continuous_absence = len(recent_activity) == 0

        return {
            "user_id": user_id,
            "two_consecutive_absences": consecutive_absences,
            "six_months_continuous_absence": continuous_absence,
            "suggested_sanction": (
                SanctionType.EXCLUSION_DEFINITIVE
                if continuous_absence
                else SanctionType.SUSPENSION_TEMPORAIRE if consecutive_absences else SanctionType.AUCUNE
            ),
        }
