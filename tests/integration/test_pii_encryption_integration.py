"""
Tests d'intégration — Chiffrement PII sur tous les repositories concernés.

Vérifie que :
  - Les données sont chiffrées AVANT d'arriver en base (requête SQL directe)
  - Les données sont déchiffrées APRÈS lecture (API du repository)
  - Les méthodes enrich_* retournent bien le texte clair via decrypt_str_fields
"""
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import text

from src.core.entities.attendance import Attendance, AttendanceStatus, AttendanceType
from src.core.entities.discipline import (
    DisciplineCase,
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
    SanctionType,
)
from src.core.entities.invitation import InvitationCode, InvitationStatus
from src.core.entities.sunday_schedule import (
    LiturgicalPosition,
    MassLanguage,
    SundayMassAssignment,
    SundayMassSlot,
    SundayScheduleStatus,
    SundayScheduleTemplate,
)
from src.core.entities.user import User, UserRole
from src.infrastructure.repositories.attendance_repository import AttendanceRepository
from src.infrastructure.repositories.discipline_repository import (
    DisciplineCaseRepository,
)
from src.infrastructure.repositories.invitation_repository import (
    InvitationCodeRepository as InvitationRepository,
)
from src.infrastructure.repositories.sunday_schedule_repository import (
    SundayScheduleRepository,
)
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.utils import SecurityUtils


@pytest.fixture(autouse=True)
def reset_encryptor_singleton():
    import src.infrastructure.security.field_encryption as fe

    original = fe._encryptor_instance
    fe._encryptor_instance = None
    yield
    fe._encryptor_instance = original


def _now():
    return datetime.now(timezone.utc)


# ── Helpers ──────────────────────────────────────────────────────────────


async def _create_admin(session) -> User:
    repo = UserRepository(session)
    return await repo.create(
        User(
            id=uuid4(),
            email=f"admin-{uuid4().hex[:6]}@test.cm",
            hashed_password=SecurityUtils.get_password_hash("TestPass1"),
            first_name="Admin",
            last_name="Test",
            role=UserRole.ADMIN,
            is_active=True,
            phone_number=f"+23760{uuid4().int % 9_000_000 + 1_000_000}",
        )
    )


async def _create_servant(session) -> User:
    repo = UserRepository(session)
    return await repo.create(
        User(
            id=uuid4(),
            email=f"servant-{uuid4().hex[:6]}@test.cm",
            hashed_password=SecurityUtils.get_password_hash("TestPass1"),
            first_name="Servant",
            last_name="Chœur",
            role=UserRole.SERVANT,
            is_active=True,
            phone_number=f"+23769{uuid4().int % 9_000_000 + 1_000_000}",
        )
    )


# ═══════════════════════════════════════════════════════════════════════════
#  AttendanceRepository — champ justification
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.integration
class TestAttendanceEncryption:
    async def test_justification_stored_encrypted(self, db_session):
        servant = await _create_servant(db_session)
        repo = AttendanceRepository(db_session)

        att = await repo.create(
            Attendance(
                id=uuid4(),
                user_id=servant.id,
                attendance_type=AttendanceType.FORMATION,
                attendance_date=_now(),
                title="Répétition du dimanche",
                status=AttendanceStatus.ABSENT,
                justification="Raison médicale confidentielle",
                recorded_by=servant.id,
            )
        )

        row = (
            await db_session.execute(
                text("SELECT justification FROM attendances WHERE id = :uid"),
                {"uid": att.id.hex},
            )
        ).one()

        assert row.justification != "Raison médicale confidentielle"
        assert len(row.justification) > 20

    async def test_justification_decrypted_on_get(self, db_session):
        servant = await _create_servant(db_session)
        repo = AttendanceRepository(db_session)

        created = await repo.create(
            Attendance(
                id=uuid4(),
                user_id=servant.id,
                attendance_type=AttendanceType.FORMATION,
                attendance_date=_now(),
                title="Test",
                status=AttendanceStatus.ABSENT,
                justification="Maladie grave",
                recorded_by=servant.id,
            )
        )

        fetched = await repo.get(created.id)
        assert fetched.justification == "Maladie grave"

    async def test_null_justification_stays_null(self, db_session):
        servant = await _create_servant(db_session)
        repo = AttendanceRepository(db_session)

        created = await repo.create(
            Attendance(
                id=uuid4(),
                user_id=servant.id,
                attendance_type=AttendanceType.MESSE_CLASSEMENT,
                attendance_date=_now(),
                title="Messe dominicale",
                status=AttendanceStatus.PRESENT,
                justification=None,
                recorded_by=servant.id,
            )
        )

        fetched = await repo.get(created.id)
        assert fetched.justification is None


