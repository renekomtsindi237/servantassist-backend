"""
Repository pour la gestion des activités sportives et culturelles.
"""

from datetime import datetime, timezone
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.sport_culture import (
    EventParticipation,
    EventResult,
    EventStatus,
    EventTeam,
    EventType,
    ParticipationStatus,
    SportCultureEvent,
)
from src.core.entities.user import User
from src.core.utils import utc_now
from src.infrastructure.security.field_encryption import decrypt_str_fields

_USER_PII = ("first_name", "last_name")


class SportCultureEventRepository:
    """Repository pour les événements sportifs et culturels."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, event: SportCultureEvent) -> SportCultureEvent:
        """Crée un nouvel événement."""
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def get_by_id(self, event_id: UUID) -> Optional[SportCultureEvent]:
        """Récupère un événement par son ID."""
        result = await self.session.execute(select(SportCultureEvent).where(SportCultureEvent.id == event_id))
        return result.scalar_one_or_none()

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
        query = select(SportCultureEvent)

        # Filtres
        if event_type:
            query = query.where(SportCultureEvent.event_type == event_type)
        if status:
            query = query.where(SportCultureEvent.status == status)
        if start_date:
            query = query.where(SportCultureEvent.date >= start_date)
        if end_date:
            query = query.where(SportCultureEvent.date <= end_date)

        # Compter le total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar()

        # Pagination et tri
        query = query.order_by(SportCultureEvent.date.desc())
        query = query.offset(skip).limit(limit)

        result = await self.session.execute(query)
        events = list(result.scalars().all())

        return events, total

    async def update(self, event: SportCultureEvent) -> SportCultureEvent:
        """Met à jour un événement."""
        event.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def delete(self, event_id: UUID) -> bool:
        """Supprime un événement."""
        event = await self.get_by_id(event_id)
        if not event:
            return False

        await self.session.delete(event)
        await self.session.commit()
        return True

    async def get_upcoming_events(self, limit: int = 10) -> List[SportCultureEvent]:
        """Récupère les événements à venir."""
        now = utc_now()
        result = await self.session.execute(
            select(SportCultureEvent)
            .where(SportCultureEvent.date >= now)
            .where(SportCultureEvent.status.in_([EventStatus.PLANIFIE, EventStatus.OUVERT, EventStatus.COMPLET]))
            .order_by(SportCultureEvent.date)
            .limit(limit)
        )
        return list(result.scalars().all())


class EventParticipationRepository:
    """Repository pour les participations aux événements."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, participation: EventParticipation) -> EventParticipation:
        """Crée une nouvelle participation."""
        self.session.add(participation)
        await self.session.commit()
        await self.session.refresh(participation)
        return participation

    async def create_batch(self, participations: List[EventParticipation]) -> List[EventParticipation]:
        """Crée plusieurs participations en batch."""
        for participation in participations:
            self.session.add(participation)
        await self.session.commit()
        for participation in participations:
            await self.session.refresh(participation)
        return participations

    async def get_by_id(self, participation_id: UUID) -> Optional[EventParticipation]:
        """Récupère une participation par son ID."""
        result = await self.session.execute(select(EventParticipation).where(EventParticipation.id == participation_id))
        return result.scalar_one_or_none()

    async def get_by_event(self, event_id: UUID) -> List[EventParticipation]:
        """Récupère les participations d'un événement."""
        result = await self.session.execute(
            select(EventParticipation)
            .where(EventParticipation.event_id == event_id)
            .order_by(EventParticipation.registration_date)
        )
        return list(result.scalars().all())

    async def get_by_servant(
        self,
        servant_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[EventParticipation]:
        """Récupère les participations d'un servant."""
        # Joindre avec les événements pour filtrer par date
        query = (
            select(EventParticipation)
            .join(SportCultureEvent, EventParticipation.event_id == SportCultureEvent.id)
            .where(EventParticipation.servant_id == servant_id)
        )

        if start_date:
            query = query.where(SportCultureEvent.date >= start_date)
        if end_date:
            query = query.where(SportCultureEvent.date <= end_date)

        query = query.order_by(SportCultureEvent.date.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_event_and_servant(self, event_id: UUID, servant_id: UUID) -> Optional[EventParticipation]:
        """Récupère une participation spécifique."""
        result = await self.session.execute(
            select(EventParticipation).where(
                and_(
                    EventParticipation.event_id == event_id,
                    EventParticipation.servant_id == servant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def update(self, participation: EventParticipation) -> EventParticipation:
        """Met à jour une participation."""
        participation.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(participation)
        return participation

    async def delete(self, participation_id: UUID) -> bool:
        """Supprime une participation."""
        participation = await self.get_by_id(participation_id)
        if not participation:
            return False

        await self.session.delete(participation)
        await self.session.commit()
        return True

    async def count_by_event(self, event_id: UUID) -> int:
        """Compte les participations d'un événement."""
        result = await self.session.execute(select(func.count()).where(EventParticipation.event_id == event_id))
        return result.scalar()

    async def count_confirmed_by_event(self, event_id: UUID) -> int:
        """Compte les participations confirmées d'un événement."""
        result = await self.session.execute(
            select(func.count()).where(
                and_(
                    EventParticipation.event_id == event_id,
                    EventParticipation.status.in_([ParticipationStatus.CONFIRME, ParticipationStatus.PRESENT]),
                )
            )
        )
        return result.scalar()

    async def enrich_participation(self, participation: EventParticipation) -> EventParticipation:
        """Enrichit une participation avec les noms."""
        # Récupérer le nom du servant
        servant_result = await self.session.execute(select(User).where(User.id == participation.servant_id))
        servant = servant_result.scalar_one_or_none()
        if servant:
            decrypt_str_fields(servant, _USER_PII)
            participation.servant_name = f"{servant.first_name} {servant.last_name}"

        return participation


class EventResultRepository:
    """Repository pour les résultats d'événements."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, result: EventResult) -> EventResult:
        """Crée un nouveau résultat."""
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result

    async def get_by_event(self, event_id: UUID) -> List[EventResult]:
        """Récupère les résultats d'un événement."""
        result = await self.session.execute(
            select(EventResult).where(EventResult.event_id == event_id).order_by(EventResult.created_at)
        )
        return list(result.scalars().all())

    async def delete(self, result_id: UUID) -> bool:
        """Supprime un résultat."""
        result = await self.session.execute(select(EventResult).where(EventResult.id == result_id))
        result_obj = result.scalar_one_or_none()
        if not result_obj:
            return False

        await self.session.delete(result_obj)
        await self.session.commit()
        return True


class EventTeamRepository:
    """Repository pour les équipes d'événements."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, team: EventTeam) -> EventTeam:
        """Crée une nouvelle équipe."""
        self.session.add(team)
        await self.session.commit()
        await self.session.refresh(team)
        return team

    async def get_by_id(self, team_id: UUID) -> Optional[EventTeam]:
        """Récupère une équipe par son ID."""
        result = await self.session.execute(select(EventTeam).where(EventTeam.id == team_id))
        return result.scalar_one_or_none()

    async def get_by_event(self, event_id: UUID) -> List[EventTeam]:
        """Récupère les équipes d'un événement."""
        result = await self.session.execute(
            select(EventTeam).where(EventTeam.event_id == event_id).order_by(EventTeam.team_name)
        )
        return list(result.scalars().all())

    async def update(self, team: EventTeam) -> EventTeam:
        """Met à jour une équipe."""
        await self.session.commit()
        await self.session.refresh(team)
        return team

    async def delete(self, team_id: UUID) -> bool:
        """Supprime une équipe."""
        team = await self.get_by_id(team_id)
        if not team:
            return False

        await self.session.delete(team)
        await self.session.commit()
        return True

    async def enrich_team(self, team: EventTeam) -> EventTeam:
        """Enrichit une équipe avec les noms."""
        # Récupérer le nom du capitaine
        captain_result = await self.session.execute(select(User).where(User.id == team.captain_id))
        captain = captain_result.scalar_one_or_none()
        if captain:
            decrypt_str_fields(captain, _USER_PII)
            team.captain_name = f"{captain.first_name} {captain.last_name}"

        # Récupérer les noms des membres
        if team.members:
            try:
                # Convertir les chaînes UUID en objets UUID
                member_ids = [UUID(str(m_id)) for m_id in team.members]

                members_result = await self.session.execute(select(User).where(User.id.in_(member_ids)))
                members = list(members_result.scalars().all())
                for m in members:
                    decrypt_str_fields(m, _USER_PII)

                # Créer une map pour respecter l'ordre ou juste lister les noms
                members_map = {m.id: f"{m.first_name} {m.last_name}" for m in members}

                team.members_names = []
                for m_id in member_ids:
                    if m_id in members_map:
                        team.members_names.append(members_map[m_id])

            except (ValueError, TypeError):
                # En cas d'erreur de format UUID
                team.members_names = []

        return team
