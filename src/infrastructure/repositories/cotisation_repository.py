"""
Repository pour les cotisations et paiements.
"""
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.cotisation import CotisationPeriod, CotisationStatus, CotisationType, MemberCotisation
from src.core.entities.user import User


class CotisationPeriodRepository:
    """Operations sur les periodes de cotisation."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, period_id: UUID) -> Optional[CotisationPeriod]:
        stmt = select(CotisationPeriod).where(CotisationPeriod.id == period_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def list_active(self) -> List[CotisationPeriod]:
        stmt = (
            select(CotisationPeriod)
            .where(CotisationPeriod.is_active == True)
            .order_by(CotisationPeriod.start_date.desc())
        )
        result = await self.session.exec(stmt)
        return result.all()

    async def list_all(
        self,
        *,
        cotisation_type: Optional[CotisationType] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[CotisationPeriod], int]:
        stmt = select(CotisationPeriod)
        if cotisation_type:
            stmt = stmt.where(CotisationPeriod.cotisation_type == cotisation_type)
        if is_active is not None:
            stmt = stmt.where(CotisationPeriod.is_active == is_active)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.exec(count_stmt)).one()

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size).order_by(CotisationPeriod.start_date.desc())
        result = await self.session.exec(stmt)
        return result.all(), total

    async def create(self, period: CotisationPeriod) -> CotisationPeriod:
        self.session.add(period)
        await self.session.commit()
        await self.session.refresh(period)
        return period

    async def update(self, period: CotisationPeriod) -> CotisationPeriod:
        self.session.add(period)
        await self.session.commit()
        await self.session.refresh(period)
        return period

    async def delete(self, period_id: UUID) -> bool:
        period = await self.get(period_id)
        if period:
            await self.session.delete(period)
            await self.session.commit()
            return True
        return False


class MemberCotisationRepository:
    """Operations sur les paiements individuels."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, cotisation_id: UUID) -> Optional[MemberCotisation]:
        stmt = select(MemberCotisation).where(MemberCotisation.id == cotisation_id)
        result = await self.session.exec(stmt)
        return result.first()

    async def get_by_period_and_user(self, period_id: UUID, user_id: UUID) -> Optional[MemberCotisation]:
        stmt = select(MemberCotisation).where(
            MemberCotisation.period_id == period_id,
            MemberCotisation.user_id == user_id,
        )
        result = await self.session.exec(stmt)
        return result.first()

    async def list_by_period(self, period_id: UUID) -> List[MemberCotisation]:
        stmt = (
            select(MemberCotisation)
            .where(MemberCotisation.period_id == period_id)
            .order_by(MemberCotisation.created_at.desc())
        )
        result = await self.session.exec(stmt)
        return result.all()

    async def list_by_user(self, user_id: UUID) -> List[MemberCotisation]:
        stmt = (
            select(MemberCotisation)
            .where(MemberCotisation.user_id == user_id)
            .order_by(MemberCotisation.created_at.desc())
        )
        result = await self.session.exec(stmt)
        return result.all()

    async def get_period_stats(self, period_id: UUID) -> Dict:
        """Stats d'une periode : total paye, nb payeurs, etc."""
        paid_count = (
            await self.session.exec(
                select(func.count()).where(
                    MemberCotisation.period_id == period_id,
                    MemberCotisation.status == CotisationStatus.PAYE,
                )
            )
        ).one()

        total_collected = (
            await self.session.exec(
                select(func.coalesce(func.sum(MemberCotisation.amount_paid), 0)).where(
                    MemberCotisation.period_id == period_id,
                )
            )
        ).one()

        total_members = (
            await self.session.exec(
                select(func.count()).where(
                    MemberCotisation.period_id == period_id,
                )
            )
        ).one()

        return {
            "total_members": total_members,
            "total_paid": paid_count,
            "total_amount_collected": float(total_collected),
        }

    async def enrich_cotisation(self, cotisation: MemberCotisation) -> Dict:
        """Enrichit un paiement avec infos utilisateur et periode."""
        user = (await self.session.exec(select(User).where(User.id == cotisation.user_id))).first()

        period = (
            await self.session.exec(select(CotisationPeriod).where(CotisationPeriod.id == cotisation.period_id))
        ).first()

        return {
            "id": cotisation.id,
            "period_id": cotisation.period_id,
            "user_id": cotisation.user_id,
            "amount_paid": cotisation.amount_paid,
            "status": cotisation.status,
            "payment_date": cotisation.payment_date,
            "payment_method": cotisation.payment_method,
            "notes": cotisation.notes,
            "recorded_by": cotisation.recorded_by,
            "created_at": cotisation.created_at,
            "updated_at": cotisation.updated_at,
            "user_first_name": user.first_name if user else None,
            "user_last_name": user.last_name if user else None,
            "period_title": period.title if period else None,
            "amount_expected": period.amount_expected if period else None,
        }

    async def enrich_cotisations(self, cotisations: List[MemberCotisation]) -> List[Dict]:
        return [await self.enrich_cotisation(c) for c in cotisations]

    async def create(self, cotisation: MemberCotisation) -> MemberCotisation:
        self.session.add(cotisation)
        await self.session.commit()
        await self.session.refresh(cotisation)
        return cotisation

    async def update(self, cotisation: MemberCotisation) -> MemberCotisation:
        self.session.add(cotisation)
        await self.session.commit()
        await self.session.refresh(cotisation)
        return cotisation

    async def delete(self, cotisation_id: UUID) -> bool:
        cotisation = await self.get(cotisation_id)
        if cotisation:
            await self.session.delete(cotisation)
            await self.session.commit()
            return True
        return False
