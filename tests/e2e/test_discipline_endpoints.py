"""
Tests E2E du module Discipline — workflow complet.

Couvre :
- Ouverture de dossier
- Workflow : Signale → Convoque → En_audience → Verdict → Execute
- Classement sans suite
- Listing et stats
- Controle d'acces (RBAC)
"""
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import VALID_PASSWORD, make_auth_header

# ═══════════════════════════════════════════════════════════════════════════
#  OUVERTURE DE DOSSIER
# ═══════════════════════════════════════════════════════════════════════════


class TestOpenDisciplineCase:
    """Tests pour l'ouverture de dossiers disciplinaires."""

    @pytest.mark.asyncio
    async def test_open_case_success(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        resp = await client.post(
            "/api/v1/discipline/",
            json={
                "accused_user_id": str(servant_user.id),
                "offense_category": "ABSENCE_NON_JUSTIFIEE",
                "offense_description": "Absent a la messe dominicale du 1er mars sans prevenir.",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "SIGNALE"
        assert body["accused_user_id"] == str(servant_user.id)
        assert body["offense_category"] == "ABSENCE_NON_JUSTIFIEE"
        assert body["severity"] == "MOYEN"  # Default for ABSENCE_NON_JUSTIFIEE

    @pytest.mark.asyncio
    async def test_open_case_with_custom_severity(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        resp = await client.post(
            "/api/v1/discipline/",
            json={
                "accused_user_id": str(servant_user.id),
                "offense_category": "RETARD_REPETE",
                "offense_description": "Retards repetes lors des 4 dernieres messes.",
                "severity": "MOYEN",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        assert resp.json()["severity"] == "MOYEN"

    @pytest.mark.asyncio
    async def test_open_case_non_servant_rejected(
        self, client: AsyncClient, aumonier_user: User, parent_user: User
    ):
        resp = await client.post(
            "/api/v1/discipline/",
            json={
                "accused_user_id": str(parent_user.id),
                "offense_category": "INSUBORDINATION",
                "offense_description": "Tentative de test sur un parent.",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_open_case_servant_forbidden(
        self, client: AsyncClient, servant_user: User
    ):
        """Un servant ne peut pas ouvrir de dossier."""
        resp = await client.post(
            "/api/v1/discipline/",
            json={
                "accused_user_id": str(servant_user.id),
                "offense_category": "RETARD_REPETE",
                "offense_description": "Test non autorise.",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  WORKFLOW COMPLET : SIGNALE → CONVOQUE → EN_AUDIENCE → VERDICT → EXECUTE
# ═══════════════════════════════════════════════════════════════════════════


class TestDisciplineWorkflow:
    """Tests du workflow disciplinaire complet."""

    async def _open_case(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ) -> dict:
        resp = await client.post(
            "/api/v1/discipline/",
            json={
                "accused_user_id": str(servant_user.id),
                "offense_category": "INSUBORDINATION",
                "offense_description": "Refus d'obeir aux instructions du ceremoniaire.",
                "severity": "GRAVE",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        return resp.json()

    @pytest.mark.asyncio
    async def test_full_workflow_with_suspension(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        case = await self._open_case(client, aumonier_user, servant_user)
        case_id = case["id"]

        # Convoquer
        convocation_date = (datetime.now() + timedelta(days=3)).isoformat()
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/convoke",
            json={
                "convocation_date": convocation_date,
                "convocation_notes": "Presence obligatoire au conseil.",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CONVOQUE"

        # Ouvrir audience
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/hearing",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "EN_AUDIENCE"

        # Verdict : suspension
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/verdict",
            json={
                "sanction_type": "SUSPENSION_TEMPORAIRE",
                "verdict_notes": "Suspension de 15 jours pour insubordination.",
                "suspension_days": 15,
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "VERDICT_RENDU"
        assert body["sanction_type"] == "SUSPENSION_TEMPORAIRE"
        assert body["suspension_days"] == 15

        # Executer
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/execute",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "EXECUTE"

    @pytest.mark.asyncio
    async def test_workflow_dismiss_case(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        case = await self._open_case(client, aumonier_user, servant_user)
        case_id = case["id"]

        # Classer sans suite
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/dismiss",
            params={"notes": "Pas de preuves suffisantes."},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "CLASSE"
        assert body["sanction_type"] == "AUCUNE"

    @pytest.mark.asyncio
    async def test_invalid_workflow_transition(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        case = await self._open_case(client, aumonier_user, servant_user)
        case_id = case["id"]

        # Essayer d'ouvrir une audience sans convoquer d'abord
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/hearing",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_execute_without_verdict(
        self, client: AsyncClient, aumonier_user: User, servant_user: User
    ):
        case = await self._open_case(client, aumonier_user, servant_user)
        case_id = case["id"]

        resp = await client.post(
            f"/api/v1/discipline/{case_id}/execute",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════
#  LECTURE ET STATS
# ═══════════════════════════════════════════════════════════════════════════


class TestDisciplineRead:
    """Tests de lecture et statistiques."""

    @pytest.mark.asyncio
    async def test_list_cases(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_discipline_case,
    ):
        resp = await client.get(
            "/api/v1/discipline/",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["items"]) >= 1

    @pytest.mark.asyncio
    async def test_get_case_detail(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_discipline_case,
    ):
        resp = await client.get(
            f"/api/v1/discipline/{sample_discipline_case.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_discipline_case.id)
        assert body["offense_category"] == "ABSENCE_NON_JUSTIFIEE"

    @pytest.mark.asyncio
    async def test_get_case_not_found(self, client: AsyncClient, aumonier_user: User):
        resp = await client.get(
            f"/api/v1/discipline/{uuid4()}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_user_stats(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_discipline_case,
    ):
        resp = await client.get(
            f"/api/v1/discipline/user/{servant_user.id}/stats",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["user_id"] == str(servant_user.id)
        assert body["total_cases"] >= 1
