"""
Tests E2E du module Convocation — convocation formelle des parents (Art. 48-49).
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import make_auth_header


@pytest.mark.e2e
class TestCreateConvocation:
    """Convocation manuelle des parents d'un servant."""

    async def test_censeur_creates_convocation(
        self,
        client: AsyncClient,
        censeur_user: User,
        servant_user: User,
    ):
        resp = await client.post(
            "/api/v1/convocations/",
            json={
                "servant_id": str(servant_user.id),
                "motif": "ABSENCES_REPETEES",
                "details": "2 mois d'absence non justifiee.",
            },
            headers=make_auth_header(censeur_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["servant_id"] == str(servant_user.id)
        assert body["motif"] == "ABSENCES_REPETEES"
        assert body["status"] == "EN_ATTENTE"

        # Le delai de reponse (Art. 49) doit etre d'environ 30 jours
        convocation_date = datetime.fromisoformat(body["convocation_date"])
        deadline = datetime.fromisoformat(body["response_deadline"])
        assert 29 <= (deadline - convocation_date).days <= 31

    async def test_secretaire_creates_convocation(
        self,
        client: AsyncClient,
        secretaire_user: User,
        servant_user: User,
    ):
        resp = await client.post(
            "/api/v1/convocations/",
            json={
                "servant_id": str(servant_user.id),
                "motif": "TENUE_INCORRECTE",
            },
            headers=make_auth_header(secretaire_user),
        )
        assert resp.status_code == 201

    async def test_aumonier_creates_convocation(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
    ):
        resp = await client.post(
            "/api/v1/convocations/",
            json={
                "servant_id": str(servant_user.id),
                "motif": "NON_COTISATION",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201

    async def test_servant_cannot_create_convocation(
        self,
        client: AsyncClient,
        servant_user: User,
        servant_user_2: User,
    ):
        resp = await client.post(
            "/api/v1/convocations/",
            json={
                "servant_id": str(servant_user_2.id),
                "motif": "NON_COTISATION",
            },
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403

    async def test_parent_cannot_create_convocation(
        self,
        client: AsyncClient,
        parent_user: User,
        servant_user: User,
    ):
        resp = await client.post(
            "/api/v1/convocations/",
            json={
                "servant_id": str(servant_user.id),
                "motif": "NON_COTISATION",
            },
            headers=make_auth_header(parent_user),
        )
        assert resp.status_code == 403

    async def test_cannot_convoke_for_non_servant(
        self,
        client: AsyncClient,
        censeur_user: User,
        parent_user: User,
    ):
        resp = await client.post(
            "/api/v1/convocations/",
            json={
                "servant_id": str(parent_user.id),
                "motif": "NON_COTISATION",
            },
            headers=make_auth_header(censeur_user),
        )
        assert resp.status_code == 400


@pytest.mark.e2e
class TestListAndHonorConvocation:
    """Historique et cloture d'une convocation."""

    async def _create_convocation(self, client: AsyncClient, censeur_user: User, servant_user: User) -> str:
        resp = await client.post(
            "/api/v1/convocations/",
            json={
                "servant_id": str(servant_user.id),
                "motif": "ABSENCES_REPETEES",
            },
            headers=make_auth_header(censeur_user),
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_list_servant_convocations(
        self,
        client: AsyncClient,
        censeur_user: User,
        servant_user: User,
    ):
        await self._create_convocation(client, censeur_user, servant_user)
        resp = await client.get(
            f"/api/v1/convocations/servant/{servant_user.id}",
            headers=make_auth_header(censeur_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) >= 1

    async def test_honor_convocation(
        self,
        client: AsyncClient,
        censeur_user: User,
        aumonier_user: User,
        servant_user: User,
    ):
        convocation_id = await self._create_convocation(client, censeur_user, servant_user)
        resp = await client.post(
            f"/api/v1/convocations/{convocation_id}/honor",
            json={"notes": "Le père s'est présenté."},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "HONOREE"
        assert body["honored_at"] is not None

    async def test_cannot_honor_twice(
        self,
        client: AsyncClient,
        censeur_user: User,
        aumonier_user: User,
        servant_user: User,
    ):
        convocation_id = await self._create_convocation(client, censeur_user, servant_user)
        await client.post(
            f"/api/v1/convocations/{convocation_id}/honor",
            json={},
            headers=make_auth_header(aumonier_user),
        )
        resp = await client.post(
            f"/api/v1/convocations/{convocation_id}/honor",
            json={},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    async def test_servant_cannot_honor(
        self,
        client: AsyncClient,
        censeur_user: User,
        servant_user: User,
        servant_user_2: User,
    ):
        convocation_id = await self._create_convocation(client, censeur_user, servant_user)
        resp = await client.post(
            f"/api/v1/convocations/{convocation_id}/honor",
            json={},
            headers=make_auth_header(servant_user_2),
        )
        assert resp.status_code == 403
