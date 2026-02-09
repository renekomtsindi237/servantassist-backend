"""
Fixtures et configuration partagées pour tous les tests.

IMPORTANT : les variables d'environnement sont définies AVANT tout import applicatif
pour que les Settings Pydantic soient initialisées correctement.
"""
import os

# ── Variables d'environnement de test (AVANT tout import src.*) ──────────
os.environ.update(
    {
        "APP_ENV": "testing",
        "APP_DEBUG": "False",
        "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
        "JWT_SECRET_KEY": "test-jwt-secret-key-minimum-32-chars-long-for-hs256!",
        "JWT_ALGORITHM": "HS256",
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
        "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "7",
        "SECRET_KEY": "test-app-secret-key-minimum-32-chars-long!",
        "CLOUDFLARE_R2_ENDPOINT": "https://test.r2.cloudflarestorage.com",
        "CLOUDFLARE_R2_ACCESS_KEY": "test-access-key",
        "CLOUDFLARE_R2_SECRET_KEY": "test-secret-key",
        "CLOUDFLARE_R2_BUCKET": "test-bucket",
        "CLOUDFLARE_R2_PUBLIC_URL": "https://test.r2.dev",
        "CLOUDFLARE_R2_PROFILE_BUCKET": "profile",
        "FRONTEND_URL": "http://localhost:3000",
        "SMTP_FROM_NAME": "ServantAssist Test",
    }
)

from datetime import datetime, timedelta
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from src.core.entities.assignment import Assignment, AssignmentStatus, LiturgicalRole
from src.core.entities.event import Event, EventParticipant, EventType, EventStatus
from src.core.entities.invitation import InvitationCode, InvitationStatus
from src.core.entities.responsable import (
    Nomination, NominationStatus, PosteAction, PosteResponsable,
    ActionCategory, ActionStatus,
)
from src.core.entities.discipline import (
    DisciplineCase, DisciplineCaseStatus, SanctionType,
    SanctionSeverity, OffenseCategory,
)
from src.core.entities.cotisation import (
    CotisationPeriod, MemberCotisation, CotisationType,
    CotisationStatus, PeriodType,
)
from src.core.entities.attendance import Attendance, AttendanceType, AttendanceStatus
from src.core.entities.subgroup import SubGroup, SubGroupMember
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.security.utils import SecurityUtils
from src.presentation.api.v1 import (
    admin, auth, users, activities, assignments,
    responsables, poste, discipline, cotisations,
    attendance, subgroups,
)

# ── Constantes de test ───────────────────────────────────────────────────
VALID_PASSWORD = "TestPass1"  # 8+ chars, majuscule, minuscule, chiffre
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ── App de test ──────────────────────────────────────────────────────────
def create_test_app() -> FastAPI:
    """Cree une application FastAPI minimale pour les tests."""
    test_app = FastAPI(title="ServantAssist Test")
    test_app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    test_app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    test_app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
    test_app.include_router(activities.router, prefix="/api/v1/events", tags=["Events"])
    test_app.include_router(assignments.router, prefix="/api/v1/assignments", tags=["Assignments"])
    test_app.include_router(responsables.router, prefix="/api/v1/responsables", tags=["Responsables"])
    test_app.include_router(poste.router, prefix="/api/v1/poste", tags=["Poste Actions"])
    test_app.include_router(discipline.router, prefix="/api/v1/discipline", tags=["Discipline"])
    test_app.include_router(cotisations.router, prefix="/api/v1/cotisations", tags=["Cotisations"])
    test_app.include_router(attendance.router, prefix="/api/v1/attendance", tags=["Attendance"])
    test_app.include_router(subgroups.router, prefix="/api/v1/subgroups", tags=["Sub-Groups"])
    return test_app


# ── Fixtures base de données ─────────────────────────────────────────────
@pytest_asyncio.fixture()
async def db_engine():
    """Moteur SQLite async en mémoire — recréé pour chaque test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Session async liée au moteur de test (SQLModel AsyncSession avec .exec())."""
    factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest_asyncio.fixture()
async def app(db_session: AsyncSession) -> FastAPI:
    """Application de test avec session DB surchargée."""
    test_app = create_test_app()

    async def _override():
        yield db_session

    test_app.dependency_overrides[get_db_session] = _override
    return test_app


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP async pour les tests e2e."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Fabriques d'utilisateurs ─────────────────────────────────────────────
@pytest_asyncio.fixture()
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email="admin@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Admin",
        last_name="Test",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def aumonier_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email="aumonier@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Aumonier",
        last_name="Test",
        role=UserRole.AUMÔNIER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def servant_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email="servant@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Servant",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=True,
        phone_number="+237600000001",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def parent_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email="parent@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Parent",
        last_name="Test",
        role=UserRole.PARENT,
        is_active=True,
        phone_number="+237600000002",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture()