# ═══════════════════════════════════════════════════════════════════════════
#  DisciplineCaseRepository — champs offense/verdict/convocation
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.integration
class TestDisciplineEncryption:
    async def test_offense_description_stored_encrypted(self, db_session):
        admin = await _create_admin(db_session)
        servant = await _create_servant(db_session)
        repo = DisciplineCaseRepository(db_session)

        case = await repo.create(
            DisciplineCase(
                id=uuid4(),
                accused_user_id=servant.id,
                reported_by=admin.id,
                offense_category=OffenseCategory.INSUBORDINATION,
                offense_description="Description confidentielle du cas",
                offense_date=_now(),
                severity=SanctionSeverity.MINEUR,
                status=DisciplineCaseStatus.SIGNALE,
                sanction_type=SanctionType.AUCUNE,
            )
        )

        row = (
            await db_session.execute(
                text(
                    "SELECT offense_description FROM discipline_cases WHERE id = :uid"
                ),
                {"uid": case.id.hex},
            )
        ).one()

        assert row.offense_description != "Description confidentielle du cas"

    async def test_all_sensitive_fields_roundtrip(self, db_session):
        admin = await _create_admin(db_session)
        servant = await _create_servant(db_session)
        repo = DisciplineCaseRepository(db_session)

        case = await repo.create(
            DisciplineCase(
                id=uuid4(),
                accused_user_id=servant.id,
                reported_by=admin.id,
                offense_category=OffenseCategory.ABSENCE_NON_JUSTIFIEE,
                offense_description="Absent sans justification",
                convocation_notes="Convoqué pour audience",
                offense_date=_now(),
                severity=SanctionSeverity.MINEUR,
                status=DisciplineCaseStatus.SIGNALE,
                sanction_type=SanctionType.AUCUNE,
            )
        )

        fetched = await repo.get(case.id)
        assert fetched.offense_description == "Absent sans justification"
        assert fetched.convocation_notes == "Convoqué pour audience"

    async def test_enrich_case_decrypts_user_names(self, db_session):
        admin = await _create_admin(db_session)
        servant = await _create_servant(db_session)
        repo = DisciplineCaseRepository(db_session)

        case = await repo.create(
            DisciplineCase(
                id=uuid4(),
                accused_user_id=servant.id,
                reported_by=admin.id,
                offense_category=OffenseCategory.INSUBORDINATION,
                offense_description="Test enrich",
                offense_date=_now(),
                severity=SanctionSeverity.MINEUR,
                status=DisciplineCaseStatus.SIGNALE,
                sanction_type=SanctionType.AUCUNE,
            )
        )

        enriched = await repo.enrich_case(case)
        assert enriched["accused_first_name"] == "Servant"
        assert enriched["accused_last_name"] == "Chœur"
        assert enriched["reporter_first_name"] == "Admin"


# ═══════════════════════════════════════════════════════════════════════════
#  InvitationRepository — email et phone chiffrés avec index HMAC
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.integration
class TestInvitationEncryption:
    async def test_invitation_email_stored_encrypted(self, db_session):
        admin = await _create_admin(db_session)
        repo = InvitationRepository(db_session)

        inv = await repo.create(
            InvitationCode(
                id=uuid4(),
                code=f"INV-{uuid4().hex[:8].upper()}",
                role=UserRole.SERVANT,
                email="invite@paroisse.cm",
                created_by=admin.id,
                status=InvitationStatus.PENDING,
            )
        )

        row = (
            await db_session.execute(
                text("SELECT email, email_hmac FROM invitation_codes WHERE id = :uid"),
                {"uid": inv.id.hex},
            )
        ).one()

        assert row.email != "invite@paroisse.cm"
        assert row.email_hmac is not None

    async def test_get_by_email_finds_via_hmac(self, db_session):
        admin = await _create_admin(db_session)
        repo = InvitationRepository(db_session)

        await repo.create(
            InvitationCode(
                id=uuid4(),
                code=f"INV-{uuid4().hex[:8].upper()}",
                role=UserRole.SERVANT,
                email="findme@paroisse.cm",
                created_by=admin.id,
                status=InvitationStatus.PENDING,
            )
        )

        found = await repo.get_by_email("findme@paroisse.cm")
        assert found is not None
        assert found.email == "findme@paroisse.cm"


