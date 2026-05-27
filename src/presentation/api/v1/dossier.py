"""
Endpoint pour le dossier unique d'un servant (agrégation multi-modules).
"""
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from src.core.entities.attendance_session import AttendanceRecord, AttendanceStatus
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.attendance_session_repository import (
    AttendanceSessionRepository,
)
from src.infrastructure.repositories.responsable_repository import NominationRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.field_encryption import decrypt_str_fields
from src.presentation.dependencies.auth_deps import get_current_active_user
from src.presentation.schemas.dossier import (
    DossierAttendanceStat,
    DossierCotisation,
    DossierDiscipline,
    DossierNomination,
    DossierResponse,
    DossierSportCulture,
    DossierTraining,
    DossierUserInfo,
)

router = APIRouter()

_USER_PII = ("first_name", "last_name", "email", "phone_number")


@router.get(
    "/{user_id}",
    response_model=DossierResponse,
    summary="Dossier complet d'un servant",
)
async def get_dossier(
    user_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
):
    # RBAC : un servant ne peut consulter que son propre dossier
    if current_user.role == UserRole.SERVANT and current_user.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Vous n'êtes pas autorisé à consulter le dossier d'un autre servant.",
        )

    user_repo = UserRepository(session)
    user = await user_repo.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Servant introuvable.")

    decrypt_str_fields(user, _USER_PII)

    # ── Attendance stats ───────────────────────────────────────────
    records_result = await session.execute(
        select(AttendanceRecord).where(AttendanceRecord.servant_id == user_id)
    )
    records = list(records_result.scalars().all())

    total = len(records)
    present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
    absent = sum(1 for r in records if r.status == AttendanceStatus.ABSENT)
    late = sum(1 for r in records if r.status == AttendanceStatus.LATE)
    excused = sum(1 for r in records if r.status == AttendanceStatus.EXCUSED)
    rate = round((present + late) / total * 100, 1) if total > 0 else 0.0

    attendance_stats = DossierAttendanceStat(
        total_sessions=total,
        present_count=present,
        absent_count=absent,
        late_count=late,
        excused_count=excused,
        attendance_rate=rate,
    )

    # ── Nominations ────────────────────────────────────────────────
    nom_repo = NominationRepository(session)
    raw_nominations = await nom_repo.get_active_by_user(user_id)
    nominations = [
        DossierNomination(
            id=n.id,
            poste=n.poste.value,
            start_date=getattr(n, "start_date", None),
            end_date=getattr(n, "end_date", None),
            is_active=True,
        )
        for n in raw_nominations
    ]

    # ── Cotisations ────────────────────────────────────────────────
    cotisations: list[DossierCotisation] = []
    try:
        from src.core.entities.cotisation import MemberCotisation, CotisationPeriod

        cot_result = await session.execute(
            select(MemberCotisation, CotisationPeriod)
            .join(CotisationPeriod, MemberCotisation.period_id == CotisationPeriod.id)
            .where(MemberCotisation.member_id == user_id)
            .order_by(CotisationPeriod.start_date.desc())
            .limit(10)
        )
        for cot, period in cot_result.all():
            cotisations.append(
                DossierCotisation(
                    id=cot.id,
                    period_label=f"{period.name}"
                    if hasattr(period, "name")
                    else str(period.id),
                    amount_due=float(getattr(period, "amount", 0)),
                    amount_paid=float(getattr(cot, "amount_paid", 0)),
                    status=getattr(cot, "status", "UNKNOWN"),
                    paid_at=getattr(cot, "paid_at", None),
                )
            )
    except Exception:
        pass

    # ── Trainings ──────────────────────────────────────────────────
    trainings: list[DossierTraining] = []
    try:
        from src.core.entities.training import Training, TrainingParticipant

        train_result = await session.execute(
            select(Training)
            .join(TrainingParticipant, TrainingParticipant.training_id == Training.id)
            .where(TrainingParticipant.servant_id == user_id)
            .order_by(Training.training_date.desc())
            .limit(10)
        )
        for t in train_result.scalars().all():
            trainings.append(
                DossierTraining(
                    id=t.id,
                    title=t.title,
                    training_date=getattr(t, "training_date", None),
                    status=getattr(t, "status", "UNKNOWN"),
                )
            )
    except Exception:
        pass

    # ── Discipline ─────────────────────────────────────────────────
    discipline_cases: list[DossierDiscipline] = []
    try:
        from src.core.entities.discipline import DisciplineCase

        disc_result = await session.execute(
            select(DisciplineCase)
            .where(DisciplineCase.servant_id == user_id)
            .order_by(DisciplineCase.incident_date.desc())
            .limit(10)
        )
        for d in disc_result.scalars().all():
            discipline_cases.append(
                DossierDiscipline(
                    id=d.id,
                    incident_type=getattr(d, "incident_type", ""),
                    incident_date=getattr(d, "incident_date", None),
                    sanction=getattr(d, "sanction", None),
                    status=getattr(d, "status", "UNKNOWN"),
                )
            )
    except Exception:
        pass

    # ── Sport & Culture ────────────────────────────────────────────
    sport_culture: list[DossierSportCulture] = []
    try:
        from src.core.entities.sport_culture import (
            SportCultureEvent,
            SportCultureParticipation,
        )

        sc_result = await session.execute(
            select(SportCultureEvent, SportCultureParticipation)
            .join(
                SportCultureParticipation,
                SportCultureParticipation.event_id == SportCultureEvent.id,
            )
            .where(SportCultureParticipation.servant_id == user_id)
            .order_by(SportCultureEvent.event_date.desc())
            .limit(10)
        )
        for evt, part in sc_result.all():
            sport_culture.append(
                DossierSportCulture(
                    id=part.id,
                    event_title=evt.title,
                    event_date=getattr(evt, "event_date", None),
                    role=getattr(part, "role", None),
                    result=getattr(part, "result", None),
                )
            )
    except Exception:
        pass

    user_info = DossierUserInfo(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        role=user.role.value,
        phone_number=user.phone_number,
        profile_photo_url=user.profile_photo_url,
        is_active=user.is_active,
        birth_date=user.birth_date,
        baptism_date=user.baptism_date,
        created_at=user.created_at,
    )

    return DossierResponse(
        user=user_info,
        attendance_stats=attendance_stats,
        nominations=nominations,
        cotisations=cotisations,
        trainings=trainings,
        discipline_cases=discipline_cases,
        sport_culture=sport_culture,
        generated_at=datetime.now(timezone.utc),
    )
