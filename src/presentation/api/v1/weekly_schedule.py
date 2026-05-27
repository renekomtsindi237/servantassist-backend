"""
Endpoints de gestion des modèles de classement hebdomadaire.

Gestion (CHARGE_CLASSEMENT_SEMAINE uniquement) :
    POST   /                              Créer un modèle
    GET    /                              Liste paginée avec filtres
    GET    /{template_id}                 Détail d'un modèle
    PATCH  /{template_id}                 Modifier un modèle
    PATCH  /{template_id}/publish         Publier un modèle
    PATCH  /{template_id}/archive         Archiver un modèle
    DELETE /{template_id}                 Supprimer un modèle
    PATCH  /slots/{slot_id}               Modifier un créneau
    DELETE /slots/{slot_id}               Supprimer un créneau
    POST   /slots/{slot_id}/servants      Ajouter un servant à un créneau
    DELETE /assignments/{assignment_id}   Retirer un servant d'un créneau

Consultation (Tous les utilisateurs authentifiés) :
    GET    /published                     Modèles publiés (visible par tous)
"""
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.weekly_schedule_service import WeeklyScheduleService
from src.core.entities.user import User
from src.core.entities.weekly_schedule import ScheduleStatus
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.repositories.weekly_schedule_repository import (
    WeeklyScheduleRepository,
)
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_charge_classement_semaine,
)
from src.presentation.schemas.user import PaginatedResponse
from src.presentation.schemas.weekly_schedule import (
    SlotServantCreate,
    SlotServantResponse,
    WeeklyScheduleSlotResponse,
    WeeklyScheduleSlotUpdate,
    WeeklyScheduleTemplateCreate,
    WeeklyScheduleTemplateResponse,
    WeeklyScheduleTemplateSummary,
    WeeklyScheduleTemplateUpdate,
)

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────
def _get_service(session: AsyncSession) -> WeeklyScheduleService:
    return WeeklyScheduleService(
        schedule_repository=WeeklyScheduleRepository(session),
        user_repository=UserRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CONSULTATION — Tous les utilisateurs authentifiés
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/published", response_model=List[WeeklyScheduleTemplateSummary])
async def get_published_templates(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Liste de tous les modèles de classement publiés.

    **Accessible à :** Tous les utilisateurs authentifiés.

    Les modèles publiés sont visibles par tous pour consultation.
    """
    service = _get_service(session)
    return await service.get_published_templates()


@router.get("/{template_id}", response_model=WeeklyScheduleTemplateResponse)
async def get_template(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Détail d'un modèle de classement avec tous ses créneaux.

    **Accessible à :** Tous les utilisateurs authentifiés.
    """
    service = _get_service(session)
    return await service.get_template(template_id)


# ═══════════════════════════════════════════════════════════════════════════
#  CRÉATION — CHARGE_CLASSEMENT_SEMAINE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=WeeklyScheduleTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: WeeklyScheduleTemplateCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
):
    """
    Créer un nouveau modèle de classement hebdomadaire.

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.

    Le modèle peut être créé avec des créneaux pré-remplis ou vide.
    Chaque créneau peut avoir 0 ou plusieurs servants assignés.

    **Horaires des messes :**
    - Matin (6h15) : Lundi à Samedi
    - Midi (12h00) : Lundi à Vendredi
    - Soir (18h00) : Lundi à Vendredi
    """
    service = _get_service(session)
    return await service.create_template(data, created_by=current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURE — CHARGE_CLASSEMENT_SEMAINE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/", response_model=PaginatedResponse[WeeklyScheduleTemplateSummary])
async def list_templates(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
    status_filter: Optional[ScheduleStatus] = Query(
        None, alias="status", description="Filtrer par statut"
    ),
    start_date: Optional[datetime] = Query(
        None, description="Modèles à partir de cette date"
    ),
    end_date: Optional[datetime] = Query(
        None, description="Modèles jusqu'à cette date"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """
    Liste paginée de tous les modèles de classement avec filtres.

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.

    **Filtres disponibles :**
    - ``status`` : DRAFT, PUBLISHED, ARCHIVED
    - ``start_date`` / ``end_date`` : plage de dates
    """
    service = _get_service(session)
    return await service.list_templates(
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  MODIFICATION — CHARGE_CLASSEMENT_SEMAINE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.patch("/{template_id}", response_model=WeeklyScheduleTemplateResponse)
async def update_template(
    template_id: UUID,
    data: WeeklyScheduleTemplateUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
):
    """
    Modifier un modèle de classement.

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.
    """
    service = _get_service(session)
    return await service.update_template(template_id, data, updated_by=current_user.id)


@router.patch(
    "/{template_id}/publish",
    response_model=WeeklyScheduleTemplateResponse,
)
async def publish_template(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
):
    """
    Publier un modèle (le rendre visible par tous).

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.

    Une fois publié, le modèle est visible par tous les utilisateurs
    authentifiés via l'endpoint GET /published.
    """
    service = _get_service(session)
    return await service.publish_template(template_id, published_by=current_user.id)


@router.patch(
    "/{template_id}/archive",
    response_model=WeeklyScheduleTemplateResponse,
)
async def archive_template(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
):
    """
    Archiver un modèle.

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.
    """
    service = _get_service(session)
    return await service.archive_template(template_id, archived_by=current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  SUPPRESSION — CHARGE_CLASSEMENT_SEMAINE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
):
    """
    Supprimer définitivement un modèle et tous ses créneaux.

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.
    """
    service = _get_service(session)
    await service.delete_template(template_id)


# ═══════════════════════════════════════════════════════════════════════════
#  GESTION DES CRÉNEAUX — CHARGE_CLASSEMENT_SEMAINE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.patch("/slots/{slot_id}", response_model=WeeklyScheduleSlotResponse)
async def update_slot(
    slot_id: UUID,
    data: WeeklyScheduleSlotUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
):
    """
    Modifier un créneau.

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.
    """
    service = _get_service(session)
    return await service.update_slot(slot_id, data)


@router.delete("/slots/{slot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_slot(
    slot_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
):
    """
    Supprimer un créneau.

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.
    """
    service = _get_service(session)
    await service.delete_slot(slot_id)


# ═══════════════════════════════════════════════════════════════════════════
#  GESTION DES ASSIGNATIONS — CHARGE_CLASSEMENT_SEMAINE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/slots/{slot_id}/servants",
    response_model=SlotServantResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_servant_to_slot(
    slot_id: UUID,
    data: SlotServantCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
):
    """
    Ajouter un servant à un créneau.

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.

    Permet d'assigner un servant à un créneau en utilisant soit :
    - ``servant_id`` : ID d'un servant existant dans le système
    - ``servant_name`` : Nom libre pour un servant pas encore enregistré

    Un créneau peut avoir plusieurs servants assignés.
    """
    service = _get_service(session)
    return await service.add_servant_to_slot(slot_id, data, assigned_by=current_user.id)


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_servant_from_slot(
    assignment_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_semaine)],
):
    """
    Retirer un servant d'un créneau.

    **Accessible à :** CHARGE_CLASSEMENT_SEMAINE, Admin, Aumônier.
    """
    service = _get_service(session)
    await service.remove_servant_from_slot(assignment_id)
