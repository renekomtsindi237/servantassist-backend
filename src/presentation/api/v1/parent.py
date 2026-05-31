"""
Endpoints pour le tableau de bord parent.
Permet à un PARENT de consulter le profil et l'activité de son enfant servant.
"""

import logging
import uuid as _uuid
from datetime import datetime
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlmodel import select

from src.core.entities.user import User
from src.infrastructure.database.session import get_db_session
from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository
from src.infrastructure.repositories.cotisation_repository import MemberCotisationRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.presentation.dependencies.auth_deps import get_current_active_user

router = APIRouter()
logger = logging.getLogger(__name__)


# ── Schemas de réponse ────────────────────────────────────────────────────────


class RecentAttendance(BaseModel):
    session_date: str
    status: str
    session_type: str


class PendingContribution(BaseModel):
    period_id: str
    amount_paid: float
    status: str


class ChildSummaryResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    phone_number: Optional[str] = None
    profile_photo_url: Optional[str] = None
    birth_date: Optional[str] = None
    position: Optional[str] = None

    attendance_rate: float
    present_count: int
    absent_count: int
    total_sessions: int
    last_attendances: List[RecentAttendance]

    pending_contributions: List[PendingContribution]
    open_discipline_cases: int


# ── Dépendance : accès PARENT uniquement ─────────────────────────────────────


async def get_current_parent_user(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    if current_user.role.value != "PARENT":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux parents.",
        )
    return current_user


# ── Endpoint ──────────────────────────────────────────────────────────────────


@router.get(
    "/my-child",
    response_model=ChildSummaryResponse,
    summary="Profil et activité de l'enfant servant",
    description="Retourne le dossier synthétique de l'enfant lié au compte parent connecté.",
)
async def get_my_child(
    current_parent: Annotated[User, Depends(get_current_parent_user)],
    session=Depends(get_db_session),
) -> ChildSummaryResponse:
    user_repo = UserRepository(session)
    children = await user_repo.get_children_of(current_parent.id)

    if not children:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun enfant servant n'est lié à votre compte. Contactez l'administrateur.",
        )

    child = children[0]

    # ── Statistiques de présence ──────────────────────────────────────────
    attendance_repo = AttendanceSessionRepository(session)
    present_count = absent_count = total_sessions = 0
    attendance_rate = 0.0
    try:
        stats = await attendance_repo.calculate_servant_stats(child.id)
        present_count = stats.present_count
        absent_count = stats.absent_count
        total_sessions = stats.total_sessions
        attendance_rate = stats.attendance_rate if total_sessions > 0 else 0.0
    except Exception:
        pass

    # ── 5 dernières présences ─────────────────────────────────────────────
    last_attendances: List[RecentAttendance] = []
    try:
        records = await attendance_repo.get_servant_records(child.id)
        for r in sorted(records, key=lambda r: r.created_at or datetime.min, reverse=True)[:5]:
            last_attendances.append(
                RecentAttendance(
                    session_date=r.created_at.strftime("%d/%m/%Y") if r.created_at else "—",
                    status=r.status.value if hasattr(r.status, "value") else str(r.status),
                    session_type="Appel",
                )
            )
    except Exception:
        pass

    # ── Contributions en attente ou en retard ─────────────────────────────
    pending_contributions: List[PendingContribution] = []
    try:
        cotisation_repo = MemberCotisationRepository(session)
        cotisations = await cotisation_repo.list_by_user(child.id)
        for c in cotisations:
            status_val = c.status.value if hasattr(c.status, "value") else str(c.status)
            if status_val in ("EN_ATTENTE", "EN_RETARD", "PAYE_PARTIELLEMENT"):
                pending_contributions.append(
                    PendingContribution(
                        period_id=str(c.period_id),
                        amount_paid=c.amount_paid,
                        status=status_val,
                    )
                )
    except Exception:
        pass

    # ── Cas disciplinaires ouverts ────────────────────────────────────────
    open_discipline_cases = 0
    try:
        from src.core.entities.discipline import DisciplineCase, DisciplineCaseStatus

        result = await session.exec(
            select(DisciplineCase).where(
                DisciplineCase.accused_user_id == child.id,
                DisciplineCase.status != DisciplineCaseStatus.CLASSE,
            )
        )
        open_discipline_cases = len(list(result.all()))
    except Exception:
        pass

    birth_date_str: Optional[str] = None
    if child.birth_date:
        if isinstance(child.birth_date, str):
            birth_date_str = child.birth_date
        else:
            birth_date_str = child.birth_date.isoformat()

    return ChildSummaryResponse(
        id=child.id,
        first_name=child.first_name or "",
        last_name=child.last_name or "",
        phone_number=child.phone_number,
        profile_photo_url=child.profile_photo_url,
        birth_date=birth_date_str,
        position=child.position.value if child.position else None,
        attendance_rate=round(attendance_rate, 1),
        present_count=present_count,
        absent_count=absent_count,
        total_sessions=total_sessions,
        last_attendances=last_attendances,
        pending_contributions=pending_contributions,
        open_discipline_cases=open_discipline_cases,
    )


# ── Création du profil enfant ─────────────────────────────────────────────────


class ChildCreate(BaseModel):
    """Données pour créer le profil servant d'un enfant < 13 ans."""

    first_name: str
    last_name: str
    birth_date: datetime
    phone_number: Optional[str] = None
    password: str = Field(..., min_length=8)


@router.post(
    "/children",
    status_code=status.HTTP_201_CREATED,
    summary="Créer le profil servant de son enfant",
    description=(
        "Permet à un PARENT de créer le compte servant de son enfant (typiquement < 13 ans). "
        "L'email est auto-généré. Le lien parent est fixé automatiquement."
    ),
)
async def create_child_profile(
    data: ChildCreate,
    session: Annotated[object, Depends(get_db_session)],
    current_parent: Annotated[User, Depends(get_current_parent_user)],
):
    from src.application.services.auth_service import AuthService
    from src.core.entities.user import UserRole
    from src.presentation.schemas.auth import UserCreate

    phone_key = (data.phone_number or "").lstrip("+").replace(" ", "")
    suffix = str(_uuid.uuid4())[:8]
    generated_email = f"{phone_key or suffix}@bmra.servant.local"

    user_create = UserCreate(
        email=generated_email,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
        role=UserRole.SERVANT,
        phone_number=data.phone_number,
        birth_date=data.birth_date,
        parent_id=current_parent.id,
    )

    auth_service = AuthService(UserRepository(session))
    child = await auth_service.register_user(
        user_create,
        invitation_code=None,
        admin_id=None,
        skip_age_check=True,
    )
    return {
        "id": str(child.id),
        "first_name": child.first_name,
        "last_name": child.last_name,
        "email": child.email,
        "phone_number": child.phone_number,
        "parent_id": str(child.parent_id),
        "is_active": child.is_active,
    }
