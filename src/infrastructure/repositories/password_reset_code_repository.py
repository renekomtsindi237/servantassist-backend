from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import delete
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.entities.password_reset_code import PasswordResetCode
from src.core.utils import utc_now


class PasswordResetCodeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, code: PasswordResetCode) -> PasswordResetCode:
        self.session.add(code)
        await self.session.commit()
        await self.session.refresh(code)
        return code

    async def get_valid(self, email: str, code: str) -> Optional[PasswordResetCode]:
        """Retourne le code s'il est valide (non utilisé et non expiré)."""
        now = utc_now()
        result = await self.session.exec(
            select(PasswordResetCode)
            .where(PasswordResetCode.email == email)
            .where(PasswordResetCode.code == code)
            .where(PasswordResetCode.used == False)  # noqa: E712
            .where(PasswordResetCode.expires_at > now)
        )
        return result.first()

    async def mark_used(self, code_id: UUID) -> None:
        result = await self.session.exec(
            select(PasswordResetCode).where(PasswordResetCode.id == code_id)
        )
        entry = result.first()
        if entry:
            entry.used = True
            self.session.add(entry)
            await self.session.commit()

    async def delete_expired(self) -> None:
        """Purge les codes expirés (appelé à chaque requête pour éviter l'accumulation)."""
        await self.session.exec(
            delete(PasswordResetCode).where(PasswordResetCode.expires_at < utc_now())
        )
        await self.session.commit()

    async def delete_for_email(self, email: str) -> None:
        """Supprime tous les codes existants pour cet email avant d'en créer un nouveau."""
        await self.session.exec(
            delete(PasswordResetCode).where(PasswordResetCode.email == email)
        )
        await self.session.commit()
