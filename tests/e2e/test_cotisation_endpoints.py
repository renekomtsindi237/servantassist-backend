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
from src.core.entities.servant_parent import ServantParent
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
            json={"title": "Cotisation Janvier Modifiee"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["title"] == "Cotisation Janvier Modifiee"

    @pytest.mark.asyncio
    async def test_update_period_wrong_fixed_amount_rejected(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_cotisation_period: CotisationPeriod,
    ):
        """ORDINAIRE/MENSUEL doit rester a 500 FCFA (Art. 22)."""
        resp = await client.patch(
            f"/api/v1/cotisations/periods/{sample_cotisation_period.id}",
            json={"amount_expected": 1500.0},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

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
    async def test_create_period_ordinaire_mensuel_wrong_amount_rejected(
        self, client: AsyncClient, aumonier_user: User
    ):
        """ORDINAIRE/MENSUEL doit valoir exactement 500 FCFA (Art. 22)."""
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Cotisation mars 2026",
                "cotisation_type": "ORDINAIRE",
                "period_type": "MENSUEL",
                "amount_expected": 400.0,
                "start_date": "2026-03-01T00:00:00",
                "end_date": "2026-03-31T00:00:00",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_period_ordinaire_hebdomadaire_correct_amount(
        self, client: AsyncClient, aumonier_user: User
    ):
        """ORDINAIRE/HEBDOMADAIRE doit valoir exactement 100 FCFA (Art. 22)."""
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Cotisation samedi 7 mars",
                "cotisation_type": "ORDINAIRE",
                "period_type": "HEBDOMADAIRE",
                "amount_expected": 100.0,
                "start_date": "2026-03-07T00:00:00",
                "end_date": "2026-03-07T23:59:59",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        assert resp.json()["amount_expected"] == 100.0

    @pytest.mark.asyncio
    async def test_create_period_aube_free_amount(self, client: AsyncClient, aumonier_user: User):
        """La cotisation AUBE (Art. 21) reste a montant libre."""
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Cotisation aubes 2026",
                "cotisation_type": "AUBE",
                "period_type": "ANNUEL",
                "amount_expected": 3000.0,
                "start_date": "2026-08-01T00:00:00",
                "end_date": "2027-07-31T23:59:59",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        assert resp.json()["amount_expected"] == 3000.0

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
#  OBLIGATION AUTOMATIQUE (Art. 22 — cotisation obligatoire, sans negociation)
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.e2e
class TestCotisationObligation:
    """Obligation automatique de cotisation pour les servants non-responsables."""

    async def test_ordinaire_period_creates_obligation_for_free_servants(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        servant_user_2: User,
    ):
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Cotisation Avril 2026",
                "cotisation_type": "ORDINAIRE",
                "period_type": "MENSUEL",
                "amount_expected": 500.0,
                "start_date": "2026-04-01T00:00:00",
                "end_date": "2026-04-30T23:59:59",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        period_id = resp.json()["id"]

        payments_resp = await client.get(
            f"/api/v1/cotisations/periods/{period_id}/payments",
            headers=make_auth_header(aumonier_user),
        )
        assert payments_resp.status_code == 200
        payments = payments_resp.json()
        by_user = {p["user_id"]: p for p in payments}

        assert str(servant_user.id) in by_user
        assert str(servant_user_2.id) in by_user
        assert by_user[str(servant_user.id)]["status"] == "EN_ATTENTE"
        assert by_user[str(servant_user.id)]["amount_paid"] == 0.0

    async def test_ordinaire_period_exempts_responsable(
        self,
        client: AsyncClient,
        aumonier_user: User,
        econome_user: User,
    ):
        """Un servant titulaire d'un poste (ex. Econome) n'a pas d'obligation automatique."""
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Cotisation Mai 2026",
                "cotisation_type": "ORDINAIRE",
                "period_type": "MENSUEL",
                "amount_expected": 500.0,
                "start_date": "2026-05-01T00:00:00",
                "end_date": "2026-05-31T23:59:59",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        period_id = resp.json()["id"]

        payments_resp = await client.get(
            f"/api/v1/cotisations/periods/{period_id}/payments",
            headers=make_auth_header(aumonier_user),
        )
        assert payments_resp.status_code == 200
        payer_ids = {p["user_id"] for p in payments_resp.json()}
        assert str(econome_user.id) not in payer_ids

    async def test_speciale_period_creates_obligation_for_free_servants(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """Art. 23 : le camp spirituel est obligatoire pour tous les servants."""
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Camp spirituel 2026",
                "cotisation_type": "SPECIALE",
                "period_type": "EVENEMENT",
                "amount_expected": 15000.0,
                "start_date": "2026-07-01T00:00:00",
                "end_date": "2026-08-15T23:59:59",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        period_id = resp.json()["id"]

        payments_resp = await client.get(
            f"/api/v1/cotisations/periods/{period_id}/payments",
            headers=make_auth_header(aumonier_user),
        )
        assert payments_resp.status_code == 200
        payments = payments_resp.json()
        by_user = {p["user_id"]: p for p in payments}
        assert str(servant_user.id) in by_user
        assert by_user[str(servant_user.id)]["status"] == "EN_ATTENTE"

    async def test_aube_period_creates_obligation_for_free_servants(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """Art. 21 : la cotisation aube est obligatoire pour les nouveaux et les anciens."""
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Cotisation aubes 2026",
                "cotisation_type": "AUBE",
                "period_type": "ANNUEL",
                "amount_expected": 3000.0,
                "start_date": "2026-08-01T00:00:00",
                "end_date": "2027-07-31T23:59:59",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        period_id = resp.json()["id"]

        payments_resp = await client.get(
            f"/api/v1/cotisations/periods/{period_id}/payments",
            headers=make_auth_header(aumonier_user),
        )
        assert payments_resp.status_code == 200
        payer_ids = {p["user_id"] for p in payments_resp.json()}
        assert str(servant_user.id) in payer_ids

    async def test_amende_period_creates_no_obligation(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """Une amende est une penalite individuelle, pas une obligation pour tous."""
        resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Amende retard",
                "cotisation_type": "AMENDE",
                "period_type": "PONCTUEL",
                "amount_expected": 1000.0,
                "start_date": "2026-07-01T00:00:00",
                "end_date": "2026-07-02T00:00:00",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        period_id = resp.json()["id"]

        payments_resp = await client.get(
            f"/api/v1/cotisations/periods/{period_id}/payments",
            headers=make_auth_header(aumonier_user),
        )
        assert payments_resp.status_code == 200
        assert payments_resp.json() == []


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
    async def test_cannot_cumulate_mensuel_and_hebdomadaire(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        """Un servant ne peut pas cumuler mensuel et hebdomadaire sur la meme periode (Art. 22)."""
        mensuel_resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Cotisation mars 2026 (mensuel)",
                "cotisation_type": "ORDINAIRE",
                "period_type": "MENSUEL",
                "amount_expected": 500.0,
                "start_date": "2026-03-01T00:00:00",
                "end_date": "2026-03-31T00:00:00",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert mensuel_resp.status_code == 201
        mensuel_id = mensuel_resp.json()["id"]

        hebdo_resp = await client.post(
            "/api/v1/cotisations/periods",
            json={
                "title": "Cotisation samedi 7 mars (hebdo)",
                "cotisation_type": "ORDINAIRE",
                "period_type": "HEBDOMADAIRE",
                "amount_expected": 100.0,
                "start_date": "2026-03-07T00:00:00",
                "end_date": "2026-03-07T23:59:59",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert hebdo_resp.status_code == 201
        hebdo_id = hebdo_resp.json()["id"]

        pay_mensuel = await client.post(
            "/api/v1/cotisations/payments",
            json={"period_id": mensuel_id, "user_id": str(servant_user.id), "amount_paid": 500.0},
            headers=make_auth_header(aumonier_user),
        )
        assert pay_mensuel.status_code == 201

        pay_hebdo = await client.post(
            "/api/v1/cotisations/payments",
            json={"period_id": hebdo_id, "user_id": str(servant_user.id), "amount_paid": 100.0},
            headers=make_auth_header(aumonier_user),
        )
        assert pay_hebdo.status_code == 409

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


# ═══════════════════════════════════════════════════════════════════════════
#  CONFORMITE (Art. 48, 50)
# ═══════════════════════════════════════════════════════════════════════════


class TestCotisationCompliance:
    """Tests de la conformite des cotisations ordinaires."""

    @pytest.mark.asyncio
    async def test_get_compliance_up_to_date(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_cotisation_period: CotisationPeriod,
        sample_member_cotisation: MemberCotisation,
    ):
        resp = await client.get(
            f"/api/v1/cotisations/servant/{servant_user.id}/compliance",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == str(servant_user.id)
        assert "needs_parent_convocation" in body
        assert "flagged_for_radiation" in body


# ═══════════════════════════════════════════════════════════════════════════
#  HISTORIQUE D'UN SERVANT (self / parent lie / econome / admin / aumonier)
# ═══════════════════════════════════════════════════════════════════════════


class TestServantCotisationHistory:
    """Tests de GET /cotisations/servant/{id} — controle d'acces."""

    @pytest.mark.asyncio
    async def test_servant_can_view_own_history(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_member_cotisation: MemberCotisation,
    ):
        resp = await client.get(
            f"/api/v1/cotisations/servant/{servant_user.id}",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) == 1
        assert body[0]["user_id"] == str(servant_user.id)

    @pytest.mark.asyncio
    async def test_linked_parent_can_view_child_history(
        self,
        client: AsyncClient,
        parent_user: User,
        servant_user: User,
        sample_member_cotisation: MemberCotisation,
        db_session,
    ):
        link = ServantParent(servant_id=servant_user.id, parent_id=parent_user.id)
        db_session.add(link)
        await db_session.commit()

        resp = await client.get(
            f"/api/v1/cotisations/servant/{servant_user.id}",
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1

    @pytest.mark.asyncio
    async def test_unlinked_parent_gets_403(
        self,
        client: AsyncClient,
        parent_user: User,
        servant_user: User,
        sample_member_cotisation: MemberCotisation,
    ):
        # Aucun lien ServantParent cree : parent_user n'est pas le parent de servant_user.
        resp = await client.get(
            f"/api/v1/cotisations/servant/{servant_user.id}",
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_econome_can_view_any_servant_history(
        self,
        client: AsyncClient,
        econome_user: User,
        servant_user: User,
        sample_member_cotisation: MemberCotisation,
    ):
        resp = await client.get(
            f"/api/v1/cotisations/servant/{servant_user.id}",
            headers=make_auth_header(econome_user),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_admin_and_aumonier_can_view_any_servant_history(
        self,
        client: AsyncClient,
        admin_user: User,
        aumonier_user: User,
        servant_user: User,
        sample_member_cotisation: MemberCotisation,
    ):
        for user in (admin_user, aumonier_user):
            resp = await client.get(
                f"/api/v1/cotisations/servant/{servant_user.id}",
                headers=make_auth_header(user),
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_unrelated_servant_gets_403(
        self,
        client: AsyncClient,
        servant_user: User,
        servant_user_2: User,
        sample_member_cotisation: MemberCotisation,
    ):
        resp = await client.get(
            f"/api/v1/cotisations/servant/{servant_user.id}",
            headers=make_auth_header(servant_user_2),
        )
        assert resp.status_code == 403
