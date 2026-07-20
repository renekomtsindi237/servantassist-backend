"""
Repository pour les convocations de parents (Art. 48-49 du reglement interieur).
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.convocation import Convocation, ConvocationMotif, ConvocationStatus
from src.core.utils import utc_now


class ConvocationRepository:
    """Operations sur les convocations de parents."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, convocation_id: UUID) -> Optional[Convocation]:
        stmt = select(Convocation).where(Convocation.id == convocation_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def create(self, convocation: Convocation) -> Convocation:
        self.session.add(convocation)
        await self.session.commit()
        await self.session.refresh(convocation)
        return convocation

    async def update(self, convocation: Convocation) -> Convocation:
        convocation.updated_at = utc_now()
        self.session.add(convocation)
        await self.session.commit()
        await self.session.refresh(convocation)
        return convocation

    async def list_by_servant(self, servant_id: UUID) -> List[Convocation]:
        stmt = (
            select(Convocation)
            .where(Convocation.servant_id == servant_id)
            .order_by(Convocation.convocation_date.desc())
        )
        result = await self.session.exec(stmt)
        return result.all()

    async def get_pending_by_servant_and_motif(
        self, servant_id: UUID, motif: ConvocationMotif
    ) -> Optional[Convocation]:
        """Convocation EN_ATTENTE existante pour ce servant et ce motif (idempotence)."""
        stmt = select(Convocation).where(
            Convocation.servant_id == servant_id,
            Convocation.motif == motif,
            Convocation.status == ConvocationStatus.EN_ATTENTE,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def list_pending_past_deadline(self) -> List[Convocation]:
        """Convocations EN_ATTENTE dont le delai de reponse (Art. 49) est depasse."""
        now = utc_now()
        stmt = select(Convocation).where(
            Convocation.status == ConvocationStatus.EN_ATTENTE,
            Convocation.response_deadline < now,
        )
        result = await self.session.exec(stmt)
        return result.all()
