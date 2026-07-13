"""
Unit tests for ContributionRepository and ConnectionLogRepository.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _sa_exec_result(scalar_one=None, scalars_list=None, scalar=None, all_=None):
    """SQLAlchemy AsyncSession.execute() result."""
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=scalar_one)
    r.scalar_one = MagicMock(return_value=scalar_one)
    r.scalar = MagicMock(return_value=scalar)
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = scalars_list or []
    r.scalars.return_value = scalars_obj
    r.all = MagicMock(return_value=all_ or [])
    return r


# ═══════════════════════════════════════════════════════════════════════════════
#  ContributionRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_contribution(**kw):
    from src.core.entities.contribution import Contribution, PaymentMode, PaymentStatus

    c = MagicMock()
    c.id = kw.get("id", uuid4())
    c.servant_id = kw.get("servant_id", uuid4())
    c.recorded_by = kw.get("recorded_by", uuid4())
    c.amount = kw.get("amount", 500)
    c.month = kw.get("month", 6)
    c.year = kw.get("year", 2026)
    c.payment_mode = kw.get("payment_mode", PaymentMode.MONTHLY)
    c.payment_date = kw.get("payment_date", datetime.utcnow())
    c.status = kw.get("status", PaymentStatus.PAID)
    c.created_at = kw.get("created_at", datetime.utcnow())
    c.updated_at = kw.get("updated_at", datetime.utcnow())
    c.model_dump = MagicMock(return_value={"id": str(c.id), "amount": c.amount})
    return c


@pytest.mark.asyncio
async def test_contribution_create():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    c = _make_contribution()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(c)
    assert result is c
    session.add.assert_called_once_with(c)


@pytest.mark.asyncio
async def test_contribution_get_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    c = _make_contribution()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=c))

    result = await repo.get(c.id)
    assert result is c


@pytest.mark.asyncio
async def test_contribution_get_not_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.get(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_contribution_list():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    contributions = [_make_contribution()]

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar=1),          # count
        _sa_exec_result(scalars_list=contributions),   # results
    ])

    result, total = await repo.list()
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_contribution_list_with_filters():
    from src.core.entities.contribution import PaymentMode
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar=0),
        _sa_exec_result(scalars_list=[]),
    ])

    result, total = await repo.list(
        servant_id=uuid4(),
        month=6,
        year=2026,
        payment_mode=PaymentMode.MONTHLY,
    )
    assert total == 0
    assert result == []


@pytest.mark.asyncio
async def test_contribution_get_servant_contributions():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    contributions = [_make_contribution(), _make_contribution()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=contributions))

    result = await repo.get_servant_contributions(uuid4())
    assert len(result) == 2


@pytest.mark.asyncio
async def test_contribution_get_servant_contributions_with_dates():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=[]))
    now = datetime.utcnow()

    result = await repo.get_servant_contributions(
        uuid4(), start_date=now - timedelta(days=30), end_date=now
    )
    assert result == []


@pytest.mark.asyncio
async def test_contribution_get_monthly_contributions():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    contributions = [_make_contribution(month=6, year=2026)]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=contributions))

    result = await repo.get_monthly_contributions(6, 2026)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_contribution_update_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    existing = _make_contribution()

    # Mock model_dump on new contribution
    new_contrib = _make_contribution()
    new_contrib.model_dump = MagicMock(return_value={"amount": 700})

    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=existing))
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(existing.id, new_contrib)
    assert result is existing


@pytest.mark.asyncio
async def test_contribution_update_not_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    new_contrib = _make_contribution()
    new_contrib.model_dump = MagicMock(return_value={"amount": 700})

    result = await repo.update(uuid4(), new_contrib)
    assert result is None


@pytest.mark.asyncio
async def test_contribution_delete_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    c = _make_contribution()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=c))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(c.id)
    assert result is True


@pytest.mark.asyncio
async def test_contribution_delete_not_found():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_contribution_get_monthly_summary():
    from src.core.entities.contribution import Contribution, PaymentMode, PaymentStatus
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    servant_id = uuid4()

    # Use a real-ish Contribution to avoid Pydantic validation errors
    c = Contribution(
        servant_id=servant_id,
        recorded_by=uuid4(),
        amount=500,
        month=6,
        year=2026,
        payment_mode=PaymentMode.MONTHLY,
        payment_date=datetime.utcnow(),
    )
    servant = MagicMock()
    servant.first_name = "Jean"
    servant.last_name = "Nkemelu"

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalars_list=[c]),   # contributions
        _sa_exec_result(scalar_one=servant), # servant
    ])

    with patch("src.infrastructure.repositories.contribution_repository.decrypt_str_fields"):
        result = await repo.get_monthly_summary(servant_id, 6, 2026)

    assert result.servant_id == servant_id
    assert result.paid_amount == 500


@pytest.mark.asyncio
async def test_contribution_get_monthly_summary_no_servant():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    servant_id = uuid4()

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalars_list=[]),    # no contributions
        _sa_exec_result(scalar_one=None),    # no servant
    ])

    result = await repo.get_monthly_summary(servant_id, 6, 2026)
    assert result.servant_name == "Inconnu"
    assert result.paid_amount == 0


@pytest.mark.asyncio
async def test_contribution_get_all_servants():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    servants = [MagicMock(), MagicMock()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=servants))

    with patch("src.infrastructure.repositories.contribution_repository.decrypt_str_fields"):
        result = await repo.get_all_servants()

    assert len(result) == 2


@pytest.mark.asyncio
async def test_contribution_calculate_period_stats():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    servant_id = uuid4()

    servant = MagicMock()
    servants = [servant]
    c = _make_contribution(servant_id=servant_id, amount=500)

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalars_list=servants),   # servants (get_all_servants)
        _sa_exec_result(scalars_list=[c]),         # contributions in period
    ])

    now = datetime.utcnow()
    with patch("src.infrastructure.repositories.contribution_repository.decrypt_str_fields"):
        result = await repo.calculate_period_stats(now - timedelta(days=30), now)

    assert "total_expected" in result
    assert "total_collected" in result
    assert result["total_collected"] == 500


@pytest.mark.asyncio
async def test_contribution_enrich_contribution():
    from src.infrastructure.repositories.contribution_repository import ContributionRepository

    session = _mock_session()
    repo = ContributionRepository(session)
    c = _make_contribution()

    servant = MagicMock()
    servant.first_name = "Jean"
    servant.last_name = "Nkemelu"
    recorder = MagicMock()
    recorder.first_name = "Admin"
    recorder.last_name = "Resp"

    session.execute = AsyncMock(side_effect=[
        _sa_exec_result(scalar_one=servant),
        _sa_exec_result(scalar_one=recorder),
    ])

    with patch("src.infrastructure.repositories.contribution_repository.decrypt_str_fields"):
        result = await repo.enrich_contribution(c)

    assert result["servant_name"] == "Jean Nkemelu"
    assert result["recorded_by_name"] == "Admin Resp"


# ═══════════════════════════════════════════════════════════════════════════════
#  ConnectionLogRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_connection_log(**kw):
    from src.core.entities.connection_log import ConnectionLog

    log = MagicMock()
    log.id = kw.get("id", uuid4())
    log.user_id = kw.get("user_id", uuid4())
    log.country = kw.get("country", "Cameroon")
    log.country_code = kw.get("country_code", "CM")
    log.city = kw.get("city", "Yaoundé")
    log.lat = kw.get("lat", 3.848)
    log.lng = kw.get("lng", 11.502)
    log.logged_at = kw.get("logged_at", datetime.utcnow())
    return log


@pytest.mark.asyncio
async def test_connection_log_create():
    from src.infrastructure.repositories.connection_log_repository import ConnectionLogRepository

    session = _mock_session()
    repo = ConnectionLogRepository(session)
    log = _make_connection_log()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(log)
    assert result is log


@pytest.mark.asyncio
async def test_connection_log_get_geo_points():
    from src.infrastructure.repositories.connection_log_repository import ConnectionLogRepository

    session = _mock_session()
    repo = ConnectionLogRepository(session)

    row = MagicMock()
    row.country = "Cameroon"
    row.country_code = "CM"
    row.city = "Yaoundé"
    row.lat = 3.848
    row.lng = 11.502
    row.count = 5
    row.last_seen = datetime.utcnow()

    exec_result = MagicMock()
    exec_result.all = MagicMock(return_value=[row])
    session.execute = AsyncMock(return_value=exec_result)

    result = await repo.get_geo_points(days=30)
    assert len(result) == 1
    assert result[0]["country"] == "Cameroon"
    assert result[0]["count"] == 5


@pytest.mark.asyncio
async def test_connection_log_get_geo_points_no_last_seen():
    from src.infrastructure.repositories.connection_log_repository import ConnectionLogRepository

    session = _mock_session()
    repo = ConnectionLogRepository(session)

    row = MagicMock()
    row.country = "France"
    row.country_code = "FR"
    row.city = "Paris"
    row.lat = 48.8566
    row.lng = 2.3522
    row.count = 1
    row.last_seen = None  # Edge case: no last_seen

    exec_result = MagicMock()
    exec_result.all = MagicMock(return_value=[row])
    session.execute = AsyncMock(return_value=exec_result)

    result = await repo.get_geo_points(days=7)
    assert result[0]["last_seen"] is None


@pytest.mark.asyncio
async def test_connection_log_get_geo_points_empty():
    from src.infrastructure.repositories.connection_log_repository import ConnectionLogRepository

    session = _mock_session()
    repo = ConnectionLogRepository(session)

    exec_result = MagicMock()
    exec_result.all = MagicMock(return_value=[])
    session.execute = AsyncMock(return_value=exec_result)

    result = await repo.get_geo_points()
    assert result == []
