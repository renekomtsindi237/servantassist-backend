"""
Service pour la gestion des entrées financières (COMMISSAIRE_AUX_COMPTES).
"""

from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from src.core.entities.financial_entry import (
    AuditReport,
    Discrepancy,
    EntryCategory,
    EntrySource,
    FinancialEntry,
    FinancialSummary,
    VerificationStatus,
)
from src.core.interfaces.repositories import (
    IDiscrepancyRepository,
    IFinancialEntryRepository,
)


class FinancialEntryService:
    """Service de gestion des entrées financières."""

    def __init__(
        self,
        entry_repo: IFinancialEntryRepository,
        discrepancy_repo: IDiscrepancyRepository,
    ):
        self.entry_repo = entry_repo
        self.discrepancy_repo = discrepancy_repo

    async def create_entry(
        self,
        date: datetime,
        amount: float,
        category: EntryCategory,
        source: EntrySource,
        description: str,
        recorded_by: UUID,
        reference: Optional[str] = None,
    ) -> FinancialEntry:
        """Crée une nouvelle entrée financière."""
        entry = FinancialEntry(
            id=uuid4(),
            date=date,
            amount=amount,
            category=category,
            source=source,
            reference=reference,
            description=description,
            recorded_by=recorded_by,
            verification_status=VerificationStatus.PENDING,
        )

        return await self.entry_repo.create(entry)

    async def get_entry(self, entry_id: UUID) -> Optional[FinancialEntry]:
        """Récupère une entrée par son ID."""
        return await self.entry_repo.get_by_id(entry_id)

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
        """Liste les entrées avec filtres."""
        return await self.entry_repo.list_entries(
            skip=skip,
            limit=limit,
            category=category,
            source=source,
            verification_status=verification_status,
            start_date=start_date,
            end_date=end_date,
        )

    async def update_entry(
        self,
        entry_id: UUID,
        date: Optional[datetime] = None,
        amount: Optional[float] = None,
        category: Optional[EntryCategory] = None,
        source: Optional[EntrySource] = None,
        reference: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[FinancialEntry]:
        """Met à jour une entrée."""
        entry = await self.entry_repo.get_by_id(entry_id)
        if not entry:
            return None

        # Vérifier que l'entrée n'est pas vérifiée
        if entry.verification_status == VerificationStatus.VERIFIED:
            raise ValueError("Les entrées vérifiées ne peuvent pas être modifiées")

        # Mise à jour des champs
        if date is not None:
            entry.date = date
        if amount is not None:
            entry.amount = amount
        if category is not None:
            entry.category = category
        if source is not None:
            entry.source = source
        if reference is not None:
            entry.reference = reference
        if description is not None:
            entry.description = description

        return await self.entry_repo.update(entry)

    async def delete_entry(self, entry_id: UUID) -> bool:
        """Supprime une entrée."""
        entry = await self.entry_repo.get_by_id(entry_id)
        if not entry:
            return False

        # Vérifier que l'entrée n'est pas vérifiée
        if entry.verification_status == VerificationStatus.VERIFIED:
            raise ValueError("Les entrées vérifiées ne peuvent pas être supprimées")

        return await self.entry_repo.delete(entry_id)

    async def verify_entry(
        self,
        entry_id: UUID,
        verified_by: UUID,
        status: VerificationStatus,
        notes: Optional[str] = None,
    ) -> Optional[FinancialEntry]:
        """Vérifie une entrée."""
        entry = await self.entry_repo.get_by_id(entry_id)
        if not entry:
            return None

        return await self.entry_repo.verify(
            entry_id=entry_id,
            verified_by=verified_by,
            status=status,
            notes=notes,
        )

    async def get_my_entries(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[list[FinancialEntry], int]:
        """Récupère les entrées enregistrées par un utilisateur."""
        return await self.entry_repo.get_by_recorded_by(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    async def get_financial_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ):
        """Retourne un résumé simplifié income/expense pour la période."""
        from datetime import datetime as _dt

        start = start_date or _dt(2000, 1, 1)
        end = end_date or _dt(2099, 12, 31)
        stats = await self.entry_repo.get_statistics(start, end)

        class _Summary:
            def __init__(self, total_income: float, total_expense: float):
                self.total_income = total_income
                self.total_expense = total_expense

        return _Summary(
            total_income=float(stats.get("total_amount", 0) or 0),
            total_expense=0.0,
        )

    async def get_summary_by_category(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[dict]:
        """Résumé par catégorie."""
        return await self.entry_repo.get_summary_by_category(start_date, end_date)

    async def get_statistics(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> dict:
        """Calcule les statistiques pour une période."""
        stats = await self.entry_repo.get_statistics(start_date, end_date)

        # Calculer le taux de vérification
        if stats["total_entries"] > 0:
            stats["verification_rate"] = (stats["verified_entries"] / stats["total_entries"]) * 100
        else:
            stats["verification_rate"] = 0.0

        # Calculer le montant moyen
        if stats["total_entries"] > 0:
            stats["average_entry_amount"] = stats["total_amount"] / stats["total_entries"]
        else:
            stats["average_entry_amount"] = 0.0

        stats["period_start"] = start_date
        stats["period_end"] = end_date

        return stats

    async def generate_audit_report(
        self,
        start_date: datetime,
        end_date: datetime,
        generated_by: UUID,
    ) -> AuditReport:
        """Génère un rapport d'audit."""
        # Récupérer les statistiques
        stats = await self.entry_repo.get_statistics(start_date, end_date)

        # Récupérer les résumés par catégorie
        await self.entry_repo.get_summary_by_category(start_date, end_date)

        # Récupérer les écarts non résolus
        unresolved_discrepancies = await self.discrepancy_repo.list_unresolved()

        # Construire la liste des écarts
        discrepancies = [f"{d.type}: {d.description}" for d in unresolved_discrepancies]

        # Générer des recommandations
        recommendations = self._generate_recommendations(stats, unresolved_discrepancies)

        # Créer le rapport
        report = AuditReport(
            id=uuid4(),
            start_date=start_date,
            end_date=end_date,
            total_entries=stats["total_entries"],
            total_amount=stats["total_amount"],
            verified_entries=stats["verified_entries"],
            pending_entries=stats["pending_entries"],
            rejected_entries=stats["rejected_entries"],
            discrepancies=discrepancies,
            recommendations=recommendations,
            generated_by=generated_by,
        )

        return report

    def _generate_recommendations(
        self,
        stats: dict,
        unresolved_discrepancies: List[Discrepancy],
    ) -> str:
        """Génère des recommandations basées sur les statistiques."""
        recommendations = []

        # Taux de vérification faible
        if stats["total_entries"] > 0:
            verification_rate = (stats["verified_entries"] / stats["total_entries"]) * 100
            if verification_rate < 50:
                recommendations.append(
                    f"Taux de vérification faible ({verification_rate:.1f}%). "
                    "Il est recommandé de vérifier les entrées en attente."
                )

        # Entrées rejetées
        if stats["rejected_entries"] > 0:
            recommendations.append(
                f"{stats['rejected_entries']} entrée(s) rejetée(s). Vérifier et corriger les anomalies détectées."
            )

        # Écarts non résolus
        if unresolved_discrepancies:
            recommendations.append(
                f"{len(unresolved_discrepancies)} écart(s) non résolu(s). "
                "Résoudre les écarts détectés pour assurer la cohérence des données."
            )

        # Montant élevé en attente
        if stats["pending_amount"] > stats["total_amount"] * 0.3:
            recommendations.append(
                f"Montant important en attente de vérification ({stats['pending_amount']:.0f} FCFA)."  # noqa: E501
            )

        if not recommendations:
            recommendations.append(
                "Aucune anomalie majeure détectée. " "Continuer le suivi régulier des entrées financières."
            )

        return "\n".join(recommendations)

    # ── Gestion des écarts ───────────────────────────────────────────────
    async def create_discrepancy(
        self,
        entry_id: UUID,
        type: str,
        description: str,
        detected_by: UUID,
        expected_amount: Optional[float] = None,
        actual_amount: Optional[float] = None,
    ) -> Optional[Discrepancy]:
        """Crée un écart."""
        # Vérifier que l'entrée existe
        entry = await self.entry_repo.get_by_id(entry_id)
        if not entry:
            return None

        discrepancy = Discrepancy(
            id=uuid4(),
            entry_id=entry_id,
            type=type,
            description=description,
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            detected_by=detected_by,
        )

        return await self.discrepancy_repo.create(discrepancy)

    async def get_discrepancies_by_entry(
        self,
        entry_id: UUID,
    ) -> List[Discrepancy]:
        """Récupère les écarts d'une entrée."""
        return await self.discrepancy_repo.get_by_entry(entry_id)

    async def list_unresolved_discrepancies(self) -> List[Discrepancy]:
        """Liste les écarts non résolus."""
        return await self.discrepancy_repo.list_unresolved()

    async def resolve_discrepancy(
        self,
        discrepancy_id: UUID,
        resolution_notes: str,
    ) -> Optional[Discrepancy]:
        """Résout un écart."""
        return await self.discrepancy_repo.resolve(
            discrepancy_id=discrepancy_id,
            resolution_notes=resolution_notes,
        )

    async def delete_discrepancy(self, discrepancy_id: UUID) -> bool:
        """Supprime un écart."""
        return await self.discrepancy_repo.delete(discrepancy_id)
