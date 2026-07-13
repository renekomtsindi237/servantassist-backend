"""
Tests de performance pour le module COMMISSAIRE - Audit financier.
"""

import time
from datetime import datetime
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_create_entry_performance(client, commissaire_token):
    """Test performance création d'entrée."""
    start_time = time.time()

    response = await client.post(
        "/api/v1/financial-entries/",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={
            "date": "2026-02-10T10:00:00",
            "amount": 5000.0,
            "category": "CONTRIBUTION",
            "source": "SERVANT",
            "description": "Test performance",
        },
    )

    elapsed = time.time() - start_time

    assert response.status_code == 201
    assert elapsed < 1.0


@pytest.mark.asyncio
async def test_list_entries_performance(client, commissaire_token, db_session):
    """Test performance liste des entrées."""
    from src.core.entities.financial_entry import (
        EntryCategory,
        EntrySource,
        FinancialEntry,
        VerificationStatus,
    )

    # Créer 100 entrées
    for i in range(100):
        entry = FinancialEntry(
            id=uuid4(),
            date=datetime(2026, 2, 10),
            amount=1000.0 + i,
            category=EntryCategory.CONTRIBUTION,
            source=EntrySource.SERVANT,
            description=f"Entrée {i}",
            recorded_by=uuid4(),
            verification_status=VerificationStatus.PENDING,
        )
        db_session.add(entry)

    await db_session.commit()

    start_time = time.time()

    response = await client.get(
        "/api/v1/financial-entries/?limit=100",
        headers={"Authorization": f"Bearer {commissaire_token}"},
    )

    elapsed = time.time() - start_time

    assert response.status_code == 200
    assert elapsed < 2.0


@pytest.mark.asyncio
async def test_generate_audit_report_performance(client, commissaire_token):
    """Test performance génération de rapport."""
    start_time = time.time()

    response = await client.post(
        "/api/v1/financial-entries/audit/report",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={
            "start_date": "2026-02-01T00:00:00",
            "end_date": "2026-02-28T23:59:59",
        },
    )

    elapsed = time.time() - start_time

    assert response.status_code == 200
    assert elapsed < 3.0
