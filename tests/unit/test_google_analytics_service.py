"""Unit tests for google_analytics_service module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.services.google_analytics_service import (
    _mock_realtime,
    _mock_summary,
    _parse_realtime,
    _parse_summary,
    _sa_json,
    get_realtime,
    get_today_summary,
)

# ─── _sa_json ─────────────────────────────────────────────────────────────────


def test_sa_json_empty_string():
    assert _sa_json("") is None


def test_sa_json_none():
    assert _sa_json(None) is None


def test_sa_json_invalid_json():
    assert _sa_json("not json") is None


def test_sa_json_valid():
    result = _sa_json('{"client_email": "sa@test.com", "private_key": "key"}')
    assert result["client_email"] == "sa@test.com"


# ─── _mock_realtime / _mock_summary ──────────────────────────────────────────


def test_mock_realtime():
    r = _mock_realtime()
    assert r["source"] == "mock"
    assert r["active_users"] == 0
    assert r["top_pages"] == []


def test_mock_summary():
    s = _mock_summary()
    assert s["source"] == "mock"
    assert s["users_today"] == 0


# ─── _parse_realtime ──────────────────────────────────────────────────────────


def test_parse_realtime_empty():
    result = _parse_realtime({})
    assert result["active_users"] == 0
    assert result["source"] == "ga4"
    assert result["top_pages"] == []


def test_parse_realtime_with_data():
    data = {
        "metricHeaders": [
            {"name": "activeUsers"},
            {"name": "eventCount"},
            {"name": "screenPageViews"},
        ],
        "dimensionHeaders": [],
        "totals": [{"metricValues": [{"value": "42"}, {"value": "100"}, {"value": "200"}]}],
        "rows": [],
    }
    result = _parse_realtime(data)
    assert result["active_users"] == 42
    assert result["event_count"] == 100
    assert result["page_views"] == 200
    assert result["source"] == "ga4"


def test_parse_realtime_with_empty_totals():
    data = {
        "metricHeaders": [{"name": "activeUsers"}],
        "dimensionHeaders": [],
        "totals": [],
        "rows": [],
    }
    result = _parse_realtime(data)
    assert result["active_users"] == 0
    assert result["source"] == "ga4"


# ─── _parse_summary ───────────────────────────────────────────────────────────


def test_parse_summary_empty():
    result = _parse_summary({})
    assert result["users_today"] == 0
    assert result["source"] == "ga4"
    assert result["top_pages"] == []


def test_parse_summary_with_data():
    data = {
        "metricHeaders": [
            {"name": "activeUsers"},
            {"name": "sessions"},
            {"name": "screenPageViews"},
            {"name": "bounceRate"},
            {"name": "averageSessionDuration"},
        ],
        "dimensionHeaders": [{"name": "pagePath"}],
        "totals": [
            {
                "metricValues": [
                    {"value": "5"},
                    {"value": "10"},
                    {"value": "50"},
                    {"value": "0.3"},
                    {"value": "120"},
                ]
            }
        ],
        "rows": [
            {
                "dimensionValues": [{"value": "/dashboard"}],
                "metricValues": [
                    {"value": "3"},
                    {"value": "5"},
                    {"value": "20"},
                    {"value": "0.2"},
                    {"value": "90"},
                ],
            }
        ],
    }
    result = _parse_summary(data)
    assert result["users_today"] == 5
    assert result["sessions_today"] == 10
    assert result["bounce_rate"] == 30.0
    assert result["avg_session_duration"] == 120
    assert len(result["top_pages"]) == 1


# ─── get_realtime ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_realtime_no_sa():
    result = await get_realtime("", "123456789")
    assert result["source"] == "mock"


@pytest.mark.asyncio
async def test_get_realtime_invalid_sa():
    result = await get_realtime("not-json", "123456789")
    assert result["source"] == "mock"


@pytest.mark.asyncio
async def test_get_realtime_token_failure():
    sa = '{"client_email": "sa@test.com", "private_key": "-----BEGIN RSA PRIVATE KEY-----"}'

    with patch("src.infrastructure.services.google_analytics_service._get_access_token", return_value=None):
        result = await get_realtime(sa, "123456789")

    assert result["source"] == "mock"


@pytest.mark.asyncio
async def test_get_realtime_api_success():
    sa = '{"client_email": "sa@test.com", "private_key": "key"}'

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "metricHeaders": [{"name": "activeUsers"}, {"name": "eventCount"}, {"name": "screenPageViews"}],
        "dimensionHeaders": [],
        "totals": [{"metricValues": [{"value": "5"}, {"value": "10"}, {"value": "20"}]}],
        "rows": [],
    }

    with (
        patch("src.infrastructure.services.google_analytics_service._get_access_token", return_value="token123"),
        patch("httpx.AsyncClient") as MockClient,
    ):
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        instance.post = AsyncMock(return_value=mock_response)
        MockClient.return_value = instance

        result = await get_realtime(sa, "123456789")

    assert result["source"] == "ga4"


@pytest.mark.asyncio
async def test_get_realtime_api_exception():
    sa = '{"client_email": "sa@test.com", "private_key": "key"}'

    with (
        patch("src.infrastructure.services.google_analytics_service._get_access_token", return_value="tok"),
        patch("httpx.AsyncClient") as MockClient,
    ):
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        instance.post = AsyncMock(side_effect=Exception("Network error"))
        MockClient.return_value = instance

        result = await get_realtime(sa, "123456789")

    assert result["source"] == "mock"


# ─── get_today_summary ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_today_summary_no_sa():
    result = await get_today_summary("", "123456789")
    assert result["source"] == "mock"


@pytest.mark.asyncio
async def test_get_today_summary_token_failure():
    sa = '{"client_email": "sa@test.com", "private_key": "key"}'

    with patch("src.infrastructure.services.google_analytics_service._get_access_token", return_value=None):
        result = await get_today_summary(sa, "123456789")

    assert result["source"] == "mock"


@pytest.mark.asyncio
async def test_get_today_summary_success():
    sa = '{"client_email": "sa@test.com", "private_key": "key"}'

    mock_response = MagicMock()
    mock_response.json.return_value = {"metricHeaders": [], "dimensionHeaders": [], "totals": [], "rows": []}

    with (
        patch("src.infrastructure.services.google_analytics_service._get_access_token", return_value="token123"),
        patch("httpx.AsyncClient") as MockClient,
    ):
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        instance.post = AsyncMock(return_value=mock_response)
        MockClient.return_value = instance

        result = await get_today_summary(sa, "123456789")

    assert result["source"] == "ga4"


@pytest.mark.asyncio
async def test_get_today_summary_exception():
    sa = '{"client_email": "sa@test.com", "private_key": "key"}'

    with (
        patch("src.infrastructure.services.google_analytics_service._get_access_token", return_value="tok"),
        patch("httpx.AsyncClient") as MockClient,
    ):
        instance = AsyncMock()
        instance.__aenter__ = AsyncMock(return_value=instance)
        instance.__aexit__ = AsyncMock(return_value=None)
        instance.post = AsyncMock(side_effect=Exception("Timeout"))
        MockClient.return_value = instance

        result = await get_today_summary(sa, "123456789")

    assert result["source"] == "mock"
