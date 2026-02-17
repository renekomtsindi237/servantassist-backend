"""
Repository pour la gestion des contributions financières.
"""
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.contribution import Contribution, MonthlyContributionSummary, PaymentMode, PaymentStatus
from src.core.entities.user import User, UserRole


class ContributionRepository:
    """Repository pour les contributions financières."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ══════════════════════════════════════════════════════════════════
    #  CRÉATION
    # ══════════════════════════════════════════════════════════════════

    async def create(self, contribution: Contribution) -> Contribution:
        """Crée une nouvelle contribution."""
        self.session.add(contribution)
        await self.session.commit()
        await self.session.refresh(contribution)
        return contribution

    # ══════════════════════════════════════════════════════════════════
    #  LECTURE
    # ══════════════════════════════════════════════════════════════════

    async def get(self, contribution_id: UUID) -> Optional[Contribution]:
        """Récupère une contribution par son ID."""
        result = await self.session.execute(select(Contribution).where(Contribution.id == contribution_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        servant_id: Optional[UUID] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        payment_mode: Optional[PaymentMode] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Contribution], int]:
        """Liste les contributions avec filtres et pagination."""
        query = select(Contribution)

        # Filtres
        conditions = []
        if servant_id:
            conditions.append(Contribution.servant_id == servant_id)
        if month:
            conditions.append(Contribution.month == month)
        if year:
            conditions.append(Contribution.year == year)
        if payment_mode:
            conditions.append(Contribution.payment_mode == payment_mode)

        if conditions:
            query = query.where(and_(*conditions))

        # Compte total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination
        query = query.order_by(Contribution.payment_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(query)
        contributions = result.scalars().all()

        return list(contributions), total

    async def get_servant_contributions(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[Contribution]:
        """Récupère toutes les contributions d'un servant."""
        query = select(Contribution).where(Contribution.servant_id == servant_id)

        if start_date:
            query = query.where(Contribution.payment_date >= start_date)
        if end_date:
            query = query.where(Contribution.payment_date <= end_date)

        query = query.order_by(Contribution.payment_date.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_monthly_contributions(self, month: int, year: int) -> List[Contribution]:
        """Récupère toutes les contributions d'un mois."""
        query = select(Contribution).where(and_(Contribution.month == month, Contribution.year == year))
        result = await self.session.execute(query)
        return list(result.scalars().all())

    # ══════════════════════════════════════════════════════════════════
    #  MODIFICATION
    # ══════════════════════════════════════════════════════════════════

    async def update(self, contribution_id: UUID, contribution: Contribution) -> Optional[Contribution]:
        """Met à jour une contribution."""
        existing = await self.get(contribution_id)
        if not existing:
            return None

        for key, value in contribution.model_dump(exclude_unset=True).items():
            setattr(existing, key, value)

        existing.updated_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(existing)
        return existing

    # ══════════════════════════════════════════════════════════════════
    #  SUPPRESSION
    # ══════════════════════════════════════════════════════════════════

    async def delete(self, contribution_id: UUID) -> bool:
        """Supprime une contribution."""
        contribution = await self.get(contribution_id)
        if not contribution:
            return False

        await self.session.delete(contribution)
        await self.session.commit()
        return True

    # ══════════════════════════════════════════════════════════════════
    #  STATISTIQUES ET RAPPORTS
    # ══════════════════════════════════════════════════════════════════

    async def get_monthly_summary(self, servant_id: UUID, month: int, year: int) -> MonthlyContributionSummary:
        """Génère le résumé mensuel pour un servant."""
        # Récupérer les contributions du mois
        contributions = await self.session.execute(
            select(Contribution).where(
                and_(
                    Contribution.servant_id == servant_id,
                    Contribution.month == month,
                    Contribution.year == year,
                )
            )
        )
        contributions_list = list(contributions.scalars().all())

        # Récupérer le servant
        servant_result = await self.session.execute(select(User).where(User.id == servant_id))
        servant = servant_result.scalar_one_or_none()
        servant_name = f"{servant.first_name} {servant.last_name}" if servant else "Inconnu"

        # Calculer les montants
        paid_amount = sum(c.amount for c in contributions_list)
        payment_mode = contributions_list[0].payment_mode if contributions_list else PaymentMode.MONTHLY

        # Montant attendu selon le mode
        expected_amount = 500 if payment_mode == PaymentMode.MONTHLY else 400

        # Déterminer le statut
        if paid_amount >= expected_amount:
            status = PaymentStatus.PAID
        elif paid_amount > 0:
            status = PaymentStatus.PENDING
        else:
            status = PaymentStatus.LATE

        return MonthlyContributionSummary(
            servant_id=servant_id,
            servant_name=servant_name,
            month=month,
            year=year,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            payment_mode=payment_mode,
            status=status,
            payments=contributions_list,
        )

    async def get_all_servants(self) -> List[User]:
        """Récupère tous les servants."""
        result = await self.session.execute(select(User).where(User.role == UserRole.SERVANT).order_by(User.last_name))
        return list(result.scalars().all())

    async def calculate_period_stats(self, start_date: datetime, end_date: datetime) -> dict:
        """Calcule les statistiques pour une période."""
        # Récupérer tous les servants
        servants = await self.get_all_servants()

        # Récupérer toutes les contributions de la période
        contributions_result = await self.session.execute(
            select(Contribution).where(
                and_(
                    Contribution.payment_date >= start_date,
                    Contribution.payment_date <= end_date,
                )
            )
        )
        contributions = list(contributions_result.scalars().all())

        # Calculer les statistiques
        total_collected = sum(c.amount for c in contributions)

        # Calculer le montant attendu (approximatif basé sur le nombre de mois)
        months_diff = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
        total_expected = len(servants) * 500 * months_diff  # Approximation

        # Compter les servants à jour et en retard
        servants_paid = len(set(c.servant_id for c in contributions))
        servants_late = len(servants) - servants_paid

        collection_rate = (total_collected / total_expected * 100) if total_expected > 0 else 0

        return {
            "total_expected": total_expected,
            "total_collected": total_collected,
            "collection_rate": collection_rate,
            "servants_paid": servants_paid,
            "servants_late": servants_late,
        }

    # ══════════════════════════════════════════════════════════════════
    #  ENRICHISSEMENT
    # ══════════════════════════════════════════════════════════════════

    async def enrich_contribution(self, contribution: Contribution) -> dict:
        """Enrichit une contribution avec les noms."""
        # Récupérer le servant
        servant_result = await self.session.execute(select(User).where(User.id == contribution.servant_id))
        servant = servant_result.scalar_one_or_none()
        servant_name = f"{servant.first_name} {servant.last_name}" if servant else "Inconnu"

        # Récupérer l'enregistreur
        recorder_result = await self.session.execute(select(User).where(User.id == contribution.recorded_by))
        recorder = recorder_result.scalar_one_or_none()
        recorded_by_name = f"{recorder.first_name} {recorder.last_name}" if recorder else "Inconnu"

        return {
            **contribution.model_dump(),
            "servant_name": servant_name,
            "recorded_by_name": recorded_by_name,
        }
