"""Unit tests for ConvocationService (Art. 48-49 du reglement interieur)."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.convocation_service import ConvocationService
from src.core.entities.convocation import Convocation, ConvocationMotif, ConvocationStatus
from src.core.entities.user import User, UserRole

NOW = datetime(2026, 6, 1, 10, 0, 0)


def _make_user(role=UserRole.SERVANT, is_active=True) -> User:
    return User(
        id=uuid4(),
        first_name="Jean",
        last_name="Pierre",
        email="jean@test.com",
        hashed_password="x",
        role=role,
        is_active=is_active,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_convocation(**kwargs) -> Convocation:
    return Convocation(
        id=kwargs.pop("id", uuid4()),
        servant_id=kwargs.pop("servant_id", uuid4()),
        motif=kwargs.pop("motif", ConvocationMotif.NON_COTISATION),
        status=kwargs.pop("status", ConvocationStatus.EN_ATTENTE),
        convocation_date=kwargs.pop("convocation_date", NOW),
        response_deadline=kwargs.pop("response_deadline", NOW + timedelta(days=30)),
        convened_by=kwargs.pop("convened_by", uuid4()),
        created_at=kwargs.pop("created_at", NOW),
        updated_at=kwargs.pop("updated_at", NOW),
        **kwargs,
    )


def _make_svc(convocation_repo=None, user_repo=None) -> ConvocationService:
    if convocation_repo is None:
        convocation_repo = MagicMock()
        convocation_repo.get = AsyncMock(return_value=None)
        convocation_repo.create = AsyncMock()
        convocation_repo.update = AsyncMock()
        convocation_repo.list_by_servant = AsyncMock(return_value=[])
        convocation_repo.get_pending_by_servant_and_motif = AsyncMock(return_value=None)
        convocation_repo.list_pending_past_deadline = AsyncMock(return_value=[])
    if user_repo is None:
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=None)
        user_repo.update = AsyncMock()
    return ConvocationService(convocation_repo, user_repo)


# ── create_convocation ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_convocation_servant_not_found():
    svc = _make_svc()
    svc.user_repo.get.return_value = None
    data = MagicMock(servant_id=uuid4(), motif=ConvocationMotif.NON_COTISATION, details=None)
    with pytest.raises(Exception) as exc:
        await svc.create_convocation(data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_create_convocation_not_servant_rejected():
    svc = _make_svc()
    svc.user_repo.get.return_value = _make_user(role=UserRole.PARENT)
    data = MagicMock(servant_id=uuid4(), motif=ConvocationMotif.NON_COTISATION, details=None)
    with pytest.raises(Exception) as exc:
        await svc.create_convocation(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_convocation_success():
    servant = _make_user()
    convocation = _make_convocation(servant_id=servant.id)
    svc = _make_svc()
    svc.user_repo.get.return_value = servant
    svc.convocation_repo.create.return_value = convocation
    data = MagicMock(servant_id=servant.id, motif=ConvocationMotif.TENUE_INCORRECTE, details="3x tenue incorrecte")
    result = await svc.create_convocation(data, uuid4())
    assert result.id == convocation.id
    assert result.status == ConvocationStatus.EN_ATTENTE


# ── create_if_not_pending ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_if_not_pending_creates_when_absent():
    svc = _make_svc()
    svc.convocation_repo.get_pending_by_servant_and_motif.return_value = None
    convocation = _make_convocation()
    svc.convocation_repo.create.return_value = convocation
    result = await svc.create_if_not_pending(
        servant_id=uuid4(), motif=ConvocationMotif.ABSENCES_REPETEES, details="test", convened_by=uuid4()
    )
    assert result is convocation
    svc.convocation_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_if_not_pending_idempotent_when_already_pending():
    svc = _make_svc()
    existing = _make_convocation()
    svc.convocation_repo.get_pending_by_servant_and_motif.return_value = existing
    result = await svc.create_if_not_pending(
        servant_id=uuid4(), motif=ConvocationMotif.ABSENCES_REPETEES, details="test", convened_by=uuid4()
    )
    assert result is None
    svc.convocation_repo.create.assert_not_called()


# ── mark_honored ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_mark_honored_not_found():
    svc = _make_svc()
    svc.convocation_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.mark_honored(uuid4(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_mark_honored_already_resolved_rejected():
    convocation = _make_convocation(status=ConvocationStatus.HONOREE)
    svc = _make_svc()
    svc.convocation_repo.get.return_value = convocation
    with pytest.raises(Exception) as exc:
        await svc.mark_honored(convocation.id, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_mark_honored_success():
    convocation = _make_convocation(status=ConvocationStatus.EN_ATTENTE)
    svc = _make_svc()
    svc.convocation_repo.get.return_value = convocation
    svc.convocation_repo.update.return_value = convocation
    result = await svc.mark_honored(convocation.id, uuid4(), notes="Mère présente")
    assert result.status == ConvocationStatus.HONOREE
    assert convocation.honored_at is not None


# ── process_expired_convocations ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_expired_convocations_none_expired():
    svc = _make_svc()
    svc.convocation_repo.list_pending_past_deadline.return_value = []
    result = await svc.process_expired_convocations()
    assert result["expired_convocations_processed"] == 0


@pytest.mark.asyncio
async def test_process_expired_convocations_suspends_servant():
    servant = _make_user(is_active=True)
    convocation = _make_convocation(servant_id=servant.id)
    svc = _make_svc()
    svc.convocation_repo.list_pending_past_deadline.return_value = [convocation]
    svc.user_repo.get.return_value = servant
    result = await svc.process_expired_convocations()
    assert result["expired_convocations_processed"] == 1
    assert convocation.status == ConvocationStatus.SANS_REPONSE
    svc.user_repo.update.assert_called_once()
    assert servant.is_active is False


@pytest.mark.asyncio
async def test_process_expired_convocations_already_inactive_servant():
    """Si le servant est deja inactif, on ne relance pas de mise a jour user."""
    servant = _make_user(is_active=False)
    convocation = _make_convocation(servant_id=servant.id)
    svc = _make_svc()
    svc.convocation_repo.list_pending_past_deadline.return_value = [convocation]
    svc.user_repo.get.return_value = servant
    result = await svc.process_expired_convocations()
    assert result["expired_convocations_processed"] == 1
    svc.user_repo.update.assert_not_called()
