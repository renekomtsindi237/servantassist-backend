"""
Unit tests for ConnectionLogRepository.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


# ═══════════════════════════════════════════════════════════════════════════════
#  ConnectionLogRepository
# ═══════════════════════════════════════════════════════════════════════════════


def _make_connection_log(**kw):
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
