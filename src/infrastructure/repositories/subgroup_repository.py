"""
Repository pour les sous-groupes et leurs membres.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.subgroup import SubGroup, SubGroupMember
from src.core.entities.user import User


class SubGroupRepository:
    """Operations sur les sous-groupes."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, group_id: UUID) -> Optional[SubGroup]:
        stmt = select(SubGroup).where(SubGroup.id == group_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def get_by_name(self, name: str) -> Optional[SubGroup]:
        stmt = select(SubGroup).where(SubGroup.name == name)
        result = await self.session.exec(stmt)
        return result.first()

    async def list_all(self, active_only: bool = True) -> List[SubGroup]:
        stmt = select(SubGroup)
        if active_only:
            stmt = stmt.where(SubGroup.is_active == True)
        stmt = stmt.order_by(SubGroup.name)
        result = await self.session.exec(stmt)
        return result.all()

    async def create(self, group: SubGroup) -> SubGroup:
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def update(self, group: SubGroup) -> SubGroup:
        self.session.add(group)
        await self.session.commit()
        await self.session.refresh(group)
        return group

    async def delete(self, group_id: UUID) -> bool:
        group = await self.get(group_id)
        if group:
            await self.session.delete(group)
            await self.session.commit()
            return True
        return False

    async def get_member_count(self, group_id: UUID) -> int:
        stmt = select(func.count()).where(
            SubGroupMember.sub_group_id == group_id,
            SubGroupMember.is_active == True,
        )
        result = await self.session.exec(stmt)
        return result.one()

    async def get_members(self, group_id: UUID) -> List[SubGroupMember]:
        stmt = (
            select(SubGroupMember)
            .where(
                SubGroupMember.sub_group_id == group_id,
                SubGroupMember.is_active == True,
            )
            .order_by(SubGroupMember.joined_at)
        )
        result = await self.session.exec(stmt)
        return result.all()

    async def get_active_membership(self, user_id: UUID) -> Optional[SubGroupMember]:
        """Retourne l'appartenance active d'un utilisateur (un seul sous-groupe)."""
        stmt = select(SubGroupMember).where(
            SubGroupMember.user_id == user_id,
            SubGroupMember.is_active == True,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def add_member(self, membership: SubGroupMember) -> SubGroupMember:
        self.session.add(membership)
        await self.session.commit()
        await self.session.refresh(membership)
        return membership

    async def remove_member(self, membership: SubGroupMember) -> SubGroupMember:
        membership.is_active = False
        membership.left_at = datetime.now(timezone.utc)
        self.session.add(membership)
        await self.session.commit()
        await self.session.refresh(membership)
        return membership

    async def get_membership(self, group_id: UUID, user_id: UUID) -> Optional[SubGroupMember]:
        stmt = select(SubGroupMember).where(
            SubGroupMember.sub_group_id == group_id,
            SubGroupMember.user_id == user_id,
            SubGroupMember.is_active == True,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def enrich_member(self, member: SubGroupMember) -> Dict:
        user = (await self.session.exec(select(User).where(User.id == member.user_id))).first()

        return {
            "id": member.id,
            "user_id": member.user_id,
            "sub_group_id": member.sub_group_id,
            "is_active": member.is_active,
            "joined_at": member.joined_at,
            "left_at": member.left_at,
            "user_first_name": user.first_name if user else None,
            "user_last_name": user.last_name if user else None,
            "user_email": user.email if user else None,
            "user_phone": user.phone_number if user else None,
        }

    async def enrich_members(self, members: List[SubGroupMember]) -> List[Dict]:
        return [await self.enrich_member(m) for m in members]
