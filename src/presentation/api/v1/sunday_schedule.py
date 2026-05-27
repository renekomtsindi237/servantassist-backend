"""
Endpoints de gestion des modèles de classement dominical.

Gestion (CHARGE_CLASSEMENT_DIMANCHE uniquement) :
    POST   /                              Créer un modèle
    POST   /generate/ordinary             Générer un modèle ordinaire
    POST   /generate/exceptional          Générer un modèle exceptionnel
    GET    /                              Liste paginée avec filtres
    GET    /{template_id}                 Détail d'un modèle
    PATCH  /{template_id}                 Modifier un modèle
    PATCH  /{template_id}/publish         Publier un modèle
    PATCH  /{template_id}/archive         Archiver un modèle
    DELETE /{template_id}                 Supprimer un modèle
    PATCH  /masses/{mass_id}              Modifier une messe
    DELETE /masses/{mass_id}              Supprimer une messe
    POST   /masses/{mass_id}/assignments  Ajouter une assignation
    DELETE /assignments/{assignment_id}   Retirer une assignation

Consultation (Tous les utilisateurs authentifiés) :
    GET    /published                     Modèles publiés (visible par tous)
"""
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.sunday_schedule_service import SundayScheduleService
from src.core.entities.sunday_schedule import SundayScheduleStatus
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.sunday_schedule_repository import (
    SundayScheduleRepository,
)
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import (
    get_current_active_user,
    get_current_charge_classement_dimanche,
    get_sunday_schedule_history_access,
)
from src.presentation.schemas.sunday_schedule import (
    GenerateExceptionalScheduleRequest,
    GenerateOrdinaryScheduleRequest,
    MarkPresenceRequest,
    ModificationLogResponse,
    SundayMassAssignmentCreate,
    SundayMassAssignmentResponse,
    SundayMassSlotResponse,
    SundayMassSlotUpdate,
    SundayScheduleTemplateCreate,
    SundayScheduleTemplateResponse,
    SundayScheduleTemplateSummary,
    SundayScheduleTemplateUpdate,
)
from src.presentation.schemas.user import PaginatedResponse

