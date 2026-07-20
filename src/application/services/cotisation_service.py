"""
Service metier pour le module Cotisations.

Regles du reglement interieur :
- L'Econome collecte les fonds et les depose aupres de l'Aumonier
- Les Commissaires aux comptes verifient les ecritures
- L'Aumonier / Admin cree les periodes de cotisation
- Le non-paiement repete peut entrainer des sanctions
"""

import math
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.cotisation import (
    FIXED_AMOUNTS,
    CotisationPeriod,
    CotisationStatus,
    CotisationType,
    MemberCotisation,
    PeriodType,
)
from src.core.entities.user import UserRole
from src.core.interfaces.repositories import (
    ICotisationPeriodRepository,
    IMemberCotisationRepository,
    INominationRepository,
    IUserRepository,
)
from src.core.utils import utc_now
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
        period_repo: ICotisationPeriodRepository,
        payment_repo: IMemberCotisationRepository,
        user_repo: IUserRepository,
        nomination_repo: Optional[INominationRepository] = None,
    ):
        self.period_repo = period_repo
        self.payment_repo = payment_repo
        self.user_repo = user_repo
        self.nomination_repo = nomination_repo

    # ══════════════════════════════════════════════════════════════════
    #  PERIODES
    # ══════════════════════════════════════════════════════════════════

    async def create_period(self, data: CotisationPeriodCreate, created_by: UUID) -> CotisationPeriodResponse:
        if data.end_date <= data.start_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La date de fin doit etre posterieure a la date de debut.",
            )

        fixed_amount = FIXED_AMOUNTS.get((data.cotisation_type, data.period_type))
        if fixed_amount is not None and data.amount_expected != fixed_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Le montant pour une cotisation {data.cotisation_type.value} "
                    f"{data.period_type.value.lower()} doit etre de {fixed_amount:.0f} FCFA "
                    f"(Art. 22 du reglement interieur)."
                ),
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

        # Obligatoire pour chaque servant sans poste de responsabilite actif
        # — l'obligation EN_ATTENTE est creee immediatement pour chacun,
        # plutot que de deduire l'absence de paiement par l'absence de
        # ligne. Concerne :
        # - ORDINAIRE mensuel/hebdomadaire (Art. 22 : cotisation reguliere)
        # - SPECIALE (Art. 23 : camp spirituel, fete de fin d'annee —
        #   "obligatoires pour tous les servants")
        # - AUBE (Art. 21 : entretien/confection des aubes, "obligatoire
        #   pour les nouveaux et les anciens")
        # AMENDE (penalite individuelle) et AUTRE (contribution volontaire)
        # ne generent jamais d'obligation automatique.
        is_ordinaire_periodique = data.cotisation_type == CotisationType.ORDINAIRE and data.period_type in (
            PeriodType.MENSUEL,
            PeriodType.HEBDOMADAIRE,
        )
        is_obligatoire_evenementielle = data.cotisation_type in (
            CotisationType.SPECIALE,
            CotisationType.AUBE,
        )
        if is_ordinaire_periodique or is_obligatoire_evenementielle:
            await self._create_obligations_for_period(created)

        return await self._build_period_response(created)

    async def _create_obligations_for_period(self, period: CotisationPeriod) -> None:
        """
        Cree une obligation EN_ATTENTE pour chaque servant sans poste de
        responsabilite actif — rend la cotisation reellement obligatoire et
        interrogeable (Art. 21, 22, 23), pas seulement deduite par l'absence
        de paiement enregistre.
        """
        if self.nomination_repo is None:
            return

        servants, _ = await self.user_repo.list_paginated(
            role=UserRole.SERVANT, is_active=True, page_size=10000
        )
        active_nominations = await self.nomination_repo.list_all_active()
        postes_by_user = {n.user_id for n in active_nominations}

        for servant in servants:
            if servant.id in postes_by_user:
                continue  # responsable — exempte de la cotisation obligatoire
            existing = await self.payment_repo.get_by_period_and_user(period.id, servant.id)
            if existing:
                continue
            obligation = MemberCotisation(
                period_id=period.id,
                user_id=servant.id,
                amount_paid=0,
                status=CotisationStatus.EN_ATTENTE,
            )
            await self.payment_repo.create(obligation)

    async def update_period(self, period_id: UUID, data: CotisationPeriodUpdate) -> CotisationPeriodResponse:
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
            fixed_amount = FIXED_AMOUNTS.get((period.cotisation_type, period.period_type))
            if fixed_amount is not None and data.amount_expected != fixed_amount:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Le montant pour une cotisation {period.cotisation_type.value} "
                        f"{period.period_type.value.lower()} doit etre de {fixed_amount:.0f} FCFA "
                        f"(Art. 22 du reglement interieur)."
                    ),
                )
            period.amount_expected = data.amount_expected
        if data.end_date is not None:
            period.end_date = data.end_date
        if data.is_active is not None:
            period.is_active = data.is_active
        period.updated_at = utc_now()

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

    async def _build_period_response(self, period: CotisationPeriod) -> CotisationPeriodResponse:
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

    async def record_payment(self, data: MemberCotisationCreate, recorded_by: UUID) -> MemberCotisationResponse:
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

        # Exclusivite mensuel/hebdomadaire (Art. 22) : un servant choisit un
        # seul mode de cotisation ordinaire, jamais les deux simultanement
        # sur une periode qui se chevauche.
        if period.cotisation_type == CotisationType.ORDINAIRE and period.period_type in (
            PeriodType.MENSUEL,
            PeriodType.HEBDOMADAIRE,
        ):
            other_period_type = (
                PeriodType.HEBDOMADAIRE if period.period_type == PeriodType.MENSUEL else PeriodType.MENSUEL
            )
            overlapping = await self.payment_repo.get_overlapping_ordinaire_payment(
                data.user_id, other_period_type, period.start_date, period.end_date
            )
            if overlapping:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Ce servant a deja choisi le mode {other_period_type.value}. "
                        "Impossible de cumuler mensuel et hebdomadaire sur la meme periode."
                    ),
                )

        existing = await self.payment_repo.get_by_period_and_user(data.period_id, data.user_id)
        if existing:
            # Mettre a jour le paiement existant (paiement supplementaire)
            existing.amount_paid += data.amount_paid
            if existing.amount_paid >= period.amount_expected:
                existing.status = CotisationStatus.PAYE
            else:
                existing.status = CotisationStatus.PAYE_PARTIELLEMENT
            existing.payment_date = utc_now()
            existing.payment_method = data.payment_method or existing.payment_method
            existing.notes = data.notes or existing.notes
            existing.recorded_by = recorded_by
            existing.updated_at = utc_now()
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
            payment_date=utc_now(),
            payment_method=data.payment_method,
            notes=data.notes,
            recorded_by=recorded_by,
        )
        created = await self.payment_repo.create(cotisation)
        enriched = await self.payment_repo.enrich_cotisation(created)
        return MemberCotisationResponse(**enriched)

    async def get_period_payments(self, period_id: UUID) -> List[MemberCotisationResponse]:
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

    async def check_payment_compliance(self, user_id: UUID) -> dict:
        """
        Verifie la conformite des cotisations ordinaires d'un servant (Art. 48, 50) :
        - 2 periodes ordinaires consecutives manquees -> convocation des parents
        - 6 periodes ordinaires consecutives manquees -> radiation
        """
        six_months_ago = utc_now() - timedelta(days=180)
        periods = await self.period_repo.list_ordinaire_since(six_months_ago)
        periods = sorted(periods, key=lambda p: p.start_date, reverse=True)

        consecutive_missing = 0
        max_consecutive_missing = 0
        for period in periods:
            payment = await self.payment_repo.get_by_period_and_user(period.id, user_id)
            paid = payment is not None and payment.status in (
                CotisationStatus.PAYE,
                CotisationStatus.PAYE_PARTIELLEMENT,
                CotisationStatus.EXONERE,
            )
            if paid:
                consecutive_missing = 0
            else:
                consecutive_missing += 1
                max_consecutive_missing = max(max_consecutive_missing, consecutive_missing)

        needs_parent_convocation = max_consecutive_missing >= 2

        if needs_parent_convocation:
            # Enregistrement structure de la convocation (Art. 48-49),
            # idempotent — ne cree pas de doublon si deja EN_ATTENTE.
            try:
                from src.core.entities.convocation import ConvocationMotif
                from src.application.services.convocation_service import ConvocationService
                from src.infrastructure.repositories.convocation_repository import (
                    ConvocationRepository,
                )

                convocation_service = ConvocationService(
                    convocation_repo=ConvocationRepository(self.period_repo.session),
                    user_repo=self.user_repo,
                )
                user = await self.user_repo.get(user_id)
                if user:
                    await convocation_service.create_if_not_pending(
                        servant_id=user_id,
                        motif=ConvocationMotif.NON_COTISATION,
                        details=(
                            f"{max_consecutive_missing} periodes de cotisation ordinaire "
                            "consecutives non reglees."
                        ),
                        # Declenchement automatique (pas d'utilisateur "current" dans ce contexte).
                        convened_by=UUID("00000000-0000-0000-0000-000000000000"),
                    )
            except Exception:
                pass  # Le calcul de conformite ne doit jamais echouer a cause de la convocation

        return {
            "user_id": user_id,
            "consecutive_missing_periods": max_consecutive_missing,
            "needs_parent_convocation": needs_parent_convocation,
            "flagged_for_radiation": max_consecutive_missing >= 6,
            "checked_at": utc_now(),
        }
