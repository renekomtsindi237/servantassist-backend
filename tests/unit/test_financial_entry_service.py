"""
Tests unitaires pour le service d'audit financier (COMMISSAIRE).
"""
from datetime import datetime
from unittest.mock import AsyncMock
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


@pytest.fixture
def mock_entry_repo():
    return AsyncMock()


@pytest.fixture
def mock_discrepancy_repo():
    return AsyncMock()


@pytest.fixture
def service(mock_entry_repo, mock_discrepancy_repo):
    return FinancialEntryService(mock_entry_repo, mock_discrepancy_repo)


@pytest.mark.asyncio
async def test_create_entry(service, mock_entry_repo):
    """Test création d'entrée."""
    entry_id = uuid4()
    recorded_by = uuid4()

    mock_entry_repo.create.return_value = FinancialEntry(
        id=entry_id,
        date=datetime(2026, 2, 10),
        amount=5000.0,
        category=EntryCategory.CONTRIBUTION,
        source=EntrySource.SERVANT,
        description="Test",
        recorded_by=recorded_by,
        verification_status=VerificationStatus.PENDING,
    )

    result = await service.create_entry(
        date=datetime(2026, 2, 10),
        amount=5000.0,
        category=EntryCategory.CONTRIBUTION,
        source=EntrySource.SERVANT,
        description="Test",
        recorded_by=recorded_by,
    )

    assert result.amount == 5000.0
    assert result.verification_status == VerificationStatus.PENDING


@pytest.mark.asyncio
async def test_verify_entry(service, mock_entry_repo):
    """Test vérification d'entrée."""
    entry_id = uuid4()
    verified_by = uuid4()

    entry = FinancialEntry(
        id=entry_id,
        date=datetime(2026, 2, 10),
        amount=5000.0,
        category=EntryCategory.CONTRIBUTION,
        source=EntrySource.SERVANT,
        description="Test",
        recorded_by=uuid4(),
        verification_status=VerificationStatus.VERIFIED,
        verified_by=verified_by,
    )

    mock_entry_repo.get_by_id.return_value = entry
    mock_entry_repo.verify.return_value = entry

    result = await service.verify_entry(
        entry_id=entry_id,
        verified_by=verified_by,
        status=VerificationStatus.VERIFIED,
    )

    assert result.verification_status == VerificationStatus.VERIFIED


@pytest.mark.asyncio
async def test_generate_recommendations(service):
    """Test génération de recommandations."""
    stats = {
        "total_entries": 100,
        "verified_entries": 30,
        "rejected_entries": 5,
        "pending_amount": 50000.0,
        "total_amount": 100000.0,
    }

    recommendations = service._generate_recommendations(stats, [])

    assert "vérification faible" in recommendations.lower()
