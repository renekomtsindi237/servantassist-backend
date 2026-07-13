"""
Unit tests for repositories with low coverage:
- FinancialEntryRepository / DiscrepancyRepository
- ContributionRepository
- AttendanceSessionRepository
- SundayScheduleRepository (partial)
"""

from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest


# ─── Mock session builder ─────────────────────────────────────────────────────


def _mock_session() -> AsyncMock:
    """Create an AsyncMock simulating SQLAlchemy AsyncSession."""
    session = AsyncMock()
    return session


def _exec_result(scalars_list=None, scalar_one=None, scalar=None, one=None):
    """Build a mock execute() result with explicitly controlled return values."""
    result = MagicMock()
    scalars_obj = MagicMock()

    if scalars_list is not None:
        scalars_obj.all.return_value = scalars_list
        scalars_obj.first.return_value = scalars_list[0] if scalars_list else None
        result.scalars.return_value = scalars_obj

    # Explicitly set these regardless so they don't use auto-created MagicMocks
    # (which are truthy). Use a sentinel for "not set" detection.
    if scalar_one is not None or scalar_one is None:
        # Always set scalar_one_or_none and scalar_one explicitly when parameter provided
        pass

    result.scalar_one_or_none = MagicMock(return_value=scalar_one)
    result.scalar_one = MagicMock(return_value=scalar_one if scalar_one is not None else scalar)

    if scalar is not None:
        result.scalar = MagicMock(return_value=scalar)
    else:
        result.scalar = MagicMock(return_value=None)

    if one is not None:
        result.one = MagicMock(return_value=one)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  FinancialEntryRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_financial_entry(**kw):
    from src.core.entities.financial_entry import (
        EntryCategory,
        EntrySource,
        FinancialEntry,
        VerificationStatus,
    )

    return FinancialEntry(
        id=kw.pop("id", uuid4()),
        amount=kw.pop("amount", 5000.0),
        category=kw.pop("category", EntryCategory.COTISATION),
        source=kw.pop("source", EntrySource.SERVANT),
        verification_status=kw.pop("verification_status", VerificationStatus.PENDING),
        recorded_by=kw.pop("recorded_by", uuid4()),
        date=kw.pop("date", datetime.utcnow()),
        **kw,
    )


@pytest.mark.asyncio
async def test_financial_entry_create():
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)
    entry = _make_financial_entry()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(entry)

    session.add.assert_called_once_with(entry)
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(entry)
    assert result is entry


@pytest.mark.asyncio
async def test_financial_entry_get_by_id_found():
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)
    entry = _make_financial_entry()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=entry))

    result = await repo.get_by_id(entry.id)
    assert result is entry


@pytest.mark.asyncio
async def test_financial_entry_get_by_id_not_found():
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_financial_entry_delete_not_found():
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_financial_entry_delete_found():
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)
    entry = _make_financial_entry()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=entry))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(entry.id)
    assert result is True
    session.delete.assert_called_once_with(entry)


@pytest.mark.asyncio
async def test_financial_entry_list_entries():
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)

    entries = [_make_financial_entry(), _make_financial_entry()]
    # First execute returns entries, second returns count
    scalar_result = MagicMock()
    scalar_result.scalar_one.return_value = 2

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = entries
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(side_effect=[scalars_result, scalar_result])

    result_entries, total = await repo.list_entries()
    assert len(result_entries) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_financial_entry_verify_not_found():
    from src.core.entities.financial_entry import VerificationStatus
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.verify(uuid4(), uuid4(), VerificationStatus.VERIFIED)
    assert result is None


@pytest.mark.asyncio
async def test_financial_entry_verify_found():
    from src.core.entities.financial_entry import VerificationStatus
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)
    entry = _make_financial_entry()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=entry))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    verifier_id = uuid4()
    result = await repo.verify(entry.id, verifier_id, VerificationStatus.VERIFIED, notes="OK")

    session.commit.assert_called_once()
    assert result is entry
    assert entry.verification_status == VerificationStatus.VERIFIED
    assert entry.verified_by == verifier_id


