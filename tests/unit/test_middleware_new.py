"""
Unit tests for:
- ErrorHandlerMiddleware
- PayloadEncryptionMiddleware
- RateLimitMiddleware / RateLimiter / _InMemoryTokenBucket
- SecurityHeadersMiddleware
- VersioningMiddleware
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_request(path: str = "/test", method: str = "GET", headers: dict = None) -> MagicMock:
    req = MagicMock()
    req.method = method
    req.url.path = path
    req.headers = headers or {}
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    req.state = MagicMock()
    return req


async def _call_next_ok(request) -> Response:
    resp = Response(content="ok", status_code=200)
    return resp


async def _call_next_raises(exc_class):
    async def _inner(request):
        raise exc_class("test error")

    return _inner


# ═══════════════════════════════════════════════════════════════════════════════
#  VersioningMiddleware
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_versioning_adds_headers():
    from src.presentation.middleware.versioning import VersioningMiddleware

    app = Starlette()
    mw = VersioningMiddleware(app)

    req = _make_request("/api/v1/users")
    result = await mw.dispatch(req, _call_next_ok)

    assert result.headers.get("X-API-Version") == "1.0.0"
    assert "X-Request-ID" in result.headers
    assert "Vary" in result.headers


@pytest.mark.asyncio
async def test_versioning_uses_incoming_request_id():
    from src.presentation.middleware.versioning import VersioningMiddleware

    app = Starlette()
    mw = VersioningMiddleware(app)

    req = _make_request("/api/v1/users", headers={"X-Request-ID": "myid123"})
    result = await mw.dispatch(req, _call_next_ok)

    assert result.headers["X-Request-ID"] == "myid123"


@pytest.mark.asyncio
async def test_versioning_generates_request_id_if_missing():
    from src.presentation.middleware.versioning import VersioningMiddleware

    app = Starlette()
    mw = VersioningMiddleware(app)

    req = _make_request("/api/v1/items")
    result = await mw.dispatch(req, _call_next_ok)

    rid = result.headers.get("X-Request-ID", "")
    assert len(rid) > 0


def test_versioning_via_fastapi_app():
    from src.presentation.middleware.versioning import VersioningMiddleware

    app = FastAPI()
    app.add_middleware(VersioningMiddleware)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    client = TestClient(app)
    r = client.get("/ping")
    assert r.status_code == 200
    assert "X-API-Version" in r.headers


# ═══════════════════════════════════════════════════════════════════════════════
#  SecurityHeadersMiddleware
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_security_headers_added():
    from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

    app = Starlette()
    mw = SecurityHeadersMiddleware(app)

    req = _make_request("/api/v1/data")
    result = await mw.dispatch(req, _call_next_ok)

    assert result.headers.get("X-Content-Type-Options") == "nosniff"
    assert result.headers.get("X-Frame-Options") == "DENY"
    assert result.headers.get("X-XSS-Protection") == "1; mode=block"
    assert "Content-Security-Policy" in result.headers
    assert "Referrer-Policy" in result.headers
    assert "Permissions-Policy" in result.headers


@pytest.mark.asyncio
async def test_security_headers_cache_control_on_auth_path():
    from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

    app = Starlette()
    mw = SecurityHeadersMiddleware(app)

    req = _make_request("/api/v1/auth/login")
    result = await mw.dispatch(req, _call_next_ok)

    assert "no-store" in result.headers.get("Cache-Control", "")


@pytest.mark.asyncio
async def test_security_headers_hsts_only_in_production():
    from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

    app = Starlette()
    mw = SecurityHeadersMiddleware(app)

    req = _make_request("/api/v1/users")

    with patch("src.presentation.middleware.security_headers.get_settings") as mock_settings:
        settings = MagicMock()
        settings.APP_ENV = "development"
        mock_settings.return_value = settings
        result = await mw.dispatch(req, _call_next_ok)

    assert "Strict-Transport-Security" not in result.headers


@pytest.mark.asyncio
async def test_security_headers_hsts_in_production():
    from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

    app = Starlette()
    mw = SecurityHeadersMiddleware(app)

    req = _make_request("/api/v1/users")

    with patch("src.presentation.middleware.security_headers.get_settings") as mock_settings:
        settings = MagicMock()
        settings.APP_ENV = "production"
        mock_settings.return_value = settings
        result = await mw.dispatch(req, _call_next_ok)

    assert "Strict-Transport-Security" in result.headers


@pytest.mark.asyncio
async def test_security_headers_powered_by():
    from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

    app = Starlette()
    mw = SecurityHeadersMiddleware(app)

    req = _make_request("/api/v1/data")
    result = await mw.dispatch(req, _call_next_ok)

    assert result.headers.get("X-Powered-By") == "ServantAssist"


def test_security_headers_via_fastapi():
    from src.presentation.middleware.security_headers import SecurityHeadersMiddleware

    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)

    @app.get("/safe")
    def safe():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/safe")
    assert r.status_code == 200
    assert r.headers.get("X-Content-Type-Options") == "nosniff"


# ═══════════════════════════════════════════════════════════════════════════════
#  ErrorHandlerMiddleware
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_error_handler_passes_through_normal_response():
    from src.presentation.middleware.error_handler import ErrorHandlerMiddleware

    app = Starlette()
    mw = ErrorHandlerMiddleware(app)

    req = _make_request("/test")
    result = await mw.dispatch(req, _call_next_ok)
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_error_handler_catches_servant_assist_exception():
    from src.core.exceptions import ValidationException
    from src.presentation.middleware.error_handler import ErrorHandlerMiddleware

    app = Starlette()
    mw = ErrorHandlerMiddleware(app)

    req = _make_request("/test")

    async def call_next_raises(r):
        raise ValidationException("bad input")

    result = await mw.dispatch(req, call_next_raises)
    assert result.status_code == 400
    import json

    body = json.loads(result.body)
    assert "bad input" in body["detail"]
    assert "error_id" in body


@pytest.mark.asyncio
async def test_error_handler_catches_sqlalchemy_error():
    from sqlalchemy.exc import OperationalError

    from src.presentation.middleware.error_handler import ErrorHandlerMiddleware

    app = Starlette()
    mw = ErrorHandlerMiddleware(app)

    req = _make_request("/test")

    async def call_next_raises(r):
        raise OperationalError("statement", {}, Exception("DB down"))

    result = await mw.dispatch(req, call_next_raises)
    assert result.status_code == 503
    import json

    body = json.loads(result.body)
    assert "error_id" in body


@pytest.mark.asyncio
async def test_error_handler_catches_generic_exception_production():
    from src.presentation.middleware.error_handler import ErrorHandlerMiddleware

    app = Starlette()
    mw = ErrorHandlerMiddleware(app)

    req = _make_request("/test")

    async def call_next_raises(r):
        raise RuntimeError("boom")

    with patch("src.presentation.middleware.error_handler.get_settings") as mock_settings:
        settings = MagicMock()
        settings.APP_ENV = "production"
        settings.APP_DEBUG = False
        mock_settings.return_value = settings

        result = await mw.dispatch(req, call_next_raises)

    assert result.status_code == 500
    import json

    body = json.loads(result.body)
    assert "Une erreur interne" in body["detail"]
    assert "error_id" in body


@pytest.mark.asyncio
async def test_error_handler_catches_generic_exception_dev():
    from src.presentation.middleware.error_handler import ErrorHandlerMiddleware

    app = Starlette()
    mw = ErrorHandlerMiddleware(app)

    req = _make_request("/test")

    async def call_next_raises(r):
        raise RuntimeError("dev error detail")

    with patch("src.presentation.middleware.error_handler.get_settings") as mock_settings:
        settings = MagicMock()
        settings.APP_ENV = "development"
        settings.APP_DEBUG = True
        mock_settings.return_value = settings

        result = await mw.dispatch(req, call_next_raises)

    assert result.status_code == 500
    import json

    body = json.loads(result.body)
    assert "dev error detail" in body["detail"]


# ═══════════════════════════════════════════════════════════════════════════════
#  PayloadEncryptionMiddleware
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_payload_encryption_disabled_passthrough():
    """When PAYLOAD_ENCRYPTION_ENABLED is False, all requests pass through."""
    import src.infrastructure.config.settings as settings_mod
    from src.presentation.middleware.payload_encryption import PayloadEncryptionMiddleware

    app = Starlette()
    mw = PayloadEncryptionMiddleware(app)
    req = _make_request("/api/v1/data", method="POST")

    settings_obj = MagicMock()
    settings_obj.PAYLOAD_ENCRYPTION_ENABLED = False

    with patch.object(settings_mod, "get_settings", return_value=settings_obj):
        result = await mw.dispatch(req, _call_next_ok)

    assert result.status_code == 200


@pytest.mark.asyncio
async def test_payload_encryption_get_method_passthrough():
    """GET requests are never decrypted."""
    import src.infrastructure.config.settings as settings_mod
    from src.presentation.middleware.payload_encryption import PayloadEncryptionMiddleware

    app = Starlette()
    mw = PayloadEncryptionMiddleware(app)
    req = _make_request("/api/v1/data", method="GET")

    settings_obj = MagicMock()
    settings_obj.PAYLOAD_ENCRYPTION_ENABLED = True

    with patch.object(settings_mod, "get_settings", return_value=settings_obj):
        result = await mw.dispatch(req, _call_next_ok)

    assert result.status_code == 200


@pytest.mark.asyncio
async def test_payload_encryption_no_pubkey_header_passthrough():
    """POST without the pubkey header passes through unchanged."""
    import src.infrastructure.config.settings as settings_mod
    from src.presentation.middleware.payload_encryption import PayloadEncryptionMiddleware

    app = Starlette()
    mw = PayloadEncryptionMiddleware(app)
    req = _make_request("/api/v1/data", method="POST", headers={})

    settings_obj = MagicMock()
    settings_obj.PAYLOAD_ENCRYPTION_ENABLED = True

    with patch.object(settings_mod, "get_settings", return_value=settings_obj):
        result = await mw.dispatch(req, _call_next_ok)

    assert result.status_code == 200


@pytest.mark.asyncio
async def test_payload_encryption_empty_body_returns_400():
    """POST with pubkey header but empty body returns 400."""
    import src.infrastructure.config.settings as settings_mod
    from src.presentation.middleware.payload_encryption import PayloadEncryptionMiddleware

    app = Starlette()
    mw = PayloadEncryptionMiddleware(app)
    req = _make_request("/api/v1/data", method="POST", headers={"x-client-pubkey": "ABC=="})
    req.body = AsyncMock(return_value=b"")

    settings_obj = MagicMock()
    settings_obj.PAYLOAD_ENCRYPTION_ENABLED = True

    with patch.object(settings_mod, "get_settings", return_value=settings_obj):
        result = await mw.dispatch(req, _call_next_ok)

    assert result.status_code == 400
    import json

    body = json.loads(result.body)
    assert "vide" in body["detail"]


@pytest.mark.asyncio
async def test_payload_encryption_decryption_value_error_returns_400():
    """Decryption ValueError (bad tag) returns 400."""
    import src.infrastructure.config.settings as settings_mod
    import src.infrastructure.security.payload_encryption as enc_mod
    from src.presentation.middleware.payload_encryption import PayloadEncryptionMiddleware

    app = Starlette()
    mw = PayloadEncryptionMiddleware(app)
    req = _make_request("/api/v1/data", method="POST", headers={"x-client-pubkey": "PUBKEYB64=="})
    req.body = AsyncMock(return_value=b"encrypted_data_here")

    settings_obj = MagicMock()
    settings_obj.PAYLOAD_ENCRYPTION_ENABLED = True

    encryptor = MagicMock()
    encryptor.decrypt_request.side_effect = ValueError("bad tag")

    with patch.object(settings_mod, "get_settings", return_value=settings_obj):
        with patch.object(enc_mod, "get_payload_encryptor", return_value=encryptor):
            result = await mw.dispatch(req, _call_next_ok)

    assert result.status_code == 400


@pytest.mark.asyncio
async def test_payload_encryption_runtime_error_returns_503():
    """RuntimeError (no private key) returns 503."""
    import src.infrastructure.config.settings as settings_mod
    import src.infrastructure.security.payload_encryption as enc_mod
    from src.presentation.middleware.payload_encryption import PayloadEncryptionMiddleware

    app = Starlette()
    mw = PayloadEncryptionMiddleware(app)
    req = _make_request("/api/v1/data", method="POST", headers={"x-client-pubkey": "PUBKEYB64=="})
    req.body = AsyncMock(return_value=b"encrypted_data_here")

    settings_obj = MagicMock()
    settings_obj.PAYLOAD_ENCRYPTION_ENABLED = True

    def raise_runtime():
        raise RuntimeError("no private key")

    with patch.object(settings_mod, "get_settings", return_value=settings_obj):
        with patch.object(enc_mod, "get_payload_encryptor", side_effect=RuntimeError("no private key")):
            result = await mw.dispatch(req, _call_next_ok)

    assert result.status_code == 503


@pytest.mark.asyncio
async def test_payload_encryption_success():
    """Successful decryption reinjects plaintext body."""
    import src.infrastructure.config.settings as settings_mod
    import src.infrastructure.security.payload_encryption as enc_mod
    from src.presentation.middleware.payload_encryption import PayloadEncryptionMiddleware

    app = Starlette()
    mw = PayloadEncryptionMiddleware(app)
    req = _make_request("/api/v1/data", method="POST", headers={"x-client-pubkey": "PUBKEYB64=="})
    req.body = AsyncMock(return_value=b"encrypted_payload")

    settings_obj = MagicMock()
    settings_obj.PAYLOAD_ENCRYPTION_ENABLED = True

    encryptor = MagicMock()
    encryptor.decrypt_request.return_value = b'{"key":"value"}'

    with patch.object(settings_mod, "get_settings", return_value=settings_obj):
        with patch.object(enc_mod, "get_payload_encryptor", return_value=encryptor):
            result = await mw.dispatch(req, _call_next_ok)

    assert result.status_code == 200
    encryptor.decrypt_request.assert_called_once_with("PUBKEYB64==", b"encrypted_payload")


# ═══════════════════════════════════════════════════════════════════════════════
#  RateLimitMiddleware / _InMemoryTokenBucket / RateLimiter
# ═══════════════════════════════════════════════════════════════════════════════


def test_in_memory_bucket_allows_under_limit():
    from src.presentation.middleware.rate_limit import _InMemoryTokenBucket

    bucket = _InMemoryTokenBucket()
    allowed, remaining = bucket.is_allowed("ip:test", max_requests=5, window=60)
    assert allowed is True
    assert remaining == 4


def test_in_memory_bucket_blocks_at_limit():
    from src.presentation.middleware.rate_limit import _InMemoryTokenBucket

    bucket = _InMemoryTokenBucket()
    for _ in range(3):
        bucket.is_allowed("ip:spam", max_requests=3, window=60)

    allowed, remaining = bucket.is_allowed("ip:spam", max_requests=3, window=60)
    assert allowed is False
    assert remaining == 0


def test_in_memory_bucket_different_keys_isolated():
    from src.presentation.middleware.rate_limit import _InMemoryTokenBucket

    bucket = _InMemoryTokenBucket()
    for _ in range(3):
        bucket.is_allowed("ip:user1", max_requests=3, window=60)

    # Another IP should still be allowed
    allowed, _ = bucket.is_allowed("ip:user2", max_requests=3, window=60)
    assert allowed is True


def test_in_memory_bucket_cleanup():
    import time as _time

    from src.presentation.middleware.rate_limit import _InMemoryTokenBucket

    bucket = _InMemoryTokenBucket()
    bucket.is_allowed("ip:old", max_requests=5, window=1)
    # Force old timestamps by modifying internally
    bucket._store["ip:old"] = [_time.monotonic() - 400]
    bucket.cleanup(max_age=300)
    assert "ip:old" not in bucket._store


def test_in_memory_bucket_cleanup_keeps_recent():
    from src.presentation.middleware.rate_limit import _InMemoryTokenBucket

    bucket = _InMemoryTokenBucket()
    bucket.is_allowed("ip:new", max_requests=5, window=60)
    bucket.cleanup(max_age=300)
    assert "ip:new" in bucket._store


@pytest.mark.asyncio
async def test_rate_limiter_uses_memory_by_default():
    from src.presentation.middleware.rate_limit import RateLimiter

    rl = RateLimiter()
    allowed, remaining = await rl.is_allowed("test_key", max_requests=10, window=60)
    assert allowed is True


@pytest.mark.asyncio
async def test_rate_limiter_configure_redis():
    from src.presentation.middleware.rate_limit import RateLimiter

    rl = RateLimiter()
    rl.configure_redis(None)
    assert rl._use_redis is False


@pytest.mark.asyncio
async def test_rate_limiter_redis_fallback_on_error():
    from src.presentation.middleware.rate_limit import RateLimiter, _RedisTokenBucket

    rl = RateLimiter()
    mock_redis_backend = AsyncMock()
    mock_redis_backend.is_allowed.side_effect = Exception("Redis down")
    rl._redis_backend = mock_redis_backend
    rl._use_redis = True

    allowed, remaining = await rl.is_allowed("test_key", max_requests=10, window=60)
    # Falls back to memory backend
    assert allowed is True
    assert rl._use_redis is False  # switched off after error


@pytest.mark.asyncio
async def test_rate_limit_middleware_allows_normal_request():
    from src.presentation.middleware.rate_limit import RateLimitMiddleware

    app = Starlette()
    mw = RateLimitMiddleware(app)

    req = _make_request("/api/v1/users")

    with patch("src.presentation.middleware.rate_limit.get_settings") as mock_settings:
        settings = MagicMock()
        settings.RATE_LIMIT_GLOBAL = 100
        settings.RATE_LIMIT_AUTH = 5
        settings.TRUST_PROXY_HEADERS = False
        mock_settings.return_value = settings

        with patch("src.presentation.middleware.rate_limit.rate_limiter") as mock_limiter:
            mock_limiter.is_allowed = AsyncMock(return_value=(True, 99))
            result = await mw.dispatch(req, _call_next_ok)

    assert result.status_code == 200
    assert result.headers.get("X-RateLimit-Limit") == "100"


@pytest.mark.asyncio
async def test_rate_limit_middleware_blocks_exceeded():
    from src.presentation.middleware.rate_limit import RateLimitMiddleware

    app = Starlette()
    mw = RateLimitMiddleware(app)

    req = _make_request("/api/v1/auth/login")

    with patch("src.presentation.middleware.rate_limit.get_settings") as mock_settings:
        settings = MagicMock()
        settings.RATE_LIMIT_GLOBAL = 60
        settings.RATE_LIMIT_AUTH = 5
        settings.TRUST_PROXY_HEADERS = False
        mock_settings.return_value = settings

        with patch("src.presentation.middleware.rate_limit.rate_limiter") as mock_limiter:
            mock_limiter.is_allowed = AsyncMock(return_value=(False, 0))
            result = await mw.dispatch(req, _call_next_ok)

    assert result.status_code == 429


def test_get_client_ip_direct():
    from src.presentation.middleware.rate_limit import _get_client_ip

    req = MagicMock()
    req.client = MagicMock()
    req.client.host = "1.2.3.4"
    req.headers = {}

    with patch("src.presentation.middleware.rate_limit.get_settings") as mock_settings:
        settings = MagicMock()
        settings.TRUST_PROXY_HEADERS = False
        mock_settings.return_value = settings

        ip = _get_client_ip(req)

    assert ip == "1.2.3.4"


def test_get_client_ip_from_x_forwarded_for():
    from src.presentation.middleware.rate_limit import _get_client_ip

    req = MagicMock()
    req.headers = {"x-forwarded-for": "5.6.7.8, 10.0.0.1"}
    req.client = MagicMock()
    req.client.host = "10.0.0.1"

    with patch("src.presentation.middleware.rate_limit.get_settings") as mock_settings:
        settings = MagicMock()
        settings.TRUST_PROXY_HEADERS = True
        mock_settings.return_value = settings

        ip = _get_client_ip(req)

    assert ip == "5.6.7.8"


def test_get_client_ip_from_x_real_ip():
    from src.presentation.middleware.rate_limit import _get_client_ip

    req = MagicMock()
    req.headers = {"x-real-ip": "9.10.11.12"}
    req.client = MagicMock()
    req.client.host = "10.0.0.1"

    with patch("src.presentation.middleware.rate_limit.get_settings") as mock_settings:
        settings = MagicMock()
        settings.TRUST_PROXY_HEADERS = True
        mock_settings.return_value = settings

        ip = _get_client_ip(req)

    assert ip == "9.10.11.12"


def test_get_client_ip_from_cf_connecting_ip():
    from src.presentation.middleware.rate_limit import _get_client_ip

    req = MagicMock()
    req.headers = {"cf-connecting-ip": "99.1.2.3"}
    req.client = MagicMock()
    req.client.host = "10.0.0.1"

    with patch("src.presentation.middleware.rate_limit.get_settings") as mock_settings:
        settings = MagicMock()
        settings.TRUST_PROXY_HEADERS = True
        mock_settings.return_value = settings

        ip = _get_client_ip(req)

    assert ip == "99.1.2.3"


def test_get_client_ip_no_client():
    from src.presentation.middleware.rate_limit import _get_client_ip

    req = MagicMock()
    req.headers = {}
    req.client = None

    with patch("src.presentation.middleware.rate_limit.get_settings") as mock_settings:
        settings = MagicMock()
        settings.TRUST_PROXY_HEADERS = False
        mock_settings.return_value = settings

        ip = _get_client_ip(req)

    assert ip == "unknown"


@pytest.mark.asyncio
async def test_redis_token_bucket_allowed():
    from src.presentation.middleware.rate_limit import _RedisTokenBucket

    mock_redis = MagicMock()
    pipe = AsyncMock()
    pipe.execute = AsyncMock(return_value=[0, 2, 1, 60])  # zremrange, zcard=2, zadd, expire
    mock_redis.pipeline.return_value = pipe

    bucket = _RedisTokenBucket(mock_redis)
    allowed, remaining = await bucket.is_allowed("ip:test", max_requests=5, window=60)
    assert allowed is True
    assert remaining == 2  # 5 - 2 - 1


@pytest.mark.asyncio
async def test_redis_token_bucket_blocked():
    from src.presentation.middleware.rate_limit import _RedisTokenBucket

    mock_redis = MagicMock()
    pipe = AsyncMock()
    pipe.execute = AsyncMock(return_value=[0, 5, 1, 60])  # count == max_requests
    mock_redis.pipeline.return_value = pipe

    bucket = _RedisTokenBucket(mock_redis)
    allowed, remaining = await bucket.is_allowed("ip:test", max_requests=5, window=60)
    assert allowed is False
    assert remaining == 0
