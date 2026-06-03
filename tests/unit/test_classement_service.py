"""
Tests unitaires pour ClassementService.

Couvre toutes les méthodes : create, get, list, update, advance_status, delete.
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.classement_service import ClassementService
from src.core.entities.classement import Classement, ClassementStatus, ClassementType


def _make_classement(
    status: ClassementStatus = ClassementStatus.BROUILLON,
    id=None,
) -> Classement:
    c = MagicMock(spec=Classement)
    c.id = id or uuid4()
    c.status = status
    c.published_at = None
    return c


# ── create ─────────────────────────────────────────────────────────────────


class TestClassementServiceCreate:
    @pytest.mark.asyncio
    async def test_create_delegates_to_repo(self):
        repo = AsyncMock()
        expected = _make_classement()
        repo.create.return_value = expected

        svc = ClassementService(repo)
        result = await svc.create(
            type=ClassementType.DIMANCHE,
            date=date.today(),
            heure="06h30",
            lieu="Cathédrale",
            created_by=uuid4(),
        )

        repo.create.assert_called_once()
        assert result is expected

    @pytest.mark.asyncio
    async def test_create_with_postes(self):
        repo = AsyncMock()
        repo.create.return_value = _make_classement()

        svc = ClassementService(repo)
        postes = [{"poste": "RESPONSABLE", "servant_id": str(uuid4())}]
        await svc.create(
            type=ClassementType.DIMANCHE,
            date=date.today(),
            heure="08h30",
            lieu="Paroisse",
            created_by=uuid4(),
            postes=postes,
        )

        call_arg = repo.create.call_args[0][0]
        assert call_arg.postes == postes

    @pytest.mark.asyncio
    async def test_create_with_empty_postes_defaults_to_empty_list(self):
        repo = AsyncMock()
        repo.create.return_value = _make_classement()

        svc = ClassementService(repo)
        await svc.create(
            type=ClassementType.SEMAINE,
            date=date.today(),
            heure="17h00",
            lieu="Chapelle",
            created_by=uuid4(),
        )

        call_arg = repo.create.call_args[0][0]
        assert call_arg.postes == []

    @pytest.mark.asyncio
    async def test_create_sets_brouillon_status(self):
        repo = AsyncMock()
        repo.create.return_value = _make_classement()

        svc = ClassementService(repo)
        await svc.create(
            type=ClassementType.DIMANCHE,
            date=date.today(),
            heure="10h00",
            lieu="Test",
            created_by=uuid4(),
        )

        call_arg = repo.create.call_args[0][0]
        assert call_arg.status == ClassementStatus.BROUILLON

    @pytest.mark.asyncio
    async def test_create_with_all_optional_fields(self):
        repo = AsyncMock()
        repo.create.return_value = _make_classement()
        svc = ClassementService(repo)

        await svc.create(
            type=ClassementType.SEMAINE,
            date=date.today(),
            heure="06h30",
            lieu="Nsi",
            created_by=uuid4(),
            solennite="Pâques",
            couleur_liturgique="Blanc",
            semaine=15,
            annee=2026,
            horaire="Ordinaire",
            type_extra="Fête",
            participants="Tous les servants",
        )
        repo.create.assert_called_once()


# ── get ────────────────────────────────────────────────────────────────────


class TestClassementServiceGet:
    @pytest.mark.asyncio
    async def test_get_returns_classement(self):
        repo = AsyncMock()
        expected = _make_classement()
        repo.get_by_id.return_value = expected

        svc = ClassementService(repo)
        result = await svc.get(expected.id)

        repo.get_by_id.assert_called_once_with(expected.id)
        assert result is expected

    @pytest.mark.asyncio
    async def test_get_returns_none_when_not_found(self):
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        svc = ClassementService(repo)
        result = await svc.get(uuid4())

        assert result is None


# ── list ───────────────────────────────────────────────────────────────────


class TestClassementServiceList:
    @pytest.mark.asyncio
    async def test_list_delegates_to_repo(self):
        repo = AsyncMock()
        classements = [_make_classement(), _make_classement()]
        repo.list.return_value = (classements, 2)

        svc = ClassementService(repo)
        result, total = await svc.list()

        repo.list.assert_called_once()
        assert total == 2
        assert result is classements

    @pytest.mark.asyncio
    async def test_list_passes_filters(self):
        repo = AsyncMock()
        repo.list.return_value = ([], 0)

        svc = ClassementService(repo)
        created_by = uuid4()
        await svc.list(
            skip=10,
            limit=5,
            type=ClassementType.DIMANCHE,
            status=ClassementStatus.PUBLIE,
            created_by=created_by,
        )

        call_kwargs = repo.list.call_args[1]
        assert call_kwargs["skip"] == 10
        assert call_kwargs["limit"] == 5
        assert call_kwargs["type"] == ClassementType.DIMANCHE
        assert call_kwargs["status"] == ClassementStatus.PUBLIE
        assert call_kwargs["created_by"] == created_by


# ── update ─────────────────────────────────────────────────────────────────


class TestClassementServiceUpdate:
    @pytest.mark.asyncio
    async def test_update_returns_none_when_not_found(self):
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        svc = ClassementService(repo)
        result = await svc.update(uuid4(), heure="09h00")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_updates_heure(self):
        repo = AsyncMock()
        classement = MagicMock(spec=Classement)
        classement.heure = "06h30"
        repo.get_by_id.return_value = classement
        repo.update.return_value = classement

        svc = ClassementService(repo)
        await svc.update(classement.id, heure="09h00")

        assert classement.heure == "09h00"
        repo.update.assert_called_once_with(classement)

    @pytest.mark.asyncio
    async def test_update_updates_all_fields(self):
        repo = AsyncMock()
        classement = MagicMock(spec=Classement)
        repo.get_by_id.return_value = classement
        repo.update.return_value = classement

        svc = ClassementService(repo)
        new_date = date.today()
        postes = [{"poste": "CRUCIFERE"}]

        await svc.update(
            classement.id,
            date=new_date,
            heure="11h00",
            lieu="Sanctuaire",
            solennite="Assomption",
            couleur_liturgique="Blanc",
            semaine=20,
            annee=2026,
            horaire="Solennel",
            type_extra="Grand rite",
            participants="Tous",
            postes=postes,
        )

        assert classement.date == new_date
        assert classement.heure == "11h00"
        assert classement.lieu == "Sanctuaire"
        assert classement.solennite == "Assomption"
        assert classement.semaine == 20
        assert classement.postes == postes

    @pytest.mark.asyncio
    async def test_update_does_not_change_unset_fields(self):
        repo = AsyncMock()
        classement = MagicMock(spec=Classement)
        classement.heure = "06h30"
        classement.lieu = "Original"
        repo.get_by_id.return_value = classement
        repo.update.return_value = classement

        svc = ClassementService(repo)
        # Only update heure, not lieu
        await svc.update(classement.id, heure="09h00")

        assert classement.heure == "09h00"
        assert classement.lieu == "Original"


# ── advance_status ─────────────────────────────────────────────────────────


class TestClassementServiceAdvanceStatus:
    @pytest.mark.asyncio
    async def test_advance_brouillon_to_finalise(self):
        repo = AsyncMock()
        classement = MagicMock(spec=Classement)
        classement.status = ClassementStatus.BROUILLON
        classement.published_at = None
        repo.get_by_id.return_value = classement
        repo.update.return_value = classement

        svc = ClassementService(repo)
        await svc.advance_status(classement.id)

        assert classement.status == ClassementStatus.FINALISE
        repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_advance_finalise_to_publie(self):
        repo = AsyncMock()
        classement = MagicMock(spec=Classement)
        classement.status = ClassementStatus.FINALISE
        classement.published_at = None
        repo.get_by_id.return_value = classement
        repo.update.return_value = classement

        svc = ClassementService(repo)
        await svc.advance_status(classement.id)

        assert classement.status == ClassementStatus.PUBLIE
        assert classement.published_at is not None

    @pytest.mark.asyncio
    async def test_advance_publie_raises_value_error(self):
        repo = AsyncMock()
        classement = MagicMock(spec=Classement)
        classement.status = ClassementStatus.PUBLIE
        repo.get_by_id.return_value = classement

        svc = ClassementService(repo)
        with pytest.raises(ValueError, match="déjà publié"):
            await svc.advance_status(classement.id)

    @pytest.mark.asyncio
    async def test_advance_returns_none_when_not_found(self):
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        svc = ClassementService(repo)
        result = await svc.advance_status(uuid4())

        assert result is None


# ── delete ─────────────────────────────────────────────────────────────────


class TestClassementServiceDelete:
    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(self):
        repo = AsyncMock()
        repo.get_by_id.return_value = None

        svc = ClassementService(repo)
        result = await svc.delete(uuid4())

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_raises_value_error_when_publie(self):
        repo = AsyncMock()
        classement = MagicMock(spec=Classement)
        classement.status = ClassementStatus.PUBLIE
        repo.get_by_id.return_value = classement

        svc = ClassementService(repo)
        with pytest.raises(ValueError, match="publié"):
            await svc.delete(classement.id)

    @pytest.mark.asyncio
    async def test_delete_calls_repo_when_brouillon(self):
        repo = AsyncMock()
        classement = MagicMock(spec=Classement)
        classement.id = uuid4()
        classement.status = ClassementStatus.BROUILLON
        repo.get_by_id.return_value = classement
        repo.delete.return_value = True

        svc = ClassementService(repo)
        result = await svc.delete(classement.id)

        repo.delete.assert_called_once_with(classement.id)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_calls_repo_when_finalise(self):
        repo = AsyncMock()
        classement = MagicMock(spec=Classement)
        classement.id = uuid4()
        classement.status = ClassementStatus.FINALISE
        repo.get_by_id.return_value = classement
        repo.delete.return_value = True

        svc = ClassementService(repo)
        result = await svc.delete(classement.id)

        repo.delete.assert_called_once_with(classement.id)
        assert result is True
