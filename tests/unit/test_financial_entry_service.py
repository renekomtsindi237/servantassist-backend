"""Unit tests for FinancialEntryService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.financial_entry_service import FinancialEntryService
from src.core.entities.financial_entry import (
    Discrepancy,
    EntryCategory,
    EntrySource,
    FinancialEntry,
    VerificationStatus,
)

NOW = datetime(2026, 6, 1, 10, 0, 0)
START = datetime(2026, 6, 1, 0, 0, 0)
END = datetime(2026, 6, 30, 0, 0, 0)


# ── Factories ──────────────────────────────────────────────────────────────


def _make_entry(verification_status=VerificationStatus.PENDING, **kwargs) -> FinancialEntry:
    return FinancialEntry(
        id=kwargs.pop("id", uuid4()),
        date=kwargs.pop("date", NOW),
        amount=kwargs.pop("amount", 5000.0),
        category=kwargs.pop("category", EntryCategory.COTISATION),
        source=kwargs.pop("source", EntrySource.SERVANT),
        description=kwargs.pop("description", "Cotisation mensuelle"),
        recorded_by=kwargs.pop("recorded_by", uuid4()),
        verification_status=verification_status,
        created_at=kwargs.pop("created_at", NOW),
        updated_at=kwargs.pop("updated_at", NOW),
        **kwargs,
    )


def _make_discrepancy(entry_id=None, **kwargs) -> Discrepancy:
    d = MagicMock(spec=Discrepancy)
    d.id = kwargs.pop("id", uuid4())
    d.entry_id = entry_id or uuid4()
    d.type = kwargs.pop("type", "AMOUNT_MISMATCH")
    d.description = kwargs.pop("description", "Montant ne correspond pas")
    d.resolved = False
    return d


def _base_stats() -> dict:
    return {
        "total_entries": 10,
        "total_amount": 50000.0,
        "verified_entries": 7,
        "pending_entries": 2,
        "rejected_entries": 1,
        "pending_amount": 10000.0,
    }


def _make_svc(entry_repo=None, discrepancy_repo=None) -> FinancialEntryService:
    if entry_repo is None:
        entry_repo = MagicMock()
        entry_repo.create = AsyncMock()
        entry_repo.get_by_id = AsyncMock(return_value=None)
        entry_repo.update = AsyncMock()
        entry_repo.delete = AsyncMock(return_value=True)
        entry_repo.verify = AsyncMock()
        entry_repo.list_entries = AsyncMock(return_value=([], 0))
        entry_repo.get_by_recorded_by = AsyncMock(return_value=([], 0))
        entry_repo.get_statistics = AsyncMock(return_value=_base_stats())
        entry_repo.get_summary_by_category = AsyncMock(return_value=[])
    if discrepancy_repo is None:
        discrepancy_repo = MagicMock()
        discrepancy_repo.create = AsyncMock()
        discrepancy_repo.get_by_entry = AsyncMock(return_value=[])
        discrepancy_repo.list_unresolved = AsyncMock(return_value=[])
        discrepancy_repo.resolve = AsyncMock()
        discrepancy_repo.delete = AsyncMock(return_value=True)
    return FinancialEntryService(entry_repo, discrepancy_repo)


# ── create_entry ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_entry_success():
    entry = _make_entry()
    svc = _make_svc()
    svc.entry_repo.create.return_value = entry
    result = await svc.create_entry(
        date=NOW,
        amount=5000.0,
        category=EntryCategory.COTISATION,
        source=EntrySource.SERVANT,
        description="Cotisation mensuelle",
        recorded_by=uuid4(),
    )
    assert result.id == entry.id
    svc.entry_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_entry_with_reference():
    entry = _make_entry()
    svc = _make_svc()
    svc.entry_repo.create.return_value = entry
    result = await svc.create_entry(
        date=NOW,
        amount=5000.0,
        category=EntryCategory.COTISATION,
        source=EntrySource.SERVANT,
        description="Cotisation",
        recorded_by=uuid4(),
        reference="REF-001",
    )
    assert result.id == entry.id


# ── get_entry ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_entry_not_found():
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = None
    result = await svc.get_entry(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_entry_found():
    entry = _make_entry()
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = entry
    result = await svc.get_entry(entry.id)
    assert result.id == entry.id


# ── list_entries ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_entries_empty():
    svc = _make_svc()
    svc.entry_repo.list_entries.return_value = ([], 0)
    entries, total = await svc.list_entries()
    assert total == 0
    assert entries == []


@pytest.mark.asyncio
async def test_list_entries_with_items():
    entry = _make_entry()
    svc = _make_svc()
    svc.entry_repo.list_entries.return_value = ([entry], 1)
    entries, total = await svc.list_entries(limit=10, category=EntryCategory.COTISATION)
    assert total == 1
    assert entries[0].id == entry.id


# ── update_entry ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_entry_not_found():
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = None
    result = await svc.update_entry(uuid4(), amount=6000)
    assert result is None


@pytest.mark.asyncio
async def test_update_entry_verified_raises():
    entry = _make_entry(verification_status=VerificationStatus.VERIFIED)
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = entry
    with pytest.raises(ValueError, match="vérifiées"):
        await svc.update_entry(entry.id, amount=6000)


@pytest.mark.asyncio
async def test_update_entry_success():
    entry = _make_entry()
    updated = _make_entry(amount=6000)
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = entry
    svc.entry_repo.update.return_value = updated
    result = await svc.update_entry(entry.id, amount=6000, description="Mise à jour")
    assert result.id == updated.id
    svc.entry_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_update_entry_all_fields():
    entry = _make_entry()
    updated = _make_entry()
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = entry
    svc.entry_repo.update.return_value = updated
    result = await svc.update_entry(
        entry.id,
        date=START,
        amount=1000,
        category=EntryCategory.DONATION,
        source=EntrySource.EXTERNAL,
        reference="REF-002",
        description="Don externe",
    )
    assert result is not None


# ── delete_entry ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_entry_not_found():
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = None
    result = await svc.delete_entry(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_delete_entry_verified_raises():
    entry = _make_entry(verification_status=VerificationStatus.VERIFIED)
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = entry
    with pytest.raises(ValueError, match="vérifiées"):
        await svc.delete_entry(entry.id)


@pytest.mark.asyncio
async def test_delete_entry_success():
    entry = _make_entry()
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = entry
    svc.entry_repo.delete.return_value = True
    result = await svc.delete_entry(entry.id)
    assert result is True


# ── verify_entry ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_verify_entry_not_found():
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = None
    result = await svc.verify_entry(uuid4(), uuid4(), VerificationStatus.VERIFIED)
    assert result is None


@pytest.mark.asyncio
async def test_verify_entry_success():
    entry = _make_entry()
    verified = _make_entry(verification_status=VerificationStatus.VERIFIED)
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = entry
    svc.entry_repo.verify.return_value = verified
    result = await svc.verify_entry(entry.id, uuid4(), VerificationStatus.VERIFIED, notes="OK")
    assert result.id == verified.id


@pytest.mark.asyncio
async def test_verify_entry_rejected():
    entry = _make_entry()
    rejected = _make_entry(verification_status=VerificationStatus.REJECTED)
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = entry
    svc.entry_repo.verify.return_value = rejected
    result = await svc.verify_entry(entry.id, uuid4(), VerificationStatus.REJECTED, notes="Anomalie")
    assert result.id == rejected.id


# ── get_my_entries ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_my_entries():
    entry = _make_entry()
    svc = _make_svc()
    svc.entry_repo.get_by_recorded_by.return_value = ([entry], 1)
    entries, total = await svc.get_my_entries(uuid4())
    assert total == 1


# ── get_financial_summary ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_financial_summary():
    svc = _make_svc()
    svc.entry_repo.get_statistics.return_value = {**_base_stats(), "total_amount": 50000.0}
    result = await svc.get_financial_summary(start_date=START, end_date=END)
    assert result.total_income == 50000.0
    assert result.total_expense == 0.0


@pytest.mark.asyncio
async def test_get_financial_summary_no_dates():
    svc = _make_svc()
    svc.entry_repo.get_statistics.return_value = {**_base_stats()}
    result = await svc.get_financial_summary()
    assert result.total_income >= 0


# ── get_statistics ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_statistics_with_entries():
    svc = _make_svc()
    svc.entry_repo.get_statistics.return_value = _base_stats()
    result = await svc.get_statistics(START, END)
    assert result["verification_rate"] == 70.0  # 7/10
    assert result["average_entry_amount"] == 5000.0  # 50000/10
    assert result["period_start"] == START


@pytest.mark.asyncio
async def test_get_statistics_no_entries():
    svc = _make_svc()
    svc.entry_repo.get_statistics.return_value = {
        "total_entries": 0,
        "total_amount": 0.0,
        "verified_entries": 0,
        "pending_entries": 0,
        "rejected_entries": 0,
        "pending_amount": 0.0,
    }
    result = await svc.get_statistics(START, END)
    assert result["verification_rate"] == 0.0
    assert result["average_entry_amount"] == 0.0


# ── get_summary_by_category ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_summary_by_category():
    svc = _make_svc()
    svc.entry_repo.get_summary_by_category.return_value = [{"category": "COTISATION", "total_amount": 30000}]
    result = await svc.get_summary_by_category(START, END)
    assert len(result) == 1


# ── generate_audit_report ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_audit_report_no_discrepancies():
    svc = _make_svc()
    svc.entry_repo.get_statistics.return_value = _base_stats()
    svc.entry_repo.get_summary_by_category.return_value = []
    svc.discrepancy_repo.list_unresolved.return_value = []
    result = await svc.generate_audit_report(START, END, uuid4())
    assert result.total_entries == 10
    assert result.recommendations is not None


@pytest.mark.asyncio
async def test_generate_audit_report_with_discrepancies():
    d = _make_discrepancy()
    svc = _make_svc()
    svc.entry_repo.get_statistics.return_value = _base_stats()
    svc.entry_repo.get_summary_by_category.return_value = []
    svc.discrepancy_repo.list_unresolved.return_value = [d]
    result = await svc.generate_audit_report(START, END, uuid4())
    assert len(result.discrepancies) == 1


@pytest.mark.asyncio
async def test_generate_audit_report_low_verification_rate():
    stats = {
        **_base_stats(),
        "verified_entries": 2,
        "total_entries": 10,
    }
    svc = _make_svc()
    svc.entry_repo.get_statistics.return_value = stats
    svc.discrepancy_repo.list_unresolved.return_value = []
    result = await svc.generate_audit_report(START, END, uuid4())
    assert "vérification faible" in result.recommendations


# ── _generate_recommendations ──────────────────────────────────────────────


def test_generate_recommendations_clean():
    svc = _make_svc()
    stats = {
        "total_entries": 10,
        "verified_entries": 9,
        "rejected_entries": 0,
        "pending_amount": 0,
        "total_amount": 50000,
    }
    result = svc._generate_recommendations(stats, [])
    assert "Aucune anomalie" in result


def test_generate_recommendations_with_rejected():
    svc = _make_svc()
    stats = {
        "total_entries": 10,
        "verified_entries": 8,
        "rejected_entries": 2,
        "pending_amount": 0,
        "total_amount": 50000,
    }
    result = svc._generate_recommendations(stats, [])
    assert "rejetée" in result


def test_generate_recommendations_high_pending():
    svc = _make_svc()
    stats = {
        "total_entries": 10,
        "verified_entries": 8,
        "rejected_entries": 0,
        "pending_amount": 25000,  # > 30% of 50000
        "total_amount": 50000,
    }
    result = svc._generate_recommendations(stats, [])
    assert "en attente" in result


def test_generate_recommendations_with_discrepancies():
    d = _make_discrepancy()
    svc = _make_svc()
    stats = {
        "total_entries": 5,
        "verified_entries": 5,
        "rejected_entries": 0,
        "pending_amount": 0,
        "total_amount": 25000,
    }
    result = svc._generate_recommendations(stats, [d])
    assert "écart" in result


# ── create_discrepancy ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_discrepancy_entry_not_found():
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = None
    result = await svc.create_discrepancy(uuid4(), "AMOUNT", "Montant erroné", uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_create_discrepancy_success():
    entry = _make_entry()
    d = _make_discrepancy(entry_id=entry.id)
    svc = _make_svc()
    svc.entry_repo.get_by_id.return_value = entry
    svc.discrepancy_repo.create.return_value = d
    result = await svc.create_discrepancy(entry.id, "AMOUNT", "Montant erroné", uuid4())
    assert result is not None


# ── get_discrepancies_by_entry ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_discrepancies_by_entry_empty():
    svc = _make_svc()
    svc.discrepancy_repo.get_by_entry.return_value = []
    result = await svc.get_discrepancies_by_entry(uuid4())
    assert result == []


# ── list_unresolved_discrepancies ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_unresolved_discrepancies():
    d = _make_discrepancy()
    svc = _make_svc()
    svc.discrepancy_repo.list_unresolved.return_value = [d]
    result = await svc.list_unresolved_discrepancies()
    assert len(result) == 1


# ── resolve_discrepancy ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_discrepancy():
    d = _make_discrepancy()
    d.resolved = True
    svc = _make_svc()
    svc.discrepancy_repo.resolve.return_value = d
    result = await svc.resolve_discrepancy(d.id, "Résolu après vérification")
    assert result.resolved is True


# ── delete_discrepancy ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_discrepancy():
    svc = _make_svc()
    svc.discrepancy_repo.delete.return_value = True
    result = await svc.delete_discrepancy(uuid4())
    assert result is True
