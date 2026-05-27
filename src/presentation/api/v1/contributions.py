"""
Endpoints API pour la gestion des contributions financières (ECONOME).
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Path, Query, status

from src.application.services.contribution_service import ContributionService
from src.core.entities.contribution import PaymentMode
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.contribution_repository import (
    ContributionRepository,
)
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import (
    get_current_user,
    require_econome_or_admin,
)
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

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  DÉPENDANCES
# ══════════════════════════════════════════════════════════════════


async def get_contribution_service(
    session=Depends(get_db_session),
) -> ContributionService:
    """Injecte le service de contributions."""
    contribution_repo = ContributionRepository(session)
    user_repo = UserRepository(session)
    return ContributionService(contribution_repo, user_repo)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - GESTION DES CONTRIBUTIONS
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=ContributionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enregistrer un paiement",
    description="Enregistre un paiement de contribution (ECONOME uniquement)",
)
async def record_payment(
    data: ContributionCreate,
    current_user: User = Depends(require_econome_or_admin),
    service: ContributionService = Depends(get_contribution_service),
):
    """Enregistre un nouveau paiement de contribution."""
    return await service.record_payment(data, current_user.id)


@router.get(
    "/",
    response_model=PaginatedResponse[ContributionResponse],
    summary="Liste des contributions",
    description="Liste paginée des contributions avec filtres",
)
async def list_contributions(
    servant_id: Optional[UUID] = Query(None, description="Filtrer par servant"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filtrer par mois"),
    year: Optional[int] = Query(None, ge=2020, description="Filtrer par année"),
    payment_mode: Optional[PaymentMode] = Query(None, description="Filtrer par mode de paiement"),
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(50, ge=1, le=100, description="Taille de page"),
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    """Liste les contributions avec filtres et pagination."""
    return await service.list_contributions(
        servant_id=servant_id,
        month=month,
        year=year,
        payment_mode=payment_mode,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{contribution_id}",
    response_model=ContributionResponse,
    summary="Détail d'une contribution",
    description="Récupère les détails d'une contribution",
)
async def get_contribution(
    contribution_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    """Récupère une contribution par son ID."""
    return await service.get_contribution(contribution_id)


@router.patch(
    "/{contribution_id}",
    response_model=ContributionResponse,
    summary="Modifier une contribution",
    description="Modifie une contribution existante (ECONOME uniquement)",
)
async def update_payment(
    contribution_id: UUID,
    data: ContributionUpdate,
    current_user: User = Depends(require_econome_or_admin),
    service: ContributionService = Depends(get_contribution_service),
):
    """Met à jour une contribution."""
    return await service.update_payment(contribution_id, data)


@router.delete(
    "/{contribution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une contribution",
    description="Supprime une contribution (ECONOME uniquement)",
)
async def delete_payment(
    contribution_id: UUID,
    current_user: User = Depends(require_econome_or_admin),
    service: ContributionService = Depends(get_contribution_service),
):
    """Supprime une contribution."""
    await service.delete_payment(contribution_id)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - CONSULTATIONS PAR SERVANT
# ══════════════════════════════════════════════════════════════════


@router.get(
    "/servant/{servant_id}",
    response_model=list[ContributionResponse],
    summary="Contributions d'un servant",
    description="Récupère toutes les contributions d'un servant",
)
async def get_servant_contributions(
    servant_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Date de début"),
    end_date: Optional[datetime] = Query(None, description="Date de fin"),
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    """Récupère les contributions d'un servant."""
    return await service.get_servant_contributions(servant_id, start_date, end_date)


@router.get(
    "/servant/{servant_id}/stats",
    response_model=ServantContributionStats,
    summary="Statistiques d'un servant",
    description="Calcule les statistiques de contribution d'un servant",
)
async def get_servant_stats(
    servant_id: UUID,
    start_date: datetime = Query(..., description="Date de début"),
    end_date: datetime = Query(..., description="Date de fin"),
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    """Calcule les statistiques de contribution d'un servant."""
    return await service.get_servant_stats(servant_id, start_date, end_date)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - RÉSUMÉS ET RAPPORTS
# ══════════════════════════════════════════════════════════════════


@router.get(
    "/summary/{month}/{year}",
    response_model=list[MonthlyContributionSummaryResponse],
    summary="Résumé mensuel",
    description="Génère le résumé des contributions pour un mois donné",
)
async def get_monthly_summary(
    month: int = Path(..., ge=1, le=12, description="Mois (1-12)"),
    year: int = Path(..., ge=2020, description="Année"),
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    """Génère le résumé mensuel des contributions."""
    return await service.get_monthly_summary(month, year)


@router.post(
    "/report",
    response_model=FinancialReportResponse,
    summary="Générer un rapport financier",
    description="Génère un rapport financier complet pour une période (ECONOME uniquement)",
)
async def generate_financial_report(
    request: FinancialReportRequest,
    current_user: User = Depends(require_econome_or_admin),
    service: ContributionService = Depends(get_contribution_service),
):
    """Génère un rapport financier complet."""
    return await service.generate_financial_report(request, current_user.id)


@router.get(
    "/servant/{servant_id}/compliance",
    response_model=dict,
    summary="Vérifier la conformité des paiements",
    description="Vérifie si le servant est à jour ou en retard (Art 48, 50)",
)
async def get_payment_compliance(
    servant_id: UUID,
    current_user: User = Depends(get_current_user),
    service: ContributionService = Depends(get_contribution_service),
):
    """Vérifie la conformité des paiements."""
    return await service.check_payment_compliance(servant_id)