@pytest.mark.asyncio
async def test_financial_entry_update():
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)
    entry = _make_financial_entry()

    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(entry)
    session.commit.assert_called_once()
    assert result is entry


@pytest.mark.asyncio
async def test_financial_entry_get_statistics():
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)

    def _count_sum_result(count, amount):
        r = MagicMock()
        r.one.return_value = (count, amount)
        return r

    session.execute = AsyncMock(
        side_effect=[
            _count_sum_result(10, 50000),   # total
            _count_sum_result(8, 40000),    # verified
            _count_sum_result(2, 10000),    # pending
            _count_sum_result(0, None),     # rejected
        ]
    )

    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 6, 30)

    stats = await repo.get_statistics(start_date, end_date)

    assert stats["total_entries"] == 10
    assert stats["total_amount"] == 50000.0
    assert stats["verified_entries"] == 8
    assert stats["rejected_entries"] == 0
    assert stats["rejected_amount"] == 0.0


@pytest.mark.asyncio
async def test_financial_entry_get_summary_by_category():
    from src.core.entities.financial_entry import EntryCategory, VerificationStatus
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)

    entries = [
        _make_financial_entry(
            category=EntryCategory.COTISATION,
            amount=5000.0,
            verification_status=VerificationStatus.VERIFIED,
        ),
        _make_financial_entry(
            category=EntryCategory.COTISATION,
            amount=3000.0,
            verification_status=VerificationStatus.PENDING,
        ),
    ]

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = entries
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(return_value=scalars_result)

    start_date = datetime(2026, 1, 1)
    end_date = datetime(2026, 6, 30)

    summary = await repo.get_summary_by_category(start_date, end_date)

    assert len(summary) == 1
    assert summary[0]["entry_count"] == 2
    assert summary[0]["total_amount"] == 8000.0


@pytest.mark.asyncio
async def test_financial_entry_get_by_recorded_by():
    from src.infrastructure.repositories.financial_entry_repository import FinancialEntryRepository

    session = _mock_session()
    repo = FinancialEntryRepository(session)

    user_id = uuid4()
    entries = [_make_financial_entry(recorded_by=user_id)]

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = entries
    scalars_result.scalars.return_value = scalars_obj

    count_result = MagicMock()
    count_result.scalar_one.return_value = 1

    session.execute = AsyncMock(side_effect=[scalars_result, count_result])

    result_entries, total = await repo.get_by_recorded_by(user_id)
    assert len(result_entries) == 1
    assert total == 1


# ═══════════════════════════════════════════════════════════════════════════════
#  DiscrepancyRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_discrepancy(**kw):
    from src.core.entities.financial_entry import Discrepancy

    return Discrepancy(
        id=kw.pop("id", uuid4()),
        entry_id=kw.pop("entry_id", uuid4()),
        description=kw.pop("description", "Mismatch in amount"),
        resolved=kw.pop("resolved", False),
        detected_at=kw.pop("detected_at", datetime.utcnow()),
        **kw,
    )


@pytest.mark.asyncio
async def test_discrepancy_create():
    from src.infrastructure.repositories.financial_entry_repository import DiscrepancyRepository

    session = _mock_session()
    repo = DiscrepancyRepository(session)
    disc = _make_discrepancy()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(disc)
    session.add.assert_called_once_with(disc)
    assert result is disc


@pytest.mark.asyncio
async def test_discrepancy_get_by_id_found():
    from src.infrastructure.repositories.financial_entry_repository import DiscrepancyRepository

    session = _mock_session()
    repo = DiscrepancyRepository(session)
    disc = _make_discrepancy()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=disc))
    result = await repo.get_by_id(disc.id)
    assert result is disc


@pytest.mark.asyncio
async def test_discrepancy_list_unresolved():
    from src.infrastructure.repositories.financial_entry_repository import DiscrepancyRepository

    session = _mock_session()
    repo = DiscrepancyRepository(session)

    discs = [_make_discrepancy(), _make_discrepancy()]
    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = discs
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(return_value=scalars_result)

    result = await repo.list_unresolved()
    assert len(result) == 2


