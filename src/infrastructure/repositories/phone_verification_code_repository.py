from typing import Optional
from uuid import UUID

from sqlalchemy import delete
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.entities.phone_verification_code import PhoneVerificationCode
from src.core.utils import utc_now


class PhoneVerificationCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, entry: PhoneVerificationCode) -> PhoneVerificationCode:
        self.session.add(entry)
        await self.session.commit()
        await self.session.refresh(entry)
        return entry

    async def get_valid_by_phone_hmac(self, phone_hmac: str, code: str) -> Optional[PhoneVerificationCode]:
        """Retourne le code s'il est valide (non utilisé et non expiré)."""
        now = utc_now()
        result = await self.session.exec(
            select(PhoneVerificationCode)
            .where(PhoneVerificationCode.phone_hmac == phone_hmac)
            .where(PhoneVerificationCode.code == code)
            .where(PhoneVerificationCode.used == False)  # noqa: E712
            .where(PhoneVerificationCode.expires_at > now)
        )
        return result.first()

    async def mark_verified(self, entry_id: UUID, token: str) -> None:
        result = await self.session.exec(select(PhoneVerificationCode).where(PhoneVerificationCode.id == entry_id))
        entry = result.first()
        if entry:
            entry.used = True
            entry.verified_at = utc_now()
            entry.verification_token = token
            self.session.add(entry)
            await self.session.commit()

    async def get_by_token(self, phone_hmac: str, token: str) -> Optional[PhoneVerificationCode]:
        """Relecture au moment de POST /auth/register : le token doit correspondre
        à un code vérifié pour ce numéro, non expiré."""
        now = utc_now()
        result = await self.session.exec(
            select(PhoneVerificationCode)
            .where(PhoneVerificationCode.phone_hmac == phone_hmac)
            .where(PhoneVerificationCode.verification_token == token)
            .where(PhoneVerificationCode.verified_at.is_not(None))  # noqa: E711
            .where(PhoneVerificationCode.expires_at > now)
        )
        return result.first()

    async def delete_for_phone_hmac(self, phone_hmac: str) -> None:
        """Supprime tous les codes existants pour ce numéro avant d'en créer un nouveau."""
        await self.session.exec(delete(PhoneVerificationCode).where(PhoneVerificationCode.phone_hmac == phone_hmac))
        await self.session.commit()

    async def delete_expired(self) -> None:
        await self.session.exec(delete(PhoneVerificationCode).where(PhoneVerificationCode.expires_at < utc_now()))
        await self.session.commit()
