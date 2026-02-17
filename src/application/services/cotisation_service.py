"""
Service metier pour le module Cotisations.

Regles du reglement interieur :
- L'Econome collecte les fonds et les depose aupres de l'Aumonier
- Les Commissaires aux comptes verifient les ecritures
- L'Aumonier / Admin cree les periodes de cotisation
- Le non-paiement repete peut entrainer des sanctions
"""
import math
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.cotisation import CotisationPeriod, CotisationStatus, CotisationType, MemberCotisation
from src.core.entities.user import UserRole
from src.infrastructure.repositories.cotisation_repository import CotisationPeriodRepository, MemberCotisationRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.schemas.cotisation import (
    CotisationBilanResponse,
    CotisationPeriodCreate,
    CotisationPeriodResponse,
    CotisationPeriodUpdate,
    MemberCotisationCreate,
    MemberCotisationResponse,
    MemberCotisationUpdate,
)
from src.presentation.schemas.user import PaginatedResponse


class CotisationService:
    """Logique metier des cotisations financieres."""

    def __init__(
        self,
        period_repo: CotisationPeriodRepository,
        payment_repo: MemberCotisationRepository,
        user_repo: UserRepository,
    ):
        self.period_repo = period_repo
        self.payment_repo = payment_repo
        self.user_repo = user_repo

    # ══════════════════════════════════════════════════════════════════
    #  PERIODES
    # ══════════════════════════════════════════════════════════════════

    async def create_period(
        self, data: CotisationPeriodCreate, created_by: UUID
    ) -> CotisationPeriodResponse:
        if data.end_date <= data.start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La date de fin doit etre posterieure a la date de debut.",
            )

        period = CotisationPeriod(
            title=data.title,
            description=data.description,
            cotisation_type=data.cotisation_type,
            period_type=data.period_type,
            amount_expected=data.amount_expected,
            start_date=data.start_date,
            end_date=data.end_date,
            event_id=data.event_id,
            created_by=created_by,
        )
        created = await self.period_repo.create(period)
        return await self._build_period_response(created)

    async def update_period(
        self, period_id: UUID, data: CotisationPeriodUpdate
    ) -> CotisationPeriodResponse:
        period = await self.period_repo.get(period_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Periode de cotisation introuvable.",
            )
        if data.title is not None:
            period.title = data.title
        if data.description is not None:
            period.description = data.description
        if data.amount_expected is not None:
            period.amount_expected = data.amount_expected
        if data.end_date is not None:
            period.end_date = data.end_date
        if data.is_active is not None:
            period.is_active = data.is_active
        period.updated_at = datetime.now(timezone.utc)

        updated = await self.period_repo.update(period)
        return await self._build_period_response(updated)

    async def get_period(self, period_id: UUID) -> CotisationPeriodResponse:
        period = await self.period_repo.get(period_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Periode de cotisation introuvable.",
            )
        return await self._build_period_response(period)

    async def list_periods(
        self,
        *,
        cotisation_type: Optional[CotisationType] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[CotisationPeriodResponse]:
        periods, total = await self.period_repo.list_all(
            cotisation_type=cotisation_type,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1
        items = [await self._build_period_response(p) for p in periods]
        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def delete_period(self, period_id: UUID) -> None:
        period = await self.period_repo.get(period_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Periode de cotisation introuvable.",
            )
        await self.period_repo.delete(period_id)

    async def _build_period_response(
        self, period: CotisationPeriod
    ) -> CotisationPeriodResponse:
        stats = await self.payment_repo.get_period_stats(period.id)
        rate = 0.0
        if stats["total_members"] > 0:
            rate = (stats["total_paid"] / stats["total_members"]) * 100

        return CotisationPeriodResponse(
            id=period.id,
            title=period.title,
            description=period.description,
            cotisation_type=period.cotisation_type,
            period_type=period.period_type,
            amount_expected=period.amount_expected,
            start_date=period.start_date,
            end_date=period.end_date,
            event_id=period.event_id,
            is_active=period.is_active,
            created_by=period.created_by,
            created_at=period.created_at,
            updated_at=period.updated_at,
            total_members=stats["total_members"],
            total_paid=stats["total_paid"],
            total_amount_collected=stats["total_amount_collected"],
            collection_rate=round(rate, 1),
        )

    # ══════════════════════════════════════════════════════════════════
    #  PAIEMENTS
    # ══════════════════════════════════════════════════════════════════

    async def record_payment(
        self, data: MemberCotisationCreate, recorded_by: UUID
    ) -> MemberCotisationResponse:
        """Enregistrer un paiement de cotisation."""
        period = await self.period_repo.get(data.period_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Periode de cotisation introuvable.",
            )
        if not period.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cette periode de cotisation n'est plus active.",
            )

        user = await self.user_repo.get(data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur introuvable.",
            )

        existing = await self.payment_repo.get_by_period_and_user(
            data.period_id, data.user_id
        )
        if existing:
            # Mettre a jour le paiement existant (paiement supplementaire)
            existing.amount_paid += data.amount_paid
            if existing.amount_paid >= period.amount_expected:
                existing.status = CotisationStatus.PAYE
            else:
                existing.status = CotisationStatus.PAYE_PARTIELLEMENT
            existing.payment_date = datetime.now(timezone.utc)
            existing.payment_method = data.payment_method or existing.payment_method
            existing.notes = data.notes or existing.notes
            existing.recorded_by = recorded_by
            existing.updated_at = datetime.now(timezone.utc)
            updated = await self.payment_repo.update(existing)
            enriched = await self.payment_repo.enrich_cotisation(updated)
            return MemberCotisationResponse(**enriched)

        # Nouveau paiement
        payment_status = CotisationStatus.PAYE
        if data.amount_paid < period.amount_expected:
            payment_status = CotisationStatus.PAYE_PARTIELLEMENT

        cotisation = MemberCotisation(
            period_id=data.period_id,
            user_id=data.user_id,
            amount_paid=data.amount_paid,
            status=payment_status,
            payment_date=datetime.now(timezone.utc),
            payment_method=data.payment_method,
            notes=data.notes,
            recorded_by=recorded_by,
        )
        created = await self.payment_repo.create(cotisation)
        enriched = await self.payment_repo.enrich_cotisation(created)
        return MemberCotisationResponse(**enriched)

    async def get_period_payments(
        self, period_id: UUID
    ) -> List[MemberCotisationResponse]:
        period = await self.period_repo.get(period_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Periode de cotisation introuvable.",
            )
        payments = await self.payment_repo.list_by_period(period_id)
        enriched = await self.payment_repo.enrich_cotisations(payments)
        return [MemberCotisationResponse(**e) for e in enriched]

    async def get_user_payments(self, user_id: UUID) -> List[MemberCotisationResponse]:
        payments = await self.payment_repo.list_by_user(user_id)
        enriched = await self.payment_repo.enrich_cotisations(payments)
        return [MemberCotisationResponse(**e) for e in enriched]

    async def get_bilan(self, period_id: UUID) -> CotisationBilanResponse:
        """Bilan financier d'une periode."""
        period = await self.period_repo.get(period_id)
        if not period:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Periode de cotisation introuvable.",
            )

        period_response = await self._build_period_response(period)
        payments = await self.payment_repo.list_by_period(period_id)
        enriched_payments = await self.payment_repo.enrich_cotisations(payments)
        payment_responses = [MemberCotisationResponse(**e) for e in enriched_payments]

        total_expected = period.amount_expected * period_response.total_members
        total_collected = period_response.total_amount_collected
        total_remaining = max(0, total_expected - total_collected)
        taux = (total_collected / total_expected * 100) if total_expected > 0 else 0

        return CotisationBilanResponse(
            period=period_response,
            payments=payment_responses,
            total_expected=total_expected,
            total_collected=total_collected,
            total_remaining=total_remaining,
            taux_recouvrement=round(taux, 1),
        )
