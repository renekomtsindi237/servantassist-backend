"""
Service pour la gestion des activités sportives et culturelles.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID, uuid4

from fastapi import HTTPException, status

from src.core.entities.sport_culture import (
    EventParticipation,
    EventResult,
    EventStatus,
    EventTeam,
    EventType,
    ParticipationStatus,
    ResultType,
    SportCultureEvent,
    SportCultureReport,
    SportType,
)
from src.core.interfaces.repositories import (
    IEventParticipationRepository,
    IEventResultRepository,
    IEventTeamRepository,
    ISportCultureEventRepository,
)
from src.core.utils import utc_now


class SportCultureService:
    """Service de gestion des activités sportives et culturelles."""

    def __init__(
        self,
        event_repo: ISportCultureEventRepository,
        participation_repo: IEventParticipationRepository,
        result_repo: IEventResultRepository,
        team_repo: IEventTeamRepository,
    ):
        self.event_repo = event_repo
        self.participation_repo = participation_repo
        self.result_repo = result_repo
        self.team_repo = team_repo

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES ÉVÉNEMENTS
    # ══════════════════════════════════════════════════════════════════

    async def create_event(
        self,
        title: str,
        description: str,
        event_type: EventType,
        date: datetime,
        start_time: str,
        end_time: str,
        location: str,
        max_participants: int,
        created_by: UUID,
        sport_type: Optional[SportType] = None,
        cost: Optional[float] = None,
        registration_deadline: Optional[datetime] = None,
        notes: Optional[str] = None,
        broadcast_notification: bool = True,
    ) -> SportCultureEvent:
        """Crée un nouvel événement."""
        event = SportCultureEvent(
            id=uuid4(),
            title=title,
            description=description,
            event_type=event_type,
            sport_type=sport_type,
            date=date,
            start_time=start_time,
            end_time=end_time,
            location=location,
            max_participants=max_participants,
            cost=cost,
            registration_deadline=registration_deadline,
            notes=notes,
            broadcast_notification=broadcast_notification,
            created_by=created_by,
        )

        event = await self.event_repo.create(event)

        if broadcast_notification:
            from src.application.services.notification_service import (
                NotificationService,
            )
            from src.core.entities.notification import (
                NotificationChannel,
                NotificationPriority,
                NotificationType,
            )

            notif_service = NotificationService(self.event_repo.session)
            await notif_service.broadcast(
                target="all",
                notification_type=NotificationType.GENERAL,
                channel=NotificationChannel.IN_APP,
                priority=NotificationPriority.NORMAL,
                title=f"Nouvel événement : {event.title}",
                body=(f"Le {event.date.strftime('%d/%m/%Y')} " f"à {event.start_time} — {event.location}."),
                sent_by=event.created_by,
            )

        return event

    async def get_event(self, event_id: UUID) -> Optional[SportCultureEvent]:
        """Récupère un événement par son ID."""
        return await self.event_repo.get_by_id(event_id)

    async def list_events(
        self,
        skip: int = 0,
        limit: int = 50,
        event_type: Optional[EventType] = None,
        status: Optional[EventStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Tuple[List[SportCultureEvent], int]:
        """Liste les événements avec filtres."""
        return await self.event_repo.list_events(
            skip=skip,
            limit=limit,
            event_type=event_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
        )

    async def update_event(
        self,
        event_id: UUID,
        title: Optional[str] = None,
        description: Optional[str] = None,
        event_type: Optional[EventType] = None,
        sport_type: Optional[SportType] = None,
        date: Optional[datetime] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        location: Optional[str] = None,
        max_participants: Optional[int] = None,
        cost: Optional[float] = None,
        status: Optional[EventStatus] = None,
        registration_deadline: Optional[datetime] = None,
        notes: Optional[str] = None,
    ) -> Optional[SportCultureEvent]:
        """Met à jour un événement."""
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            return None

        # Mise à jour des champs
        if title is not None:
            event.title = title
        if description is not None:
            event.description = description
        if event_type is not None:
            event.event_type = event_type
        if sport_type is not None:
            event.sport_type = sport_type
        if date is not None:
            event.date = date
        if start_time is not None:
            event.start_time = start_time
        if end_time is not None:
            event.end_time = end_time
        if location is not None:
            event.location = location
        if max_participants is not None:
            event.max_participants = max_participants
        if cost is not None:
            event.cost = cost
        if status is not None:
            event.status = status
        if registration_deadline is not None:
            event.registration_deadline = registration_deadline
        if notes is not None:
            event.notes = notes

        return await self.event_repo.update(event)

    async def add_event_photo(
        self,
        event_id: UUID,
        photo_url: str,
    ) -> Optional[SportCultureEvent]:
        """Ajoute une photo à un événement sport/culture."""
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            return None
        event.photos = list(event.photos or []) + [photo_url]
        return await self.event_repo.update(event)

    async def delete_event(self, event_id: UUID) -> bool:
        """Supprime un événement."""
        # Vérifier qu'il n'y a pas de participations
        participations = await self.participation_repo.get_by_event(event_id)
        if participations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete event with participants",
            )

        return await self.event_repo.delete(event_id)

    async def get_upcoming_events(self, limit: int = 10) -> List[SportCultureEvent]:
        """Récupère les événements à venir."""
        return await self.event_repo.get_upcoming_events(limit)

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES PARTICIPATIONS
    # ══════════════════════════════════════════════════════════════════

    async def register_participant(
        self,
        event_id: UUID,
        servant_id: UUID,
        registered_by: UUID,
        notes: Optional[str] = None,
    ) -> EventParticipation:
        """Inscrit un participant à un événement."""
        # Vérifier que l'événement existe
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found.",
            )

        # Vérifier que le servant n'est pas déjà inscrit
        existing = await self.participation_repo.get_by_event_and_servant(event_id, servant_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This servant is already registered for this event.",
            )

        # Vérifier le nombre maximum de participants
        if event.max_participants > 0:
            count = await self.participation_repo.count_by_event(event_id)
            if count >= event.max_participants:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="This event is full. The maximum number of participants has been reached.",
                )

        participation = EventParticipation(
            id=uuid4(),
            event_id=event_id,
            servant_id=servant_id,
            notes=notes,
            registered_by=registered_by,
        )

        created = await self.participation_repo.create(participation)
        return await self.participation_repo.enrich_participation(created)

    async def register_participants_batch(
        self,
        event_id: UUID,
        servant_ids: List[UUID],
        registered_by: UUID,
        notes: Optional[str] = None,
    ) -> List[EventParticipation]:
        """Inscrit plusieurs participants à un événement."""
        # Vérifier que l'événement existe
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cet événement est introuvable.",
            )

        # Vérifier le nombre maximum de participants
        if event.max_participants > 0:
            current_count = await self.participation_repo.count_by_event(event_id)
            if current_count + len(servant_ids) > event.max_participants:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Not enough space for all participants",
                )

        participations = []
        for servant_id in servant_ids:
            # Vérifier que le servant n'est pas déjà inscrit
            existing = await self.participation_repo.get_by_event_and_servant(event_id, servant_id)
            if not existing:
                participation = EventParticipation(
                    id=uuid4(),
                    event_id=event_id,
                    servant_id=servant_id,
                    notes=notes,
                    registered_by=registered_by,
                )
                participations.append(participation)

        created_participations = await self.participation_repo.create_batch(participations)

        # Enrichir les participations
        enriched = []
        for participation in created_participations:
            enriched_participation = await self.participation_repo.enrich_participation(participation)
            enriched.append(enriched_participation)

        return enriched

    async def get_event_participants(self, event_id: UUID) -> List[EventParticipation]:
        """Récupère les participants d'un événement."""
        participations = await self.participation_repo.get_by_event(event_id)

        # Enrichir les participations
        enriched = []
        for participation in participations:
            enriched_participation = await self.participation_repo.enrich_participation(participation)
            enriched.append(enriched_participation)

        return enriched

    async def get_servant_participations(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[EventParticipation]:
        """Récupère les participations d'un servant."""
        participations = await self.participation_repo.get_by_servant(servant_id, start_date, end_date)

        # Enrichir les participations
        enriched = []
        for participation in participations:
            enriched_participation = await self.participation_repo.enrich_participation(participation)
            enriched.append(enriched_participation)

        return enriched

    async def mark_attendance(
        self,
        participation_id: UUID,
        status: ParticipationStatus,
        marked_by: UUID,
        notes: Optional[str] = None,
    ) -> Optional[EventParticipation]:
        """Marque la présence d'un participant."""
        participation = await self.participation_repo.get_by_id(participation_id)
        if not participation:
            return None

        participation.status = status
        participation.attendance_marked_at = utc_now()
        participation.marked_by = marked_by
        if notes:
            participation.notes = notes

        updated = await self.participation_repo.update(participation)
        return await self.participation_repo.enrich_participation(updated)

    async def mark_payment(
        self,
        participation_id: UUID,
        payment_status: bool,
        notes: Optional[str] = None,
    ) -> Optional[EventParticipation]:
        """Marque le paiement d'un participant."""
        participation = await self.participation_repo.get_by_id(participation_id)
        if not participation:
            return None

        participation.payment_status = payment_status
        if payment_status:
            participation.payment_date = utc_now()
        if notes:
            participation.notes = notes

        updated = await self.participation_repo.update(participation)
        return await self.participation_repo.enrich_participation(updated)

    async def cancel_registration(self, participation_id: UUID) -> bool:
        """Annule une inscription."""
        return await self.participation_repo.delete(participation_id)

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES RÉSULTATS
    # ══════════════════════════════════════════════════════════════════

    async def add_result(
        self,
        event_id: UUID,
        result_type: ResultType,
        description: str,
        recorded_by: UUID,
        team_name: Optional[str] = None,
        score: Optional[int] = None,
        opponent_name: Optional[str] = None,
        opponent_score: Optional[int] = None,
        ranking: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> Optional[EventResult]:
        """Ajoute un résultat à un événement."""
        # Vérifier que l'événement existe
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            return None

        result = EventResult(
            id=uuid4(),
            event_id=event_id,
            result_type=result_type,
            team_name=team_name,
            score=score,
            opponent_name=opponent_name,
            opponent_score=opponent_score,
            ranking=ranking,
            description=description,
            notes=notes,
            recorded_by=recorded_by,
        )

        return await self.result_repo.create(result)

    async def get_event_results(self, event_id: UUID) -> List[EventResult]:
        """Récupère les résultats d'un événement."""
        return await self.result_repo.get_by_event(event_id)

    async def delete_result(self, result_id: UUID) -> bool:
        """Supprime un résultat."""
        return await self.result_repo.delete(result_id)

    # ══════════════════════════════════════════════════════════════════
    #  GESTION DES ÉQUIPES
    # ══════════════════════════════════════════════════════════════════

    async def create_team(
        self,
        event_id: UUID,
        team_name: str,
        captain_id: UUID,
        created_by: UUID,
        members: List[UUID] = None,
    ) -> Optional[EventTeam]:
        """Crée une équipe pour un événement."""
        # Vérifier que l'événement existe
        event = await self.event_repo.get_by_id(event_id)
        if not event:
            return None

        # Convert UUIDs to strings for JSON serialization
        member_strings = [str(m) for m in (members or [])]

        team = EventTeam(
            id=uuid4(),
            event_id=event_id,
            team_name=team_name,
            captain_id=captain_id,
            members=member_strings,
            created_by=created_by,
        )

        created = await self.team_repo.create(team)
        return await self.team_repo.enrich_team(created)

    async def get_event_teams(self, event_id: UUID) -> List[EventTeam]:
        """Récupère les équipes d'un événement."""
        teams = await self.team_repo.get_by_event(event_id)

        # Enrichir les équipes
        enriched = []
        for team in teams:
            enriched_team = await self.team_repo.enrich_team(team)
            enriched.append(enriched_team)

        return enriched

    async def update_team(
        self,
        team_id: UUID,
        team_name: Optional[str] = None,
        captain_id: Optional[UUID] = None,
        members: Optional[List[UUID]] = None,
    ) -> Optional[EventTeam]:
        """Met à jour une équipe."""
        team = await self.team_repo.get_by_id(team_id)
        if not team:
            return None

        if team_name is not None:
            team.team_name = team_name
        if captain_id is not None:
            team.captain_id = captain_id
        if members is not None:
            team.members = [str(m) for m in members]

        updated = await self.team_repo.update(team)
        return await self.team_repo.enrich_team(updated)

    async def delete_team(self, team_id: UUID) -> bool:
        """Supprime une équipe."""
        return await self.team_repo.delete(team_id)

    # ══════════════════════════════════════════════════════════════════
    #  RAPPORTS ET STATISTIQUES
    # ══════════════════════════════════════════════════════════════════

    async def generate_report(
        self,
        start_date: datetime,
        end_date: datetime,
        generated_by: UUID,
        event_type: Optional[EventType] = None,
    ) -> SportCultureReport:
        """Génère un rapport d'activités."""
        # Récupérer tous les événements de la période
        events, total_events = await self.event_repo.list_events(
            skip=0,
            limit=1000,
            event_type=event_type,
            start_date=start_date,
            end_date=end_date,
        )

        # Répartition par type
        events_by_type = {}
        for event in events:
            event_type_str = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
            events_by_type[event_type_str] = events_by_type.get(event_type_str, 0) + 1

        # Calculer les statistiques de participation
        total_participants = 0
        total_present = 0
        total_cost = 0.0
        total_revenue = 0.0
        events_summary = []

        for event in events:
            participations = await self.participation_repo.get_by_event(event.id)
            participants_count = len(participations)
            present_count = sum(
                1 for p in participations if p.status in [ParticipationStatus.PRESENT, ParticipationStatus.CONFIRME]
            )
            paid_count = sum(1 for p in participations if p.payment_status)

            total_participants += participants_count
            total_present += present_count

            if event.cost:
                total_cost += event.cost * participants_count
                total_revenue += event.cost * paid_count

            events_summary.append(
                {
                    "id": str(event.id),
                    "title": event.title,
                    "date": event.date.isoformat(),
                    "type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
                    "participants": participants_count,
                    "present": present_count,
                    "cost": event.cost or 0.0,
                }
            )

        # Taux de participation moyen
        average_participation_rate = (total_present / total_participants * 100) if total_participants > 0 else 0.0

        # Top participants
        # Compter les participations par servant
        servant_participations = {}
        for event in events:
            participations = await self.participation_repo.get_by_event(event.id)
            for participation in participations:
                servant_id = str(participation.servant_id)
                if servant_id not in servant_participations:
                    servant_participations[servant_id] = {
                        "servant_id": servant_id,
                        "servant_name": participation.servant_name or "Unknown",
                        "count": 0,
                    }
                servant_participations[servant_id]["count"] += 1

        # Trier par nombre de participations
        top_participants = sorted(servant_participations.values(), key=lambda x: x["count"], reverse=True)[:10]

        return SportCultureReport(
            id=uuid4(),
            start_date=start_date,
            end_date=end_date,
            total_events=total_events,
            events_by_type=events_by_type,
            total_participants=total_participants,
            average_participation_rate=average_participation_rate,
            total_cost=total_cost,
            total_revenue=total_revenue,
            events_summary=events_summary,
            top_participants=top_participants,
            generated_by=generated_by,
        )

    async def get_statistics(self) -> dict:
        """Récupère les statistiques globales."""
        # Récupérer tous les événements
        events, total_events = await self.event_repo.list_events(skip=0, limit=1000)

        # Répartition par type
        events_by_type = {}
        for event in events:
            event_type_str = (
                event.event_type.value
                if hasattr(event.event_type, "value")
                else str(event.event_type) if hasattr(event.event_type, "value") else str(event.event_type)
            )
            events_by_type[event_type_str] = events_by_type.get(event_type_str, 0) + 1

        # Répartition par statut
        events_by_status = {}
        for event in events:
            status_str = event.status.value if hasattr(event.status, "value") else str(event.status)
            events_by_status[status_str] = events_by_status.get(status_str, 0) + 1

        # Calculer les statistiques de participation
        total_participants = 0
        total_present = 0

        for event in events:
            participations = await self.participation_repo.get_by_event(event.id)
            total_participants += len(participations)
            total_present += sum(
                1 for p in participations if p.status in [ParticipationStatus.PRESENT, ParticipationStatus.CONFIRME]
            )

        average_participation_rate = (total_present / total_participants * 100) if total_participants > 0 else 0.0

        # Événements à venir et terminés
        now = utc_now()
        upcoming_events = sum(1 for e in events if e.date >= now)
        completed_events = sum(1 for e in events if str(e.status) in (EventStatus.TERMINE, EventStatus.TERMINE.value))

        return {
            "total_events": total_events,
            "events_by_type": events_by_type,
            "events_by_status": events_by_status,
            "total_participants": total_participants,
            "average_participation_rate": average_participation_rate,
            "upcoming_events": upcoming_events,
            "completed_events": completed_events,
        }

    async def get_servant_stats(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Récupère les statistiques d'un servant."""
        participations = await self.participation_repo.get_by_servant(servant_id, start_date, end_date)

        total_participations = len(participations)
        events_attended = sum(
            1 for p in participations if p.status in [ParticipationStatus.PRESENT, ParticipationStatus.CONFIRME]
        )
        events_missed = sum(1 for p in participations if p.status == ParticipationStatus.ABSENT)

        attendance_rate = (events_attended / total_participations * 100) if total_participations > 0 else 0.0

        # Calculer le total payé
        total_paid = 0.0
        for participation in participations:
            if participation.payment_status:
                event = await self.event_repo.get_by_id(participation.event_id)
                if event and event.cost:
                    total_paid += event.cost

        # Répartition par type d'événement
        events_by_type = {}
        for participation in participations:
            event = await self.event_repo.get_by_id(participation.event_id)
            if event:
                event_type_str = event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type)
                events_by_type[event_type_str] = events_by_type.get(event_type_str, 0) + 1

        return {
            "servant_id": str(servant_id),
            "total_participations": total_participations,
            "events_attended": events_attended,
            "events_missed": events_missed,
            "attendance_rate": attendance_rate,
            "total_paid": total_paid,
            "events_by_type": events_by_type,
        }