@pytest.mark.asyncio
async def test_discrepancy_resolve_not_found():
    from src.infrastructure.repositories.financial_entry_repository import DiscrepancyRepository

    session = _mock_session()
    repo = DiscrepancyRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.resolve(uuid4(), "some note")
    assert result is None


@pytest.mark.asyncio
async def test_discrepancy_resolve_found():
    from src.infrastructure.repositories.financial_entry_repository import DiscrepancyRepository

    session = _mock_session()
    repo = DiscrepancyRepository(session)
    disc = _make_discrepancy()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=disc))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.resolve(disc.id, "Resolved OK")
    assert result is disc
    assert disc.resolved is True
    assert disc.resolution_notes == "Resolved OK"


@pytest.mark.asyncio
async def test_discrepancy_delete_not_found():
    from src.infrastructure.repositories.financial_entry_repository import DiscrepancyRepository

    session = _mock_session()
    repo = DiscrepancyRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))
    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_discrepancy_delete_found():
    from src.infrastructure.repositories.financial_entry_repository import DiscrepancyRepository

    session = _mock_session()
    repo = DiscrepancyRepository(session)
    disc = _make_discrepancy()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=disc))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(disc.id)
    assert result is True
    session.delete.assert_called_once_with(disc)


@pytest.mark.asyncio
async def test_discrepancy_get_by_entry():
    from src.infrastructure.repositories.financial_entry_repository import DiscrepancyRepository

    session = _mock_session()
    repo = DiscrepancyRepository(session)
    entry_id = uuid4()
    discs = [_make_discrepancy(entry_id=entry_id)]

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = discs
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(return_value=scalars_result)

    result = await repo.get_by_entry(entry_id)
    assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════════════
#  ContributionRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_contribution(**kw):
    from src.core.entities.contribution import Contribution, PaymentMode, PaymentStatus

    return Contribution(
        id=kw.pop("id", uuid4()),
        servant_id=kw.pop("servant_id", uuid4()),
        amount=kw.pop("amount", 500.0),
        month=kw.pop("month", 6),
        year=kw.pop("year", 2026),
        payment_mode=kw.pop("payment_mode", PaymentMode.MONTHLY),
        payment_date=kw.pop("payment_date", datetime.utcnow()),
        recorded_by=kw.pop("recorded_by", uuid4()),
        **kw,
    )


@pytest.mark.asyncio
async def test_contribution_create():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    contrib = _make_contribution()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(contrib)
    session.add.assert_called_once_with(contrib)
    assert result is contrib


@pytest.mark.asyncio
async def test_contribution_get_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    contrib = _make_contribution()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=contrib))

    result = await repo.get(contrib.id)
    assert result is contrib


@pytest.mark.asyncio
async def test_contribution_get_not_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_contribution_delete_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    contrib = _make_contribution()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=contrib))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(contrib.id)
    assert result is True
    session.delete.assert_called_once_with(contrib)


@pytest.mark.asyncio
async def test_contribution_delete_not_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_contribution_update_not_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.update(uuid4(), _make_contribution())
    assert result is None