async def inactive_user(db_session: AsyncSession) -> User:
    user = User(
        id=uuid4(),
        email="inactive@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Inactive",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=False,
        phone_number="+237600000099",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ── Helpers tokens ────────────────────────────────────────────────────────
def make_access_token(user: User, expires: timedelta | None = None) -> str:
    """Génère un access token pour un utilisateur de test."""
    return SecurityUtils.create_access_token(
        subject=user.email,
        role=user.role.value,
        expires_delta=expires or timedelta(minutes=30),
    )


def make_auth_header(user: User) -> dict:
    """Retourne un header Authorization: Bearer <token>."""
    return {"Authorization": f"Bearer {make_access_token(user)}"}


# ── Fixtures invitations ─────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def valid_invitation(db_session: AsyncSession, admin_user: User) -> InvitationCode:
    invitation = InvitationCode(
        id=uuid4(),
        code="INV-TESTCODE123",
        role="PARENT",
        status=InvitationStatus.PENDING,
        created_by=admin_user.id,
    )
    db_session.add(invitation)
    await db_session.commit()
    await db_session.refresh(invitation)
    return invitation


@pytest_asyncio.fixture()
async def email_locked_invitation(
    db_session: AsyncSession, admin_user: User
) -> InvitationCode:
    invitation = InvitationCode(
        id=uuid4(),
        code="INV-EMAILLOCKED",
        role="PARENT",
        email="specific@test.com",
        status=InvitationStatus.PENDING,
        created_by=admin_user.id,
    )
    db_session.add(invitation)
    await db_session.commit()
    await db_session.refresh(invitation)
    return invitation


@pytest_asyncio.fixture()
async def used_invitation(db_session: AsyncSession, admin_user: User) -> InvitationCode:
    invitation = InvitationCode(
        id=uuid4(),
        code="INV-USEDCODE456",
        role="PARENT",
        status=InvitationStatus.ACCEPTED,
        created_by=admin_user.id,
        used_by=uuid4(),
    )
    db_session.add(invitation)
    await db_session.commit()
    await db_session.refresh(invitation)
    return invitation


# ── Second servant (pour les tests batch) ─────────────────────────────────
@pytest_asyncio.fixture()
async def servant_user_2(db_session: AsyncSession) -> User:
    """Deuxieme servant pour les tests de creation par lot."""
    user = User(
        id=uuid4(),
        email="servant2@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Pierre",
        last_name="Dupont",
        role=UserRole.SERVANT,
        is_active=True,
        phone_number="+237600000003",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


# ── Fixtures événements ──────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def sample_event(db_session: AsyncSession, aumonier_user: User) -> Event:
    """Evenement de test cree par l'aumonier."""
    event = Event(
        id=uuid4(),
        title="Messe dominicale de test",
        description="Messe du dimanche pour les tests",
        start_time=datetime(2026, 3, 1, 9, 0),
        end_time=datetime(2026, 3, 1, 11, 0),
        location="Paroisse Saint-Pierre",
        event_type=EventType.MESSE_DOMINICALE,
        status=EventStatus.PUBLIE,
        created_by=aumonier_user.id,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


# ── Fixtures affectations ─────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def sample_assignment(
    db_session: AsyncSession,
    sample_event: Event,
    servant_user: User,
    aumonier_user: User,
) -> Assignment:
    """Affectation de test : servant comme crucifer a la messe dominicale."""
    assignment = Assignment(
        id=uuid4(),
        event_id=sample_event.id,
        user_id=servant_user.id,
        liturgical_role=LiturgicalRole.CRUCIFER,
        status=AssignmentStatus.PENDING,
        assigned_by=aumonier_user.id,
    )
    db_session.add(assignment)
    await db_session.commit()
    await db_session.refresh(assignment)
    return assignment


# ── Fixtures responsables ─────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def nomination_delegue(
    db_session: AsyncSession,
    servant_user: User,
    aumonier_user: User,
) -> Nomination:
    """Nomination du servant comme delegue."""
    nomination = Nomination(
        id=uuid4(),
        user_id=servant_user.id,
        poste=PosteResponsable.DELEGUE,
        status=NominationStatus.ACTIVE,
        nominated_by=aumonier_user.id,
    )
    db_session.add(nomination)
    await db_session.commit()
    await db_session.refresh(nomination)
    return nomination


@pytest_asyncio.fixture()
async def nomination_censeur(
    db_session: AsyncSession,
    servant_user_2: User,
    aumonier_user: User,
) -> Nomination:
    """Nomination du servant_2 comme censeur."""
    nomination = Nomination(
        id=uuid4(),
        user_id=servant_user_2.id,
        poste=PosteResponsable.CENSEUR,
        status=NominationStatus.ACTIVE,
        nominated_by=aumonier_user.id,
    )
    db_session.add(nomination)
    await db_session.commit()
    await db_session.refresh(nomination)
    return nomination


@pytest_asyncio.fixture()
async def sample_poste_action(
    db_session: AsyncSession,
    servant_user: User,
    nomination_delegue: Nomination,
) -> PosteAction:
    """Action de poste de test : decision du delegue."""
    action = PosteAction(
        id=uuid4(),
        poste=PosteResponsable.DELEGUE,
        category=ActionCategory.DECISION,
        title="Decision du conseil n1",
        content="Le conseil a decide de programmer une recollection.",
        status=ActionStatus.PUBLIE,
        created_by=servant_user.id,
    )
    db_session.add(action)
    await db_session.commit()
    await db_session.refresh(action)
    return action


# ── Fixtures discipline ──────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def sample_discipline_case(
    db_session: AsyncSession,
    servant_user: User,
    aumonier_user: User,
) -> DisciplineCase:
    """Dossier disciplinaire de test."""
    case = DisciplineCase(
        id=uuid4(),
        accused_user_id=servant_user.id,
        reported_by=aumonier_user.id,
        offense_category=OffenseCategory.ABSENCE_NON_JUSTIFIEE,
        offense_description="Absent a la messe sans justification",
        status=DisciplineCaseStatus.SIGNALE,
    )
    db_session.add(case)
    await db_session.commit()
    await db_session.refresh(case)
    return case


