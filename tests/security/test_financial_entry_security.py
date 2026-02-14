"""
Tests de sécurité pour le module COMMISSAIRE - Audit financier.
"""
import pytest
from datetime import timedelta
from uuid import uuid4


@pytest.mark.asyncio
async def test_only_commissaire_can_create_entry(client, servant_token, admin_token):
    """Test que seul le COMMISSAIRE peut créer une entrée."""
    # Servant normal ne peut pas
    response = await client.post(
        "/api/v1/financial-entries/",
        headers={"Authorization": f"Bearer {servant_token}"},
        json={
            "date": "2026-02-10T10:00:00",
            "amount": 5000.0,
            "category": "CONTRIBUTION",
            "source": "SERVANT",
            "description": "Test",
        },
    )
    assert response.status_code == 403
    
    # Admin ne peut pas non plus
    response = await client.post(
        "/api/v1/financial-entries/",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "date": "2026-02-10T10:00:00",
            "amount": 5000.0,
            "category": "CONTRIBUTION",
            "source": "SERVANT",
            "description": "Test",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cannot_modify_verified_entry(client, commissaire_token, db_session):
    """Test qu'on ne peut pas modifier une entrée vérifiée."""
    from src.core.entities.financial_entry import FinancialEntry, EntryCategory, EntrySource, VerificationStatus
    from datetime import datetime
    
    entry = FinancialEntry(
        id=uuid4(),
        date=datetime(2026, 2, 10),
        amount=5000.0,
        category=EntryCategory.CONTRIBUTION,
        source=EntrySource.SERVANT,
        description="Test",
        recorded_by=uuid4(),
        verification_status=VerificationStatus.VERIFIED,
        verified_by=uuid4(),
    )
    db_session.add(entry)
    await db_session.commit()
    
    response = await client.patch(
        f"/api/v1/financial-entries/{entry.id}",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={"amount": 6000.0},
    )
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_sql_injection_protection(client, commissaire_token):
    """Test protection contre injection SQL."""
    response = await client.post(
        "/api/v1/financial-entries/",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={
            "date": "2026-02-10T10:00:00",
            "amount": 5000.0,
            "category": "CONTRIBUTION",
            "source": "SERVANT",
            "description": "'; DROP TABLE financial_entries; --",
        },
    )
    
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_negative_amount_rejected(client, commissaire_token):
    """Test que les montants négatifs sont rejetés."""
    response = await client.post(
        "/api/v1/financial-entries/",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={
            "date": "2026-02-10T10:00:00",
            "amount": -5000.0,
            "category": "CONTRIBUTION",
            "source": "SERVANT",
            "description": "Test",
        },
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_token_expiration(client, commissaire_user):
    """Test que les tokens expirés sont rejetés."""
    from tests.conftest import make_access_token
    
    expired_token = make_access_token(commissaire_user, expires=timedelta(seconds=-1))
    
    response = await client.get(
        "/api/v1/financial-entries/",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert response.status_code == 401
