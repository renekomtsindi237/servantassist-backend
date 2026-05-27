"""
Tests de sécurité — Isolation des données PII.

Ces tests vérifient que la conformité à la Loi 2024/017 (Cameroun) est
maintenue : aucune donnée personnelle en clair ne peut être extraite
directement de la base de données, même par un attaquant ayant accès
au stockage brut (Supabase / Contabo).

Cas couverts :
  1. Aucun champ nominatif en clair dans la table users
  2. Aucun email / téléphone en clair dans la table users
  3. Les index HMAC ne permettent pas de remonter au texte clair
  4. Un lookup HMAC sur une valeur connue ne retourne que le bon utilisateur
  5. Aucun champ sensible en clair dans discipline_cases
  6. Aucune justification en clair dans attendances
  7. Les servant_name dans sunday_mass_assignments sont chiffrés
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
from src.infrastructure.repositories.sunday_schedule_repository import (
    SundayScheduleRepository,
)
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.field_encryption import get_encryptor
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


async def _insert_user(
    session, first_name="Jean", last_name="Ndaa", email=None, phone=None
) -> User:
    email = email or f"u{uuid4().hex[:6]}@pii.cm"
    phone = phone or f"+23760{uuid4().int % 9_000_000 + 1_000_000}"
    repo = UserRepository(session)
    return await repo.create(
        User(
            id=uuid4(),
            email=email,
            hashed_password=SecurityUtils.get_password_hash("TestPass1"),
            first_name=first_name,
            last_name=last_name,
            role=UserRole.SERVANT,
            is_active=True,
            phone_number=phone,
        )
    )


# ═══════════════════════════════════════════════════════════════════════════
#  TABLE users — aucun champ PII en clair
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestUsersTableHasNoPII:
    async def test_no_plaintext_first_name(self, db_session):
        user = await _insert_user(db_session, first_name="Barthélémy")
        row = (
            await db_session.execute(
                text("SELECT first_name FROM users WHERE id = :uid"),
                {"uid": user.id.hex},
            )
        ).one()
        assert row.first_name != "Barthélémy", "first_name en clair en base !"

    async def test_no_plaintext_last_name(self, db_session):
        user = await _insert_user(db_session, last_name="Mbarga")
        row = (
            await db_session.execute(
                text("SELECT last_name FROM users WHERE id = :uid"),
                {"uid": user.id.hex},
            )
        ).one()
        assert row.last_name != "Mbarga", "last_name en clair en base !"

    async def test_no_plaintext_email(self, db_session):
        email = "secret.servant@paroisse.cm"
        user = await _insert_user(db_session, email=email)
        row = (
            await db_session.execute(
                text("SELECT email FROM users WHERE id = :uid"),
                {"uid": user.id.hex},
            )
        ).one()
        assert row.email != email, "email en clair en base !"

    async def test_no_plaintext_phone(self, db_session):
        phone = "+237699123456"
        user = await _insert_user(db_session, phone=phone)
        row = (
            await db_session.execute(
                text("SELECT phone_number FROM users WHERE id = :uid"),
                {"uid": user.id.hex},
            )
        ).one()
        assert row.phone_number != phone, "phone_number en clair en base !"

    async def test_email_hmac_is_not_email(self, db_session):
        email = "hmacleak@paroisse.cm"
        user = await _insert_user(db_session, email=email)
        row = (
            await db_session.execute(
                text("SELECT email_hmac FROM users WHERE id = :uid"),
                {"uid": user.id.hex},
            )
        ).one()
        # Le HMAC ne doit pas contenir le texte de l'email
        assert email not in row.email_hmac
        assert "@" not in row.email_hmac

    async def test_phone_hmac_is_not_phone(self, db_session):
        phone = "+237699001122"
        user = await _insert_user(db_session, phone=phone)
        row = (
            await db_session.execute(
                text("SELECT phone_hmac FROM users WHERE id = :uid"),
                {"uid": user.id.hex},
            )
        ).one()
        assert phone not in row.phone_hmac
        assert "+" not in row.phone_hmac

    async def test_sql_search_by_plaintext_email_finds_nothing(self, db_session):
        """Un attaquant ne peut pas trouver un utilisateur avec 'WHERE email = plaintext'."""
        email = "undiscoverable@paroisse.cm"
        await _insert_user(db_session, email=email)

        rows = (
            await db_session.execute(
                text("SELECT id FROM users WHERE email = :e"),
                {"e": email},
            )
        ).all()

        assert (
            len(rows) == 0
        ), "L'email en clair a été trouvé en base — faille de sécurité !"

    async def test_full_table_scan_reveals_no_names(self, db_session):
        """Scan complet de la table : aucun premier/dernier nom en clair."""
        known_names = ["Alice", "Bernard", "Catherine"]
        for name in known_names:
            await _insert_user(db_session, first_name=name)

        rows = (await db_session.execute(text("SELECT first_name FROM users"))).all()
        stored = [r.first_name for r in rows if r.first_name]

        for name in known_names:
            assert name not in stored, f"'{name}' trouvé en clair dans la table users !"


# ═══════════════════════════════════════════════════════════════════════════
#  HMAC INDEX — isolation et précision du lookup
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestHmacIndexIsolation:
    async def test_hmac_lookup_returns_only_correct_user(self, db_session):
        """Le HMAC d'un email ne peut retrouver qu'un seul utilisateur spécifique."""
        u1 = await _insert_user(db_session, email="user1@pii.cm")
        u2 = await _insert_user(db_session, email="user2@pii.cm")

        repo = UserRepository(db_session)
        found = await repo.get_by_email("user1@pii.cm")

        assert found is not None
        assert found.id == u1.id
        assert found.id != u2.id

    async def test_similar_emails_have_different_hmac(self, db_session):
        """Des emails proches → HMAC totalement différents (pas de préfixe commun)."""
        enc = get_encryptor()
        h1 = enc.hmac_index("a@test.cm")
        h2 = enc.hmac_index("b@test.cm")
        assert h1 != h2
        assert not h1.startswith(h2[:10])

    async def test_wrong_email_returns_none(self, db_session):
        await _insert_user(db_session, email="real@pii.cm")
        repo = UserRepository(db_session)
        assert await repo.get_by_email("fake@pii.cm") is None


# ═══════════════════════════════════════════════════════════════════════════
#  TABLE discipline_cases — champs sensibles chiffrés
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestDisciplineTableHasNoPII:
    async def test_offense_description_not_plaintext(self, db_session):
        admin = await _insert_user(db_session, email="adm@pii.cm")
        servant = await _insert_user(db_session, email="srv@pii.cm")
        repo = DisciplineCaseRepository(db_session)

        case = await repo.create(
            DisciplineCase(
                id=uuid4(),
                accused_user_id=servant.id,
                reported_by=admin.id,
                offense_category=OffenseCategory.INSUBORDINATION,
                offense_description="Faute grave confidentielle",
                offense_date=_now(),
                severity=SanctionSeverity.GRAVE,
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

        assert row.offense_description != "Faute grave confidentielle"

    async def test_verdict_notes_not_plaintext(self, db_session):
        admin = await _insert_user(db_session, email="adm2@pii.cm")
        servant = await _insert_user(db_session, email="srv2@pii.cm")
        repo = DisciplineCaseRepository(db_session)

        case = await repo.create(
            DisciplineCase(
                id=uuid4(),
                accused_user_id=servant.id,
                reported_by=admin.id,
                offense_category=OffenseCategory.ABSENCE_NON_JUSTIFIEE,
                offense_description="Absent",
                verdict_notes="Verdict confidentiel du conseil",
                offense_date=_now(),
                severity=SanctionSeverity.MINEUR,
                status=DisciplineCaseStatus.VERDICT_RENDU,
                sanction_type=SanctionType.AVERTISSEMENT_ECRIT,
            )
        )

        row = (
            await db_session.execute(
                text("SELECT verdict_notes FROM discipline_cases WHERE id = :uid"),
                {"uid": case.id.hex},
            )
        ).one()

        assert row.verdict_notes != "Verdict confidentiel du conseil"


# ═══════════════════════════════════════════════════════════════════════════
#  TABLE attendances — justification chiffrée
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestAttendanceTableHasNoPII:
    async def test_medical_justification_not_plaintext(self, db_session):
        servant = await _insert_user(db_session, email="att@pii.cm")
        repo = AttendanceRepository(db_session)

        att = await repo.create(
            Attendance(
                id=uuid4(),
                user_id=servant.id,
                attendance_type=AttendanceType.FORMATION,
                attendance_date=_now(),
                title="Formation",
                status=AttendanceStatus.ABSENT,
                justification="Hospitalisation — donnée médicale sensible",
                recorded_by=servant.id,
            )
        )

        row = (
            await db_session.execute(
                text("SELECT justification FROM attendances WHERE id = :uid"),
                {"uid": att.id.hex},
            )
        ).one()

        assert row.justification != "Hospitalisation — donnée médicale sensible"
        assert "médical" not in (row.justification or "")


# ═══════════════════════════════════════════════════════════════════════════
#  TABLE sunday_mass_assignments — servant_name chiffré
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.security
class TestSundayAssignmentTableHasNoPII:
    async def test_servant_name_not_plaintext(self, db_session):
        admin = await _insert_user(db_session, email="admsun@pii.cm")
        schedule_repo = SundayScheduleRepository(db_session)

        template = await schedule_repo.create_template(
            SundayScheduleTemplate(
                id=uuid4(),
                title="Messe sécurité",
                schedule_date=_now(),
                status=SundayScheduleStatus.DRAFT,
                created_by=admin.id,
            )
        )
        mass = await schedule_repo.create_mass(
            SundayMassSlot(
                id=uuid4(),
                template_id=template.id,
                mass_time="10:00",
                mass_type="Messe",
                language=MassLanguage.FRANCAIS,
            )
        )
        assignment = await schedule_repo.create_assignment(
            SundayMassAssignment(
                id=uuid4(),
                mass_slot_id=mass.id,
                position=LiturgicalPosition.ACOLYTE_1,
                servant_name="Nom Secret du Servant",
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

        assert row.servant_name != "Nom Secret du Servant"
        assert "Secret" not in (row.servant_name or "")
