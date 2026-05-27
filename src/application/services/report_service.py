"""
Service pour la gestion des rapports (SECRETAIRE).
"""
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from src.core.entities.report import Report, ReportAttachment, ReportStatus, ReportType
from src.core.interfaces.repositories import IAttachmentRepository, IReportRepository
from src.infrastructure.security.utils import SecurityUtils


class ReportService:
    """Service de gestion des rapports."""

    def __init__(
        self,
        report_repo: IReportRepository,
        attachment_repo: IAttachmentRepository,
    ):
        self.report_repo = report_repo
        self.attachment_repo = attachment_repo

    async def create_report(
        self,
        type: ReportType,
        title: str,
        content: str,
        report_date: datetime,
        location: str,
        created_by: UUID,
        participants: Optional[list[str]] = None,
        decisions: Optional[str] = None,
        action_items: Optional[str] = None,
    ) -> Report:
        """Crée un nouveau rapport."""
        report = Report(
            id=uuid4(),
            type=type,
            title=SecurityUtils.sanitize_html(title),
            content=SecurityUtils.sanitize_html(content),
            report_date=report_date,
            location=location,
            participants=participants or [],
            decisions=decisions,
            action_items=action_items,
            status=ReportStatus.DRAFT,
            created_by=created_by,
        )

        return await self.report_repo.create(report)

    async def get_report(self, report_id: UUID) -> Optional[Report]:
        """Récupère un rapport par son ID."""
        return await self.report_repo.get_by_id(report_id)

    async def list_reports(
        self,
        skip: int = 0,
        limit: int = 50,
        report_type: Optional[ReportType] = None,
        status: Optional[ReportStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[list[Report], int]:
        """Liste les rapports avec filtres."""
        return await self.report_repo.list_reports(
            skip=skip,
            limit=limit,
            report_type=report_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

    async def update_report(
        self,
        report_id: UUID,
        title: Optional[str] = None,
        content: Optional[str] = None,
        report_date: Optional[datetime] = None,
        location: Optional[str] = None,
        participants: Optional[list[str]] = None,
        decisions: Optional[str] = None,
        action_items: Optional[str] = None,
    ) -> Optional[Report]:
        """Met à jour un rapport."""
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            return None

        # Vérifier que le rapport est en brouillon
        if report.status != ReportStatus.DRAFT:
            raise ValueError(
                "Seuls les rapports en brouillon peuvent être modifiés")

        # Mise à jour des champs
        if title is not None:
            report.title = SecurityUtils.sanitize_html(title)
        if content is not None:
            report.content = SecurityUtils.sanitize_html(content)
        if report_date is not None:
            report.report_date = report_date
        if location is not None:
            report.location = location
        if participants is not None:
            report.participants = participants
        if decisions is not None:
            report.decisions = decisions
        if action_items is not None:
            report.action_items = action_items

        return await self.report_repo.update(report)

    async def delete_report(self, report_id: UUID) -> bool:
        """Supprime un rapport."""
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            return False

        # Vérifier que le rapport est en brouillon
        if report.status != ReportStatus.DRAFT:
            raise ValueError(
                "Seuls les rapports en brouillon peuvent être supprimés")

        return await self.report_repo.delete(report_id)

    async def publish_report(self, report_id: UUID) -> Optional[Report]:
        """Publie un rapport."""
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            return None

        # Vérifier que le rapport est en brouillon
        if report.status != ReportStatus.DRAFT:
            raise ValueError("Seul un rapport en brouillon peut être publié")

        return await self.report_repo.publish(report_id)

    async def archive_report(self, report_id: UUID) -> Optional[Report]:
        """Archive un rapport."""
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            return None

        # Vérifier que le rapport est publié
        if report.status != ReportStatus.PUBLISHED:
            raise ValueError("Seul un rapport publié peut être archivé")

        return await self.report_repo.archive(report_id)

    async def get_my_reports(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[list[Report], int]:
        """Récupère les rapports créés par un utilisateur."""
        return await self.report_repo.get_by_created_by(
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    # ── Gestion des pièces jointes ───────────────────────────────────────
    async def add_attachment(
        self,
        report_id: UUID,
        filename: str,
        file_url: str,
        file_type: str,
        file_size: int,
        uploaded_by: UUID,
    ) -> Optional[ReportAttachment]:
        """Ajoute une pièce jointe à un rapport."""
        # Vérifier que le rapport existe
        report = await self.report_repo.get_by_id(report_id)
        if not report:
            return None

        # Vérifier que le rapport est en brouillon
        if report.status != ReportStatus.DRAFT:
            raise ValueError(
                "Les pièces jointes ne peuvent être ajoutées qu'aux rapports en brouillon")

        attachment = ReportAttachment(
            id=uuid4(),
            report_id=report_id,
            filename=filename,
            file_url=file_url,
            file_type=file_type,
            file_size=file_size,
            uploaded_by=uploaded_by,
        )

        return await self.attachment_repo.create(attachment)

    async def get_attachments(self, report_id: UUID) -> List[ReportAttachment]:
        """Récupère les pièces jointes d'un rapport."""
        return await self.attachment_repo.get_by_report(report_id)

    async def delete_attachment(self, attachment_id: UUID) -> bool:
        """Supprime une pièce jointe."""
        attachment = await self.attachment_repo.get_by_id(attachment_id)
        if not attachment:
            return False

        # Vérifier que le rapport est en brouillon
        report = await self.report_repo.get_by_id(attachment.report_id)
        if report and report.status != ReportStatus.DRAFT:
            raise ValueError(
                "Les pièces jointes ne peuvent être supprimées que des rapports en brouillon")

        return await self.attachment_repo.delete(attachment_id)
