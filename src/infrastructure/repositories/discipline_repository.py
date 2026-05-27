"""
Repository pour les dossiers disciplinaires.

Chiffrement PII (Loi 2024/017 Cameroun) :
  Les champs de description (offense, verdict, convocation) sont chiffrés
  car ils constituent des données sensibles pouvant révéler le comportement
  personnel et les antécédents disciplinaires d'un mineur.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from src.core.entities.discipline import (
    DisciplineCase,
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
    SanctionType,
)
from src.core.entities.user import User
from src.infrastructure.security.encrypted_model_mixin import EncryptedModelMixin
from src.infrastructure.security.field_encryption import decrypt_str_fields

_USER_PII = ("first_name", "last_name")


class DisciplineCaseRepository(EncryptedModelMixin):
    ENCRYPTED_FIELDS = ("offense_description", "verdict_notes", "convocation_notes")

    def __init__(self, session: AsyncSession):
        self.session = session

    # ── Lecture ────────────────────────────────────────────────────────

    async def get(self, case_id: UUID) -> Optional[DisciplineCase]:
        stmt = select(DisciplineCase).where(DisciplineCase.id == case_id)
        result = await self.session.exec(stmt)
        case = result.first()
        if case:
            self._decrypt_model(case)
        return case

    async def list_paginated(
        self,
        *,
        accused_user_id: Optional[UUID] = None,
        status: Optional[DisciplineCaseStatus] = None,
        severity: Optional[SanctionSeverity] = None,
        offense_category: Optional[OffenseCategory] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[DisciplineCase], int]:
        stmt = select(DisciplineCase)

        if accused_user_id:
            stmt = stmt.where(
    DisciplineCase.accused_user_id == accused_user_id)
        if status:
            stmt = stmt.where(DisciplineCase.status == status)
        if severity:
            stmt = stmt.where(DisciplineCase.severity == severity)
        if offense_category:
            stmt = stmt.where(
    DisciplineCase.offense_category == offense_category)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.exec(count_stmt)).one()

        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size).order_by(
            DisciplineCase.created_at.desc())
        result = await self.session.exec(stmt)
        cases = list(result.all())
        self._decrypt_list(cases)
        return cases, total

    async def list_by_user(self, user_id: UUID) -> List[DisciplineCase]:
        stmt = (
            select(DisciplineCase)
            .where(DisciplineCase.accused_user_id == user_id)
            .order_by(DisciplineCase.created_at.desc())
        )
        result = await self.session.exec(stmt)
        cases = list(result.all())
        self._decrypt_list(cases)
        return cases

    async def count_sanctions_by_user(self, user_id: UUID) -> Dict[str, int]:
        """Compte les sanctions par type pour un utilisateur."""
        counts = {}
        for st in SanctionType:
            if st == SanctionType.AUCUNE:
                continue
            stmt = select(func.count()).where(
                DisciplineCase.accused_user_id == user_id,
                DisciplineCase.sanction_type == st,
                DisciplineCase.status.in_(
                    [
                        DisciplineCaseStatus.VERDICT_RENDU,
                        DisciplineCaseStatus.EXECUTE,
                    ]
                ),
            )
            result = await self.session.exec(stmt)
            counts[st.value] = result.one()
        return counts

    async def count_active_cases(self, user_id: UUID) -> int:
        """Nombre de dossiers en cours pour un utilisateur."""
        active_statuses = [
            DisciplineCaseStatus.SIGNALE,
            DisciplineCaseStatus.CONVOQUE,
            DisciplineCaseStatus.EN_AUDIENCE,
        ]
        stmt = select(func.count()).where(
            DisciplineCase.accused_user_id == user_id,
            DisciplineCase.status.in_(active_statuses),
        )
        result = await self.session.exec(stmt)
        return result.one()

    # ── Enrichissement ─────────────────────────────────────────────────

    async def enrich_case(self, case: DisciplineCase) -> Dict:
        """Enrichit un dossier avec les noms (décrypte les PII des User chargés)."""
        accused_stmt = select(User).where(User.id == case.accused_user_id)
        accused = (await self.session.exec(accused_stmt)).first()
        if accused:
            decrypt_str_fields(accused, _USER_PII)

        reporter_stmt = select(User).where(User.id == case.reported_by)
        reporter = (await self.session.exec(reporter_stmt)).first()
        if reporter:
            decrypt_str_fields(reporter, _USER_PII)

        verdict_by_name = None
        if case.verdict_by:
            vb_stmt = select(User).where(User.id == case.verdict_by)
            vb = (await self.session.exec(vb_stmt)).first()
            if vb:
                decrypt_str_fields(vb, _USER_PII)
                verdict_by_name = f"{vb.first_name} {vb.last_name}"

        return {
            "id": case.id,
            "accused_user_id": case.accused_user_id,
            "reported_by": case.reported_by,
            "offense_category": case.offense_category,
            "offense_description": case.offense_description,
            "offense_date": case.offense_date,
            "severity": case.severity,
            "status": case.status,
            "convocation_date": case.convocation_date,
            "convocation_notes": case.convocation_notes,
            "sanction_type": case.sanction_type,
            "verdict_notes": case.verdict_notes,
            "verdict_date": case.verdict_date,
            "verdict_by": case.verdict_by,
            "suspension_start": case.suspension_start,
            "suspension_end": case.suspension_end,
            "suspension_days": case.suspension_days,
            "accused_first_name": accused.first_name if accused else None,
            "accused_last_name": accused.last_name if accused else None,
            "reporter_first_name": reporter.first_name if reporter else None,
            "reporter_last_name": reporter.last_name if reporter else None,
            "verdict_by_name": verdict_by_name,
            "created_at": case.created_at,
            "updated_at": case.updated_at,
        }

    async def enrich_cases(self, cases: List[DisciplineCase]) -> List[Dict]:
        return [await self.enrich_case(c) for c in cases]

    # ── Ecriture ──────────────────────────────────────────────────────

    async def create(self, case: DisciplineCase) -> DisciplineCase:
        self._encrypt_model(case)
        self.session.add(case)
        await self.session.commit()
        await self.session.refresh(case)
        self._decrypt_model(case)
        self.session.expunge(case)
        return case

    async def update(self, case: DisciplineCase) -> DisciplineCase:
        self._encrypt_model(case)
        self.session.add(case)
        await self.session.commit()
        await self.session.refresh(case)
        self._decrypt_model(case)
        self.session.expunge(case)
        return case

    async def delete(self, case_id: UUID) -> bool:
        case = await self.get(case_id)
        if case:
            await self.session.delete(case)
            await self.session.commit()
            return True
        return False