@pytest.mark.asyncio
async def test_contribution_update_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    contrib = _make_contribution()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=contrib))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    updated = _make_contribution(id=contrib.id, amount=1000.0)
    result = await repo.update(contrib.id, updated)
    assert result is contrib
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_contribution_list():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)

    contribs = [_make_contribution(), _make_contribution()]

    count_result = MagicMock()
    count_result.scalar.return_value = 2

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = contribs
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(side_effect=[count_result, scalars_result])

    result, total = await repo.list()
    assert len(result) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_contribution_get_servant_contributions():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)

    servant_id = uuid4()
    contribs = [_make_contribution(servant_id=servant_id)]

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = contribs
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(return_value=scalars_result)

    result = await repo.get_servant_contributions(servant_id)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_contribution_get_monthly_contributions():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)

    contribs = [_make_contribution(month=6, year=2026)]

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = contribs
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(return_value=scalars_result)

    result = await repo.get_monthly_contributions(6, 2026)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_contribution_enrich():
    from src.core.entities.user import User, UserRole
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)

    servant_id = uuid4()
    recorded_by_id = uuid4()
    contrib = _make_contribution(servant_id=servant_id, recorded_by=recorded_by_id)

    servant = User(
        id=servant_id,
        first_name="Jean",
        last_name="Doe",
        email="jean@test.com",
        role=UserRole.SERVANT,
        is_active=True,
    )
    recorder = User(
        id=recorded_by_id,
        first_name="Admin",
        last_name="User",
        email="admin@test.com",
        role=UserRole.ADMIN,
        is_active=True,
    )

    def make_scalar_result(val):
        r = MagicMock()
        r.scalar_one_or_none.return_value = val
        return r

    session.execute = AsyncMock(side_effect=[make_scalar_result(servant), make_scalar_result(recorder)])

    with patch("src.infrastructure.repositories.contribution_repository.decrypt_str_fields"):
        result = await repo.enrich_contribution(contrib)

    assert result["servant_name"] == "Jean Doe"
    assert result["recorded_by_name"] == "Admin User"


@pytest.mark.asyncio
async def test_contribution_enrich_missing_users():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)

    contrib = _make_contribution()

    def make_none_result():
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        return r

    session.execute = AsyncMock(side_effect=[make_none_result(), make_none_result()])

    result = await repo.enrich_contribution(contrib)
    assert result["servant_name"] == "Inconnu"
    assert result["recorded_by_name"] == "Inconnu"


# ═══════════════════════════════════════════════════════════════════════════════
#  AttendanceSessionRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_attendance_session(**kw):
    from src.core.entities.attendance_session import AttendanceSession

    return AttendanceSession(
        id=kw.pop("id", uuid4()),
        session_date=kw.pop("session_date", datetime.utcnow()),
        conducted_by=kw.pop("conducted_by", uuid4()),
        **kw,
    )


def _make_attendance_record(**kw):
    from src.core.entities.attendance_session import AttendanceRecord, AttendanceStatus

    return AttendanceRecord(
        id=kw.pop("id", uuid4()),
        session_id=kw.pop("session_id", uuid4()),
        servant_id=kw.pop("servant_id", uuid4()),
        status=kw.pop("status", AttendanceStatus.PRESENT),
        recorded_by=kw.pop("recorded_by", uuid4()),
        created_at=kw.pop("created_at", datetime.utcnow()),
        **kw,
    )


@pytest.mark.asyncio
async def test_attendance_session_create():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)
    att_session = _make_attendance_session()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_session(att_session)
    session.add.assert_called_once_with(att_session)
    assert result is att_session


@pytest.mark.asyncio
async def test_attendance_session_get_found():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)
    att_session = _make_attendance_session()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=att_session))

    result = await repo.get_session(att_session.id)
    assert result is att_session


@pytest.mark.asyncio
async def test_attendance_session_get_not_found():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.get_session(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_attendance_session_list_sessions():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)

    sessions_list = [_make_attendance_session(), _make_attendance_session()]

    count_result = MagicMock()
    count_result.scalar.return_value = 2

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = sessions_list
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(side_effect=[count_result, scalars_result])

    result, total = await repo.list_sessions()
    assert len(result) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_attendance_record_create():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)
    record = _make_attendance_record()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_record(record)
    session.add.assert_called_once_with(record)
    assert result is record


@pytest.mark.asyncio
async def test_attendance_record_get_found():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)
    record = _make_attendance_record()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=record))

    result = await repo.get_record(record.id)
    assert result is record


