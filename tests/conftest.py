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
        "FRONTEND_URL": "http://localhost:3000",
        "SMTP_FROM_NAME": "ServantAssist Test",
        "FIELD_ENCRYPTION_KEY": "test-field-encryption-key-for-testing-only-32ch!",
    }
)

from datetime import datetime, timedelta, timezone
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
from src.core.entities.attendance import Attendance
from src.core.entities.attendance import AttendanceStatus as BaseAttendanceStatus
from src.core.entities.attendance import AttendanceType
from src.core.entities.attendance_session import (
    AttendanceRecord,
    AttendanceSession,
    AttendanceStatus,
)
from src.core.entities.contribution import Contribution, PaymentMode
from src.core.entities.cotisation import (
    CotisationPeriod,
    CotisationStatus,
    CotisationType,
    MemberCotisation,
    PeriodType,
)
from src.core.entities.discipline import (
    DisciplineCase,
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
    SanctionType,
)
from src.core.entities.event import Event, EventParticipant, EventStatus, EventType
from src.core.entities.financial_entry import EntryCategory, EntrySource, FinancialEntry
from src.core.entities.invitation import InvitationCode, InvitationStatus
from src.core.entities.material import (
    AubeTask,
    CleaningTask,
    MaterialCategory,
    MaterialCondition,
    MaterialItem,
    TaskStatus,
    TaskType,
)
from src.core.entities.notification import (
    Notification,
    NotificationChannel,
    NotificationPreference,
    NotificationPriority,
    NotificationStatus,
    NotificationType,
)
from src.core.entities.report import Report, ReportStatus, ReportType
from src.core.entities.responsable import (
    ActionCategory,
    ActionStatus,
    Nomination,
    NominationStatus,
    PosteAction,
    PosteResponsable,
)
from src.core.entities.sport_culture import EventType as SportEventType
from src.core.entities.sport_culture import SportCultureEvent, SportType
from src.core.entities.subgroup import SubGroup, SubGroupMember
from src.core.entities.training import TrainingSession
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import get_db_session
from src.infrastructure.security.utils import SecurityUtils
from src.presentation.api.v1 import (
    activities,
    admin,
    assignments,
    attendance,
    attendance_sessions,
    auth,
    communication,
    contributions,
    cotisations,
    discipline,
    financial_entries,
    material,
    poste,
    reports,
    responsables,
    sport_culture,
    subgroups,
    sunday_schedule,
    training,
    users,
    weekly_schedule,
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
    test_app.include_router(
        attendance_sessions.router,
        prefix="/api/v1/attendance-sessions",
        tags=["Attendance Sessions"],
    )
    test_app.include_router(contributions.router, prefix="/api/v1/contributions", tags=["Contributions"])
    test_app.include_router(
        financial_entries.router,
        prefix="/api/v1/financial-entries",
        tags=["Financial Entries"],
    )
    test_app.include_router(material.router, prefix="/api/v1/material", tags=["Material"])
    test_app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])
    test_app.include_router(sport_culture.router, prefix="/api/v1/sport-culture", tags=["Sport & Culture"])
    test_app.include_router(
        sunday_schedule.router,
        prefix="/api/v1/sunday-schedule",
        tags=["Sunday Schedule"],
    )
    test_app.include_router(training.router, prefix="/api/v1/training", tags=["Training"])
    test_app.include_router(
        weekly_schedule.router,
        prefix="/api/v1/weekly-schedule",
        tags=["Weekly Schedule"],
    )
    test_app.include_router(communication.router, prefix="/api/v1/communication", tags=["Communication"])
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
async def app(db_engine) -> FastAPI:
    """Application de test avec session DB surchargée."""
    test_app = create_test_app()

    async def _override():
        """Crée une nouvelle session pour chaque requête (évite les conflits concurrents)."""
        factory = sessionmaker(bind=db_engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            yield session

    test_app.dependency_overrides[get_db_session] = _override
    return test_app


@pytest_asyncio.fixture()
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Client HTTP async pour les tests e2e."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── Fabriques d'utilisateurs ─────────────────────────────────────────────
# Tous les users passent par UserRepository.create() pour que email_hmac
# soit renseigné — indispensable pour que get_by_email() (HMAC lookup)
# fonctionne lors de la validation JWT dans les e2e tests.
async def _make_user(db_session: AsyncSession, **kwargs) -> User:
    from src.infrastructure.repositories.user_repository import UserRepository

    user = User(**kwargs)
    return await UserRepository(db_session).create(user)


@pytest_asyncio.fixture()
async def admin_user(db_session: AsyncSession) -> User:
    return await _make_user(
        db_session,
        id=uuid4(),
        email="admin@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Admin",
        last_name="Test",
        role=UserRole.ADMIN,
        is_active=True,
    )


@pytest_asyncio.fixture()
async def aumonier_user(db_session: AsyncSession) -> User:
    return await _make_user(
        db_session,
        id=uuid4(),
        email="aumonier@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Aumonier",
        last_name="Test",
        role=UserRole.AUMÔNIER,
        is_active=True,
    )


@pytest_asyncio.fixture()
async def servant_user(db_session: AsyncSession) -> User:
    return await _make_user(
        db_session,
        id=uuid4(),
        email="servant@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Servant",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=True,
        phone_number="+237600000001",
    )


@pytest_asyncio.fixture()
async def parent_user(db_session: AsyncSession) -> User:
    return await _make_user(
        db_session,
        id=uuid4(),
        email="parent@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Parent",
        last_name="Test",
        role=UserRole.PARENT,
        is_active=True,
        phone_number="+237600000002",
    )


@pytest_asyncio.fixture()
async def inactive_user(db_session: AsyncSession) -> User:
    return await _make_user(
        db_session,
        id=uuid4(),
        email="inactive@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Inactive",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=False,
        phone_number="+237600000099",
    )


# ── Helpers tokens ────────────────────────────────────────────────────────
def make_access_token(user: User, expires: timedelta | None = None) -> str:
    """Génère un access token pour un utilisateur de test."""
    return SecurityUtils.create_access_token(
        subject=user.email,
        role=user.role.value,
        expires_delta=expires or timedelta(minutes=30),
    )


@pytest_asyncio.fixture()
async def econome_user(db_session: AsyncSession, aumonier_user: User) -> User:
    """User with ECONOME nomination."""
    user = await _make_user(
        db_session,
        id=uuid4(),
        email="econome@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Econome",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=True,
    )
    db_session.add(
        Nomination(
            user_id=user.id,
            poste=PosteResponsable.ECONOME,
            status=NominationStatus.ACTIVE,
            nominated_by=aumonier_user.id,
        )
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture()
async def admin_token(admin_user: User) -> str:
    return make_access_token(admin_user)


@pytest_asyncio.fixture()
async def aumonier_token(aumonier_user: User) -> str:
    return make_access_token(aumonier_user)


@pytest_asyncio.fixture()
async def servant_token(servant_user: User) -> str:
    return make_access_token(servant_user)


@pytest_asyncio.fixture()
async def econome_token(econome_user: User) -> str:
    return make_access_token(econome_user)


@pytest_asyncio.fixture()
async def servant_user_id(servant_user: User) -> str:
    return str(servant_user.id)


@pytest_asyncio.fixture()
async def secretaire_user(db_session: AsyncSession, aumonier_user: User) -> User:
    """User with SECRETAIRE nomination."""
    user = await _make_user(
        db_session,
        id=uuid4(),
        email="secretaire@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Secretaire",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=True,
    )
    db_session.add(
        Nomination(
            user_id=user.id,
            poste=PosteResponsable.SECRETAIRE_GENERAL,
            status=NominationStatus.ACTIVE,
            nominated_by=aumonier_user.id,
        )
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture()
async def secretaire_token(secretaire_user: User) -> str:
    return make_access_token(secretaire_user)


@pytest_asyncio.fixture()
async def secretaire_adjoint_user(db_session: AsyncSession, aumonier_user: User) -> User:
    """User with SECRETAIRE_ADJOINT nomination."""
    user = await _make_user(
        db_session,
        id=uuid4(),
        email="secretaire_adj@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Secretaire",
        last_name="Adjoint",
        role=UserRole.SERVANT,
        is_active=True,
    )
    db_session.add(
        Nomination(
            user_id=user.id,
            poste=PosteResponsable.SECRETAIRE_GENERAL_ADJOINT,
            status=NominationStatus.ACTIVE,
            nominated_by=aumonier_user.id,
        )
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture()
async def secretaire_adjoint_token(secretaire_adjoint_user: User) -> str:
    return make_access_token(secretaire_adjoint_user)


@pytest_asyncio.fixture()
async def censeur_user(db_session: AsyncSession, aumonier_user: User) -> User:
    """User with CENSEUR nomination."""
    user = await _make_user(
        db_session,
        id=uuid4(),
        email="censeur@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Censeur",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=True,
    )
    db_session.add(
        Nomination(
            user_id=user.id,
            poste=PosteResponsable.CENSEUR,
            status=NominationStatus.ACTIVE,
            nominated_by=aumonier_user.id,
        )
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture()
async def censeur_token(censeur_user: User) -> str:
    return make_access_token(censeur_user)


@pytest_asyncio.fixture()
async def commissaire_user(db_session: AsyncSession, aumonier_user: User) -> User:
    """User with COMMISSAIRE nomination."""
    user = await _make_user(
        db_session,
        id=uuid4(),
        email="commissaire@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Commissaire",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=True,
    )
    db_session.add(
        Nomination(
            user_id=user.id,
            poste=PosteResponsable.COMMISSAIRE_AUX_COMPTES,
            status=NominationStatus.ACTIVE,
            nominated_by=aumonier_user.id,
        )
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture()
async def commissaire_token(commissaire_user: User) -> str:
    return make_access_token(commissaire_user)


@pytest_asyncio.fixture()
async def charge_liturgie_user(db_session: AsyncSession, aumonier_user: User) -> User:
    """User with CHARGE_LITURGIE nomination."""
    user = await _make_user(
        db_session,
        id=uuid4(),
        email="charge_liturgie@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Charge",
        last_name="Liturgie",
        role=UserRole.SERVANT,
        is_active=True,
    )
    db_session.add(
        Nomination(
            user_id=user.id,
            poste=PosteResponsable.CHARGE_LITURGIE,
            status=NominationStatus.ACTIVE,
            nominated_by=aumonier_user.id,
        )
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture()
async def charge_liturgie_token(charge_liturgie_user: User) -> str:
    return make_access_token(charge_liturgie_user)


@pytest_asyncio.fixture()
async def intendant_user(db_session: AsyncSession, aumonier_user: User) -> User:
    """User with INTENDANT nomination."""
    user = await _make_user(
        db_session,
        id=uuid4(),
        email="intendant@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Intendant",
        last_name="Test",
        role=UserRole.SERVANT,
        is_active=True,
    )
    db_session.add(
        Nomination(
            user_id=user.id,
            poste=PosteResponsable.INTENDANT,
            status=NominationStatus.ACTIVE,
            nominated_by=aumonier_user.id,
        )
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture()
async def intendant_token(intendant_user: User) -> str:
    return make_access_token(intendant_user)


@pytest_asyncio.fixture()
async def charge_sport_culture_user(db_session: AsyncSession, aumonier_user: User) -> User:
    """User with CHARGE_SPORT_CULTURE nomination."""
    user = await _make_user(
        db_session,
        id=uuid4(),
        email="charge_sport_culture@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Charge",
        last_name="Sport",
        role=UserRole.SERVANT,
        is_active=True,
    )
    db_session.add(
        Nomination(
            user_id=user.id,
            poste=PosteResponsable.CHARGE_SPORT_CULTURE,
            status=NominationStatus.ACTIVE,
            nominated_by=aumonier_user.id,
        )
    )
    await db_session.commit()
    return user


@pytest_asyncio.fixture()
async def charge_sport_culture_token(charge_sport_culture_user: User) -> str:
    return make_access_token(charge_sport_culture_user)


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
async def email_locked_invitation(db_session: AsyncSession, admin_user: User) -> InvitationCode:
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
    return await _make_user(
        db_session,
        id=uuid4(),
        email="servant2@test.com",
        hashed_password=SecurityUtils.get_password_hash(VALID_PASSWORD),
        first_name="Pierre",
        last_name="Dupont",
        role=UserRole.SERVANT,
        is_active=True,
        phone_number="+237600000003",
    )


# ── Fixtures événements ──────────────────────────────────────────────────
@pytest_asyncio.fixture()
async def sample_event(db_session: AsyncSession, aumonier_user: User) -> Event:
    """Evenement de test cree par l'aumonier."""
    event = Event(
        id=uuid4(),
        title="Messe dominicale de test",
        description="Messe du dimanche pour les tests",
        start_time=datetime(2027, 6, 1, 9, 0),
        end_time=datetime(2027, 6, 1, 11, 0),
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


@pytest_asyncio.fixture()
async def sample_contribution(
    db_session: AsyncSession,
    servant_user: User,
    econome_user: User,
) -> Contribution:
    """Contribution de test."""
    contribution = Contribution(
        id=uuid4(),
        servant_id=servant_user.id,
        amount=500.0,
        payment_mode=PaymentMode.MONTHLY,
        payment_date=datetime.now(timezone.utc),
        month=2,
        year=2026,
        recorded_by=econome_user.id,
    )
    db_session.add(contribution)
    await db_session.commit()
    await db_session.refresh(contribution)
    return contribution


@pytest_asyncio.fixture()
async def contribution_id(sample_contribution: Contribution) -> str:
    return str(sample_contribution.id)


@pytest_asyncio.fixture()
async def sample_report(
    db_session: AsyncSession,
    secretaire_user: User,
) -> Report:
    """Rapport de test."""
    report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport de test",
        content="Contenu du rapport de test",
        report_date=datetime.now(timezone.utc),
        location="Salle de test",
        status=ReportStatus.DRAFT,
        created_by=secretaire_user.id,
    )
    db_session.add(report)
    await db_session.commit()
    await db_session.refresh(report)
    return report


@pytest_asyncio.fixture()
async def report_id(sample_report: Report) -> str:
    return str(sample_report.id)


@pytest_asyncio.fixture()
async def sample_sport_event(
    db_session: AsyncSession,
    aumonier_user: User,
) -> SportCultureEvent:
    """Evenement sportif de test."""
    event = SportCultureEvent(
        id=uuid4(),
        title="Match de foot",
        description="Match amical",
        date=datetime.now(timezone.utc) + timedelta(days=1),
        start_time="16h00",
        end_time="18h00",
        location="Terrain de foot",
        sport_type=SportType.FOOTBALL,
        event_type=SportEventType.MATCH,
        max_participants=22,
        created_by=aumonier_user.id,
    )
    db_session.add(event)
    await db_session.commit()
    await db_session.refresh(event)
    return event


@pytest_asyncio.fixture()
async def sport_event_id(sample_sport_event: SportCultureEvent) -> str:
    return str(sample_sport_event.id)


@pytest_asyncio.fixture()
async def sample_event_participation(
    db_session: AsyncSession,
    sample_sport_event: SportCultureEvent,
    servant_user: User,
    aumonier_user: User,
):
    """Participation à un événement sportif de test."""
    from src.core.entities.sport_culture import EventParticipation, ParticipationStatus

    participation = EventParticipation(
        id=uuid4(),
        event_id=sample_sport_event.id,
        servant_id=servant_user.id,
        servant_name=f"{servant_user.first_name} {servant_user.last_name}",
        status=ParticipationStatus.INSCRIT,
        registered_by=aumonier_user.id,
    )
    db_session.add(participation)
    await db_session.commit()
    await db_session.refresh(participation)
    return participation


@pytest_asyncio.fixture()
async def sample_training_session(
    db_session: AsyncSession,
    aumonier_user: User,
) -> TrainingSession:
    """Session de formation de test."""
    from src.core.entities.training import TrainingLevel, TrainingStatus

    session = TrainingSession(
        id=uuid4(),
        title="Formation Liturgie",
        description="Apprentissage des rites",
        objectives=None,
        level=TrainingLevel.TOUS,
        date=datetime.now(timezone.utc) + timedelta(days=2),
        start_time="14:00",
        end_time="16:00",
        duration_minutes=120,
        location="Eglise",
        trainer_id=aumonier_user.id,
        trainer_name=None,
        max_participants=20,
        current_participants=0,
        status=TrainingStatus.PLANIFIEE,
        materials_url=None,
        notes=None,
        created_by=aumonier_user.id,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest_asyncio.fixture()
async def sample_financial_entry(
    db_session: AsyncSession,
    econome_user: User,
) -> FinancialEntry:
    """Entree financiere de test."""
    entry = FinancialEntry(
        id=uuid4(),
        amount=1000.0,
        category=EntryCategory.COTISATION,
        source=EntrySource.SERVANT,
        date=datetime.now(timezone.utc),
        description="Test revenue",
        recorded_by=econome_user.id,
    )
    db_session.add(entry)
    await db_session.commit()
    await db_session.refresh(entry)
    return entry


@pytest_asyncio.fixture()
async def sample_discrepancy(
    db_session: AsyncSession,
    sample_financial_entry: FinancialEntry,
    commissaire_user: User,
):
    """Ecart financier de test."""
    from src.core.entities.financial_entry import Discrepancy

    discrepancy = Discrepancy(
        id=uuid4(),
        entry_id=sample_financial_entry.id,
        type="Montant incorrect",
        description="Écart détecté lors de la vérification",
        expected_amount=1000.0,
        actual_amount=950.0,
        detected_by=commissaire_user.id,
        resolved=False,
    )
    db_session.add(discrepancy)
    await db_session.commit()
    await db_session.refresh(discrepancy)
    return discrepancy


@pytest_asyncio.fixture()
async def sample_material_item(
    db_session: AsyncSession,
    aumonier_user: User,
) -> MaterialItem:
    """Article de materiel de test."""
    item = MaterialItem(
        id=uuid4(),
        name="Encensoir",
        category=MaterialCategory.ENCENSOIR,
        quantity=1,
        location="Sacristie",
        condition=MaterialCondition.BON,
        created_by=aumonier_user.id,
    )
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item


@pytest_asyncio.fixture()
async def sample_cleaning_task(
    db_session: AsyncSession,
    aumonier_user: User,
) -> CleaningTask:
    """Tache de nettoyage de test."""
    task = CleaningTask(
        id=uuid4(),
        title="Nettoyage des encensoirs",
        description="Faire briller le cuivre",
        task_type=TaskType.NETTOYAGE,
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=1),
        scheduled_time="15:00",
        location="Parvis",
        status=TaskStatus.PLANIFIEE,
        created_by=aumonier_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture()
async def sample_task_assignment(
    db_session: AsyncSession,
    sample_cleaning_task: CleaningTask,
    servant_user: User,
    intendant_user: User,
):
    """Assignation de tache de test."""
    from src.core.entities.material import TaskAssignment

    assignment = TaskAssignment(
        id=uuid4(),
        task_id=sample_cleaning_task.id,
        servant_id=servant_user.id,
        servant_name=f"{servant_user.first_name} {servant_user.last_name}",
        assigned_by=intendant_user.id,
    )
    db_session.add(assignment)
    await db_session.commit()
    await db_session.refresh(assignment)
    return assignment


@pytest_asyncio.fixture()
async def sample_maintenance_history(
    db_session: AsyncSession,
    sample_material_item: MaterialItem,
    intendant_user: User,
):
    """Historique de maintenance de test."""
    from src.core.entities.material import MaintenanceHistory

    history = MaintenanceHistory(
        id=uuid4(),
        item_id=sample_material_item.id,
        maintenance_type=TaskType.NETTOYAGE,
        description="Nettoyage standard",
        cost=50.0,
        performed_date=datetime.now(timezone.utc),
        performed_by=intendant_user.id,
        notes="Maintenance de routine",
    )
    db_session.add(history)
    await db_session.commit()
    await db_session.refresh(history)
    return history


@pytest_asyncio.fixture()
async def sample_aube_task(
    db_session: AsyncSession,
    aumonier_user: User,
) -> AubeTask:
    """Tache d'aube de test."""
    task = AubeTask(
        id=uuid4(),
        title="Lavage des aubes",
        task_type=TaskType.LAVAGE,
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=1),
        scheduled_time="10:00",
        location="Blanchisserie",
        aube_count=10,
        status=TaskStatus.PLANIFIEE,
        created_by=aumonier_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture()
async def sample_attendance_session(
    db_session: AsyncSession,
    censeur_user: User,
) -> AttendanceSession:
    """Session d'appel de test."""
    session = AttendanceSession(
        id=uuid4(),
        session_date=datetime.now(timezone.utc),
        session_time="07h30",
        location="Sacristie",
        conducted_by=censeur_user.id,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    return session


@pytest.fixture()
def attendance_session_id(sample_attendance_session: AttendanceSession) -> str:
    """ID de la session de test."""
    return str(sample_attendance_session.id)


@pytest.fixture()
def servant_user_id(servant_user: User) -> str:
    """ID du servant de test."""
    return str(servant_user.id)


@pytest_asyncio.fixture()
async def sample_attendance_record(
    db_session: AsyncSession,
    sample_attendance_session: AttendanceSession,
    servant_user: User,
    aumonier_user: User,
) -> AttendanceRecord:
    """Enregistrement de présence de test."""
    record = AttendanceRecord(
        id=uuid4(),
        session_id=sample_attendance_session.id,
        servant_id=servant_user.id,
        status=AttendanceStatus.PRESENT,
        arrival_time="07h25",
        recorded_by=aumonier_user.id,
    )
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest.fixture()
def attendance_record_id(sample_attendance_record: AttendanceRecord) -> str:
    """ID de l'enregistrement de test."""
    return str(sample_attendance_record.id)


@pytest_asyncio.fixture()
async def sample_training_material(
    db_session: AsyncSession,
    charge_liturgie_user: User,
):
    """Materiel de formation de test."""
    from src.core.entities.training import MaterialType, TrainingLevel, TrainingMaterial

    material = TrainingMaterial(
        id=uuid4(),
        title="Guide de la liturgie",
        description="Guide complet des services de messe",
        type=MaterialType.DOCUMENT,
        file_url="https://example.com/guide.pdf",
        file_type="application/pdf",
        file_size=1024000,
        thumbnail_url=None,
        level=TrainingLevel.TOUS,
        tags=[],
        is_public=True,
        view_count=0,
        uploaded_by=charge_liturgie_user.id,
        uploaded_by_name=None,
    )
    db_session.add(material)
    await db_session.commit()
    await db_session.refresh(material)
    return material


@pytest_asyncio.fixture()
async def sample_training_participation(
    db_session: AsyncSession,
    sample_training_session,
    servant_user: User,
    aumonier_user: User,
):
    """Participation a une formation de test."""
    from src.core.entities.training import ParticipationStatus, TrainingParticipation

    participation = TrainingParticipation(
        id=uuid4(),
        session_id=sample_training_session.id,
        servant_id=servant_user.id,
        status=ParticipationStatus.INSCRIT,
        registered_by=aumonier_user.id,
    )
    db_session.add(participation)
    await db_session.commit()
    await db_session.refresh(participation)
    return participation


@pytest_asyncio.fixture()
async def sample_event_team(
    db_session: AsyncSession,
    sample_sport_event: SportCultureEvent,
    servant_user: User,
    charge_sport_culture_user: User,
):
    """Équipe pour un événement sportif de test."""
    from src.core.entities.sport_culture import EventTeam

    team = EventTeam(
        id=uuid4(),
        event_id=sample_sport_event.id,
        team_name="Équipe A",
        captain_id=servant_user.id,
        captain_name=f"{servant_user.first_name} {servant_user.last_name}",
        members=[str(servant_user.id)],
        members_names=[f"{servant_user.first_name} {servant_user.last_name}"],
        created_by=charge_sport_culture_user.id,
    )
    db_session.add(team)
    await db_session.commit()
    await db_session.refresh(team)
    return team


@pytest_asyncio.fixture()
async def sample_event_result(
    db_session: AsyncSession,
    sample_sport_event: SportCultureEvent,
    charge_sport_culture_user: User,
):
    """Résultat d'un événement sportif de test."""
    from src.core.entities.sport_culture import EventResult, ResultType

    result = EventResult(
        id=uuid4(),
        event_id=sample_sport_event.id,
        result_type=ResultType.VICTOIRE,
        team_name="Équipe A",
        score=2,
        opponent_name="Équipe B",
        opponent_score=1,
        ranking=None,
        description="Match de football",
        notes="Bonne performance",
        recorded_by=charge_sport_culture_user.id,
    )
    db_session.add(result)
    await db_session.commit()
    await db_session.refresh(result)
    return result


@pytest_asyncio.fixture()
async def sample_attachment(
    db_session: AsyncSession,
    sample_report: Report,
    secretaire_user: User,
):
    """Pièce jointe d'un rapport de test."""
    from src.core.entities.report import ReportAttachment

    attachment = ReportAttachment(
        id=uuid4(),
        report_id=sample_report.id,
        filename="rapport_test.pdf",
        file_url="https://example.com/files/rapport_test.pdf",
        file_type="application/pdf",
        file_size=1024000,
        uploaded_by=secretaire_user.id,
    )
    db_session.add(attachment)
    await db_session.commit()
    await db_session.refresh(attachment)
    return attachment


# ── Fixtures notifications ──────────────────────────────────────────────
@pytest_asyncio.fixture()
async def sample_notification(
    db_session: AsyncSession,
    servant_user: User,
    aumonier_user: User,
) -> Notification:
    """Notification IN_APP de test envoyee par l'aumonier au servant."""
    notif = Notification(
        id=uuid4(),
        recipient_id=servant_user.id,
        notification_type=NotificationType.GENERAL,
        channel=NotificationChannel.IN_APP,
        priority=NotificationPriority.NORMAL,
        title="Reunion ce dimanche",
        body="Rappel : reunion de preparation a 8h.",
        status=NotificationStatus.SENT,
        sent_by=aumonier_user.id,
    )
    db_session.add(notif)
    await db_session.commit()
    await db_session.refresh(notif)
    return notif


@pytest_asyncio.fixture()
async def sample_notification_preference(
    db_session: AsyncSession,
    servant_user: User,
) -> NotificationPreference:
    """Preference de notification de test pour le servant."""
    pref = NotificationPreference(
        id=uuid4(),
        user_id=servant_user.id,
        notification_type=NotificationType.GENERAL,
        email_enabled=False,
        whatsapp_enabled=False,
        in_app_enabled=True,
    )
    db_session.add(pref)
    await db_session.commit()
    await db_session.refresh(pref)
    return pref
