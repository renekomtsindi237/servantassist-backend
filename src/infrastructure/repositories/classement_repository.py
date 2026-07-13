"""
Repository pour la gestion des classements.
"""

from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.entities.classement import Classement, ClassementStatus, ClassementType
from src.core.utils import utc_now


class ClassementRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, classement: Classement) -> Classement:
        self.session.add(classement)
        await self.session.commit()
        await self.session.refresh(classement)
        return classement

    async def get_by_id(self, classement_id: UUID) -> Optional[Classement]:
        result = await self.session.execute(select(Classement).where(Classement.id == classement_id))
        return result.scalar_one_or_none()

    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        type: Optional[ClassementType] = None,
        status: Optional[ClassementStatus] = None,
        created_by: Optional[UUID] = None,
    ) -> Tuple[List[Classement], int]:
        query = select(Classement)
        count_query = select(func.count(Classement.id))

        filters = []
        if type:
            filters.append(Classement.type == type)
        if status:
            filters.append(Classement.status == status)
        if created_by:
            filters.append(Classement.created_by == created_by)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        query = query.order_by(Classement.created_at.desc()).offset(skip).limit(limit)

        result = await self.session.execute(query)
        items = list(result.scalars().all())

        count_result = await self.session.execute(count_query)
        total = count_result.scalar_one()

        return items, total

    async def update(self, classement: Classement) -> Classement:
        classement.updated_at = utc_now()
        await self.session.commit()
        await self.session.refresh(classement)
        return classement

    async def delete(self, classement_id: UUID) -> bool:
        classement = await self.get_by_id(classement_id)
        if not classement:
            return False
        await self.session.delete(classement)
        await self.session.commit()
        return True
