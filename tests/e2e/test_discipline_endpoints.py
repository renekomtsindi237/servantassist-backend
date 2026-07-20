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
    async def test_open_case_success(self, client: AsyncClient, aumonier_user: User, servant_user: User):
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
    async def test_open_case_with_custom_severity(self, client: AsyncClient, aumonier_user: User, servant_user: User):
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
    async def test_open_case_non_servant_rejected(self, client: AsyncClient, aumonier_user: User, parent_user: User):
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
    async def test_open_case_servant_forbidden(self, client: AsyncClient, servant_user: User):
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

    @pytest.mark.asyncio
    async def test_ceremoniaire_can_open_case_for_trouble_during_mass(
        self,
        client: AsyncClient,
        ceremoniaire_user: User,
        servant_user: User,
    ):
        """Art. 41 : le Ceremoniaire peut ouvrir un dossier pour trouble durant la messe."""
        resp = await client.post(
            "/api/v1/discipline/",
            json={
                "accused_user_id": str(servant_user.id),
                "offense_category": "BAVARDAGE_PENDANT_SERVICE",
                "offense_description": "A parle fort durant la celebration eucharistique.",
            },
            headers=make_auth_header(ceremoniaire_user),
        )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_econome_cannot_open_case(
        self,
        client: AsyncClient,
        econome_user: User,
        servant_user: User,
    ):
        """Un poste sans lien avec la discipline ne peut pas ouvrir de dossier."""
        resp = await client.post(
            "/api/v1/discipline/",
            json={
                "accused_user_id": str(servant_user.id),
                "offense_category": "RETARD_REPETE",
                "offense_description": "Test non autorise.",
            },
            headers=make_auth_header(econome_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  WORKFLOW COMPLET : SIGNALE → CONVOQUE → EN_AUDIENCE → VERDICT → EXECUTE
# ═══════════════════════════════════════════════════════════════════════════


class TestDisciplineWorkflow:
    """Tests du workflow disciplinaire complet."""

    async def _open_case(self, client: AsyncClient, aumonier_user: User, servant_user: User) -> dict:
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
    async def test_delegue_can_convoke_council(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        delegue_user: User,
    ):
        """Art. 16 : le conseil de discipline se reunit sous convocation du Delegue."""
        case = await self._open_case(client, aumonier_user, servant_user)
        convocation_date = (datetime.now() + timedelta(days=3)).isoformat()
        resp = await client.post(
            f"/api/v1/discipline/{case['id']}/convoke",
            json={
                "convocation_date": convocation_date,
                "convocation_notes": "Convocation par le Delegue.",
            },
            headers=make_auth_header(delegue_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "CONVOQUE"

    @pytest.mark.asyncio
    async def test_econome_cannot_convoke_council(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        econome_user: User,
    ):
        case = await self._open_case(client, aumonier_user, servant_user)
        convocation_date = (datetime.now() + timedelta(days=3)).isoformat()
        resp = await client.post(
            f"/api/v1/discipline/{case['id']}/convoke",
            json={
                "convocation_date": convocation_date,
                "convocation_notes": "Ne devrait pas passer.",
            },
            headers=make_auth_header(econome_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_full_workflow_with_suspension(self, client: AsyncClient, aumonier_user: User, servant_user: User):
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
    async def test_workflow_dismiss_case(self, client: AsyncClient, aumonier_user: User, servant_user: User):
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
    async def test_invalid_workflow_transition(self, client: AsyncClient, aumonier_user: User, servant_user: User):
        case = await self._open_case(client, aumonier_user, servant_user)
        case_id = case["id"]

        # Essayer d'ouvrir une audience sans convoquer d'abord
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/hearing",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_cannot_execute_without_verdict(self, client: AsyncClient, aumonier_user: User, servant_user: User):
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


# ═══════════════════════════════════════════════════════════════════════════
#  CONSEIL DE DISCIPLINE — VOTE COLLEGIAL (Art. 16-17)
# ═══════════════════════════════════════════════════════════════════════════


class TestDisciplineCouncilVote:
    """Vote collegial des 7 sieges du conseil de discipline."""

    async def _open_case(self, client: AsyncClient, aumonier_user: User, servant_user: User) -> str:
        resp = await client.post(
            "/api/v1/discipline/",
            json={
                "accused_user_id": str(servant_user.id),
                "offense_category": "INSUBORDINATION",
                "offense_description": "Refus d'obeir aux instructions du responsable.",
                "severity": "GRAVE",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    @pytest.mark.asyncio
    async def test_single_vote_does_not_render_verdict(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        delegue_user: User,
        vice_delegue_user: User,
        secretaire_user: User,
    ):
        """3 sieges pourvus (majorite=2) : un seul vote ne suffit pas."""
        case_id = await self._open_case(client, aumonier_user, servant_user)
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/votes",
            json={"sanction_type": "SUSPENSION_TEMPORAIRE"},
            headers=make_auth_header(delegue_user),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "SIGNALE"

    @pytest.mark.asyncio
    async def test_majority_of_filled_seats_renders_verdict(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        delegue_user: User,
        vice_delegue_user: User,
        secretaire_user: User,
        secretaire_adjoint_user: User,
        censeur_user: User,
        ceremoniaire_user: User,
    ):
        """
        6 des 7 sieges sont pourvus (CENSEUR_ADJOINT vacant) -> majorite = 4.
        4 votes identiques suffisent, un siege vacant ne bloque pas le quorum.
        """
        case_id = await self._open_case(client, aumonier_user, servant_user)

        for voter in (delegue_user, vice_delegue_user, secretaire_user):
            resp = await client.post(
                f"/api/v1/discipline/{case_id}/votes",
                json={"sanction_type": "SUSPENSION_TEMPORAIRE"},
                headers=make_auth_header(voter),
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == "SIGNALE"

        # 4e vote identique -> majorite atteinte (4/6)
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/votes",
            json={"sanction_type": "SUSPENSION_TEMPORAIRE"},
            headers=make_auth_header(secretaire_adjoint_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "VERDICT_RENDU"
        assert body["sanction_type"] == "SUSPENSION_TEMPORAIRE"

    @pytest.mark.asyncio
    async def test_revote_overwrites_previous_choice(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        delegue_user: User,
        vice_delegue_user: User,
        secretaire_user: User,
    ):
        """3 sieges pourvus (majorite=2) : le revote du seul votant ne suffit
        pas a decider, donc le dossier reste modifiable pour verifier l'ecrasement."""
        case_id = await self._open_case(client, aumonier_user, servant_user)
        await client.post(
            f"/api/v1/discipline/{case_id}/votes",
            json={"sanction_type": "AVERTISSEMENT_VERBAL"},
            headers=make_auth_header(delegue_user),
        )
        await client.post(
            f"/api/v1/discipline/{case_id}/votes",
            json={"sanction_type": "SUSPENSION_TEMPORAIRE"},
            headers=make_auth_header(delegue_user),
        )
        resp = await client.get(
            f"/api/v1/discipline/{case_id}/votes",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["votes"]) == 1
        assert body["votes"][0]["sanction_type"] == "SUSPENSION_TEMPORAIRE"

    @pytest.mark.asyncio
    async def test_non_council_member_cannot_vote(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        servant_user_2: User,
    ):
        """Un servant sans siege au conseil de discipline ne peut pas voter."""
        case_id = await self._open_case(client, aumonier_user, servant_user)
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/votes",
            json={"sanction_type": "SUSPENSION_TEMPORAIRE"},
            headers=make_auth_header(servant_user_2),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_and_aumonier_cannot_vote(
        self,
        client: AsyncClient,
        aumonier_user: User,
        admin_user: User,
        servant_user: User,
    ):
        """L'Aumonier et l'Admin supervisent le conseil mais n'y siegent pas."""
        case_id = await self._open_case(client, aumonier_user, servant_user)
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/votes",
            json={"sanction_type": "SUSPENSION_TEMPORAIRE"},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 403

        resp = await client.post(
            f"/api/v1/discipline/{case_id}/votes",
            json={"sanction_type": "SUSPENSION_TEMPORAIRE"},
            headers=make_auth_header(admin_user),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_censeur_can_render_verdict_directly(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        censeur_user: User,
    ):
        """Le Censeur peut prononcer une sanction directement (Art. 39-44), y compris une suspension."""
        case_id = await self._open_case(client, aumonier_user, servant_user)
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/verdict",
            json={"sanction_type": "SUSPENSION_TEMPORAIRE", "suspension_days": 15},
            headers=make_auth_header(censeur_user),
        )
        assert resp.status_code == 200
        assert resp.json()["sanction_type"] == "SUSPENSION_TEMPORAIRE"

    async def test_censeur_can_pronounce_radiation(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        censeur_user: User,
    ):
        """Le Censeur peut prononcer une radiation seul (Art. 51)."""
        case_id = await self._open_case(client, aumonier_user, servant_user)
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/verdict",
            json={"sanction_type": "EXCLUSION_DEFINITIVE"},
            headers=make_auth_header(censeur_user),
        )
        assert resp.status_code == 200
        assert resp.json()["sanction_type"] == "EXCLUSION_DEFINITIVE"

    async def test_censeur_adjoint_cannot_pronounce_radiation(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        censeur_adjoint_user: User,
    ):
        """L'Art. 51 ne nomme que le Censeur titulaire (pas l'adjoint) pour la radiation."""
        case_id = await self._open_case(client, aumonier_user, servant_user)
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/verdict",
            json={"sanction_type": "EXCLUSION_DEFINITIVE"},
            headers=make_auth_header(censeur_adjoint_user),
        )
        assert resp.status_code == 403

    async def test_secretaire_general_can_only_pronounce_radiation(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        secretaire_user: User,
    ):
        """Le Secretaire General peut prononcer une radiation (Art. 51), mais rien d'autre."""
        case_id = await self._open_case(client, aumonier_user, servant_user)

        resp_minor = await client.post(
            f"/api/v1/discipline/{case_id}/verdict",
            json={"sanction_type": "AVERTISSEMENT_VERBAL"},
            headers=make_auth_header(secretaire_user),
        )
        assert resp_minor.status_code == 403

        resp_radiation = await client.post(
            f"/api/v1/discipline/{case_id}/verdict",
            json={"sanction_type": "EXCLUSION_DEFINITIVE"},
            headers=make_auth_header(secretaire_user),
        )
        assert resp_radiation.status_code == 200

    async def test_ceremoniaire_can_only_pronounce_minor_sanction(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        ceremoniaire_user: User,
    ):
        """Le Ceremoniaire sanctionne un trouble en messe (Art. 41), pas une radiation/suspension."""
        case_id = await self._open_case(client, aumonier_user, servant_user)

        resp_major = await client.post(
            f"/api/v1/discipline/{case_id}/verdict",
            json={"sanction_type": "SUSPENSION_TEMPORAIRE", "suspension_days": 7},
            headers=make_auth_header(ceremoniaire_user),
        )
        assert resp_major.status_code == 403

        resp_minor = await client.post(
            f"/api/v1/discipline/{case_id}/verdict",
            json={"sanction_type": "AVERTISSEMENT_ECRIT"},
            headers=make_auth_header(ceremoniaire_user),
        )
        assert resp_minor.status_code == 200

    async def test_econome_cannot_render_verdict(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        econome_user: User,
    ):
        """Un poste sans lien avec la discipline n'a aucun acces a /verdict."""
        case_id = await self._open_case(client, aumonier_user, servant_user)
        resp = await client.post(
            f"/api/v1/discipline/{case_id}/verdict",
            json={"sanction_type": "AVERTISSEMENT_VERBAL"},
            headers=make_auth_header(econome_user),
        )
        assert resp.status_code == 403
