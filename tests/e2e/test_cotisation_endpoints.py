"""
Tests E2E du module Cotisations — contributions financieres.

Couvre :
- CRUD des periodes de cotisation
- Enregistrement de paiements
- Paiements supplementaires (cumul)
- Bilan financier
- Self-service (mes cotisations)
- Controle d'acces (RBAC)
"""
from datetime import datetime
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.cotisation import CotisationPeriod, MemberCotisation
from src.core.entities.user import User
from tests.conftest import make_auth_header

# ═══════════════════════════════════════════════════════════════════════════
#  PERIODES
# ═══════════════════════════════════════════════════════════════════════════


class TestCotisationPeriods:
    """Tests CRUD des periodes de cotisation."""

    @pytest.mark.asyncio
    async def test_create_period_success(self, client: AsyncClient, aumonier_user: User):
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Cotisation Fevrier 2026",
                "description": "Cotisation ordinaire du mois de fevrier.",
                "cotisation_type": "ORDINAIRE",
                "period_type": "MENSUEL",
                "amount_expected": 500.0,
                "start_date": "2026-02-01T00:00:00",
                "end_date": "2026-02-28T23:59:59",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Cotisation Fevrier 2026"
        assert body["amount_expected"] == 500.0
        assert body["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_period_invalid_dates(self, client: AsyncClient, aumonier_user: User):
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Dates invalides",
                "amount_expected": 100.0,
                "start_date": "2026-03-31T00:00:00",
                "end_date": "2026-03-01T00:00:00",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_periods(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_cotisation_period: CotisationPeriod,
    ):
        resp = await client.get(
            "/api/v1/cotisations/periods",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_get_period_detail(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_cotisation_period: CotisationPeriod,
    ):
        resp = await client.get(
            f"/api/v1/cotisations/periods/{sample_cotisation_period.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Cotisation Janvier 2026"

    @pytest.mark.asyncio
    async def test_update_period(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_cotisation_period: CotisationPeriod,
    ):
        resp = await client.patch(
            f"/api/v1/cotisations/periods/{sample_cotisation_period.id}",
            json={"title": "Cotisation Janvier Modifiee", "amount_expected": 1500.0},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Cotisation Janvier Modifiee"
        assert body["amount_expected"] == 1500.0

    @pytest.mark.asyncio
    async def test_delete_period(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_cotisation_period: CotisationPeriod,
    ):
        resp = await client.delete(
            f"/api/v1/cotisations/periods/{sample_cotisation_period.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_servant_cannot_create_period(self, client: AsyncClient, servant_user: User):
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Test non autorise",
                "amount_expected": 100.0,
                "start_date": "2026-01-01T00:00:00",
                "end_date": "2026-01-31T00:00:00",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  PAIEMENTS
# ═══════════════════════════════════════════════════════════════════════════


class TestCotisationPayments:
    """Tests pour l'enregistrement de paiements."""

    @pytest.mark.asyncio
    async def test_record_full_payment(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_cotisation_period: CotisationPeriod,
    ):
        resp = await client.post(
            "/api/v1/cotisations/payments",
            json={
                "period_id": str(sample_cotisation_period.id),
                "user_id": str(servant_user.id),
                "amount_paid": 1000.0,
                "payment_method": "Especes",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["amount_paid"] == 1000.0
        assert body["status"] == "PAYE"

    @pytest.mark.asyncio
    async def test_record_partial_payment(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_cotisation_period: CotisationPeriod,
    ):
        resp = await client.post(
            "/api/v1/cotisations/payments",
            json={
                "period_id": str(sample_cotisation_period.id),
                "user_id": str(servant_user.id),
                "amount_paid": 500.0,
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["amount_paid"] == 500.0
        assert body["status"] == "PAYE_PARTIELLEMENT"

    @pytest.mark.asyncio
    async def test_cumulative_payment(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_cotisation_period: CotisationPeriod,
    ):
        """Le 2eme paiement s'ajoute au premier."""
        # Premier paiement partiel
        resp1 = await client.post(
            "/api/v1/cotisations/payments",
            json={
                "period_id": str(sample_cotisation_period.id),
                "user_id": str(servant_user.id),
                "amount_paid": 600.0,
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp1.status_code == 201
        assert resp1.json()["status"] == "PAYE_PARTIELLEMENT"

        # Deuxieme paiement (cumul → 600 + 500 = 1100 ≥ 1000)
        resp2 = await client.post(
            "/api/v1/cotisations/payments",
            json={
                "period_id": str(sample_cotisation_period.id),
                "user_id": str(servant_user.id),
                "amount_paid": 500.0,
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp2.status_code == 201
        body = resp2.json()
        assert body["amount_paid"] == 1100.0
        assert body["status"] == "PAYE"

    @pytest.mark.asyncio
    async def test_get_period_payments(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_cotisation_period: CotisationPeriod,
        sample_member_cotisation: MemberCotisation,
    ):
        resp = await client.get(
            f"/api/v1/cotisations/periods/{sample_cotisation_period.id}/payments",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1

    @pytest.mark.asyncio
    async def test_get_my_cotisations(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_member_cotisation: MemberCotisation,
    ):
        resp = await client.get(
            "/api/v1/cotisations/my",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1


# ═══════════════════════════════════════════════════════════════════════════
#  BILAN
# ═══════════════════════════════════════════════════════════════════════════


class TestCotisationBilan:
    """Tests du bilan financier."""

    @pytest.mark.asyncio
    async def test_get_bilan(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_cotisation_period: CotisationPeriod,
        sample_member_cotisation: MemberCotisation,
    ):
        resp = await client.get(
            f"/api/v1/cotisations/periods/{sample_cotisation_period.id}/bilan",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "period" in body
        assert "payments" in body
        assert "total_expected" in body
        assert "total_collected" in body
        assert "taux_recouvrement" in body
