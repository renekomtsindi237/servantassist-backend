"""
Endpoints API pour le module COMMISSAIRE_AUX_COMPTES - Audit financier.
"""
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.financial_entry_service import FinancialEntryService
from src.core.entities.financial_entry import EntryCategory, EntrySource, VerificationStatus
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.financial_entry_repository import DiscrepancyRepository, FinancialEntryRepository
from src.presentation.dependencies.auth_deps import get_current_active_user, require_commissaire, require_commissaire_strict
from src.presentation.schemas.financial_entry import (
    AuditReportRequest,
    AuditReportResponse,
    DiscrepancyCreate,
    DiscrepancyResolve,
    DiscrepancyResponse,
    FinancialEntryCreate,
    FinancialEntryListResponse,
    FinancialEntryResponse,
    FinancialEntryUpdate,
    FinancialEntryVerify,
    FinancialStatsResponse,
    FinancialSummaryResponse,
)

router = APIRouter()


def get_financial_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FinancialEntryService:
    """Dependency pour obtenir le service financier."""
    entry_repo = FinancialEntryRepository(session)
    discrepancy_repo = DiscrepancyRepository(session)
    return FinancialEntryService(entry_repo, discrepancy_repo)


# ── Endpoints CRUD ────────────────────────────────────────────────────────
@router.post(
    "/",
    response_model=FinancialEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une entrée financière",
    description="Crée une nouvelle entrée financière (COMMISSAIRE uniquement)",
)
async def create_entry(
    data: FinancialEntryCreate,
    current_user: Annotated[User, Depends(require_commissaire_strict)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Crée une nouvelle entrée financière."""
    entry = await service.create_entry(
        date=data.date,
        amount=data.amount,
        category=data.category,
        source=data.source,
        reference=data.reference,
        description=data.description,
        recorded_by=current_user.id,
    )
    return entry


@router.get(
    "/",
    response_model=FinancialEntryListResponse,
    summary="Liste des entrées financières",
    description="Récupère la liste des entrées financières avec filtres",
)
async def list_entries(
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    category: Optional[EntryCategory] = None,
    source: Optional[EntrySource] = None,
    verification_status: Optional[VerificationStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """Liste les entrées financières avec filtres et pagination."""
    entries, total = await service.list_entries(
        skip=skip,
        limit=limit,
        category=category,
        source=source,
        verification_status=verification_status,
        start_date=start_date,
        end_date=end_date,
    )

    return FinancialEntryListResponse(
        items=entries,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{entry_id}",
    response_model=FinancialEntryResponse,
    summary="Détail d'une entrée",
    description="Récupère les détails d'une entrée financière",
)
async def get_entry(
    entry_id: UUID,
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Récupère une entrée par son ID."""
    entry = await service.get_entry(entry_id)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrée financière introuvable",
        )
    return entry


@router.patch(
    "/{entry_id}",
    response_model=FinancialEntryResponse,
    summary="Modifier une entrée",
    description="Modifie une entrée financière non vérifiée",
)
async def update_entry(
    entry_id: UUID,
    data: FinancialEntryUpdate,
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Modifie une entrée financière."""
    try:
        entry = await service.update_entry(
            entry_id=entry_id,
            date=data.date,
            amount=data.amount,
            category=data.category,
            source=data.source,
            reference=data.reference,
            description=data.description,
        )

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entrée financière introuvable",
            )

        return entry

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une entrée",
    description="Supprime une entrée financière non vérifiée",
)
async def delete_entry(
    entry_id: UUID,
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Supprime une entrée financière."""
    try:
        success = await service.delete_entry(entry_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entrée financière introuvable",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ── Endpoints vérification ───────────────────────────────────────────────
@router.post(
    "/{entry_id}/verify",
    response_model=FinancialEntryResponse,
    summary="Vérifier une entrée",
    description="Vérifie une entrée financière (COMMISSAIRE uniquement)",
)
async def verify_entry(
    entry_id: UUID,
    data: FinancialEntryVerify,
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Vérifie une entrée financière."""
    entry = await service.verify_entry(
        entry_id=entry_id,
        verified_by=current_user.id,
        status=data.verification_status,
        notes=data.notes,
    )

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrée financière introuvable",
        )

    return entry


# ── Endpoints mes entrées ─────────────────────────────────────────────────
@router.get(
    "/me/list",
    response_model=FinancialEntryListResponse,
    summary="Mes entrées",
    description="Récupère les entrées créées par l'utilisateur connecté",
)
async def get_my_entries(
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    """Récupère les entrées créées par l'utilisateur."""
    entries, total = await service.get_my_entries(
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )

    return FinancialEntryListResponse(
        items=entries,
        total=total,
        skip=skip,
        limit=limit,
    )


# ── Endpoints statistiques ────────────────────────────────────────────────
@router.get(
    "/stats/summary",
    response_model=FinancialStatsResponse,
    summary="Statistiques financières",
    description="Récupère les statistiques pour une période",
)
async def get_statistics(
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
):
    """Récupère les statistiques financières."""
    stats = await service.get_statistics(start_date, end_date)
    return FinancialStatsResponse(**stats)


# ── Endpoints rapport d'audit ─────────────────────────────────────────────
@router.post(
    "/audit/report",
    response_model=AuditReportResponse,
    summary="Générer un rapport d'audit",
    description="Génère un rapport d'audit complet pour une période",
)
async def generate_audit_report(
    data: AuditReportRequest,
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Génère un rapport d'audit."""
    report = await service.generate_audit_report(
        start_date=data.start_date,
        end_date=data.end_date,
        generated_by=current_user.id,
    )

    # Récupérer les résumés par catégorie via le service (utilise la session
    # existante)
    summaries_data = await service.get_summary_by_category(data.start_date, data.end_date)
    summaries = [FinancialSummaryResponse(**s) for s in summaries_data]

    return AuditReportResponse(
        **report.model_dump(),
        summaries=summaries,
    )


# ── Endpoints écarts ──────────────────────────────────────────────────────
@router.post(
    "/{entry_id}/discrepancies",
    response_model=DiscrepancyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un écart",
    description="Crée un écart pour une entrée financière",
)
async def create_discrepancy(
    entry_id: UUID,
    data: DiscrepancyCreate,
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Crée un écart."""
    discrepancy = await service.create_discrepancy(
        entry_id=entry_id,
        type=data.type,
        description=data.description,
        detected_by=current_user.id,
        expected_amount=data.expected_amount,
        actual_amount=data.actual_amount,
    )

    if not discrepancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrée financière introuvable",
        )

    return discrepancy


@router.get(
    "/{entry_id}/discrepancies",
    response_model=list[DiscrepancyResponse],
    summary="Liste des écarts d'une entrée",
    description="Récupère les écarts d'une entrée financière",
)
async def get_entry_discrepancies(
    entry_id: UUID,
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Récupère les écarts d'une entrée."""
    discrepancies = await service.get_discrepancies_by_entry(entry_id)
    return discrepancies


@router.get(
    "/discrepancies/unresolved",
    response_model=list[DiscrepancyResponse],
    summary="Écarts non résolus",
    description="Liste tous les écarts non résolus",
)
async def list_unresolved_discrepancies(
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Liste les écarts non résolus."""
    discrepancies = await service.list_unresolved_discrepancies()
    return discrepancies


@router.post(
    "/discrepancies/{discrepancy_id}/resolve",
    response_model=DiscrepancyResponse,
    summary="Résoudre un écart",
    description="Marque un écart comme résolu",
)
async def resolve_discrepancy(
    discrepancy_id: UUID,
    data: DiscrepancyResolve,
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Résout un écart."""
    discrepancy = await service.resolve_discrepancy(
        discrepancy_id=discrepancy_id,
        resolution_notes=data.resolution_notes,
    )

    if not discrepancy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Écart introuvable",
        )

    return discrepancy


@router.delete(
    "/discrepancies/{discrepancy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un écart",
    description="Supprime un écart",
)
async def delete_discrepancy(
    discrepancy_id: UUID,
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
):
    """Supprime un écart."""
    success = await service.delete_discrepancy(discrepancy_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Écart introuvable",
        )


# ── Export PDF ────────────────────────────────────────────────────────────


@router.get(
    "/export/pdf",
    summary="Exporter le bilan financier en PDF",
    description="Télécharge le bilan financier de la période en PDF.",
)
async def export_financial_pdf(
    current_user: Annotated[User, Depends(require_commissaire)],
    service: Annotated[FinancialEntryService, Depends(get_financial_service)],
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
):
    """Génère le bilan financier PDF pour la période donnée."""
    entries, _ = await service.list_entries(
        start_date=start_date,
        end_date=end_date,
        limit=1000,
    )
    summary = await service.get_financial_summary(
        start_date=start_date,
        end_date=end_date,
    )
    period_label = "Toute période"
    if start_date and end_date:
        period_label = (
            f"{start_date.strftime('%d/%m/%Y')} au {end_date.strftime('%d/%m/%Y')}"
        )
    elif start_date:
        period_label = f"Depuis le {start_date.strftime('%d/%m/%Y')}"
    elif end_date:
        period_label = f"Jusqu'au {end_date.strftime('%d/%m/%Y')}"

    from src.infrastructure.services.pdf_service import PDFService

    pdf_svc = PDFService()
    entry_dicts = [
        {
            "date": e.date,
            "description": e.description,
            "category": e.category.value if hasattr(e.category, "value") else str(e.category),
            "type": e.source.value if hasattr(e.source, "value") else str(e.source),
            "amount": float(e.amount),
        }
        for e in entries
    ]
    total_income = float(getattr(summary, "total_income", 0) or 0)
    total_expense = float(getattr(summary, "total_expense", 0) or 0)
    pdf_bytes = pdf_svc.generate_financial_statement(
        entries=entry_dicts,
        period_label=period_label,
        generated_by=f"{current_user.first_name} {current_user.last_name}",
        total_income=total_income,
        total_expense=total_expense,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="bilan_financier.pdf"'},
    )
