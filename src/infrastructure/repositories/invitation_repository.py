"""
Repository pour les codes d'invitation.

Chiffrement PII (Loi 2024/017 Cameroun) :
  email et phone_number sont chiffrés en AES-256-GCM avant stockage.
  Les lookups utilisent les colonnes HMAC (email_hmac, phone_hmac).
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.invitation import InvitationCode, InvitationStatus
from src.core.utils import utc_now
from src.infrastructure.security.encrypted_model_mixin import EncryptedModelMixin
from src.infrastructure.security.field_encryption import get_encryptor


class InvitationCodeRepository(EncryptedModelMixin):
    ENCRYPTED_FIELDS = ("email", "phone_number")
    HMAC_INDEX_MAP = {"email": "email_hmac", "phone_number": "phone_hmac"}

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, invitation_code: InvitationCode) -> InvitationCode:
        self._encrypt_model(invitation_code)
        self.session.add(invitation_code)
        await self.session.commit()
        await self.session.refresh(invitation_code)
        self._decrypt_model(invitation_code)
        self.session.expunge(invitation_code)
        return invitation_code

    async def get_by_code(self, code: str) -> Optional[InvitationCode]:
        stmt = select(InvitationCode).where(
            InvitationCode.code == code,
            InvitationCode.status == InvitationStatus.PENDING,
        )
        result = await self.session.exec(stmt)
        inv = result.first()
        if inv:
            self._decrypt_model(inv)
        return inv

    async def get_by_id(self, invitation_id: UUID) -> Optional[InvitationCode]:
        stmt = select(InvitationCode).where(InvitationCode.id == invitation_id)
        result = await self.session.exec(stmt)
        inv = result.first()
        if inv:
            self._decrypt_model(inv)
        return inv

    async def get_all_by_admin(self, admin_id: UUID) -> list[InvitationCode]:
        stmt = (
            select(InvitationCode)
            .where(InvitationCode.created_by == admin_id)
            .order_by(InvitationCode.created_at.desc())
        )
        result = await self.session.exec(stmt)
        invs = list(result.all())
        self._decrypt_list(invs)
        return invs

    async def update(
        self, invitation_id: UUID, invitation_code: InvitationCode
    ) -> InvitationCode:
        self._encrypt_model(invitation_code)
        await self.session.merge(invitation_code)
        await self.session.commit()
        return await self.get_by_id(invitation_id)

    async def mark_as_used(self, code: str, user_id: UUID) -> Optional[InvitationCode]:
        invitation = await self.get_by_code(code)
        if not invitation:
            return None
        invitation.status = InvitationStatus.ACCEPTED
        invitation.used_by = user_id
        invitation.used_at = utc_now()
        return await self.update(invitation.id, invitation)

    async def revoke(self, invitation_id: UUID) -> Optional[InvitationCode]:
        invitation = await self.get_by_id(invitation_id)
        if not invitation:
            return None
        invitation.status = InvitationStatus.REVOKED
        return await self.update(invitation_id, invitation)

    async def is_valid(self, code: str) -> bool:
        invitation = await self.get_by_code(code)
        return invitation is not None and invitation.status == InvitationStatus.PENDING

    async def get_by_email(self, email: str) -> Optional[InvitationCode]:
        """Lookup par HMAC — ne transmet jamais l'email en clair au serveur SQL."""
        hmac = get_encryptor().hmac_index(email)
        stmt = select(InvitationCode).where(InvitationCode.email_hmac == hmac)
        result = await self.session.exec(stmt)
        inv = result.first()
        if inv:
            self._decrypt_model(inv)
        return inv
