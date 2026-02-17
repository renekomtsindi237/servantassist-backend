"""
Endpoints API pour le module SECRETAIRE - Rapports.
"""
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.report_service import ReportService
from src.core.entities.report import ReportStatus, ReportType
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.report_repository import AttachmentRepository, ReportRepository
from src.presentation.dependencies.auth_deps import get_current_active_user, get_current_responsable, require_secretaire
from src.presentation.schemas.report import (
    AttachmentCreate,
    AttachmentResponse,
    ReportCreate,
    ReportListResponse,
    ReportPublish,
    ReportResponse,
    ReportUpdate,
)

router = APIRouter()


def get_report_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReportService:
    """Dependency pour obtenir le service de rapports."""
    report_repo = ReportRepository(session)
    attachment_repo = AttachmentRepository(session)
    return ReportService(report_repo, attachment_repo)


# ── Endpoints CRUD ────────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=ReportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un rapport",
    description="Crée un nouveau rapport (SECRETAIRE/SECRETAIRE_ADJOINT uniquement)",
)
async def create_report(
    data: ReportCreate,
    current_user: Annotated[User, Depends(require_secretaire)],
    service: Annotated[ReportService, Depends(get_report_service)],
):
    """Crée un nouveau rapport."""
    report = await service.create_report(
        type=data.type,
        title=data.title,
        content=data.content,
        report_date=data.report_date,
        location=data.location,
        created_by=current_user.id,
        participants=data.participants,
        decisions=data.decisions,
        action_items=data.action_items,
    )
    return report


