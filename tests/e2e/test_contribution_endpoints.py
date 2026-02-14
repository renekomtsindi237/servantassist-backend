"""
Tests end-to-end pour les endpoints de contributions (ECONOME).
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import status
from httpx import AsyncClient

from src.core.entities.contribution import PaymentMode
from src.core.entities.user import UserRole


@pytest.mark.asyncio
class TestContributionEndpoints:
    """Tests des endpoints de contributions."""

    async def test_record_payment_as_econome(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : L'ECONOME peut enregistrer un paiement."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
                "notes": "Paiement février 2026",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["amount"] == 500.0
        assert data["payment_mode"] == "MENSUEL"
        assert data["month"] == 2
        assert data["year"] == 2026

    async def test_record_weekly_payment(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Enregistrer un paiement hebdomadaire."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 100.0,
                "payment_mode": "HEBDOMADAIRE",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
                "week_number": 1,
                "notes": "Semaine 1",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["amount"] == 100.0
        assert data["payment_mode"] == "HEBDOMADAIRE"
        assert data["week_number"] == 1

    async def test_record_payment_invalid_amount_weekly(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Montant invalide pour paiement hebdomadaire."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 200.0,  # Devrait être 100
                "payment_mode": "HEBDOMADAIRE",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
                "week_number": 1,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_record_payment_invalid_amount_monthly(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Montant invalide pour paiement mensuel."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 400.0,  # Devrait être 500
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_record_payment_missing_week_number(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : week_number manquant pour paiement hebdomadaire."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 100.0,
                "payment_mode": "HEBDOMADAIRE",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
                # week_number manquant
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_record_payment_as_servant_forbidden(
        self, client: AsyncClient, servant_token: str, servant_user_id: str
    ):
        """Test : Un SERVANT ne peut pas enregistrer de paiement."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {servant_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_list_contributions(
        self, client: AsyncClient, econome_token: str
    ):
        """Test : Lister les contributions."""
        response = await client.get(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
        )
        if response.status_code != 200: print(f"ERROR: {response.json()}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    async def test_list_contributions_with_filters(
        self, client: AsyncClient, econome_token: str
    ):
        """Test : Lister avec filtres."""
        response = await client.get(
            "/api/v1/contributions/?month=2&year=2026&payment_mode=MENSUEL",
            headers={"Authorization": f"Bearer {econome_token}"},
        )
        if response.status_code != 200: print(f"ERROR: {response.json()}")
        assert response.status_code == status.HTTP_200_OK

    async def test_get_contribution(
        self, client: AsyncClient, econome_token: str, contribution_id: str
    ):
        """Test : Récupérer une contribution."""
        response = await client.get(
            f"/api/v1/contributions/{contribution_id}",
            headers={"Authorization": f"Bearer {econome_token}"},
        )
        if response.status_code != 200: print(f"ERROR: {response.json()}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == contribution_id

    async def test_get_contribution_not_found(
        self, client: AsyncClient, econome_token: str
    ):
        """Test : Contribution introuvable."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/contributions/{fake_id}",
            headers={"Authorization": f"Bearer {econome_token}"},
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_contribution(
        self, client: AsyncClient, econome_token: str, contribution_id: str
    ):
        """Test : Modifier une contribution."""
        response = await client.patch(
            f"/api/v1/contributions/{contribution_id}",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={"notes": "Note modifiée"},
        )
        if response.status_code != 200: print(f"ERROR: {response.json()}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["notes"] == "Note modifiée"

    async def test_delete_contribution(
        self, client: AsyncClient, econome_token: str, contribution_id: str
    ):
        """Test : Supprimer une contribution."""
        response = await client.delete(
            f"/api/v1/contributions/{contribution_id}",
            headers={"Authorization": f"Bearer {econome_token}"},
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

    async def test_get_servant_contributions(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Récupérer les contributions d'un servant."""
        response = await client.get(
            f"/api/v1/contributions/servant/{servant_user_id}",
            headers={"Authorization": f"Bearer {econome_token}"},
        )
        if response.status_code != 200: print(f"ERROR: {response.json()}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    async def test_get_servant_stats(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Récupérer les statistiques d'un servant."""
        start_date = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat()
        end_date = datetime(2026, 12, 31, tzinfo=timezone.utc).isoformat()
        
        response = await client.get(
            f"/api/v1/contributions/servant/{servant_user_id}/stats",
            headers={"Authorization": f"Bearer {econome_token}"},
            params={"start_date": start_date, "end_date": end_date},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "servant_id" in data
        assert "total_expected" in data
        assert "total_paid" in data
        assert "payment_rate" in data

    async def test_get_monthly_summary(
        self, client: AsyncClient, econome_token: str
    ):
        """Test : Récupérer le résumé mensuel."""
        response = await client.get(
            "/api/v1/contributions/summary/2/2026",
            headers={"Authorization": f"Bearer {econome_token}"},
        )
        if response.status_code != 200: print(f"ERROR: {response.json()}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)

    async def test_generate_financial_report(
        self, client: AsyncClient, econome_token: str
    ):
        """Test : Générer un rapport financier."""
        response = await client.post(
            "/api/v1/contributions/report",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=timezone.utc).isoformat(),
            },
        )
        if response.status_code != 200: print(f"ERROR: {response.json()}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "total_expected" in data
        assert "total_collected" in data
        assert "collection_rate" in data
        assert "servants_paid" in data
        assert "servants_late" in data
        assert "watermark_logo" in data
        assert data["watermark_logo"] == "logo_servant.jpeg"

    async def test_generate_report_with_servant_filter(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Générer un rapport filtré par servants."""
        response = await client.post(
            "/api/v1/contributions/report",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=timezone.utc).isoformat(),
                "servant_ids": [servant_user_id],
            },
        )
        if response.status_code != 200: print(f"ERROR: {response.json()}")
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
class TestContributionPermissions:
    """Tests des permissions pour les contributions."""

    async def test_admin_can_manage_contributions(
        self, client: AsyncClient, admin_token: str, servant_user_id: str
    ):
        """Test : L'ADMIN peut gérer les contributions."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_aumonier_can_manage_contributions(
        self, client: AsyncClient, aumonier_token: str, servant_user_id: str
    ):
        """Test : L'AUMÔNIER peut gérer les contributions."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {aumonier_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED

    async def test_servant_can_view_own_contributions(
        self, client: AsyncClient, servant_token: str, servant_user_id: str
    ):
        """Test : Un SERVANT peut consulter ses propres contributions."""
        response = await client.get(
            f"/api/v1/contributions/servant/{servant_user_id}",
            headers={"Authorization": f"Bearer {servant_token}"},
        )
        if response.status_code != 200: print(f"ERROR: {response.json()}")
        assert response.status_code == status.HTTP_200_OK

    async def test_servant_cannot_create_contribution(
        self, client: AsyncClient, servant_token: str, servant_user_id: str
    ):
        """Test : Un SERVANT ne peut pas créer de contribution."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {servant_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_unauthenticated_cannot_access(
        self, client: AsyncClient
    ):
        """Test : Accès non authentifié refusé."""
        response = await client.get("/api/v1/contributions/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
class TestContributionBusinessRules:
    """Tests des règles métier des contributions."""

    async def test_weekly_payment_requires_week_number(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Paiement hebdomadaire nécessite week_number."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 100.0,
                "payment_mode": "HEBDOMADAIRE",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
                # week_number manquant
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_monthly_payment_no_week_number(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Paiement mensuel ne doit pas avoir week_number."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
                "week_number": 1,  # Ne devrait pas être fourni
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_amount_must_be_positive(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Le montant doit être positif."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": -100.0,  # Négatif
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_month_must_be_valid(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Le mois doit être entre 1 et 12."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 13,  # Invalide
                "year": 2026,
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_servant_must_exist(
        self, client: AsyncClient, econome_token: str
    ):
        """Test : Le servant doit exister."""
        fake_servant_id = str(uuid4())
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": fake_servant_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND
