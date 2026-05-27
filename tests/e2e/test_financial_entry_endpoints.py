"""
Tests E2E pour le module COMMISSAIRE_AUX_COMPTES - Audit financier.
"""

from datetime import datetime
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_create_entry_success(client, commissaire_token):
    """Test création d'entrée réussie."""
    response = await client.post(
        "/api/v1/financial-entries/",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={
            "date": "2026-02-10T10:00:00",
            "amount": 5000.0,
            "category": "CONTRIBUTION",
            "source": "SERVANT",
            "reference": "CONTRIB-2026-02",
            "description": "Contributions du mois de février",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["amount"] == 5000.0
    assert data["category"] == "CONTRIBUTION"
    assert data["verification_status"] == "EN_ATTENTE"


@pytest.mark.asyncio
async def test_create_entry_unauthorized(client, servant_token):
    """Test qu'un servant normal ne peut pas créer d'entrée."""
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


@pytest.mark.asyncio
async def test_list_entries(client, commissaire_token, sample_financial_entry):
    """Test liste des entrées."""
    response = await client.get(
        "/api/v1/financial-entries/",
        headers={"Authorization": f"Bearer {commissaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_entry_detail(client, commissaire_token, sample_financial_entry):
    """Test récupération du détail."""
    response = await client.get(
        f"/api/v1/financial-entries/{sample_financial_entry.id}",
        headers={"Authorization": f"Bearer {commissaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_financial_entry.id)


@pytest.mark.asyncio
async def test_update_entry(client, commissaire_token, sample_financial_entry):
    """Test modification d'entrée."""
    response = await client.patch(
        f"/api/v1/financial-entries/{sample_financial_entry.id}",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={"amount": 5500.0, "description": "Montant corrigé"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["amount"] == 5500.0


@pytest.mark.asyncio
async def test_verify_entry(client, commissaire_token, sample_financial_entry):
    """Test vérification d'entrée."""
    response = await client.post(
        f"/api/v1/financial-entries/{sample_financial_entry.id}/verify",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={
            "verification_status": "VERIFIE",
            "notes": "Montant vérifié et conforme",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["verification_status"] == "VERIFIE"


@pytest.mark.asyncio
async def test_get_statistics(client, commissaire_token):
    """Test récupération des statistiques."""
    response = await client.get(
        "/api/v1/financial-entries/stats/summary",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        params={
            "start_date": "2026-02-01T00:00:00",
            "end_date": "2026-02-28T23:59:59",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_amount" in data
    assert "verification_rate" in data


@pytest.mark.asyncio
async def test_generate_audit_report(client, commissaire_token):
    """Test génération de rapport d'audit."""
    response = await client.post(
        "/api/v1/financial-entries/audit/report",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={
            "start_date": "2026-02-01T00:00:00",
            "end_date": "2026-02-28T23:59:59",
            "include_discrepancies": True,
            "include_recommendations": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "total_entries" in data
    assert "watermark_logo" in data


@pytest.mark.asyncio
async def test_create_discrepancy(client, commissaire_token, sample_financial_entry):
    """Test création d'écart."""
    response = await client.post(
        f"/api/v1/financial-entries/{sample_financial_entry.id}/discrepancies",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={
            "entry_id": str(sample_financial_entry.id),
            "type": "Montant incorrect",
            "description": "Écart détecté",
            "expected_amount": 5500.0,
            "actual_amount": 5000.0,
        },
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_resolve_discrepancy(client, commissaire_token, sample_discrepancy):
    """Test résolution d'écart."""
    response = await client.post(
        f"/api/v1/financial-entries/discrepancies/{sample_discrepancy.id}/resolve",
        headers={"Authorization": f"Bearer {commissaire_token}"},
        json={
            "resolved": True,
            "resolution_notes": "Écart résolu après vérification",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["resolved"] is True


@pytest.mark.asyncio
async def test_filter_by_category(client, commissaire_token):
    """Test filtrage par catégorie."""
    response = await client.get(
        "/api/v1/financial-entries/?category=CONTRIBUTION",
        headers={"Authorization": f"Bearer {commissaire_token}"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_filter_by_verification_status(client, commissaire_token):
    """Test filtrage par statut de vérification."""
    response = await client.get(
        "/api/v1/financial-entries/?verification_status=EN_ATTENTE",
        headers={"Authorization": f"Bearer {commissaire_token}"},
    )

    assert response.status_code == 200