@pytest.mark.asyncio
async def test_attendance_record_create_batch():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)
    records = [_make_attendance_record(), _make_attendance_record()]

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_records_batch(records)
    assert len(result) == 2
    assert session.add.call_count == 2
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_attendance_record_get_session_records():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)
    session_id = uuid4()
    records = [_make_attendance_record(session_id=session_id)]

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = records
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(return_value=scalars_result)

    result = await repo.get_session_records(session_id)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_attendance_record_get_by_session_and_servant():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)
    record = _make_attendance_record()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=record))

    result = await repo.get_record_by_session_and_servant(record.session_id, record.servant_id)
    assert result is record


@pytest.mark.asyncio
async def test_attendance_record_update_not_found():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.update_record(uuid4(), _make_attendance_record())
    assert result is None


@pytest.mark.asyncio
async def test_attendance_record_update_found():
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)
    record = _make_attendance_record()
    existing_record = _make_attendance_record(id=record.id)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=existing_record))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update_record(record.id, record)
    assert result is existing_record
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_attendance_get_all_servants():
    from src.core.entities.user import User, UserRole
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)

    servants = [
        User(
            id=uuid4(),
            first_name="Jean",
            last_name="Doe",
            email="jean@test.com",
            role=UserRole.SERVANT,
            is_active=True,
        )
    ]

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = servants
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(return_value=scalars_result)

    with patch("src.infrastructure.repositories.attendance_session_repository.decrypt_str_fields"):
        result = await repo.get_all_servants()

    assert len(result) == 1


@pytest.mark.asyncio
async def test_attendance_calculate_stats():
    from src.core.entities.attendance_session import AttendanceStatus
    from src.core.entities.user import User, UserRole
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)

    servant_id = uuid4()

    servant = User(
        id=servant_id,
        first_name="Jean",
        last_name="Doe",
        email="jean@test.com",
        role=UserRole.SERVANT,
        is_active=True,
    )

    records = [
        _make_attendance_record(servant_id=servant_id, status=AttendanceStatus.PRESENT),
        _make_attendance_record(servant_id=servant_id, status=AttendanceStatus.ABSENT),
        _make_attendance_record(servant_id=servant_id, status=AttendanceStatus.LATE),
    ]

    def make_scalar_one_result(val):
        r = MagicMock()
        r.scalar_one_or_none.return_value = val
        return r

    scalars_records_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = records
    scalars_records_result.scalars.return_value = scalars_obj

    total_result = MagicMock()
    total_result.scalar.return_value = 10

    servant_result = make_scalar_one_result(servant)

    session.execute = AsyncMock(
        side_effect=[
            servant_result,           # get servant
            scalars_records_result,   # get_servant_records
            total_result,             # count total sessions
        ]
    )

    with patch("src.infrastructure.repositories.attendance_session_repository.decrypt_str_fields"):
        stats = await repo.calculate_servant_stats(servant_id)

    assert stats.servant_id == servant_id
    assert stats.present_count == 1
    assert stats.absent_count == 1
    assert stats.late_count == 1
    assert stats.total_sessions == 10


@pytest.mark.asyncio
async def test_attendance_enrich_record():
    from src.core.entities.user import User, UserRole
    from src.infrastructure.repositories.attendance_session_repository import AttendanceSessionRepository

    session = _mock_session()
    repo = AttendanceSessionRepository(session)

    servant_id = uuid4()
    recorder_id = uuid4()
    record = _make_attendance_record(servant_id=servant_id, recorded_by=recorder_id)

    servant = User(
        id=servant_id, first_name="Alice", last_name="Martin",
        email="a@t.com", role=UserRole.SERVANT, is_active=True
    )
    recorder = User(
        id=recorder_id, first_name="Bob", last_name="Admin",
        email="b@t.com", role=UserRole.ADMIN, is_active=True
    )

    def make_r(val):
        r = MagicMock()
        r.scalar_one_or_none.return_value = val
        return r

    session.execute = AsyncMock(side_effect=[make_r(servant), make_r(recorder)])

    with patch("src.infrastructure.repositories.attendance_session_repository.decrypt_str_fields"):
        result = await repo.enrich_record(record)

    assert result["servant_name"] == "Alice Martin"
    assert result["recorded_by_name"] == "Bob Admin"


