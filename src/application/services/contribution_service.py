"""
Service métier pour la gestion des contributions financières (ECONOME).

Règles métier :
- Seul l'ECONOME peut enregistrer/modifier les contributions
- Paiement hebdomadaire : 100 FCFA/samedi (4 semaines = 400 FCFA/mois)
- Paiement mensuel : 500 FCFA/mois
- Traçabilité complète de tous les paiements
"""
import math
from datetime import datetime, timezone
from src.core.utils import utc_now
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.contribution import Contribution, FinancialReport, MonthlyContributionSummary, PaymentMode, PaymentStatus
from src.core.entities.user import UserRole
from src.core.interfaces.repositories import IContributionRepository
from src.core.interfaces.repositories import IUserRepository
from src.presentation.schemas.contribution import (
    ContributionCreate,
    ContributionResponse,
    ContributionUpdate,
    FinancialReportRequest,
    FinancialReportResponse,
    MonthlyContributionSummaryResponse,
    ServantContributionStats,
)
from src.presentation.schemas.user import PaginatedResponse


class ContributionService:
    """Logique métier des contributions financières."""

    def __init__(
        self,
        contribution_repository: IContributionRepository,
        user_repository: IUserRepository,
    ):
        self.contribution_repo = contribution_repository
        self.user_repo = user_repository

    # ══════════════════════════════════════════════════════════════════
    #  CRÉATION
    # ══════════════════════════════════════════════════════════════════

    async def record_payment(self, data: ContributionCreate,
                             recorded_by: UUID) -> ContributionResponse:
        """Enregistre un paiement de contribution."""
        # Valider que le servant existe
        servant = await self.user_repo.get(data.servant_id)
        if not servant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servant introuvable.",
            )

        if servant.role != UserRole.SERVANT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{
    servant.first_name} {
        servant.last_name} n'est pas un servant.",
            )

        # Validation: montant doit être positif
        if data.amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le montant doit être positif.",
            )

        # Validation: paiement hebdomadaire nécessite un numéro de semaine
        if data.payment_mode == PaymentMode.WEEKLY:
            if data.week_number is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Le numéro de semaine est requis pour un paiement hebdomadaire.",
                )
            # Validation optionnelle: montant hebdomadaire devrait être 100
            # FCFA
            if data.amount != 100:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Le montant hebdomadaire doit être de 100 FCFA.",
                )

        # Validation: paiement mensuel ne doit pas avoir de numéro de semaine
        if data.payment_mode == PaymentMode.MONTHLY:
            if data.week_number is not None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Le numéro de semaine ne doit pas être fourni pour un paiement mensuel.",
                )
            # Validation optionnelle: montant mensuel devrait être 500 FCFA
            if data.amount != 500:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Le montant mensuel doit être de 500 FCFA.",
                )

        # Créer la contribution
        contribution = Contribution(
            servant_id=data.servant_id,
            amount=data.amount,
            payment_mode=data.payment_mode,
            payment_date=data.payment_date,
            month=data.month,
            year=data.year,
            week_number=data.week_number,
            recorded_by=recorded_by,
            notes=data.notes,
        )

        created = await self.contribution_repo.create(contribution)
        enriched = await self.contribution_repo.enrich_contribution(created)
        return ContributionResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  LECTURE
    # ══════════════════════════════════════════════════════════════════

    async def get_contribution(
        self, contribution_id: UUID) -> ContributionResponse:
        """Récupère une contribution par son ID."""
        contribution = await self.contribution_repo.get(contribution_id)
        if not contribution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contribution introuvable.",
            )

        enriched = await self.contribution_repo.enrich_contribution(contribution)
        return ContributionResponse(**enriched)

    async def list_contributions(
        self,
        servant_id: Optional[UUID] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        payment_mode: Optional[PaymentMode] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[ContributionResponse]:
        """Liste les contributions avec filtres."""
        contributions, total = await self.contribution_repo.list(
            servant_id=servant_id,
            month=month,
            year=year,
            payment_mode=payment_mode,
            page=page,
            page_size=page_size,
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1

        # Enrichir les contributions
        enriched_list = []
        for contribution in contributions:
            enriched = await self.contribution_repo.enrich_contribution(contribution)
            enriched_list.append(ContributionResponse(**enriched))

        return PaginatedResponse(
            items=enriched_list,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def get_servant_contributions(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[ContributionResponse]:
        """Récupère toutes les contributions d'un servant."""
        # Valider que le servant existe
        servant = await self.user_repo.get(servant_id)
        if not servant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servant introuvable.",
            )

        contributions = await self.contribution_repo.get_servant_contributions(servant_id, start_date, end_date)

        # Enrichir
        enriched_list = []
        for contribution in contributions:
            enriched = await self.contribution_repo.enrich_contribution(contribution)
            enriched_list.append(ContributionResponse(**enriched))

        return enriched_list

    async def get_monthly_summary(
        self, month: int, year: int) -> List[MonthlyContributionSummaryResponse]:
        """Génère le résumé mensuel pour tous les servants."""
        # Récupérer tous les servants
        servants = await self.contribution_repo.get_all_servants()

        summaries = []
        for servant in servants:
            summary = await self.contribution_repo.get_monthly_summary(servant.id, month, year)

            # Enrichir les contributions
            enriched_payments = []
            for payment in summary.payments:
                enriched = await self.contribution_repo.enrich_contribution(payment)
                enriched_payments.append(ContributionResponse(**enriched))

            summary_dict = summary.model_dump()
            summary_dict["payments"] = enriched_payments
            summaries.append(
    MonthlyContributionSummaryResponse(
        **summary_dict))

        return summaries

    # ══════════════════════════════════════════════════════════════════
    #  MODIFICATION
    # ══════════════════════════════════════════════════════════════════

    async def update_payment(self, contribution_id: UUID,
                             data: ContributionUpdate) -> ContributionResponse:
        """Met à jour une contribution."""
        contribution = await self.contribution_repo.get(contribution_id)
        if not contribution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contribution introuvable.",
            )

        # Mettre à jour les champs
        if data.amount is not None:
            contribution.amount = data.amount
        if data.payment_date is not None:
            contribution.payment_date = data.payment_date
        if data.notes is not None:
            contribution.notes = data.notes

        updated = await self.contribution_repo.update(contribution_id, contribution)
        enriched = await self.contribution_repo.enrich_contribution(updated)
        return ContributionResponse(**enriched)

    # ══════════════════════════════════════════════════════════════════
    #  SUPPRESSION
    # ══════════════════════════════════════════════════════════════════

    async def delete_payment(self, contribution_id: UUID) -> None:
        """Supprime une contribution."""
        contribution = await self.contribution_repo.get(contribution_id)
        if not contribution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Contribution introuvable.",
            )

        deleted = await self.contribution_repo.delete(contribution_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de la contribution.",
            )

    # ══════════════════════════════════════════════════════════════════
    #  RAPPORTS ET STATISTIQUES
    # ══════════════════════════════════════════════════════════════════

    async def generate_financial_report(
        self, request: FinancialReportRequest, generated_by: UUID
    ) -> FinancialReportResponse:
        """Génère un rapport financier complet."""
        # Calculer les statistiques de la période
        stats = await self.contribution_repo.calculate_period_stats(request.start_date, request.end_date)

        # Récupérer les résumés mensuels
        # Pour simplifier, on prend le mois de début et de fin
        start_month = request.start_date.month
        start_year = request.start_date.year
        end_month = request.end_date.month
        end_year = request.end_date.year

        all_summaries = []

        # Générer les résumés pour chaque mois de la période
        current_month = start_month
        current_year = start_year

        while (current_year < end_year) or (current_year ==
               end_year and current_month <= end_month):
            monthly_summaries = await self.get_monthly_summary(current_month, current_year)

            # Filtrer par servants si spécifié
            if request.servant_ids:
                monthly_summaries = [
    s for s in monthly_summaries if s.servant_id in request.servant_ids]

            all_summaries.extend(monthly_summaries)

            # Passer au mois suivant
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        # Récupérer le générateur
        generator = await self.user_repo.get(generated_by)
        generated_by_name = f"{
    generator.first_name} {
        generator.last_name}" if generator else "Inconnu"

        return FinancialReportResponse(
            start_date=request.start_date,
            end_date=request.end_date,
            total_expected=stats["total_expected"],
            total_collected=stats["total_collected"],
            collection_rate=stats["collection_rate"],
            servants_paid=stats["servants_paid"],
            servants_late=stats["servants_late"],
            contributions=all_summaries,
            generated_by=generated_by,
            generated_by_name=generated_by_name,
            generated_at=utc_now(),
        )

    async def get_servant_stats(
        self, servant_id: UUID, start_date: datetime, end_date: datetime
    ) -> ServantContributionStats:
        """Calcule les statistiques de contribution d'un servant."""
        # Valider que le servant existe
        servant = await self.user_repo.get(servant_id)
        if not servant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Servant introuvable.",
            )

        # Récupérer les contributions
        contributions = await self.contribution_repo.get_servant_contributions(servant_id, start_date, end_date)

        # Calculer les statistiques
        total_paid = sum(c.amount for c in contributions)

        # Calculer le montant attendu
        months_diff = (end_date.year - start_date.year) * 12 + \
                       end_date.month - start_date.month + 1
        total_expected = 500 * months_diff  # Approximation

        payment_rate = (
    total_paid /
    total_expected *
     100) if total_expected > 0 else 0

        # Compter les mois payés et en retard
        months_paid = len(set((c.month, c.year) for c in contributions))
        months_late = months_diff - months_paid

        last_payment_date = max(
    c.payment_date for c in contributions) if contributions else None

        return ServantContributionStats(
            servant_id=servant_id,
            servant_name=f"{servant.first_name} {servant.last_name}",
            total_expected=total_expected,
            total_paid=total_paid,
            payment_rate=payment_rate,
            months_paid=months_paid,
            months_late=months_late,
            last_payment_date=last_payment_date,
        )

    async def check_payment_compliance(self, servant_id: UUID) -> dict:
        """
        Vérifie la conformité des paiements (Art 48, 50) :
        - 2 mois consécutifs -> Alerte convocation parents.
        - 6 mois consécutifs -> Radiation.
        """
        now = utc_now()
        current_month = now.month
        current_year = now.year

        # On remonte sur les 6 derniers mois
        consecutive_missing = 0
        max_consecutive_missing = 0

        for i in range(1, 7):
            m = current_month - i
            y = current_year
            if m <= 0:
                m += 12
                y -= 1

            # Vérifier si payé pour ce mois
            summary = await self.contribution_repo.get_monthly_summary(servant_id, m, y)
            if summary.status == PaymentStatus.LATE:
                consecutive_missing += 1
                max_consecutive_missing = max(
    max_consecutive_missing, consecutive_missing)
            else:
                consecutive_missing = 0  # On reset car on veut du consécutif

        status = {
            "servant_id": servant_id,
            "consecutive_missing_months": max_consecutive_missing,
            "needs_parent_convocation": max_consecutive_missing >= 2,
            "flagged_for_radiation": max_consecutive_missing >= 6,
            "checked_at": now,
        }
        return status
