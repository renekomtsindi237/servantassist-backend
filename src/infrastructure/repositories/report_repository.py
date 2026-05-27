"""
Repository pour la gestion des rapports (SECRETAIRE).
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import String, and_, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.report import Report, ReportAttachment, ReportStatus, ReportType
from src.core.utils import utc_now


class ReportRepository:
    """Repository pour les rapports."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, report: Report) -> Report:
        """Crée un nouveau rapport."""
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_by_id(self, report_id: UUID) -> Optional[Report]:
        """Récupère un rapport par son ID."""
        result = await self.session.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()

    async def list_reports(
        self,
        skip: int = 0,
        limit: int = 50,
        report_type: Optional[ReportType] = None,
        status: Optional[ReportStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[list[Report], int]:
        """Liste les rapports avec filtres et pagination."""
        # Construction de la requête
        query = select(Report)
        count_query = select(func.count(Report.id))

        # Filtres
        filters = []
        if report_type:
            filters.append(Report.type == report_type)
        if status:
            filters.append(Report.status == status)
        if start_date:
            filters.append(Report.report_date >= start_date)
        if end_date:
            filters.append(Report.report_date <= end_date)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        # Tri par date décroissante
        query = query.order_by(Report.report_date.desc())

        # Pagination
        query = query.offset(skip).limit(limit)

        # Exécution
        result = await self.session.execute(query)
        reports = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return reports, total

    async def update(self, report: Report) -> Report:
        """Met à jour un rapport."""
        report.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def delete(self, report_id: UUID) -> bool:
        """Supprime un rapport."""
        report = await self.get_by_id(report_id)
        if not report:
            return False

        await self.session.delete(report)
        await self.session.commit()
        return True

    async def publish(self, report_id: UUID) -> Optional[Report]:
        """Publie un rapport."""
        report = await self.get_by_id(report_id)
        if not report:
            return None

        report.status = ReportStatus.PUBLISHED
        report.published_at = utc_now()
        report.updated_at = utc_now()

        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def archive(self, report_id: UUID) -> Optional[Report]:
        """Archive un rapport."""
        report = await self.get_by_id(report_id)
        if not report:
            return None

        report.status = ReportStatus.ARCHIVED
        report.updated_at = utc_now()

        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_by_created_by(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[list[Report], int]:
        """Récupère les rapports créés par un utilisateur."""
        query = (
            select(Report)
            .where(Report.created_by == user_id)
            .order_by(Report.created_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        reports = list(result.scalars().all())

        count_query = select(func.count(Report.id)).where(Report.created_by == user_id)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return reports, total


class AttachmentRepository:
    """Repository pour les pièces jointes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, attachment: ReportAttachment) -> ReportAttachment:
        """Crée une nouvelle pièce jointe."""
        self.session.add(attachment)
        await self.session.commit()
        await self.session.refresh(attachment)
        return attachment

    async def get_by_id(self, attachment_id: UUID) -> Optional[ReportAttachment]:
        """Récupère une pièce jointe par son ID."""
        result = await self.session.execute(select(ReportAttachment).where(ReportAttachment.id == attachment_id))
        return result.scalar_one_or_none()

    async def get_by_report(self, report_id: UUID) -> List[ReportAttachment]:
        """Récupère toutes les pièces jointes d'un rapport."""
        result = await self.session.execute(
            select(ReportAttachment)
            .where(ReportAttachment.report_id == report_id)
            .order_by(ReportAttachment.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete(self, attachment_id: UUID) -> bool:
        """Supprime une pièce jointe."""
        attachment = await self.get_by_id(attachment_id)
        if not attachment:
            return False

        await self.session.delete(attachment)
        await self.session.commit()
        return True