# ═══════════════════════════════════════════════════════════════════════════
#  SundayScheduleRepository — servant_name dans SundayMassAssignment
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.integration
class TestSundayScheduleEncryption:
    async def _make_template(self, session, admin_id) -> SundayScheduleTemplate:
        repo = SundayScheduleRepository(session)
        return await repo.create_template(
            SundayScheduleTemplate(
                id=uuid4(),
                title="Messe du dimanche test",
                schedule_date=_now(),
                status=SundayScheduleStatus.DRAFT,
                created_by=admin_id,
            )
        )

    async def _make_mass(self, session, template_id) -> SundayMassSlot:
        repo = SundayScheduleRepository(session)
        return await repo.create_mass(
            SundayMassSlot(
                id=uuid4(),
                template_id=template_id,
                mass_time="09:00",
                mass_type="Messe paroissiale",
                language=MassLanguage.FRANCAIS,
            )
        )

    async def test_servant_name_stored_encrypted(self, db_session):
        admin = await _create_admin(db_session)
        template = await self._make_template(db_session, admin.id)
        mass = await self._make_mass(db_session, template.id)

        repo = SundayScheduleRepository(db_session)
        assignment = await repo.create_assignment(
            SundayMassAssignment(
                id=uuid4(),
                mass_slot_id=mass.id,
                position=LiturgicalPosition.ACOLYTE_1,
                servant_name="Pierre Kamdem",
                assigned_by=admin.id,
            )
        )

        row = (
            await db_session.execute(
                text(
                    "SELECT servant_name FROM sunday_mass_assignments WHERE id = :uid"
                ),
                {"uid": assignment.id.hex},
            )
        ).one()

        assert row.servant_name != "Pierre Kamdem"

    async def test_servant_name_decrypted_on_read(self, db_session):
        admin = await _create_admin(db_session)
        template = await self._make_template(db_session, admin.id)
        mass = await self._make_mass(db_session, template.id)

        repo = SundayScheduleRepository(db_session)
        created = await repo.create_assignment(
            SundayMassAssignment(
                id=uuid4(),
                mass_slot_id=mass.id,
                position=LiturgicalPosition.ACOLYTE_1,
                servant_name="Paul Nguema",
                assigned_by=admin.id,
            )
        )

        fetched = await repo.get_assignment(created.id)
        assert fetched.servant_name == "Paul Nguema"

    async def test_enrich_mass_returns_decrypted_names(self, db_session):
        admin = await _create_admin(db_session)
        template = await self._make_template(db_session, admin.id)
        mass = await self._make_mass(db_session, template.id)

        repo = SundayScheduleRepository(db_session)
        await repo.create_assignment(
            SundayMassAssignment(
                id=uuid4(),
                mass_slot_id=mass.id,
                position=LiturgicalPosition.THURIFERAIRE,
                servant_name="Marc Bella",
                assigned_by=admin.id,
            )
        )

        enriched = await repo.enrich_mass(mass)
        names = [
            a["servant_name"] for a in enriched["assignments"] if a.get("servant_name")
        ]
        assert "Marc Bella" in names

    async def test_enrich_template_decrypts_creator_name(self, db_session):
        admin = await _create_admin(db_session)
        template = await self._make_template(db_session, admin.id)

        repo = SundayScheduleRepository(db_session)
        enriched = await repo.enrich_template(template)

        assert enriched["creator_first_name"] == "Admin"
        assert enriched["creator_last_name"] == "Test"