# ── Fixtures cotisations ─────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def sample_cotisation_period(
    db_session: AsyncSession,
    aumonier_user: User,
) -> CotisationPeriod:
    """Periode de cotisation de test."""
    period = CotisationPeriod(
        id=uuid4(),
        title="Cotisation Janvier 2026",
        period_type=PeriodType.MENSUEL,
        cotisation_type=CotisationType.ORDINAIRE,
        amount_expected=1000.0,
        start_date=datetime(2026, 1, 1),
        end_date=datetime(2026, 1, 31),
        created_by=aumonier_user.id,
    )
    db_session.add(period)
    await db_session.commit()
    await db_session.refresh(period)
    return period


@pytest_asyncio.fixture()
async def sample_member_cotisation(
    db_session: AsyncSession,
    sample_cotisation_period: CotisationPeriod,
    servant_user: User,
) -> MemberCotisation:
    """Cotisation individuelle de test."""
    mc = MemberCotisation(
        id=uuid4(),
        period_id=sample_cotisation_period.id,
        user_id=servant_user.id,
        amount_paid=0.0,
        status=CotisationStatus.EN_ATTENTE,
    )
    db_session.add(mc)
    await db_session.commit()
    await db_session.refresh(mc)
    return mc


# ── Fixtures attendance ──────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def sample_attendance(
    db_session: AsyncSession,
    sample_event: Event,
    servant_user: User,
    aumonier_user: User,
) -> Attendance:
    """Enregistrement de presence de test."""
    att = Attendance(
        id=uuid4(),
        event_id=sample_event.id,
        user_id=servant_user.id,
        attendance_type=AttendanceType.MESSE_CLASSEMENT,
        attendance_date=datetime(2026, 3, 1, 9, 0),
        status=AttendanceStatus.PRESENT,
        recorded_by=aumonier_user.id,
    )
    db_session.add(att)
    await db_session.commit()
    await db_session.refresh(att)
    return att


# ── Fixtures subgroups ───────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def sample_subgroup(
    db_session: AsyncSession,
    aumonier_user: User,
) -> SubGroup:
    """Sous-groupe de test."""
    sg = SubGroup(
        id=uuid4(),
        name="Groupe A",
        description="Premier sous-groupe de test",
        created_by=aumonier_user.id,
    )
    db_session.add(sg)
    await db_session.commit()
    await db_session.refresh(sg)
    return sg


@pytest_asyncio.fixture()
async def sample_subgroup_member(
    db_session: AsyncSession,
    sample_subgroup: SubGroup,
    servant_user: User,
    aumonier_user: User,
) -> SubGroupMember:
    """Membre de sous-groupe de test."""
    member = SubGroupMember(
        id=uuid4(),
        sub_group_id=sample_subgroup.id,
        user_id=servant_user.id,
        added_by=aumonier_user.id,
    )
    db_session.add(member)
    await db_session.commit()
    await db_session.refresh(member)
    return member
