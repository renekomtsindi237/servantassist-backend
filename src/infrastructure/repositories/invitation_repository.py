"""
Repository for managing invitation codes
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.invitation import InvitationCode, InvitationStatus
from src.core.utils import utc_now


class InvitationCodeRepository:
    """Repository for CRUD operations on invitation codes"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, invitation_code: InvitationCode) -> InvitationCode:
        """Create a new invitation code"""
        self.session.add(invitation_code)
        await self.session.commit()
        await self.session.refresh(invitation_code)
        return invitation_code

    async def get_by_code(self, code: str) -> Optional[InvitationCode]:
        """Get invitation by code"""
        stmt = select(InvitationCode).where(
            InvitationCode.code == code,
            InvitationCode.status == InvitationStatus.PENDING,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def get_by_id(self, invitation_id: UUID) -> Optional[InvitationCode]:
        """Get invitation by ID"""
        stmt = select(InvitationCode).where(InvitationCode.id == invitation_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def get_all_by_admin(self, admin_id: UUID) -> list[InvitationCode]:
        """Get all invitations created by an admin"""
        stmt = (
            select(InvitationCode)
            .where(InvitationCode.created_by == admin_id)
            .order_by(InvitationCode.created_at.desc())
        )
        result = await self.session.exec(stmt)
        return result.all()

    async def update(
        self, invitation_id: UUID, invitation_code: InvitationCode
    ) -> InvitationCode:
        """Update an invitation code"""
        await self.session.merge(invitation_code)
        await self.session.commit()
        return await self.get_by_id(invitation_id)

    async def mark_as_used(self, code: str, user_id: UUID) -> Optional[InvitationCode]:
        """Mark invitation as accepted/used"""
        invitation = await self.get_by_code(code)
        if not invitation:
            return None

        invitation.status = InvitationStatus.ACCEPTED
        invitation.used_by = user_id
        invitation.used_at = utc_now()
        return await self.update(invitation.id, invitation)

    async def revoke(self, invitation_id: UUID) -> Optional[InvitationCode]:
        """Revoke an invitation"""
        invitation = await self.get_by_id(invitation_id)
        if not invitation:
            return None

        invitation.status = InvitationStatus.REVOKED
        return await self.update(invitation_id, invitation)

    async def is_valid(self, code: str) -> bool:
        """Check if invitation code is valid (exists and pending)"""
        invitation = await self.get_by_code(code)
        return invitation is not None and invitation.status == InvitationStatus.PENDING
