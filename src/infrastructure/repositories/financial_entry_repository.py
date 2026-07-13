"""
Repository pour la gestion des entrées financières (COMMISSAIRE_AUX_COMPTES).
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.financial_entry import (
    Discrepancy,
    EntryCategory,
    EntrySource,
    FinancialEntry,
    VerificationStatus,
)
from src.core.utils import utc_now


class FinancialEntryRepository:
    """Repository pour les entrées financières."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, entry: FinancialEntry) -> FinancialEntry:
        """Crée une nouvelle entrée financière."""
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def get_by_id(self, entry_id: UUID) -> Optional[FinancialEntry]:
        """Récupère une entrée par son ID."""
        result = await self.session.execute(select(FinancialEntry).where(FinancialEntry.id == entry_id))
        return result.scalar_one_or_none()

    async def list_entries(
        self,
        skip: int = 0,
        limit: int = 50,
        category: Optional[EntryCategory] = None,
        source: Optional[EntrySource] = None,
        verification_status: Optional[VerificationStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[list[FinancialEntry], int]:
        """Liste les entrées avec filtres et pagination."""
        # Construction de la requête
        query = select(FinancialEntry)
        count_query = select(func.count(FinancialEntry.id))

        # Filtres
        filters = []
        if category:
            filters.append(FinancialEntry.category == category)
        if source:
            filters.append(FinancialEntry.source == source)
        if verification_status:
            filters.append(FinancialEntry.verification_status == verification_status)
        if start_date:
            filters.append(FinancialEntry.date >= start_date)
        if end_date:
            filters.append(FinancialEntry.date <= end_date)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Tri par date décroissante
        query = query.order_by(FinancialEntry.date.desc())

        # Pagination
        query = query.offset(skip).limit(limit)

        # Exécution
        result = await self.session.execute(query)
        entries = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return entries, total

    async def update(self, entry: FinancialEntry) -> FinancialEntry:
        """Met à jour une entrée."""
        entry.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def delete(self, entry_id: UUID) -> bool:
        """Supprime une entrée."""
        entry = await self.get_by_id(entry_id)
        if not entry:
            return False

        await self.session.delete(entry)
        await self.session.commit()
        return True

    async def verify(
        self,
        entry_id: UUID,
        verified_by: UUID,
        status: VerificationStatus,
        notes: Optional[str] = None,
    ) -> Optional[FinancialEntry]:
        """Vérifie une entrée."""
        entry = await self.get_by_id(entry_id)
        if not entry:
            return None

        entry.verification_status = status
        entry.verified_by = verified_by
        entry.verification_date = utc_now()
        entry.notes = notes
        entry.updated_at = utc_now()

        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def get_by_recorded_by(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[list[FinancialEntry], int]:
        """Récupère les entrées enregistrées par un utilisateur."""
        query = (
            select(FinancialEntry)
            .where(FinancialEntry.recorded_by == user_id)
            .order_by(FinancialEntry.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        entries = list(result.scalars().all())

        count_query = select(func.count(FinancialEntry.id)).where(FinancialEntry.recorded_by == user_id)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return entries, total

    async def get_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Calcule les statistiques pour une période."""
        # Total
        total_query = select(func.count(FinancialEntry.id), func.sum(FinancialEntry.amount)).where(
            and_(FinancialEntry.date >= start_date, FinancialEntry.date <= end_date)
        )
        total_result = await self.session.execute(total_query)
        total_count, total_amount = total_result.one()

        # Vérifiées
        verified_query = select(func.count(FinancialEntry.id), func.sum(FinancialEntry.amount)).where(
            and_(
                FinancialEntry.date >= start_date,
                FinancialEntry.date <= end_date,
                FinancialEntry.verification_status == VerificationStatus.VERIFIED,
            )
        )
        verified_result = await self.session.execute(verified_query)
        verified_count, verified_amount = verified_result.one()

        # En attente
        pending_query = select(func.count(FinancialEntry.id), func.sum(FinancialEntry.amount)).where(
            and_(
                FinancialEntry.date >= start_date,
                FinancialEntry.date <= end_date,
                FinancialEntry.verification_status == VerificationStatus.PENDING,
            )
        )
        pending_result = await self.session.execute(pending_query)
        pending_count, pending_amount = pending_result.one()

        # Rejetées
        rejected_query = select(func.count(FinancialEntry.id), func.sum(FinancialEntry.amount)).where(
            and_(
                FinancialEntry.date >= start_date,
                FinancialEntry.date <= end_date,
                FinancialEntry.verification_status == VerificationStatus.REJECTED,
            )
        )
        rejected_result = await self.session.execute(rejected_query)
        rejected_count, rejected_amount = rejected_result.one()

        return {
            "total_entries": total_count or 0,
            "total_amount": float(total_amount or 0),
            "verified_entries": verified_count or 0,
            "verified_amount": float(verified_amount or 0),
            "pending_entries": pending_count or 0,
            "pending_amount": float(pending_amount or 0),
            "rejected_entries": rejected_count or 0,
            "rejected_amount": float(rejected_amount or 0),
        }

    async def get_summary_by_category(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[dict]:
        """Résumé par catégorie."""
        # Récupération de toutes les entrées de la période
        query = select(FinancialEntry).where(and_(FinancialEntry.date >= start_date, FinancialEntry.date <= end_date))

        result = await self.session.execute(query)
        entries = result.scalars().all()

        # Agrégation en Python
        summary_map = {}

        for entry in entries:
            category = entry.category
            if category not in summary_map:
                summary_map[category] = {
                    "category": category,
                    "entry_count": 0,
                    "total_amount": 0.0,
                    "verified_amount": 0.0,
                    "pending_amount": 0.0,
                }

            stats = summary_map[category]
            stats["entry_count"] += 1
            stats["total_amount"] += entry.amount

            if entry.verification_status == VerificationStatus.VERIFIED:
                stats["verified_amount"] += entry.amount
            elif entry.verification_status == VerificationStatus.PENDING:
                stats["pending_amount"] += entry.amount

        return list(summary_map.values())


class DiscrepancyRepository:
    """Repository pour les écarts."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, discrepancy: Discrepancy) -> Discrepancy:
        """Crée un nouvel écart."""
        self.session.add(discrepancy)
        await self.session.commit()
        await self.session.refresh(discrepancy)
        return discrepancy

    async def get_by_id(self, discrepancy_id: UUID) -> Optional[Discrepancy]:
        """Récupère un écart par son ID."""
        result = await self.session.execute(select(Discrepancy).where(Discrepancy.id == discrepancy_id))
        return result.scalar_one_or_none()

    async def get_by_entry(self, entry_id: UUID) -> List[Discrepancy]:
        """Récupère les écarts d'une entrée."""
        result = await self.session.execute(
            select(Discrepancy).where(Discrepancy.entry_id == entry_id).order_by(Discrepancy.detected_at.desc())
        )
        return list(result.scalars().all())

    async def list_unresolved(self) -> List[Discrepancy]:
        """Liste les écarts non résolus."""
        result = await self.session.execute(
            select(Discrepancy).where(Discrepancy.resolved.is_(False)).order_by(Discrepancy.detected_at.desc())
        )
        return list(result.scalars().all())

    async def resolve(
        self,
        discrepancy_id: UUID,
        resolution_notes: str,
    ) -> Optional[Discrepancy]:
        """Résout un écart."""
        discrepancy = await self.get_by_id(discrepancy_id)
        if not discrepancy:
            return None

        discrepancy.resolved = True
        discrepancy.resolution_notes = resolution_notes

        await self.session.commit()
        await self.session.refresh(discrepancy)
        return discrepancy

    async def delete(self, discrepancy_id: UUID) -> bool:
        """Supprime un écart."""
        discrepancy = await self.get_by_id(discrepancy_id)
        if not discrepancy:
            return False

        await self.session.delete(discrepancy)
        await self.session.commit()
        return True
