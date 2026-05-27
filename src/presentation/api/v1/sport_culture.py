"""
API endpoints pour le module CHARGE_SPORT_CULTURE - Activités sportives et culturelles.

Permissions:
- CHARGE_SPORT_CULTURE / CHARGE_SPORT_CULTURE_ADJOINT : Gestion complète
- Tous les utilisateurs authentifiés : Consultation et participation
"""

from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.services.sport_culture_service import SportCultureService
from src.core.entities.sport_culture import (
    EventStatus,
    EventType,
    ParticipationStatus,
    ResultType,
    SportType,
)
from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.sport_culture_repository import (
    EventParticipationRepository,
    EventResultRepository,
    EventTeamRepository,
    SportCultureEventRepository,
)
from src.infrastructure.services.storage_service import StorageService
from src.presentation.dependencies.auth_deps import (
    get_current_user,
    require_charge_sport_culture,
)
from src.presentation.schemas.sport_culture import (
    EventParticipationBatchCreate,
    EventParticipationCreate,
    EventParticipationListResponse,
    EventParticipationMarkAttendance,
    EventParticipationMarkPayment,
    EventParticipationResponse,
    EventResultCreate,
    EventResultResponse,
    EventTeamCreate,
    EventTeamResponse,
    EventTeamUpdate,
    ServantParticipationStatsResponse,
    SportCultureEventCreate,
    SportCultureEventListResponse,
    SportCultureEventResponse,
    SportCultureEventUpdate,
    SportCultureReportRequest,
    SportCultureReportResponse,
    SportCultureStatsResponse,
)

router = APIRouter()


# ══════════════════════════════════════════════════════════════════
#  DÉPENDANCES
# ══════════════════════════════════════════════════════════════════


