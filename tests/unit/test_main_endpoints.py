"""
Unit tests for src/main.py endpoint functions and application creation.

Tests the simple endpoint functions directly (root, health_check, readiness_probe,
api_version) using mocked dependencies.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
#  root()
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_root_returns_expected_keys():
    from src.main import root

    result = await root()
    assert "name" in result
    assert "version" in result
    assert "docs" in result
    assert "health" in result
    assert "ready" in result
    assert result["docs"] == "/api/docs"
    assert result["health"] == "/health"


# ═══════════════════════════════════════════════════════════════════════════════
#  api_version()
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_api_version_returns_version_info():
    from src.main import api_version

    result = await api_version()
    assert "version" in result
    assert "release_date" in result
    assert "environment" in result
    assert "min_client_version" in result
    assert "deprecations" in result
    assert result["version"] == "1.0.0"


# ═══════════════════════════════════════════════════════════════════════════════
#  health_check()
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_health_check_healthy():
    """health_check returns 200 when DB and Redis are OK."""
    from src.main import app, health_check

    # Mock sessionmanager
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(return_value=MagicMock())

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    # Mock redis
    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()
    mock_redis.close = AsyncMock()

    with patch("src.main.sessionmanager", mock_sm):
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            # Ensure app.state.ws_manager does not exist
            if hasattr(app.state, "ws_manager"):
                del app.state.ws_manager

            response = await health_check()

    import json
    body = json.loads(response.body)
    assert body["status"] in ("healthy", "degraded")
    assert "database" in body["checks"]


@pytest.mark.asyncio
async def test_health_check_unhealthy_db():
    """health_check returns 503 when DB is not available."""
    from src.main import app, health_check

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    with patch("src.main.sessionmanager", mock_sm):
        with patch("redis.asyncio.from_url", side_effect=Exception("redis down")):
            if hasattr(app.state, "ws_manager"):
                del app.state.ws_manager

            response = await health_check()

    import json
    body = json.loads(response.body)
    assert body["status"] == "unhealthy"
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_health_check_degraded_redis_down():
    """health_check returns 200 but status='degraded' when Redis is down."""
    from src.main import app, health_check

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(return_value=MagicMock())

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    with patch("src.main.sessionmanager", mock_sm):
        with patch("redis.asyncio.from_url", side_effect=Exception("redis down")):
            if hasattr(app.state, "ws_manager"):
                del app.state.ws_manager

            response = await health_check()

    import json
    body = json.loads(response.body)
    # DB OK, Redis KO → degraded
    assert body["status"] == "degraded"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["redis"]["status"] == "error"


@pytest.mark.asyncio
async def test_health_check_with_ws_manager():
    """health_check includes websocket info when ws_manager is on app.state."""
    from src.main import app, health_check

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(return_value=MagicMock())

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock()
    mock_redis.close = AsyncMock()

    mock_ws = MagicMock()
    mock_ws.total_connections = 5
    mock_ws.connected_users = 3
    app.state.ws_manager = mock_ws

    with patch("src.main.sessionmanager", mock_sm):
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            response = await health_check()

    import json
    body = json.loads(response.body)
    assert "websocket" in body["checks"]
    assert body["checks"]["websocket"]["active_connections"] == 5

    # Clean up
    del app.state.ws_manager


# ═══════════════════════════════════════════════════════════════════════════════
#  readiness_probe()
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_readiness_probe_ready():
    from src.main import readiness_probe

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.exec = AsyncMock(return_value=MagicMock())

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    with patch("src.main.sessionmanager", mock_sm):
        result = await readiness_probe()

    assert result == {"status": "ready"}


@pytest.mark.asyncio
async def test_readiness_probe_not_ready():
    from src.main import readiness_probe

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(side_effect=Exception("no db"))
    mock_session.__aexit__ = AsyncMock(return_value=None)

    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session

    with patch("src.main.sessionmanager", mock_sm):
        response = await readiness_probe()

    import json
    body = json.loads(response.body)
    assert body["status"] == "not_ready"
    assert response.status_code == 503


# ═══════════════════════════════════════════════════════════════════════════════
#  App creation — verify app is properly configured
# ═══════════════════════════════════════════════════════════════════════════════


def test_app_is_fastapi_instance():
    from fastapi import FastAPI
    from src.main import app

    assert isinstance(app, FastAPI)


def test_app_has_routes():
    from src.main import app

    routes = [r.path for r in app.routes if hasattr(r, "path")]
    assert "/health" in routes
    assert "/ready" in routes
    assert "/" in routes


def test_app_metrics_counter_defined():
    from src.main import http_requests_total, http_request_duration_seconds, active_ws_connections

    assert http_requests_total is not None
    assert http_request_duration_seconds is not None
    assert active_ws_connections is not None