@router.get(
    "/",
    response_model=ReportListResponse,
    summary="Liste des rapports",
    description="Récupère la liste des rapports publiés (tous les responsables + aumônier)",
)
async def list_reports(
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    report_type: Optional[ReportType] = None,
    status: Optional[ReportStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Liste les rapports avec filtres et pagination."""
    # Les non-secrétaires ne voient que les rapports publiés
    from src.core.entities.responsable import PosteResponsable
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    # Vérifier si l'utilisateur est secrétaire
    is_secretaire = False
    if current_user.role.value == "SERVANT":
        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)
        is_secretaire = any(
            nom.poste
            in (
                PosteResponsable.SECRETAIRE_GENERAL,
                PosteResponsable.SECRETAIRE_GENERAL_ADJOINT,
            )
            for nom in nominations
        )

    # Si pas secrétaire, forcer le filtre sur les rapports publiés
    if not is_secretaire:
        status = ReportStatus.PUBLISHED

    reports, total = await service.list_reports(
        skip=skip,
        limit=limit,
        report_type=report_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )

    return ReportListResponse(
        items=reports,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Détail d'un rapport",
    description="Récupère les détails d'un rapport",
)
async def get_report(
    report_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    """Récupère un rapport par son ID."""
    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport introuvable",
        )

    # Vérifier les permissions
    # Les non-secrétaires ne peuvent voir que les rapports publiés
    from src.core.entities.responsable import PosteResponsable
    from src.infrastructure.repositories.responsable_repository import NominationRepository

    is_secretaire = False
    if current_user.role.value == "SERVANT":
        nom_repo = NominationRepository(session)
        nominations = await nom_repo.get_active_by_user(current_user.id)
        is_secretaire = any(
            nom.poste
            in (
                PosteResponsable.SECRETAIRE_GENERAL,
                PosteResponsable.SECRETAIRE_GENERAL_ADJOINT,
                PosteResponsable.SECRETAIRE,
                PosteResponsable.SECRETAIRE_ADJOINT,
            )
            for nom in nominations
        )

    if not is_secretaire and report.status != ReportStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous ne pouvez consulter que les rapports publiés",
        )

    return report


@router.patch(
    "/{report_id}",
    response_model=ReportResponse,
    summary="Modifier un rapport",
    description="Modifie un rapport en brouillon (SECRETAIRE/SECRETAIRE_ADJOINT uniquement)",
)
async def update_report(
    report_id: UUID,
    data: ReportUpdate,
    current_user: Annotated[User, Depends(require_secretaire)],
    service: Annotated[ReportService, Depends(get_report_service)],
):
    """Modifie un rapport."""
    try:
        report = await service.update_report(
            report_id=report_id,
            title=data.title,
            content=data.content,
            report_date=data.report_date,
            location=data.location,
            participants=data.participants,
            decisions=data.decisions,
            action_items=data.action_items,
        )

        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport introuvable",
            )

        return report

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{report_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un rapport",
    description="Supprime un rapport en brouillon (SECRETAIRE/SECRETAIRE_ADJOINT uniquement)",
)
async def delete_report(
    report_id: UUID,
    current_user: Annotated[User, Depends(require_secretaire)],
    service: Annotated[ReportService, Depends(get_report_service)],
):
    """Supprime un rapport."""
    try:
        success = await service.delete_report(report_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport introuvable",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ── Endpoints publication ─────────────────────────────────────────────────
@router.post(
    "/{report_id}/publish",
    response_model=ReportResponse,
    summary="Publier un rapport",
    description="Publie un rapport (SECRETAIRE/SECRETAIRE_ADJOINT uniquement)",
)
async def publish_report(
    report_id: UUID,
    current_user: Annotated[User, Depends(require_secretaire)],
    service: Annotated[ReportService, Depends(get_report_service)],
):
    """Publie un rapport."""
    try:
        report = await service.publish_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport introuvable",
            )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post(
    "/{report_id}/archive",
    response_model=ReportResponse,
    summary="Archiver un rapport",
    description="Archive un rapport publié (SECRETAIRE/SECRETAIRE_ADJOINT uniquement)",
)
async def archive_report(
    report_id: UUID,
    current_user: Annotated[User, Depends(require_secretaire)],
    service: Annotated[ReportService, Depends(get_report_service)],
):
    """Archive un rapport."""
    try:
        report = await service.archive_report(report_id)
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport introuvable",
            )
        return report
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ── Endpoints mes rapports ────────────────────────────────────────────────
@router.get(
    "/me/list",
    response_model=ReportListResponse,
    summary="Mes rapports",
    description="Récupère les rapports créés par l'utilisateur connecté",
)
async def get_my_reports(
    current_user: Annotated[User, Depends(require_secretaire)],
    service: Annotated[ReportService, Depends(get_report_service)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Récupère les rapports créés par l'utilisateur."""
    reports, total = await service.get_my_reports(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    return ReportListResponse(
        items=reports,
        total=total,
        skip=skip,
        limit=limit,
    )


# ── Endpoints pièces jointes ──────────────────────────────────────────────
@router.post(
    "/{report_id}/attachments",
    response_model=AttachmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter une pièce jointe",
    description="Ajoute une pièce jointe à un rapport (SECRETAIRE/SECRETAIRE_ADJOINT uniquement)",
)
async def add_attachment(
    report_id: UUID,
    data: AttachmentCreate,
    current_user: Annotated[User, Depends(require_secretaire)],
    service: Annotated[ReportService, Depends(get_report_service)],
):
    """Ajoute une pièce jointe à un rapport."""
    try:
        attachment = await service.add_attachment(
            report_id=report_id,
            filename=data.filename,
            file_url=data.file_url,
            file_type=data.file_type,
            file_size=data.file_size,
            uploaded_by=current_user.id,
        )

        if not attachment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport introuvable",
            )

        return attachment

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{report_id}/attachments",
    response_model=list[AttachmentResponse],
    summary="Liste des pièces jointes",
    description="Récupère les pièces jointes d'un rapport",
)
async def get_attachments(
    report_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[ReportService, Depends(get_report_service)],
):
    """Récupère les pièces jointes d'un rapport."""
    # Vérifier que le rapport existe
    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rapport introuvable",
        )

    attachments = await service.get_attachments(report_id)
    return attachments


@router.delete(
    "/attachments/{attachment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une pièce jointe",
    description="Supprime une pièce jointe (SECRETAIRE/SECRETAIRE_ADJOINT uniquement)",
)
async def delete_attachment(
    attachment_id: UUID,
    current_user: Annotated[User, Depends(require_secretaire)],
    service: Annotated[ReportService, Depends(get_report_service)],
):
    """Supprime une pièce jointe."""
    try:
        success = await service.delete_attachment(attachment_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pièce jointe introuvable",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