def get_sport_culture_service(
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> SportCultureService:
    """Dépendance pour obtenir le service sport/culture."""
    event_repo = SportCultureEventRepository(db)
    participation_repo = EventParticipationRepository(db)
    result_repo = EventResultRepository(db)
    team_repo = EventTeamRepository(db)
    return SportCultureService(event_repo, participation_repo, result_repo, team_repo)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - ÉVÉNEMENTS
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/events",
    response_model=SportCultureEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un événement",
    description="Crée un nouvel événement sportif ou culturel (CHARGE_SPORT_CULTURE uniquement)",
)
async def create_event(
    data: SportCultureEventCreate,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Crée un nouvel événement."""
    event = await service.create_event(
        title=data.title,
        description=data.description,
        event_type=data.event_type,
        sport_type=data.sport_type,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        location=data.location,
        max_participants=data.max_participants,
        cost=data.cost,
        registration_deadline=data.registration_deadline,
        notes=data.notes,
        broadcast_notification=data.broadcast_notification,
        created_by=current_user.id,
    )

    # Enrichir avec les compteurs
    participants_count = await service.participation_repo.count_by_event(event.id)
    confirmed_count = await service.participation_repo.count_confirmed_by_event(event.id)

    event_dict = event.model_dump()
    event_dict["participants_count"] = participants_count
    event_dict["confirmed_count"] = confirmed_count

    return SportCultureEventResponse(**event_dict)


@router.get(
    "/events",
    response_model=SportCultureEventListResponse,
    summary="Liste des événements",
    description="Liste tous les événements avec filtres",
)
async def list_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    event_type: Optional[EventType] = None,
    status: Optional[EventStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Liste les événements."""
    events, total = await service.list_events(
        skip=skip,
        limit=limit,
        event_type=event_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
    )

    # Enrichir avec les compteurs
    enriched_events = []
    for event in events:
        participants_count = await service.participation_repo.count_by_event(event.id)
        confirmed_count = await service.participation_repo.count_confirmed_by_event(event.id)

        event_dict = event.model_dump()
        event_dict["participants_count"] = participants_count
        event_dict["confirmed_count"] = confirmed_count

        enriched_events.append(SportCultureEventResponse(**event_dict))

    return SportCultureEventListResponse(
        items=enriched_events,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/events/{event_id}",
    response_model=SportCultureEventResponse,
    summary="Détail d'un événement",
    description="Récupère les détails d'un événement",
)
async def get_event(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Récupère un événement."""
    event = await service.get_event(event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet événement est introuvable.",
        )

    # Enrichir avec les compteurs
    participants_count = await service.participation_repo.count_by_event(event.id)
    confirmed_count = await service.participation_repo.count_confirmed_by_event(event.id)

    event_dict = event.model_dump()
    event_dict["participants_count"] = participants_count
    event_dict["confirmed_count"] = confirmed_count

    return SportCultureEventResponse(**event_dict)


@router.patch(
    "/events/{event_id}",
    response_model=SportCultureEventResponse,
    summary="Modifier un événement",
    description="Modifie un événement (CHARGE_SPORT_CULTURE uniquement)",
)
async def update_event(
    event_id: UUID,
    data: SportCultureEventUpdate,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Modifie un événement."""
    event = await service.update_event(
        event_id=event_id,
        title=data.title,
        description=data.description,
        event_type=data.event_type,
        sport_type=data.sport_type,
        date=data.date,
        start_time=data.start_time,
        end_time=data.end_time,
        location=data.location,
        max_participants=data.max_participants,
        cost=data.cost,
        status=data.status,
        registration_deadline=data.registration_deadline,
        notes=data.notes,
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet événement est introuvable.",
        )

    # Enrichir avec les compteurs
    participants_count = await service.participation_repo.count_by_event(event.id)
    confirmed_count = await service.participation_repo.count_confirmed_by_event(event.id)

    event_dict = event.model_dump()
    event_dict["participants_count"] = participants_count
    event_dict["confirmed_count"] = confirmed_count

    return SportCultureEventResponse(**event_dict)


@router.delete(
    "/events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un événement",
    description="Supprime un événement (CHARGE_SPORT_CULTURE uniquement)",
)
async def delete_event(
    event_id: UUID,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Supprime un événement."""
    success = await service.delete_event(event_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet événement est introuvable.",
        )


@router.get(
    "/events/upcoming/list",
    response_model=SportCultureEventListResponse,
    summary="Événements à venir",
    description="Récupère les événements à venir",
)
async def get_upcoming_events(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Récupère les événements à venir."""
    events = await service.get_upcoming_events(limit)

    # Enrichir avec les compteurs
    enriched_events = []
    for event in events:
        participants_count = await service.participation_repo.count_by_event(event.id)
        confirmed_count = await service.participation_repo.count_confirmed_by_event(event.id)

        event_dict = event.model_dump()
        event_dict["participants_count"] = participants_count
        event_dict["confirmed_count"] = confirmed_count

        enriched_events.append(SportCultureEventResponse(**event_dict))

    return SportCultureEventListResponse(
        items=enriched_events,
        total=len(enriched_events),
        skip=0,
        limit=limit,
    )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - PHOTOS ÉVÉNEMENTS
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/events/{event_id}/photos",
    response_model=SportCultureEventResponse,
    summary="Ajouter une photo à un événement",
    description=(
        "Upload une photo et l'ajoute à la galerie de l'événement "
        "(CHARGE_SPORT_CULTURE uniquement). Format JPEG/PNG/WebP, max 5 Mo."
    ),
)
async def upload_event_photo(
    event_id: UUID,
    file: Annotated[UploadFile, File(description="Photo de l'événement (JPEG, PNG, WebP, max 5 Mo)")],
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Upload une photo et l'associe à l'événement."""
    event = await service.get_event(event_id)
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Événement introuvable")

    storage = StorageService()
    try:
        photo_url = await storage.upload_sport_culture_photo(
            event_id=str(event_id),
            file_data=await file.read(),
            content_type=file.content_type or "image/jpeg",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    updated = await service.add_event_photo(event_id, photo_url)
    return updated


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - PARTICIPATIONS
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/events/{event_id}/register",
    response_model=EventParticipationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="S'inscrire à un événement",
    description="Inscrit un servant à un événement",
)
async def register_to_event(
    event_id: UUID,
    data: EventParticipationCreate,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Inscrit un servant à un événement."""
    participation = await service.register_participant(
        event_id=event_id,
        servant_id=data.servant_id,
        registered_by=current_user.id,
        notes=data.notes,
    )
    return participation


@router.post(
    "/events/{event_id}/register-batch",
    response_model=EventParticipationListResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Inscrire plusieurs servants",
    description="Inscrit plusieurs servants à un événement (CHARGE_SPORT_CULTURE uniquement)",
)
async def register_batch_to_event(
    event_id: UUID,
    data: EventParticipationBatchCreate,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Inscrit plusieurs servants à un événement."""
    participations = await service.register_participants_batch(
        event_id=event_id,
        servant_ids=data.servant_ids,
        registered_by=current_user.id,
        notes=data.notes,
    )
    return EventParticipationListResponse(
        items=participations,
        total=len(participations),
    )


@router.get(
    "/events/{event_id}/participants",
    response_model=EventParticipationListResponse,
    summary="Participants d'un événement",
    description="Liste les participants d'un événement",
)
async def get_event_participants(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Liste les participants d'un événement."""
    participations = await service.get_event_participants(event_id)
    return EventParticipationListResponse(
        items=participations,
        total=len(participations),
    )


@router.post(
    "/participations/{participation_id}/attendance",
    response_model=EventParticipationResponse,
    summary="Marquer la présence",
    description="Marque la présence d'un participant (CHARGE_SPORT_CULTURE uniquement)",
)
async def mark_participant_attendance(
    participation_id: UUID,
    data: EventParticipationMarkAttendance,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Marque la présence d'un participant."""
    participation = await service.mark_attendance(
        participation_id=participation_id,
        status=data.status,
        marked_by=current_user.id,
        notes=data.notes,
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette participation est introuvable.",
        )
    return participation


@router.post(
    "/participations/{participation_id}/payment",
    response_model=EventParticipationResponse,
    summary="Marquer le paiement",
    description="Marque le paiement d'un participant (CHARGE_SPORT_CULTURE uniquement)",
)
async def mark_participant_payment(
    participation_id: UUID,
    data: EventParticipationMarkPayment,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Marque le paiement d'un participant."""
    participation = await service.mark_payment(
        participation_id=participation_id,
        payment_status=data.payment_status,
        notes=data.notes,
    )
    if not participation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette participation est introuvable.",
        )
    return participation


@router.delete(
    "/participations/{participation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Annuler une inscription",
    description="Annule l'inscription d'un participant (CHARGE_SPORT_CULTURE uniquement)",
)
async def cancel_participation(
    participation_id: UUID,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Annule une inscription."""
    success = await service.cancel_registration(participation_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette participation est introuvable.",
        )


@router.get(
    "/servants/{servant_id}/participations",
    response_model=EventParticipationListResponse,
    summary="Participations d'un servant",
    description="Liste les participations d'un servant",
)
async def get_servant_participations(
    servant_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Liste les participations d'un servant."""
    participations = await service.get_servant_participations(
        servant_id=servant_id,
        start_date=start_date,
        end_date=end_date,
    )
    return EventParticipationListResponse(
        items=participations,
        total=len(participations),
    )


@router.get(
    "/servants/{servant_id}/stats",
    response_model=ServantParticipationStatsResponse,
    summary="Statistiques d'un servant",
    description="Récupère les statistiques de participation d'un servant",
)
async def get_servant_stats(
    servant_id: UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Récupère les statistiques d'un servant."""
    stats = await service.get_servant_stats(
        servant_id=servant_id,
        start_date=start_date,
        end_date=end_date,
    )
    return ServantParticipationStatsResponse(**stats)


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - RÉSULTATS
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/events/{event_id}/results",
    response_model=EventResultResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ajouter un résultat",
    description="Ajoute un résultat à un événement (CHARGE_SPORT_CULTURE uniquement)",
)
async def add_event_result(
    event_id: UUID,
    data: EventResultCreate,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Ajoute un résultat à un événement."""
    result = await service.add_result(
        event_id=event_id,
        result_type=data.result_type,
        description=data.description,
        recorded_by=current_user.id,
        team_name=data.team_name,
        score=data.score,
        opponent_name=data.opponent_name,
        opponent_score=data.opponent_score,
        ranking=data.ranking,
        notes=data.notes,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet événement est introuvable.",
        )
    return result


@router.get(
    "/events/{event_id}/results",
    response_model=List[EventResultResponse],
    summary="Résultats d'un événement",
    description="Récupère les résultats d'un événement",
)
async def get_event_results(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Récupère les résultats d'un événement."""
    results = await service.get_event_results(event_id)
    return results


@router.delete(
    "/results/{result_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer un résultat",
    description="Supprime un résultat (CHARGE_SPORT_CULTURE uniquement)",
)
async def delete_result(
    result_id: UUID,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Supprime un résultat."""
    success = await service.delete_result(result_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce résultat est introuvable.",
        )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - ÉQUIPES
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/events/{event_id}/teams",
    response_model=EventTeamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Créer une équipe",
    description="Crée une équipe pour un événement (CHARGE_SPORT_CULTURE uniquement)",
)
async def create_event_team(
    event_id: UUID,
    data: EventTeamCreate,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Crée une équipe pour un événement."""
    team = await service.create_team(
        event_id=event_id,
        team_name=data.team_name,
        captain_id=data.captain_id,
        members=data.members,
        created_by=current_user.id,
    )
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cet événement est introuvable.",
        )
    return team


@router.get(
    "/events/{event_id}/teams",
    response_model=List[EventTeamResponse],
    summary="Équipes d'un événement",
    description="Récupère les équipes d'un événement",
)
async def get_event_teams(
    event_id: UUID,
    current_user: User = Depends(get_current_user),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Récupère les équipes d'un événement."""
    teams = await service.get_event_teams(event_id)
    return teams


@router.patch(
    "/teams/{team_id}",
    response_model=EventTeamResponse,
    summary="Modifier une équipe",
    description="Modifie une équipe (CHARGE_SPORT_CULTURE uniquement)",
)
async def update_team(
    team_id: UUID,
    data: EventTeamUpdate,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Modifie une équipe."""
    team = await service.update_team(
        team_id=team_id,
        team_name=data.team_name,
        captain_id=data.captain_id,
        members=data.members,
    )
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette équipe est introuvable.",
        )
    return team


@router.delete(
    "/teams/{team_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Supprimer une équipe",
    description="Supprime une équipe (CHARGE_SPORT_CULTURE uniquement)",
)
async def delete_team(
    team_id: UUID,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Supprime une équipe."""
    success = await service.delete_team(team_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cette équipe est introuvable.",
        )


# ══════════════════════════════════════════════════════════════════
#  ENDPOINTS - RAPPORTS ET STATISTIQUES
# ══════════════════════════════════════════════════════════════════


@router.post(
    "/report",
    response_model=SportCultureReportResponse,
    summary="Générer un rapport",
    description="Génère un rapport d'activités (CHARGE_SPORT_CULTURE uniquement)",
)
async def generate_report(
    data: SportCultureReportRequest,
    current_user: User = Depends(require_charge_sport_culture),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Génère un rapport d'activités."""
    report = await service.generate_report(
        start_date=data.start_date,
        end_date=data.end_date,
        generated_by=current_user.id,
        event_type=data.event_type,
    )
    return report


@router.get(
    "/stats",
    response_model=SportCultureStatsResponse,
    summary="Statistiques globales",
    description="Récupère les statistiques globales",
)
async def get_stats(
    current_user: User = Depends(get_current_user),
    service: SportCultureService = Depends(get_sport_culture_service),
):
    """Récupère les statistiques globales."""
    stats = await service.get_statistics()
    return SportCultureStatsResponse(**stats)