# ═══════════════════════════════════════════════════════════════════════════════
#  SundayScheduleRepository (basic operations)
# ═══════════════════════════════════════════════════════════════════════════════


def _make_template(**kw):
    from src.core.entities.sunday_schedule import (
        MassType,
        SundayScheduleStatus,
        SundayScheduleTemplate,
    )

    return SundayScheduleTemplate(
        id=kw.pop("id", uuid4()),
        title=kw.pop("title", "Dimanche Ordinaire"),
        schedule_date=kw.pop("schedule_date", datetime(2026, 6, 22)),
        mass_type=kw.pop("mass_type", MassType.ORDINAIRE),
        is_exceptional=kw.pop("is_exceptional", False),
        status=kw.pop("status", SundayScheduleStatus.DRAFT),
        created_by=kw.pop("created_by", uuid4()),
        created_at=kw.pop("created_at", datetime.utcnow()),
        updated_at=kw.pop("updated_at", datetime.utcnow()),
        **kw,
    )


@pytest.mark.asyncio
async def test_sunday_schedule_create_template():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_template(template)
    session.add.assert_called_once_with(template)
    assert result is template


@pytest.mark.asyncio
async def test_sunday_schedule_get_template_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=template))

    result = await repo.get_template(template.id)
    assert result is template


@pytest.mark.asyncio
async def test_sunday_schedule_get_template_not_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.get_template(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_sunday_schedule_delete_template_not_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.delete_template(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_sunday_schedule_delete_template_found_no_masses():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)
    template = _make_template()

    # First execute: get template; second execute: get masses (empty)
    template_result = _exec_result(scalar_one=template)
    masses_scalars = MagicMock()
    masses_scalars.scalars.return_value.all.return_value = []
    masses_result = masses_scalars

    session.execute = AsyncMock(side_effect=[template_result, masses_result])
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete_template(template.id)
    assert result is True
    session.delete.assert_called_with(template)


@pytest.mark.asyncio
async def test_sunday_schedule_list_templates():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)

    templates = [_make_template(), _make_template()]

    count_result = MagicMock()
    count_result.scalar_one.return_value = 2

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = templates
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(side_effect=[count_result, scalars_result])

    result, total = await repo.list_templates()
    assert len(result) == 2
    assert total == 2


@pytest.mark.asyncio
async def test_sunday_schedule_get_published_templates():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)

    templates = [_make_template()]

    scalars_result = MagicMock()
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = templates
    scalars_result.scalars.return_value = scalars_obj

    session.execute = AsyncMock(return_value=scalars_result)

    result = await repo.get_published_templates()
    assert len(result) == 1


@pytest.mark.asyncio
async def test_sunday_schedule_create_mass():
    from src.core.entities.sunday_schedule import MassLanguage, MassType, SundayMassSlot
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)

    mass = SundayMassSlot(
        id=uuid4(),
        template_id=uuid4(),
        mass_time="08:00",
        language=MassLanguage.FRANCAIS,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_mass(mass)
    session.add.assert_called_once_with(mass)
    assert result is mass


@pytest.mark.asyncio
async def test_sunday_schedule_get_mass_found():
    from src.core.entities.sunday_schedule import MassLanguage, SundayMassSlot
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)

    mass = SundayMassSlot(
        id=uuid4(),
        template_id=uuid4(),
        mass_time="10:00",
        language=MassLanguage.FRANCAIS,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=mass))

    result = await repo.get_mass(mass.id)
    assert result is mass


@pytest.mark.asyncio
async def test_sunday_schedule_delete_mass_not_found():
    from src.infrastructure.repositories.sunday_schedule_repository import SundayScheduleRepository

    session = _mock_session()
    repo = SundayScheduleRepository(session)

    session.execute = AsyncMock(return_value=_exec_result(scalar_one=None))

    result = await repo.delete_mass(uuid4())
    assert result is False
