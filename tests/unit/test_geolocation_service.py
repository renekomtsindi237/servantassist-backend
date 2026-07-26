"""
Unit tests for geolocation_service.py.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─────────────────────────────────────────────────────────────────────────────
#  _is_private
# ─────────────────────────────────────────────────────────────────────────────


def test_is_private_localhost():
    from src.infrastructure.services.geolocation_service import _is_private

    assert _is_private("127.0.0.1") is True


def test_is_private_10_range():
    from src.infrastructure.services.geolocation_service import _is_private

    assert _is_private("10.0.0.5") is True


def test_is_private_172_range():
    from src.infrastructure.services.geolocation_service import _is_private

    assert _is_private("172.20.0.1") is True


def test_is_private_192_range():
    from src.infrastructure.services.geolocation_service import _is_private

    assert _is_private("192.168.1.100") is True


def test_is_private_ipv6_loopback():
    from src.infrastructure.services.geolocation_service import _is_private

    assert _is_private("::1") is True


def test_is_private_public_ip():
    from src.infrastructure.services.geolocation_service import _is_private

    assert _is_private("8.8.8.8") is False


def test_is_private_invalid():
    from src.infrastructure.services.geolocation_service import _is_private

    assert _is_private("not-an-ip") is True


# ─────────────────────────────────────────────────────────────────────────────
#  geolocate_ip
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_geolocate_private_ip_returns_none():
    from src.infrastructure.services.geolocation_service import geolocate_ip

    result = await geolocate_ip("192.168.1.1")
    assert result is None


@pytest.mark.asyncio
async def test_geolocate_public_ip_success():
    from src.infrastructure.services.geolocation_service import geolocate_ip

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "status": "success",
        "country": "Cameroon",
        "countryCode": "CM",
        "city": "Yaoundé",
        "lat": 3.848,
        "lon": 11.502,
    }

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("src.infrastructure.services.geolocation_service.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await geolocate_ip("197.210.0.1")

    assert result is not None
    assert result["country"] == "Cameroon"
    assert result["country_code"] == "CM"
    assert result["city"] == "Yaoundé"
    assert result["lat"] == 3.848
    assert result["lng"] == 11.502


@pytest.mark.asyncio
async def test_geolocate_ip_api_fail_status():
    from src.infrastructure.services.geolocation_service import geolocate_ip

    mock_response = MagicMock()
    mock_response.json.return_value = {"status": "fail"}

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("src.infrastructure.services.geolocation_service.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await geolocate_ip("197.210.0.1")

    assert result is None


@pytest.mark.asyncio
async def test_geolocate_ip_exception_returns_none():
    from src.infrastructure.services.geolocation_service import geolocate_ip

    with patch("src.infrastructure.services.geolocation_service.httpx.AsyncClient") as mock_cls:
        mock_cls.return_value.__aenter__ = AsyncMock(side_effect=Exception("connection error"))
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        result = await geolocate_ip("197.210.0.1")

    assert result is None


# ─────────────────────────────────────────────────────────────────────────────
#  extract_client_ip
# ─────────────────────────────────────────────────────────────────────────────


def test_extract_ip_cloudflare_header():
    from src.infrastructure.services.geolocation_service import extract_client_ip

    request = MagicMock()
    request.headers.get.side_effect = lambda key, default="": {
        "cf-connecting-ip": "203.0.113.1",
        "x-forwarded-for": "",
        "x-real-ip": "",
    }.get(key, default)

    ip = extract_client_ip(request)
    assert ip == "203.0.113.1"


def test_extract_ip_x_forwarded_for():
    from src.infrastructure.services.geolocation_service import extract_client_ip

    request = MagicMock()
    request.headers.get.side_effect = lambda key, default="": {
        "cf-connecting-ip": "",
        "x-forwarded-for": "10.0.0.1, 203.0.113.1",
        "x-real-ip": "",
    }.get(key, default)

    ip = extract_client_ip(request)
    assert ip == "10.0.0.1"


def test_extract_ip_x_real_ip():
    from src.infrastructure.services.geolocation_service import extract_client_ip

    request = MagicMock()
    request.headers.get.side_effect = lambda key, default="": {
        "cf-connecting-ip": "",
        "x-forwarded-for": "",
        "x-real-ip": "203.0.113.5",
    }.get(key, default)

    ip = extract_client_ip(request)
    assert ip == "203.0.113.5"


def test_extract_ip_fallback_client_host():
    from src.infrastructure.services.geolocation_service import extract_client_ip

    request = MagicMock()
    request.headers.get.side_effect = lambda key, default="": {
        "cf-connecting-ip": "",
        "x-forwarded-for": "",
        "x-real-ip": "",
    }.get(key, default)
    request.client.host = "10.0.0.2"

    ip = extract_client_ip(request)
    assert ip == "10.0.0.2"


def test_extract_ip_fallback_no_client():
    from src.infrastructure.services.geolocation_service import extract_client_ip

    request = MagicMock()
    request.headers.get.side_effect = lambda key, default="": {
        "cf-connecting-ip": "",
        "x-forwarded-for": "",
        "x-real-ip": "",
    }.get(key, default)
    request.client = None

    ip = extract_client_ip(request)
    assert ip == "unknown"
