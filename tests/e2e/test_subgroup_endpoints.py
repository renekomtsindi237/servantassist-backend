"""
Tests E2E du module Sous-groupes — organisation interne.

Couvre :
- CRUD des sous-groupes
- Ajout / retrait de membres
- Regles : un servant par sous-groupe, capacite maximale, unicite du nom
- Self-service (mon sous-groupe)
- Controle d'acces (RBAC)
"""
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.subgroup import SubGroup, SubGroupMember
from src.core.entities.user import User
from tests.conftest import make_auth_header

# ═══════════════════════════════════════════════════════════════════════════
#  CRUD SOUS-GROUPES
# ═══════════════════════════════════════════════════════════════════════════


class TestSubGroupCRUD:
    """Tests CRUD des sous-groupes."""

    @pytest.mark.asyncio
    async def test_create_subgroup(self, client: AsyncClient, aumonier_user: User):
        resp = await client.post(
            "/api/v1/subgroups/",
            json={
                "name": "Equipe Alpha",
                "description": "Equipe des 1er et 3e dimanches.",
                "max_members": 10,
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "Equipe Alpha"
        assert body["is_active"] is True
        assert body["max_members"] == 10
        assert body["member_count"] == 0

    @pytest.mark.asyncio
    async def test_create_duplicate_name_rejected(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_subgroup: SubGroup,
    ):
        resp = await client.post(
            "/api/v1/subgroups/",
            json={"name": sample_subgroup.name},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_list_subgroups(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_subgroup: SubGroup,
    ):
        resp = await client.get(
            "/api/v1/subgroups/",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert any(g["name"] == sample_subgroup.name for g in body)

    @pytest.mark.asyncio
    async def test_get_subgroup_detail(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_subgroup: SubGroup,
    ):
        resp = await client.get(
            f"/api/v1/subgroups/{sample_subgroup.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_subgroup.id)
        assert body["name"] == sample_subgroup.name

    @pytest.mark.asyncio
    async def test_update_subgroup(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_subgroup: SubGroup,
    ):
        resp = await client.patch(
            f"/api/v1/subgroups/{sample_subgroup.id}",
            json={
                "description": "Description mise a jour.",
                "service_schedule": "1er et 3e dimanche",
            },
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["description"] == "Description mise a jour."
        assert body["service_schedule"] == "1er et 3e dimanche"

    @pytest.mark.asyncio
    async def test_delete_subgroup(
        self,
        client: AsyncClient,
        aumonier_user: User,
        sample_subgroup: SubGroup,
    ):
        resp = await client.delete(
            f"/api/v1/subgroups/{sample_subgroup.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_servant_cannot_create_subgroup(self, client: AsyncClient, servant_user: User):
        resp = await client.post(
            "/api/v1/subgroups/",
            json={"name": "Groupe Non Autorise"},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════
#  GESTION DES MEMBRES
# ═══════════════════════════════════════════════════════════════════════════


class TestSubGroupMembers:
    """Tests d'ajout/retrait de membres."""

    @pytest.mark.asyncio
    async def test_add_member_success(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_subgroup: SubGroup,
    ):
        resp = await client.post(
            f"/api/v1/subgroups/{sample_subgroup.id}/members",
            json={"user_id": str(servant_user.id)},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["user_id"] == str(servant_user.id)
        assert body["is_active"] is True

    @pytest.mark.asyncio
    async def test_add_duplicate_member_rejected(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_subgroup: SubGroup,
        sample_subgroup_member: SubGroupMember,
    ):
        resp = await client.post(
            f"/api/v1/subgroups/{sample_subgroup.id}/members",
            json={"user_id": str(servant_user.id)},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_add_non_servant_rejected(
        self,
        client: AsyncClient,
        aumonier_user: User,
        parent_user: User,
        sample_subgroup: SubGroup,
    ):
        resp = await client.post(
            f"/api/v1/subgroups/{sample_subgroup.id}/members",
            json={"user_id": str(parent_user.id)},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_remove_member(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_subgroup: SubGroup,
        sample_subgroup_member: SubGroupMember,
    ):
        resp = await client.delete(
            f"/api/v1/subgroups/{sample_subgroup.id}/members/{servant_user.id}",
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_max_members_enforced(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        servant_user_2: User,
    ):
        """Un sous-groupe avec max_members=1 refuse un 2eme membre."""
        # Creer un sous-groupe avec capacite 1
        create_resp = await client.post(
            "/api/v1/subgroups/",
            json={"name": "Petit Groupe", "max_members": 1},
            headers=make_auth_header(aumonier_user),
        )
        assert create_resp.status_code == 201
        group_id = create_resp.json()["id"]

        # Ajouter le 1er membre
        resp1 = await client.post(
            f"/api/v1/subgroups/{group_id}/members",
            json={"user_id": str(servant_user.id)},
            headers=make_auth_header(aumonier_user),
        )
        assert resp1.status_code == 201

        # Ajouter le 2eme → doit etre refuse
        resp2 = await client.post(
            f"/api/v1/subgroups/{group_id}/members",
            json={"user_id": str(servant_user_2.id)},
            headers=make_auth_header(aumonier_user),
        )
        assert resp2.status_code == 400

    @pytest.mark.asyncio
    async def test_servant_in_two_groups_rejected(
        self,
        client: AsyncClient,
        aumonier_user: User,
        servant_user: User,
        sample_subgroup: SubGroup,
        sample_subgroup_member: SubGroupMember,
    ):
        """Un servant ne peut pas etre dans deux sous-groupes actifs."""
        # Creer un 2eme sous-groupe
        create_resp = await client.post(
            "/api/v1/subgroups/",
            json={"name": "Deuxieme Groupe"},
            headers=make_auth_header(aumonier_user),
        )
        assert create_resp.status_code == 201
        group_id_2 = create_resp.json()["id"]

        # Essayer d'ajouter le servant dans le 2eme groupe
        resp = await client.post(
            f"/api/v1/subgroups/{group_id_2}/members",
            json={"user_id": str(servant_user.id)},
            headers=make_auth_header(aumonier_user),
        )
        assert resp.status_code == 409


# ═══════════════════════════════════════════════════════════════════════════
#  SELF-SERVICE
# ═══════════════════════════════════════════════════════════════════════════


class TestSubGroupSelfService:
    """Tests self-service (mon sous-groupe)."""

    @pytest.mark.asyncio
    async def test_get_my_subgroup_with_membership(
        self,
        client: AsyncClient,
        servant_user: User,
        sample_subgroup: SubGroup,
        sample_subgroup_member: SubGroupMember,
    ):
        resp = await client.get(
            "/api/v1/subgroups/my",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body is not None
        assert body["id"] == str(sample_subgroup.id)

    @pytest.mark.asyncio
    async def test_get_my_subgroup_none(self, client: AsyncClient, servant_user_2: User):
        """Un servant sans sous-groupe recoit null."""
        resp = await client.get(
            "/api/v1/subgroups/my",
            headers=make_auth_header(servant_user_2),
        )
        assert resp.status_code == 200
        assert resp.json() is None