router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────────────────
def _get_service(session: AsyncSession) -> SundayScheduleService:
    return SundayScheduleService(
        schedule_repository=SundayScheduleRepository(session),
        user_repository=UserRepository(session),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CONSULTATION — Tous les utilisateurs authentifiés
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/published", response_model=List[SundayScheduleTemplateSummary])
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


@router.get("/{template_id}", response_model=SundayScheduleTemplateResponse)
async def get_template(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Détail d'un modèle de classement avec toutes ses messes.

    **Accessible à :** Tous les utilisateurs authentifiés.
    """
    service = _get_service(session)
    return await service.get_template(template_id)


# ═══════════════════════════════════════════════════════════════════════════
#  CRÉATION — CHARGE_CLASSEMENT_DIMANCHE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/",
    response_model=SundayScheduleTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_template(
    data: SundayScheduleTemplateCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Créer un nouveau modèle de classement dominical.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.

    Le modèle peut être créé avec des messes pré-remplies ou vide.
    Chaque messe peut avoir plusieurs assignations de postes liturgiques.

    **Types de messe :**
    - ORDINAIRE : Messe dominicale normale
    - SOLENNELLE : Messe solennelle
    - PONTIFICALE : Messe pontificale

    **Postes liturgiques :**
    - Cérémoniaires 1 & 2
    - Responsable
    - Crucifère
    - Acolytes 1, 2 & 3
    - Thuriféraire
    - Porte-insignes
    - Céroféréraires (pour messes solennelles)
    """
    service = _get_service(session)
    return await service.create_template(data, created_by=current_user.id)


@router.post(
    "/generate/ordinary",
    response_model=SundayScheduleTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_ordinary_template(
    data: GenerateOrdinaryScheduleRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Générer un modèle avec les horaires ordinaires pré-remplis.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.

    **Horaires ordinaires :**
    - 06h30 : Messe en Ewondo
    - 08h30 : Messe en Français
    - 10h00 : Messe en Ewondo
    - 11h30 : Messe en Anglais
    - 17h00 : Messe en Français
    """
    service = _get_service(session)
    return await service.generate_ordinary_template(data, created_by=current_user.id)


@router.post(
    "/generate/exceptional",
    response_model=SundayScheduleTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_exceptional_template(
    data: GenerateExceptionalScheduleRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Générer un modèle avec des horaires exceptionnels personnalisés.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.

    Permet de définir des horaires personnalisés pour des occasions spéciales.
    """
    service = _get_service(session)
    return await service.generate_exceptional_template(data, created_by=current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURE — CHARGE_CLASSEMENT_DIMANCHE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/", response_model=PaginatedResponse[SundayScheduleTemplateSummary])
async def list_templates(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
    status_filter: Optional[SundayScheduleStatus] = Query(
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

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.

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
#  MODIFICATION — CHARGE_CLASSEMENT_DIMANCHE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.patch("/{template_id}", response_model=SundayScheduleTemplateResponse)
async def update_template(
    template_id: UUID,
    data: SundayScheduleTemplateUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Modifier un modèle de classement.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.
    """
    service = _get_service(session)
    return await service.update_template(template_id, data, updated_by=current_user.id)


@router.patch(
    "/{template_id}/publish",
    response_model=SundayScheduleTemplateResponse,
)
async def publish_template(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Publier un modèle (le rendre visible par tous).

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.

    Une fois publié, le modèle est visible par tous les utilisateurs
    authentifiés via l'endpoint GET /published.
    """
    service = _get_service(session)
    return await service.publish_template(template_id, published_by=current_user.id)


@router.patch(
    "/{template_id}/archive",
    response_model=SundayScheduleTemplateResponse,
)
async def archive_template(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Archiver un modèle.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.
    """
    service = _get_service(session)
    return await service.archive_template(template_id, archived_by=current_user.id)


# ═══════════════════════════════════════════════════════════════════════════
#  SUPPRESSION — CHARGE_CLASSEMENT_DIMANCHE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Supprimer définitivement un modèle et toutes ses messes.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.
    """
    service = _get_service(session)
    await service.delete_template(template_id)


# ═══════════════════════════════════════════════════════════════════════════
#  GESTION DES MESSES — CHARGE_CLASSEMENT_DIMANCHE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.patch("/masses/{mass_id}", response_model=SundayMassSlotResponse)
async def update_mass(
    mass_id: UUID,
    data: SundayMassSlotUpdate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Modifier une messe.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.
    """
    service = _get_service(session)
    return await service.update_mass(mass_id, data)


@router.delete("/masses/{mass_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_mass(
    mass_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Supprimer une messe.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.
    """
    service = _get_service(session)
    await service.delete_mass(mass_id)


# ═══════════════════════════════════════════════════════════════════════════
#  GESTION DES ASSIGNATIONS — CHARGE_CLASSEMENT_DIMANCHE uniquement
# ═══════════════════════════════════════════════════════════════════════════


@router.post(
    "/masses/{mass_id}/assignments",
    response_model=SundayMassAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_assignment_to_mass(
    mass_id: UUID,
    data: SundayMassAssignmentCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Ajouter une assignation à une messe.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.

    Permet d'assigner un servant à un poste liturgique en utilisant soit :
    - ``servant_id`` : ID d'un servant existant dans le système
    - ``servant_name`` : Nom libre pour un servant pas encore enregistré

    Une messe peut avoir plusieurs assignations pour différents postes.
    """
    service = _get_service(session)
    return await service.add_assignment_to_mass(
        mass_id, data, assigned_by=current_user.id
    )


@router.delete("/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_assignment(
    assignment_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_charge_classement_dimanche)],
):
    """
    Retirer une assignation.

    **Accessible à :** CHARGE_CLASSEMENT_DIMANCHE, Admin, Aumônier.
    """
    service = _get_service(session)
    await service.remove_assignment(assignment_id)


# ═══════════════════════════════════════════════════════════════════════════
#  MARQUAGE DE PRÉSENCE — Tous les utilisateurs authentifiés
# ═══════════════════════════════════════════════════════════════════════════


@router.patch(
    "/assignments/{assignment_id}/presence",
    response_model=SundayMassAssignmentResponse,
)
async def mark_presence(
    assignment_id: UUID,
    data: MarkPresenceRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    """
    Marquer la présence ou l'absence d'un servant après une messe.

    **Accessible à :** Tous les utilisateurs authentifiés.

    Permet de marquer la présence effective d'un servant après le déroulement
    de la messe. Toutes les modifications sont tracées dans l'historique.
    """
    service = _get_service(session)
    ip_address = request.client.host if request.client else None
    return await service.mark_presence(
        assignment_id,
        data.is_present,
        marked_by=current_user.id,
        ip_address=ip_address,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  HISTORIQUE DES MODIFICATIONS — Tous les utilisateurs authentifiés
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/{template_id}/history",
    response_model=List[ModificationLogResponse],
)
async def get_modification_history(
    template_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    current_user: Annotated[User, Depends(get_sunday_schedule_history_access)],
    limit: int = Query(100, ge=1, le=500, description="Nombre maximum d'entrées"),
):
    """
    Récupérer l'historique complet des modifications d'un classement.

    **Accessible à :** Admin, Aumônier, CHARGE_CLASSEMENT_DIMANCHE, CENSEUR, CENSEUR_ADJOINT.

    Affiche toutes les modifications avec :
    - Qui a fait la modification (nom complet)
    - Quand (date et heure)
    - Quoi (description de l'action)
    - Où (adresse IP si disponible)
    - Valeurs avant/après

    Les censeurs ont accès pour leurs besoins disciplinaires.
    """
    service = _get_service(session)
    return await service.get_modification_history(template_id, limit)
