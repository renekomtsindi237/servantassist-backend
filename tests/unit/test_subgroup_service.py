"""
Tests unitaires pour SubGroupService.

Couvre les chemins non testés par les tests E2E existants :
erreurs 404/409/400 et cas limites.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.services.subgroup_service import SubGroupService
from src.core.entities.subgroup import AINES_MAX_MEMBERS, SubGroup, SubGroupCategory, SubGroupMember
from src.core.entities.user import User, UserRole
from src.presentation.schemas.subgroup import SubGroupCreate, SubGroupMemberAdd, SubGroupUpdate


def _mock_group(
    name="Groupe A", is_active=True, max_members=None, id=None, category=SubGroupCategory.AUTRE
) -> SubGroup:
    g = MagicMock(spec=SubGroup)
    g.id = id or uuid4()
    g.name = name
    g.is_active = is_active
    g.max_members = max_members
    g.category = category
    g.description = "Description"
    g.service_schedule = "Semaine 1"
    g.created_by = uuid4()
    g.created_at = datetime.now(timezone.utc)
    g.updated_at = datetime.now(timezone.utc)
    return g


def _mock_user(role=UserRole.SERVANT) -> User:
    u = MagicMock(spec=User)
    u.id = uuid4()
    u.role = role
    u.birth_date = None
    return u


def _mock_svc(group_repo=None, user_repo=None, training_repo=None) -> SubGroupService:
    return SubGroupService(
        group_repo=group_repo or AsyncMock(),
        user_repo=user_repo or AsyncMock(),
        training_repo=training_repo or AsyncMock(),
    )


# ── create_group ───────────────────────────────────────────────────────────


class TestCreateGroup:
    @pytest.mark.asyncio
    async def test_creates_when_name_is_unique(self):
        group_repo = AsyncMock()
        group_repo.get_by_name.return_value = None
        group = _mock_group()
        group_repo.create.return_value = group
        group_repo.get_member_count.return_value = 0
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo)
        data = SubGroupCreate(name="Nouveau Groupe", max_members=10)
        result = await svc.create_group(data, created_by=uuid4())

        group_repo.create.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_raises_409_when_name_exists(self):
        group_repo = AsyncMock()
        group_repo.get_by_name.return_value = _mock_group()

        svc = _mock_svc(group_repo=group_repo)
        data = SubGroupCreate(name="Existing")

        with pytest.raises(HTTPException) as exc_info:
            await svc.create_group(data, created_by=uuid4())

        assert exc_info.value.status_code == 409


# ── update_group ───────────────────────────────────────────────────────────


class TestUpdateGroup:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = None

        svc = _mock_svc(group_repo=group_repo)
        data = SubGroupUpdate(name="New Name")

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_group(uuid4(), data)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_409_on_name_conflict(self):
        group_id = uuid4()
        existing_group = _mock_group(id=group_id)
        conflicting_group = _mock_group(name="Taken", id=uuid4())

        group_repo = AsyncMock()
        group_repo.get.return_value = existing_group
        group_repo.get_by_name.return_value = conflicting_group

        svc = _mock_svc(group_repo=group_repo)
        data = SubGroupUpdate(name="Taken")

        with pytest.raises(HTTPException) as exc_info:
            await svc.update_group(group_id, data)

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_updates_name_when_same_group(self):
        group_id = uuid4()
        group = _mock_group(id=group_id, name="OldName")

        group_repo = AsyncMock()
        group_repo.get.return_value = group
        group_repo.get_by_name.return_value = group  # same group, not a conflict
        group_repo.update.return_value = group
        group_repo.get_member_count.return_value = 0
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo)
        data = SubGroupUpdate(name="NewName")
        await svc.update_group(group_id, data)

        assert group.name == "NewName"

    @pytest.mark.asyncio
    async def test_updates_max_members(self):
        group_id = uuid4()
        group = _mock_group(id=group_id)

        group_repo = AsyncMock()
        group_repo.get.return_value = group
        group_repo.get_by_name.return_value = None
        group_repo.update.return_value = group
        group_repo.get_member_count.return_value = 0
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo)
        data = SubGroupUpdate(max_members=20)
        await svc.update_group(group_id, data)

        assert group.max_members == 20


# ── get_group ──────────────────────────────────────────────────────────────


class TestGetGroup:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = None

        svc = _mock_svc(group_repo=group_repo)

        with pytest.raises(HTTPException) as exc_info:
            await svc.get_group(uuid4())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_group_response(self):
        group = _mock_group()
        group_repo = AsyncMock()
        group_repo.get.return_value = group
        group_repo.get_member_count.return_value = 3
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo)
        result = await svc.get_group(group.id)

        assert result.member_count == 3


# ── delete_group ───────────────────────────────────────────────────────────


class TestDeleteGroup:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = None

        svc = _mock_svc(group_repo=group_repo)

        with pytest.raises(HTTPException) as exc_info:
            await svc.delete_group(uuid4())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_deletes_successfully(self):
        group = _mock_group()
        group_repo = AsyncMock()
        group_repo.get.return_value = group

        svc = _mock_svc(group_repo=group_repo)
        await svc.delete_group(group.id)

        group_repo.delete.assert_called_once_with(group.id)


# ── add_member ─────────────────────────────────────────────────────────────


class TestAddMember:
    @pytest.mark.asyncio
    async def test_raises_404_when_group_not_found(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = None

        svc = _mock_svc(group_repo=group_repo)
        data = SubGroupMemberAdd(user_id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await svc.add_member(uuid4(), data, added_by=uuid4())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_group_inactive(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = _mock_group(is_active=False)

        svc = _mock_svc(group_repo=group_repo)
        data = SubGroupMemberAdd(user_id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await svc.add_member(uuid4(), data, added_by=uuid4())

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_404_when_user_not_found(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = _mock_group()
        user_repo = AsyncMock()
        user_repo.get.return_value = None

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo)
        data = SubGroupMemberAdd(user_id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await svc.add_member(uuid4(), data, added_by=uuid4())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_user_not_servant(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = _mock_group()
        user_repo = AsyncMock()
        user_repo.get.return_value = _mock_user(role=UserRole.PARENT)

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo)
        data = SubGroupMemberAdd(user_id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await svc.add_member(uuid4(), data, added_by=uuid4())

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_409_when_already_member(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = _mock_group()
        group_repo.get_membership.return_value = MagicMock()  # Already exists
        user_repo = AsyncMock()
        user_repo.get.return_value = _mock_user()

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo)
        data = SubGroupMemberAdd(user_id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await svc.add_member(uuid4(), data, added_by=uuid4())

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_raises_409_when_in_another_group(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = _mock_group()
        group_repo.get_membership.return_value = None
        group_repo.get_active_membership.return_value = MagicMock()  # In another group
        user_repo = AsyncMock()
        user_repo.get.return_value = _mock_user()

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo)
        data = SubGroupMemberAdd(user_id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await svc.add_member(uuid4(), data, added_by=uuid4())

        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_raises_400_when_at_capacity(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = _mock_group(max_members=5)
        group_repo.get_membership.return_value = None
        group_repo.get_active_membership.return_value = None
        group_repo.get_member_count.return_value = 5  # At max capacity
        user_repo = AsyncMock()
        user_repo.get.return_value = _mock_user()

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo)
        data = SubGroupMemberAdd(user_id=uuid4())

        with pytest.raises(HTTPException) as exc_info:
            await svc.add_member(uuid4(), data, added_by=uuid4())

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_adds_member_successfully(self):
        group_repo = AsyncMock()
        group_repo.get.return_value = _mock_group(max_members=10)
        group_repo.get_membership.return_value = None
        group_repo.get_active_membership.return_value = None
        group_repo.get_member_count.return_value = 3
        membership = MagicMock(spec=SubGroupMember)
        group_repo.add_member.return_value = membership
        group_repo.enrich_member.return_value = {
            "id": uuid4(),
            "sub_group_id": uuid4(),
            "user_id": uuid4(),
            "user_first_name": "Jean",
            "user_last_name": "Servant",
            "added_by": uuid4(),
            "added_at": datetime.now(timezone.utc),
            "is_active": True,
        }
        user_repo = AsyncMock()
        user_repo.get.return_value = _mock_user()

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo)
        data = SubGroupMemberAdd(user_id=uuid4())
        result = await svc.add_member(uuid4(), data, added_by=uuid4())

        group_repo.add_member.assert_called_once()
        assert result is not None


# ── remove_member ──────────────────────────────────────────────────────────


class TestRemoveMember:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_member(self):
        group_repo = AsyncMock()
        group_repo.get_membership.return_value = None

        svc = _mock_svc(group_repo=group_repo)

        with pytest.raises(HTTPException) as exc_info:
            await svc.remove_member(uuid4(), uuid4())

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_removes_member_successfully(self):
        membership = MagicMock(spec=SubGroupMember)
        group_repo = AsyncMock()
        group_repo.get_membership.return_value = membership
        updated = MagicMock(spec=SubGroupMember)
        group_repo.remove_member.return_value = updated
        group_repo.enrich_member.return_value = {
            "id": uuid4(),
            "sub_group_id": uuid4(),
            "user_id": uuid4(),
            "user_first_name": "Jean",
            "user_last_name": "Servant",
            "added_by": uuid4(),
            "added_at": datetime.now(timezone.utc),
            "is_active": False,
        }

        svc = _mock_svc(group_repo=group_repo)
        result = await svc.remove_member(uuid4(), uuid4())

        group_repo.remove_member.assert_called_once_with(membership)
        assert result is not None


# ── get_my_group ───────────────────────────────────────────────────────────


class TestGetMyGroup:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_membership(self):
        group_repo = AsyncMock()
        group_repo.get_active_membership.return_value = None

        svc = _mock_svc(group_repo=group_repo)
        result = await svc.get_my_group(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_group_not_found(self):
        membership = MagicMock()
        membership.sub_group_id = uuid4()
        group_repo = AsyncMock()
        group_repo.get_active_membership.return_value = membership
        group_repo.get.return_value = None

        svc = _mock_svc(group_repo=group_repo)
        result = await svc.get_my_group(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_group_response(self):
        membership = MagicMock()
        group = _mock_group()
        membership.sub_group_id = group.id

        group_repo = AsyncMock()
        group_repo.get_active_membership.return_value = membership
        group_repo.get.return_value = group
        group_repo.get_member_count.return_value = 2
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo)
        result = await svc.get_my_group(uuid4())

        assert result is not None
        assert result.member_count == 2


# ── reclassify_servant ─────────────────────────────────────────────────────


class TestReclassifyServant:
    @pytest.mark.asyncio
    async def test_returns_none_when_user_not_found(self):
        user_repo = AsyncMock()
        user_repo.get.return_value = None

        svc = _mock_svc(user_repo=user_repo)
        result = await svc.reclassify_servant(uuid4())

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_not_servant(self):
        user = _mock_user(role=UserRole.PARENT)
        user.birth_date = datetime(2005, 1, 1)
        user_repo = AsyncMock()
        user_repo.get.return_value = user

        svc = _mock_svc(user_repo=user_repo)
        result = await svc.reclassify_servant(user.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_birth_date(self):
        user = _mock_user(role=UserRole.SERVANT)
        user.birth_date = None
        user_repo = AsyncMock()
        user_repo.get.return_value = user

        svc = _mock_svc(user_repo=user_repo)
        result = await svc.reclassify_servant(user.id)

        assert result is None

    @pytest.mark.asyncio
    async def test_creates_canonical_group_when_missing(self):
        """Le groupe canonique est cree automatiquement s'il n'existe pas (ne renvoie plus None)."""
        user = _mock_user(role=UserRole.SERVANT)
        user.birth_date = datetime(2020, 1, 1)  # Young child — ASPIRANTS group
        user_repo = AsyncMock()
        user_repo.get.return_value = user

        group_repo = AsyncMock()
        group_repo.get_by_category.return_value = None
        group_repo.get_by_name.return_value = None
        created_group = _mock_group(name="Aspirants", category=SubGroupCategory.ASPIRANTS)
        group_repo.create.return_value = created_group
        group_repo.get_active_membership.return_value = None
        group_repo.get_member_count.return_value = 0
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo)
        result = await svc.reclassify_servant(user.id)

        group_repo.create.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_assigns_aspirant_for_young_servant(self):
        user = _mock_user(role=UserRole.SERVANT)
        user.birth_date = datetime(2020, 1, 1, tzinfo=timezone.utc)  # ~6 years old
        user_repo = AsyncMock()
        user_repo.get.return_value = user

        group = _mock_group(name="Aspirants", category=SubGroupCategory.ASPIRANTS)
        group_repo = AsyncMock()
        group_repo.get_by_category.return_value = group
        group_repo.get_active_membership.return_value = None
        membership = MagicMock(spec=SubGroupMember)
        group_repo.add_member.return_value = membership
        group_repo.get_member_count.return_value = 0
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo)
        result = await svc.reclassify_servant(user.id)

        group_repo.get_by_category.assert_any_call(SubGroupCategory.ASPIRANTS)
        assert result is not None

    @pytest.mark.asyncio
    async def test_already_in_target_group_returns_without_change(self):
        user = _mock_user(role=UserRole.SERVANT)
        user.birth_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        user_repo = AsyncMock()
        user_repo.get.return_value = user

        group = _mock_group(name="Aspirants", category=SubGroupCategory.ASPIRANTS)
        membership = MagicMock()
        membership.sub_group_id = group.id

        group_repo = AsyncMock()
        group_repo.get_by_category.return_value = group
        group_repo.get_active_membership.return_value = membership
        group_repo.get_member_count.return_value = 1
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo)
        result = await svc.reclassify_servant(user.id)

        group_repo.add_member.assert_not_called()
        assert result is not None

    @pytest.mark.asyncio
    async def test_reclassify_13yo_good_average_stays_confirme(self):
        """
        Seuil d'age assume : un servant de 13 ans (< 15 ans) avec une bonne
        moyenne reste Confirme — il ne devient pas Aine avant 15 ans, meme
        si le reglement fourni ne precise pas explicitement ce seuil (garde-fou
        pour eviter qu'un tres jeune servant devienne eligible responsable).
        """
        user = _mock_user(role=UserRole.SERVANT)
        user.birth_date = datetime(2013, 1, 1, tzinfo=timezone.utc)  # ~13 ans
        user_repo = AsyncMock()
        user_repo.get.return_value = user

        training_repo = AsyncMock()
        stats = MagicMock()
        stats.average_score = 95.0
        training_repo.get_servant_stats.return_value = stats

        group = _mock_group(name="Confirmés", category=SubGroupCategory.CONFIRMES)
        group_repo = AsyncMock()
        group_repo.get_by_category.return_value = group
        group_repo.get_active_membership.return_value = None
        group_repo.get_member_count.return_value = 0
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo, training_repo=training_repo)
        result = await svc.reclassify_servant(user.id)

        group_repo.get_by_category.assert_any_call(SubGroupCategory.CONFIRMES)
        assert result is not None
        assert result.category == SubGroupCategory.CONFIRMES

    @pytest.mark.asyncio
    async def test_reclassify_15yo_good_average_becomes_aine(self):
        user = _mock_user(role=UserRole.SERVANT)
        user.birth_date = datetime(2011, 1, 1, tzinfo=timezone.utc)  # ~15 ans
        user_repo = AsyncMock()
        user_repo.get.return_value = user

        training_repo = AsyncMock()
        stats = MagicMock()
        stats.average_score = 75.0  # >= 70% (14/20)
        training_repo.get_servant_stats.return_value = stats

        aines_group = _mock_group(name="Aînés", category=SubGroupCategory.AINES, max_members=AINES_MAX_MEMBERS)
        group_repo = AsyncMock()
        group_repo.get_by_category.return_value = aines_group
        group_repo.get_active_membership.return_value = None
        group_repo.get_member_count.return_value = 2  # sous le plafond de 7
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo, training_repo=training_repo)
        result = await svc.reclassify_servant(user.id)

        group_repo.get_by_category.assert_any_call(SubGroupCategory.AINES)
        assert result is not None
        assert result.category == SubGroupCategory.AINES

    @pytest.mark.asyncio
    async def test_aines_capacity_full_stays_confirme(self):
        """Le sous-groupe des Aines est plafonne a 7 membres (Art. 26.4)."""
        user = _mock_user(role=UserRole.SERVANT)
        user.birth_date = datetime(2011, 1, 1, tzinfo=timezone.utc)  # ~15 ans
        user_repo = AsyncMock()
        user_repo.get.return_value = user

        training_repo = AsyncMock()
        stats = MagicMock()
        stats.average_score = 90.0
        training_repo.get_servant_stats.return_value = stats

        aines_group = _mock_group(name="Aînés", category=SubGroupCategory.AINES, max_members=AINES_MAX_MEMBERS)
        confirmes_group = _mock_group(name="Confirmés", category=SubGroupCategory.CONFIRMES)

        def _get_by_category(category):
            if category == SubGroupCategory.AINES:
                return aines_group
            return confirmes_group

        group_repo = AsyncMock()
        group_repo.get_by_category.side_effect = _get_by_category
        group_repo.get_active_membership.return_value = None
        group_repo.get_member_count.return_value = AINES_MAX_MEMBERS  # deja complet
        group_repo.get_members.return_value = []
        group_repo.enrich_members.return_value = []

        svc = _mock_svc(group_repo=group_repo, user_repo=user_repo, training_repo=training_repo)
        result = await svc.reclassify_servant(user.id)

        assert result is not None
        assert result.category == SubGroupCategory.CONFIRMES


# ── get_or_create_canonical_group ──────────────────────────────────────────


class TestGetOrCreateCanonicalGroup:
    @pytest.mark.asyncio
    async def test_get_or_create_canonical_group_chorale(self):
        """La chorale (Art. 33-34) est un SubGroup de categorie CHORALE, cree a la demande."""
        group_repo = AsyncMock()
        group_repo.get_by_category.return_value = None
        group_repo.get_by_name.return_value = None
        created = _mock_group(name="Chorale", category=SubGroupCategory.CHORALE)
        group_repo.create.return_value = created

        svc = _mock_svc(group_repo=group_repo)
        result = await svc.get_or_create_canonical_group(SubGroupCategory.CHORALE, uuid4())

        group_repo.create.assert_called_once()
        created_group_arg = group_repo.create.call_args[0][0]
        assert created_group_arg.category == SubGroupCategory.CHORALE
        assert created_group_arg.max_members is None
        assert result.category == SubGroupCategory.CHORALE

    @pytest.mark.asyncio
    async def test_get_or_create_canonical_group_returns_existing(self):
        existing = _mock_group(name="Chorale", category=SubGroupCategory.CHORALE)
        group_repo = AsyncMock()
        group_repo.get_by_category.return_value = existing

        svc = _mock_svc(group_repo=group_repo)
        result = await svc.get_or_create_canonical_group(SubGroupCategory.CHORALE, uuid4())

        group_repo.create.assert_not_called()
        assert result is existing
