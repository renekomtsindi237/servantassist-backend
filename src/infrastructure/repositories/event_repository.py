"""
Repository pour les entites Event et EventParticipant.

Fournit les operations CRUD + filtrage + pagination + gestion des participants.
"""

import math
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.event import Event, EventParticipant, EventStatus, EventType
from src.core.entities.user import User
from src.core.interfaces.repository import IRepository
from src.infrastructure.security.field_encryption import decrypt_str_fields

_USER_PII = ("first_name", "last_name", "email", "phone_number")


class EventRepository(IRepository[Event]):
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Lecture ────────────────────────────────────────────────────────

    async def get(self, id: UUID) -> Optional[Event]:
        statement = select(Event).where(Event.id == id)
        result = await self.session.exec(statement)
        return result.first()

    async def list(
        self,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Event]:
        statement = select(Event).order_by(Event.start_time)
        if date_from:
            statement = statement.where(Event.start_time >= date_from)
        if date_to:
            statement = statement.where(Event.start_time <= date_to)
        result = await self.session.exec(statement)
        return result.all()

    async def list_paginated(
        self,
        *,
        event_type: Optional[EventType] = None,
        status: Optional[EventStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Event], int]:
        """Liste paginee avec filtres optionnels. Retourne (events, total_count)."""
        statement = select(Event)

        if event_type is not None:
            statement = statement.where(Event.event_type == event_type)
        if status is not None:
            statement = statement.where(Event.status == status)
        if start_date:
            statement = statement.where(Event.start_time >= start_date)
        if end_date:
            statement = statement.where(Event.start_time <= end_date)
        if search:
            search_term = f"%{search.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(Event.title).like(search_term),
                    func.lower(Event.location).like(search_term),
                )
            )

        # Compter le total
        count_stmt = select(func.count()).select_from(statement.subquery())
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        # Pagination
        offset = (page - 1) * page_size
        statement = statement.offset(offset).limit(page_size).order_by(Event.start_time.desc())

        result = await self.session.exec(statement)
        events = result.all()

        return events, total

    # ── Ecriture ──────────────────────────────────────────────────────

    async def create(self, entity: Event) -> Event:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: UUID, entity: Event) -> Event:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> bool:
        # Supprimer d'abord les participants lies
        part_stmt = select(EventParticipant).where(EventParticipant.event_id == id)
        part_result = await self.session.exec(part_stmt)
        for p in part_result.all():
            await self.session.delete(p)

        statement = select(Event).where(Event.id == id)
        result = await self.session.exec(statement)
        event = result.first()
        if event:
            await self.session.delete(event)
            await self.session.commit()
            return True
        return False

    # ── Participants ──────────────────────────────────────────────────

    async def get_participant_count(self, event_id: UUID) -> int:
        """Compte le nombre de participants a un evenement."""
        stmt = select(func.count()).where(EventParticipant.event_id == event_id)
        result = await self.session.exec(stmt)
        return result.one()

    async def get_participants(self, event_id: UUID) -> List[dict]:
        """
        Recupere les participants avec les infos utilisateur.
        Retourne une liste de dictionnaires enrichis.
        """
        stmt = (
            select(EventParticipant).where(EventParticipant.event_id == event_id).order_by(EventParticipant.created_at)
        )
        result = await self.session.exec(stmt)
        participants = result.all()

        enriched = []
        for p in participants:
            # Charger les infos utilisateur
            user_stmt = select(User).where(User.id == p.user_id)
            user_result = await self.session.exec(user_stmt)
            user = user_result.first()
            if user:
                decrypt_str_fields(user, _USER_PII)

            enriched.append(
                {
                    "id": p.id,
                    "event_id": p.event_id,
                    "user_id": p.user_id,
                    "participant_role": p.participant_role,
                    "status": p.status,
                    "notes": p.notes,
                    "added_by": p.added_by,
                    "user_first_name": user.first_name if user else None,
                    "user_last_name": user.last_name if user else None,
                    "user_email": user.email if user else None,
                    "user_phone": user.phone_number if user else None,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                }
            )

        return enriched

    async def add_participant(self, participant: EventParticipant) -> EventParticipant:
        """Ajoute un participant a un evenement."""
        self.session.add(participant)
        await self.session.commit()
        await self.session.refresh(participant)
        return participant

    async def get_participant(self, participant_id: UUID) -> Optional[EventParticipant]:
        """Recupere un participant par son ID."""
        stmt = select(EventParticipant).where(EventParticipant.id == participant_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def get_participant_by_event_and_user(self, event_id: UUID, user_id: UUID) -> Optional[EventParticipant]:
        """Verifie si un utilisateur est deja participant a un evenement."""
        stmt = select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.user_id == user_id,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def update_participant(self, participant: EventParticipant) -> EventParticipant:
        """Met a jour un participant."""
        self.session.add(participant)
        await self.session.commit()
        await self.session.refresh(participant)
        return participant

    async def remove_participant(self, participant_id: UUID) -> bool:
        """Supprime un participant d'un evenement."""
        stmt = select(EventParticipant).where(EventParticipant.id == participant_id)
        result = await self.session.exec(stmt)
        participant = result.first()
        if participant:
            await self.session.delete(participant)
            await self.session.commit()
            return True
        return False

    async def get_events_for_user(self, user_id: UUID) -> List[Event]:
        """Recupere tous les evenements auxquels un utilisateur participe."""
        stmt = select(EventParticipant.event_id).where(EventParticipant.user_id == user_id)
        result = await self.session.exec(stmt)
        event_ids = result.all()

        if not event_ids:
            return []

        events_stmt = select(Event).where(Event.id.in_(event_ids)).order_by(Event.start_time)
        events_result = await self.session.exec(events_stmt)
        return events_result.all()
