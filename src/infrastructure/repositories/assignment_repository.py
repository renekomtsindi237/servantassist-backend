"""
Repository pour l'entite Assignment.

Fournit les operations CRUD + filtrage + pagination + enrichissement
pour les affectations liturgiques.
"""
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.assignment import Assignment, AssignmentStatus, LiturgicalRole
from src.core.entities.event import Event
from src.core.entities.user import User
from src.core.interfaces.repository import IRepository


class AssignmentRepository(IRepository[Assignment]):
    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Lecture ────────────────────────────────────────────────────────

    async def get(self, id: UUID) -> Optional[Assignment]:
        statement = select(Assignment).where(Assignment.id == id)
        result = await self.session.exec(statement)
        return result.first()

    async def list(self) -> List[Assignment]:
        statement = select(Assignment).order_by(Assignment.created_at.desc())
        result = await self.session.exec(statement)
        return result.all()

    async def list_by_user(self, user_id: UUID) -> List[Assignment]:
        """Toutes les affectations d'un servant."""
        statement = (
            select(Assignment)
            .where(Assignment.user_id == user_id)
            .order_by(Assignment.created_at.desc())
        )
        result = await self.session.exec(statement)
        return result.all()

    async def list_by_event(self, event_id: UUID) -> List[Assignment]:
        """Toutes les affectations d'un evenement."""
        statement = (
            select(Assignment)
            .where(Assignment.event_id == event_id)
            .order_by(Assignment.created_at)
        )
        result = await self.session.exec(statement)
        return result.all()

    async def list_paginated(
        self,
        *,
        event_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        status: Optional[AssignmentStatus] = None,
        liturgical_role: Optional[LiturgicalRole] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[Assignment], int]:
        """
        Liste paginee avec filtres multiples.

        Retourne (assignments, total_count).
        """
        statement = select(Assignment)

        if event_id is not None:
            statement = statement.where(Assignment.event_id == event_id)
        if user_id is not None:
            statement = statement.where(Assignment.user_id == user_id)
        if status is not None:
            statement = statement.where(Assignment.status == status)
        if liturgical_role is not None:
            statement = statement.where(Assignment.liturgical_role == liturgical_role)

        # Filtres par date (via jointure avec Event)
        if start_date or end_date:
            statement = statement.join(Event, Assignment.event_id == Event.id)
            if start_date:
                statement = statement.where(Event.start_time >= start_date)
            if end_date:
                statement = statement.where(Event.start_time <= end_date)

        # Compter le total
        count_stmt = select(func.count()).select_from(statement.subquery())
        count_result = await self.session.exec(count_stmt)
        total = count_result.one()

        # Pagination
        offset = (page - 1) * page_size
        statement = (
            statement.offset(offset)
            .limit(page_size)
            .order_by(Assignment.created_at.desc())
        )

        result = await self.session.exec(statement)
        assignments = result.all()

        return assignments, total

    async def get_by_event_and_user(
        self, event_id: UUID, user_id: UUID
    ) -> Optional[Assignment]:
        """Verifie si un servant est deja affecte a un evenement."""
        stmt = select(Assignment).where(
            Assignment.event_id == event_id,
            Assignment.user_id == user_id,
            Assignment.status != AssignmentStatus.CANCELLED,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def get_by_event_user_role(
        self, event_id: UUID, user_id: UUID, role: LiturgicalRole
    ) -> Optional[Assignment]:
        """Verifie si un servant est deja affecte avec le meme role."""
        stmt = select(Assignment).where(
            Assignment.event_id == event_id,
            Assignment.user_id == user_id,
            Assignment.liturgical_role == role,
            Assignment.status != AssignmentStatus.CANCELLED,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def count_by_event(self, event_id: UUID) -> int:
        """Nombre d'affectations actives pour un evenement."""
        stmt = select(func.count()).where(
            Assignment.event_id == event_id,
            Assignment.status != AssignmentStatus.CANCELLED,
        )
        result = await self.session.exec(stmt)
        return result.one()

    async def count_by_user(self, user_id: UUID) -> int:
        """Nombre d'affectations actives pour un servant."""
        stmt = select(func.count()).where(
            Assignment.user_id == user_id,
            Assignment.status != AssignmentStatus.CANCELLED,
        )
        result = await self.session.exec(stmt)
        return result.one()

    async def get_upcoming_for_user(self, user_id: UUID) -> List[Assignment]:
        """Affectations a venir d'un servant (evenements futurs)."""
        from datetime import datetime as dt
        from datetime import timezone

        now = dt.now(timezone.utc)
        stmt = (
            select(Assignment)
            .join(Event, Assignment.event_id == Event.id)
            .where(
                Assignment.user_id == user_id,
                Assignment.status.in_(
                    [
                        AssignmentStatus.PENDING,
                        AssignmentStatus.ACCEPTED,
                    ]
                ),
                Event.start_time >= now,
            )
            .order_by(Event.start_time)
        )
        result = await self.session.exec(stmt)
        return result.all()

    async def list_by_event_with_cancelled(self, event_id: UUID) -> List[Assignment]:
        """Toutes les affectations d'un evenement, y compris annulees."""
        statement = (
            select(Assignment)
            .where(Assignment.event_id == event_id)
            .order_by(Assignment.created_at)
        )
        result = await self.session.exec(statement)
        return result.all()

    # ── Enrichissement ────────────────────────────────────────────────

    async def enrich_assignment(self, assignment: Assignment) -> Dict:
        """
        Enrichit une affectation avec les infos utilisateur et evenement.
        Retourne un dictionnaire pret pour AssignmentResponse.
        """
        # Info utilisateur
        user_stmt = select(User).where(User.id == assignment.user_id)
        user_result = await self.session.exec(user_stmt)
        user = user_result.first()

        # Info evenement
        event_stmt = select(Event).where(Event.id == assignment.event_id)
        event_result = await self.session.exec(event_stmt)
        event = event_result.first()

        return {
            "id": assignment.id,
            "event_id": assignment.event_id,
            "user_id": assignment.user_id,
            "liturgical_role": assignment.liturgical_role,
            "status": assignment.status,
            "notes": assignment.notes,
            "assigned_by": assignment.assigned_by,
            "user_first_name": user.first_name if user else None,
            "user_last_name": user.last_name if user else None,
            "user_email": user.email if user else None,
            "user_phone": user.phone_number if user else None,
            "event_title": event.title if event else None,
            "event_type": event.event_type if event else None,
            "event_start_time": event.start_time if event else None,
            "event_location": event.location if event else None,
            "created_at": assignment.created_at,
            "updated_at": assignment.updated_at,
        }

    async def enrich_assignments(self, assignments: List[Assignment]) -> List[Dict]:
        """Enrichit une liste d'affectations."""
        return [await self.enrich_assignment(a) for a in assignments]

    # ── Ecriture ──────────────────────────────────────────────────────

    async def create(self, entity: Assignment) -> Assignment:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def update(self, id: UUID, entity: Assignment) -> Assignment:
        self.session.add(entity)
        await self.session.commit()
        await self.session.refresh(entity)
        return entity

    async def delete(self, id: UUID) -> bool:
        statement = select(Assignment).where(Assignment.id == id)
        result = await self.session.exec(statement)
        entity = result.first()
        if entity:
            await self.session.delete(entity)
            await self.session.commit()
            return True
        return False

    async def delete_by_event(self, event_id: UUID) -> int:
        """Supprime toutes les affectations d'un evenement. Retourne le nombre supprime."""
        stmt = select(Assignment).where(Assignment.event_id == event_id)
        result = await self.session.exec(stmt)
        assignments = result.all()
        count = 0
        for a in assignments:
            await self.session.delete(a)
            count += 1
        if count > 0:
            await self.session.commit()
        return count
