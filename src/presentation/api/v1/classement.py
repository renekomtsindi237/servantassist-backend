"""
Endpoints API pour le module Classements (CHARGE_CLASSEMENT_DIMANCHE / SEMAINE).
"""

import asyncio
import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.classement_service import ClassementService
from src.core.entities.classement import ClassementStatus, ClassementType
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.classement_repository import ClassementRepository
from src.infrastructure.services.email_service import EmailService
from src.presentation.dependencies.auth_deps import get_current_active_user
from src.presentation.schemas.classement import (
    ClassementCreate,
    ClassementListResponse,
    ClassementResponse,
    ClassementUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()


async def require_classement_manager(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> User:
    if current_user.role in (UserRole.ADMIN, UserRole.AUMÔNIER):
        return current_user

    if current_user.role != UserRole.SERVANT:
        raise HTTPException(
            status_code=403,
            detail="Accès réservé aux chargés de classement.",
        )

    from src.infrastructure.repositories.responsable_repository import (
        NominationRepository,
    )

    nom_repo = NominationRepository(session)
    nominations = await nom_repo.get_active_by_user(current_user.id)
    allowed = ("CHARGE_CLASSEMENT_DIMANCHE", "CHARGE_CLASSEMENT_SEMAINE")

    if not nominations or not any(n.poste.value in allowed for n in nominations):
        roles = ", ".join(n.poste.value for n in nominations) if nominations else "aucun"
        raise HTTPException(
            status_code=403,
            detail=f"Accès réservé au Chargé de Classement. Votre rôle : {roles}",
        )

    return current_user


def get_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ClassementService:
    return ClassementService(ClassementRepository(session))


@router.post(
    "/",
    response_model=ClassementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un classement",
)
async def create_classement(
    data: ClassementCreate,
    current_user: Annotated[User, Depends(require_classement_manager)],
    service: Annotated[ClassementService, Depends(get_service)],
):
    postes_dicts = [p.model_dump() for p in data.postes]
    classement = await service.create(
        type=data.type,
        date=data.date,
        heure=data.heure,
        lieu=data.lieu,
        created_by=current_user.id,
        solennite=data.solennite,
        couleur_liturgique=data.couleur_liturgique,
        semaine=data.semaine,
        annee=data.annee,
        horaire=data.horaire,
        type_extra=data.type_extra,
        participants=data.participants,
        postes=postes_dicts,
    )
    return classement


@router.get(
    "/published",
    response_model=ClassementListResponse,
    summary="Classements publiés",
    description="Liste les classements publiés, accessibles à tous les utilisateurs authentifiés.",
)
async def list_published_classements(
    current_user: Annotated[User, Depends(get_current_active_user)],
    service: Annotated[ClassementService, Depends(get_service)],
    type: Optional[ClassementType] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    items, total = await service.list(skip=skip, limit=limit, type=type, status=ClassementStatus.PUBLIE)
    return ClassementListResponse(items=items, total=total)


@router.get(
    "/",
    response_model=ClassementListResponse,
    summary="Lister les classements",
)
async def list_classements(
    current_user: Annotated[User, Depends(require_classement_manager)],
    service: Annotated[ClassementService, Depends(get_service)],
    type: Optional[ClassementType] = Query(None),
    status_filter: Optional[ClassementStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    items, total = await service.list(skip=skip, limit=limit, type=type, status=status_filter)
    return ClassementListResponse(items=items, total=total)


@router.get(
    "/{classement_id}",
    response_model=ClassementResponse,
    summary="Obtenir un classement",
)
async def get_classement(
    classement_id: UUID,
    current_user: Annotated[User, Depends(require_classement_manager)],
    service: Annotated[ClassementService, Depends(get_service)],
):
    classement = await service.get(classement_id)
    if not classement:
        raise HTTPException(status_code=404, detail="Classement introuvable.")
    return classement


@router.patch(
    "/{classement_id}",
    response_model=ClassementResponse,
    summary="Modifier un classement",
)
async def update_classement(
    classement_id: UUID,
    data: ClassementUpdate,
    current_user: Annotated[User, Depends(require_classement_manager)],
    service: Annotated[ClassementService, Depends(get_service)],
):
    postes_dicts = [p.model_dump() for p in data.postes] if data.postes is not None else None
    classement = await service.update(
        classement_id,
        date=data.date,
        heure=data.heure,
        lieu=data.lieu,
        solennite=data.solennite,
        couleur_liturgique=data.couleur_liturgique,
        semaine=data.semaine,
        annee=data.annee,
        horaire=data.horaire,
        type_extra=data.type_extra,
        participants=data.participants,
        postes=postes_dicts,
    )
    if not classement:
        raise HTTPException(status_code=404, detail="Classement introuvable.")
    return classement


@router.post(
    "/{classement_id}/advance",
    response_model=ClassementResponse,
    summary="Avancer le statut (BROUILLON→FINALISE→PUBLIE)",
)
async def advance_classement(
    classement_id: UUID,
    current_user: Annotated[User, Depends(require_classement_manager)],
    service: Annotated[ClassementService, Depends(get_service)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    try:
        classement = await service.advance_status(classement_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not classement:
        raise HTTPException(status_code=404, detail="Classement introuvable.")

    if classement.status == ClassementStatus.PUBLIE:
        asyncio.create_task(_notify_classement_published(classement, session))

    return classement


async def _notify_classement_published(classement: ClassementResponse, session: AsyncSession) -> None:
    """Notifie tous les servants actifs qu'un classement a été publié."""
    try:
        from src.infrastructure.repositories.user_repository import UserRepository

        user_repo = UserRepository(session)
        servants, _ = await user_repo.list_paginated(role=UserRole.SERVANT, is_active=True, page_size=500)
        email_svc = EmailService()
        type_labels = {
            "DIMANCHE": "Classement du Dimanche",
            "SEMAINE": "Classement de la Semaine",
            "EXTRAORDINAIRE": "Classement Extraordinaire",
        }
        type_label = type_labels.get(
            classement.type.value if hasattr(classement.type, "value") else str(classement.type),
            "Classement",
        )
        date_str = classement.date if isinstance(classement.date, str) else str(classement.date)
        title = f"{type_label} publié — {date_str}"
        body = (
            f"Un nouveau classement vient d'être publié : <strong>{type_label}</strong> du {date_str}.<br><br>"
            f"Consultez votre rôle dans le classement pour vous préparer au service liturgique."
        )
        for servant in servants:
            if servant.email:
                await email_svc.send_general_notification(
                    to_email=servant.email,
                    user_first_name=servant.first_name or "Servant",
                    title=title,
                    body=body,
                )
    except Exception as exc:
        logger.error("Erreur notification classement publié | error=%s", str(exc))


@router.delete(
    "/{classement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un classement",
)
async def delete_classement(
    classement_id: UUID,
    current_user: Annotated[User, Depends(require_classement_manager)],
    service: Annotated[ClassementService, Depends(get_service)],
):
    try:
        deleted = await service.delete(classement_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not deleted:
        raise HTTPException(status_code=404, detail="Classement introuvable.")
