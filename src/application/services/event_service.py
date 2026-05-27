"""
Service metier pour la gestion des evenements et des participants.

Regles :
- L'aumonier et l'admin peuvent creer, modifier, supprimer des evenements.
- L'aumonier et l'admin peuvent ajouter/retirer des participants.
- Tous les utilisateurs authentifies peuvent consulter les evenements.
- Un servant/parent peut voir ses propres evenements.
- Un participant ne peut pas etre ajoute en double au meme evenement.
- La suppression d'un evenement supprime aussi ses participants (cascade logique).
"""
import math
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.event import (
    Event,
    EventParticipant,
    EventStatus,
    EventType,
    ParticipantStatus,
)
from src.core.entities.user import User
from src.core.utils import utc_now
from src.core.interfaces.repositories import IEventRepository
from src.core.interfaces.repositories import IUserRepository
from src.presentation.schemas.event import (
    EventCreate,
    EventDetailResponse,
    EventResponse,
    EventUpdate,
    ParticipantAdd,
    ParticipantResponse,
    ParticipantUpdate,
)
from src.presentation.schemas.user import PaginatedResponse


class EventService:
    def __init__(
        self,
        event_repository: IEventRepository,
        user_repository: Optional[IUserRepository] = None,
    ):
        self.event_repository = event_repository
        self.user_repository = user_repository

    # ══════════════════════════════════════════════════════════════════
    #  CRUD Evenements
    # ══════════════════════════════════════════════════════════════════

    async def create_event(
        self, event_data: EventCreate, created_by: UUID
    ) -> EventDetailResponse:
        """
        Cree un evenement avec participants optionnels.
        """
        event = Event(
            title=event_data.title,
            description=event_data.description,
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            location=event_data.location,
            event_type=event_data.event_type,
            status=event_data.status,
            created_by=created_by,
        )
        created_event = await self.event_repository.create(event)

        # Ajouter les participants si fournis
        if event_data.participants:
            for p in event_data.participants:
                await self._add_participant_internal(
                    event_id=created_event.id,
                    participant_data=p,
                    added_by=created_by,
                )

        return await self._build_event_detail(created_event.id)

    async def update_event(
        self, event_id: UUID, event_data: EventUpdate, updated_by: UUID
    ) -> EventDetailResponse:
        """Met a jour un evenement existant (modification partielle)."""
        event = await self.event_repository.get(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evenement introuvable.",
            )

        # Appliquer les modifications
        if event_data.title is not None:
            event.title = event_data.title
        if event_data.description is not None:
            event.description = event_data.description
        if event_data.start_time is not None:
            event.start_time = event_data.start_time
        if event_data.end_time is not None:
            event.end_time = event_data.end_time
        if event_data.location is not None:
            event.location = event_data.location
        if event_data.event_type is not None:
            event.event_type = event_data.event_type
        if event_data.status is not None:
            event.status = event_data.status

        # Validation coherence dates
        if event.end_time <= event.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La date de fin doit etre apres la date de debut.",
            )

        event.updated_by = updated_by
        event.updated_at = utc_now()
        await self.event_repository.update(event_id, event)

        return await self._build_event_detail(event_id)

    async def get_event(self, event_id: UUID) -> EventDetailResponse:
        """Recupere un evenement avec ses participants."""
        event = await self.event_repository.get(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evenement introuvable.",
            )
        return await self._build_event_detail(event_id)

    async def list_events(
        self,
        *,
        event_type: Optional[EventType] = None,
        event_status: Optional[EventStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[EventResponse]:
        """Liste paginee des evenements avec filtres."""
        events, total = await self.event_repository.list_paginated(
            event_type=event_type,
            status=event_status,
            start_date=start_date,
            end_date=end_date,
            search=search,
            page=page,
            page_size=page_size,
        )
        total_pages = math.ceil(total / page_size) if total > 0 else 1

        items = []
        for e in events:
            count = await self.event_repository.get_participant_count(e.id)
            items.append(
                EventResponse(
                    id=e.id,
                    title=e.title,
                    description=e.description,
                    start_time=e.start_time,
                    end_time=e.end_time,
                    location=e.location,
                    event_type=e.event_type,
                    status=e.status,
                    created_by=e.created_by,
                    updated_by=e.updated_by,
                    created_at=e.created_at,
                    updated_at=e.updated_at,
                    participant_count=count,
                )
            )

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    async def delete_event(self, event_id: UUID) -> None:
        """Supprime un evenement et ses participants."""
        event = await self.event_repository.get(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evenement introuvable.",
            )
        deleted = await self.event_repository.delete(event_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erreur lors de la suppression de l'evenement.",
            )

    async def get_my_events(self, user_id: UUID) -> List[EventResponse]:
        """Recupere les evenements auxquels l'utilisateur participe."""
        events = await self.event_repository.get_events_for_user(user_id)
        items = []
        for e in events:
            count = await self.event_repository.get_participant_count(e.id)
            items.append(
                EventResponse(
                    id=e.id,
                    title=e.title,
                    description=e.description,
                    start_time=e.start_time,
                    end_time=e.end_time,
                    location=e.location,
                    event_type=e.event_type,
                    status=e.status,
                    created_by=e.created_by,
                    updated_by=e.updated_by,
                    created_at=e.created_at,
                    updated_at=e.updated_at,
                    participant_count=count,
                )
            )
        return items

    # ══════════════════════════════════════════════════════════════════
    #  Gestion des participants
    # ══════════════════════════════════════════════════════════════════

    async def add_participant(
        self,
        event_id: UUID,
        participant_data: ParticipantAdd,
        added_by: UUID,
    ) -> ParticipantResponse:
        """Ajoute un participant a un evenement."""
        event = await self.event_repository.get(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evenement introuvable.",
            )

        return await self._add_participant_internal(
            event_id, participant_data, added_by
        )

    async def _add_participant_internal(
        self,
        event_id: UUID,
        participant_data: ParticipantAdd,
        added_by: UUID,
    ) -> ParticipantResponse:
        """Logique interne d'ajout de participant (pas de verification d'event)."""
        # Verifier que l'utilisateur existe
        if self.user_repository:
            user = await self.user_repository.get(participant_data.user_id)
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Utilisateur {participant_data.user_id} introuvable.",
                )

        # Verifier doublon
        existing = await self.event_repository.get_participant_by_event_and_user(
            event_id, participant_data.user_id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cet utilisateur est deja participant a cet evenement.",
            )

        participant = EventParticipant(
            event_id=event_id,
            user_id=participant_data.user_id,
            participant_role=participant_data.participant_role,
            notes=participant_data.notes,
            added_by=added_by,
        )
        created = await self.event_repository.add_participant(participant)

        # Enrichir avec les infos utilisateur
        user_info = None
        if self.user_repository:
            user_info = await self.user_repository.get(created.user_id)

        return ParticipantResponse(
            id=created.id,
            event_id=created.event_id,
            user_id=created.user_id,
            participant_role=created.participant_role,
            status=created.status,
            notes=created.notes,
            added_by=created.added_by,
            user_first_name=user_info.first_name if user_info else None,
            user_last_name=user_info.last_name if user_info else None,
            user_email=user_info.email if user_info else None,
            user_phone=user_info.phone_number if user_info else None,
            created_at=created.created_at,
            updated_at=created.updated_at,
        )

    async def update_participant(
        self,
        event_id: UUID,
        participant_id: UUID,
        data: ParticipantUpdate,
    ) -> ParticipantResponse:
        """Met a jour un participant (role, statut, notes)."""
        participant = await self.event_repository.get_participant(participant_id)
        if not participant or participant.event_id != event_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participant introuvable pour cet evenement.",
            )

        if data.participant_role is not None:
            participant.participant_role = data.participant_role
        if data.status is not None:
            participant.status = data.status
        if data.notes is not None:
            participant.notes = data.notes

        participant.updated_at = utc_now()
        updated = await self.event_repository.update_participant(participant)

        # Enrichir
        user_info = None
        if self.user_repository:
            user_info = await self.user_repository.get(updated.user_id)

        return ParticipantResponse(
            id=updated.id,
            event_id=updated.event_id,
            user_id=updated.user_id,
            participant_role=updated.participant_role,
            status=updated.status,
            notes=updated.notes,
            added_by=updated.added_by,
            user_first_name=user_info.first_name if user_info else None,
            user_last_name=user_info.last_name if user_info else None,
            user_email=user_info.email if user_info else None,
            user_phone=user_info.phone_number if user_info else None,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    async def remove_participant(self, event_id: UUID, participant_id: UUID) -> None:
        """Retire un participant d'un evenement."""
        participant = await self.event_repository.get_participant(participant_id)
        if not participant or participant.event_id != event_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Participant introuvable pour cet evenement.",
            )
        await self.event_repository.remove_participant(participant_id)

    async def get_event_participants(self, event_id: UUID) -> List[ParticipantResponse]:
        """Recupere la liste des participants d'un evenement."""
        event = await self.event_repository.get(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evenement introuvable.",
            )
        participants_data = await self.event_repository.get_participants(event_id)
        return [ParticipantResponse(**p) for p in participants_data]

    async def update_my_participation(
        self,
        event_id: UUID,
        user_id: UUID,
        new_status: ParticipantStatus,
    ) -> ParticipantResponse:
        """Permet a un participant de confirmer/decliner sa participation."""
        participant = await self.event_repository.get_participant_by_event_and_user(
            event_id, user_id
        )
        if not participant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vous n'etes pas participant a cet evenement.",
            )

        # Seuls certaines transitions sont autorisees pour le participant
        allowed = {ParticipantStatus.CONFIRME, ParticipantStatus.DECLINE}
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vous ne pouvez que confirmer ou decliner. Statuts autorises : {[s.value for s in allowed]}",
            )

        participant.status = new_status
        participant.updated_at = utc_now()
        updated = await self.event_repository.update_participant(participant)

        user_info = None
        if self.user_repository:
            user_info = await self.user_repository.get(updated.user_id)

        return ParticipantResponse(
            id=updated.id,
            event_id=updated.event_id,
            user_id=updated.user_id,
            participant_role=updated.participant_role,
            status=updated.status,
            notes=updated.notes,
            added_by=updated.added_by,
            user_first_name=user_info.first_name if user_info else None,
            user_last_name=user_info.last_name if user_info else None,
            user_email=user_info.email if user_info else None,
            user_phone=user_info.phone_number if user_info else None,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
        )

    # ── Helpers prives ────────────────────────────────────────────────

    async def _build_event_detail(self, event_id: UUID) -> EventDetailResponse:
        """Construit la reponse detaillee d'un evenement."""
        event = await self.event_repository.get(event_id)
        participants_data = await self.event_repository.get_participants(event_id)

        return EventDetailResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            start_time=event.start_time,
            end_time=event.end_time,
            location=event.location,
            event_type=event.event_type,
            status=event.status,
            created_by=event.created_by,
            updated_by=event.updated_by,
            created_at=event.created_at,
            updated_at=event.updated_at,
            participants=[ParticipantResponse(**p) for p in participants_data],
        )
