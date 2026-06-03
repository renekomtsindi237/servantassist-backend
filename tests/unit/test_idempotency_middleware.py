"""
Tests unitaires pour src/presentation/middleware/idempotency.py

Couvre :
- _InMemoryStore : get, set, mark_in_progress, is_in_progress, cleanup, TTL expiry
- IdempotencyMiddleware.dispatch :
    - Non-POST pass-through
    - POST sur endpoint exclu → pass-through
    - POST sans X-Idempotency-Key → pass-through
    - Cache hit → réponse en cache + header X-Idempotency-Replayed
    - In-progress → 409
    - Réponse 2xx → mise en cache
    - Réponse non-2xx → pas de cache
"""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.presentation.middleware.idempotency import (
    IdempotencyMiddleware,
    _InMemoryStore,
    _TTL_SECONDS,
)

# ── _InMemoryStore ─────────────────────────────────────────────────────────


class TestInMemoryStore:
    def test_get_miss_returns_none(self):
        store = _InMemoryStore()
        assert store.get("nonexistent") is None

    def test_set_and_get_roundtrip(self):
        store = _InMemoryStore()
        store.set("k1", 200, b'{"ok": true}', "application/json")
        result = store.get("k1")
        assert result is not None
        status, body, ct = result
        assert status == 200
        assert body == b'{"ok": true}'
        assert ct == "application/json"

    def test_get_expired_returns_none(self):
        store = _InMemoryStore()
        store.set("k2", 200, b"cached", "application/json")
        # Manually set created_at to past
        status_code, _, body, ct = store._store["k2"]
        store._store["k2"] = (status_code, int(time.time()) - _TTL_SECONDS - 1, body, ct)
        assert store.get("k2") is None

    def test_get_expired_removes_entry(self):
        store = _InMemoryStore()
        store.set("k3", 200, b"data", "text/plain")
        status_code, _, body, ct = store._store["k3"]
        store._store["k3"] = (status_code, int(time.time()) - _TTL_SECONDS - 1, body, ct)
        store.get("k3")
        assert "k3" not in store._store

    def test_mark_in_progress(self):
        store = _InMemoryStore()
        store.mark_in_progress("k4")
        assert "k4" in store._store
        assert store._store["k4"][0] == 0  # sentinel status code

    def test_is_in_progress_true(self):
        store = _InMemoryStore()
        store.mark_in_progress("k5")
        assert store.is_in_progress("k5") is True

    def test_is_in_progress_false_for_completed(self):
        store = _InMemoryStore()
        store.set("k6", 201, b"{}", "application/json")
        assert store.is_in_progress("k6") is False

    def test_is_in_progress_false_for_missing(self):
        store = _InMemoryStore()
        assert store.is_in_progress("k_missing") is False

    def test_cleanup_removes_expired(self):
        store = _InMemoryStore()
        store.set("expired_key", 200, b"x", "application/json")
        status_code, _, body, ct = store._store["expired_key"]
        store._store["expired_key"] = (status_code, int(time.time()) - _TTL_SECONDS - 100, body, ct)
        store.set("fresh_key", 200, b"y", "application/json")
        store.cleanup()
        assert "expired_key" not in store._store
        assert "fresh_key" in store._store

    def test_cleanup_keeps_valid_entries(self):
        store = _InMemoryStore()
        store.set("valid", 200, b"v", "application/json")
        store.cleanup()
        assert "valid" in store._store


# ── IdempotencyMiddleware ──────────────────────────────────────────────────


def make_response(status_code: int, body: bytes = b'{"ok":true}', content_type: str = "application/json"):
    """Create a mock Starlette Response."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = {"content-type": content_type}

    async def _iter():
        yield body

    response.body_iterator = _iter()
    return response


def make_request(method: str = "POST", path: str = "/api/v1/items", idempotency_key: str = ""):
    req = MagicMock()
    req.method = method
    req.url.path = path
    req.headers.get.return_value = idempotency_key
    return req


class TestIdempotencyMiddlewareDispatch:
    @pytest.mark.asyncio
    async def test_get_request_passes_through(self):
        """Non-POST → no idempotency logic applied."""
        app = MagicMock()
        middleware = IdempotencyMiddleware(app=app)

        req = make_request(method="GET", path="/api/v1/items")
        fake_response = MagicMock()
        call_next = AsyncMock(return_value=fake_response)

        result = await middleware.dispatch(req, call_next)
        assert result is fake_response
        call_next.assert_called_once()

    @pytest.mark.asyncio
    async def test_put_request_passes_through(self):
        app = MagicMock()
        middleware = IdempotencyMiddleware(app=app)

        req = make_request(method="PUT", path="/api/v1/items/1")
        fake_response = MagicMock()
        call_next = AsyncMock(return_value=fake_response)

        result = await middleware.dispatch(req, call_next)
        assert result is fake_response

    @pytest.mark.asyncio
    async def test_excluded_endpoint_passes_through(self):
        """POST on auth/login → excluded, pass through without idempotency."""
        app = MagicMock()
        middleware = IdempotencyMiddleware(app=app)

        req = make_request(method="POST", path="/api/v1/auth/login", idempotency_key="some-key")
        fake_response = MagicMock()
        call_next = AsyncMock(return_value=fake_response)

        result = await middleware.dispatch(req, call_next)
        assert result is fake_response

    @pytest.mark.asyncio
    async def test_excluded_register_passes_through(self):
        app = MagicMock()
        middleware = IdempotencyMiddleware(app=app)

        req = make_request(method="POST", path="/api/v1/auth/register", idempotency_key="k")
        fake_response = MagicMock()
        call_next = AsyncMock(return_value=fake_response)

        result = await middleware.dispatch(req, call_next)
        assert result is fake_response

    @pytest.mark.asyncio
    async def test_post_without_key_passes_through(self):
        """POST without X-Idempotency-Key → pass through (key not mandatory)."""
        app = MagicMock()
        middleware = IdempotencyMiddleware(app=app)

        req = make_request(method="POST", path="/api/v1/events", idempotency_key="")
        fake_response = MagicMock()
        call_next = AsyncMock(return_value=fake_response)

        result = await middleware.dispatch(req, call_next)
        assert result is fake_response

    @pytest.mark.asyncio
    async def test_in_progress_returns_409(self):
        """Second concurrent POST with same key → 409."""
        from src.presentation.middleware.idempotency import _memory_store
        import hashlib

        app = MagicMock()
        middleware = IdempotencyMiddleware(app=app)
        key = "concurrent-test-key-unique-xyz"
        path = "/api/v1/create-something"
        composite = hashlib.sha256(f"{path}:{key}".encode()).hexdigest()

        # Pre-set as in-progress
        _memory_store.mark_in_progress(composite)

        try:
            req = make_request(method="POST", path=path, idempotency_key=key)
            req.headers.get.return_value = key
            call_next = AsyncMock()

            result = await middleware.dispatch(req, call_next)
            assert result.status_code == 409
        finally:
            _memory_store._store.pop(composite, None)

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_response(self):
        """Second POST with same key after success → cached response."""
        from src.presentation.middleware.idempotency import _memory_store
        import hashlib

        app = MagicMock()
        middleware = IdempotencyMiddleware(app=app)
        key = "cache-hit-test-key-unique-abc"
        path = "/api/v1/cached-endpoint"
        composite = hashlib.sha256(f"{path}:{key}".encode()).hexdigest()

        # Pre-populate cache
        _memory_store.set(composite, 201, b'{"id":"123"}', "application/json")

        try:
            req = make_request(method="POST", path=path, idempotency_key=key)
            req.headers.get.return_value = key
            call_next = AsyncMock()

            result = await middleware.dispatch(req, call_next)
            assert result.status_code == 201
            assert result.headers.get("X-Idempotency-Replayed") == "true"
            call_next.assert_not_called()
        finally:
            _memory_store._store.pop(composite, None)

    @pytest.mark.asyncio
    async def test_non_2xx_response_not_cached(self):
        """POST with non-2xx response → not cached, key removed."""
        from src.presentation.middleware.idempotency import _memory_store
        import hashlib

        app = MagicMock()
        middleware = IdempotencyMiddleware(app=app)
        key = "non-2xx-test-key-unique-def"
        path = "/api/v1/fail-endpoint"
        composite = hashlib.sha256(f"{path}:{key}".encode()).hexdigest()

        error_response = make_response(400, b'{"detail":"bad"}', "application/json")
        call_next = AsyncMock(return_value=error_response)

        req = make_request(method="POST", path=path, idempotency_key=key)
        req.headers.get.return_value = key

        try:
            await middleware.dispatch(req, call_next)
            # Should not be in cache
            assert _memory_store.get(composite) is None
        finally:
            _memory_store._store.pop(composite, None)

    @pytest.mark.asyncio
    async def test_2xx_response_cached(self):
        """POST with 2xx response → cached for subsequent calls."""
        from src.presentation.middleware.idempotency import _memory_store
        import hashlib

        app = MagicMock()
        middleware = IdempotencyMiddleware(app=app)
        key = "success-cache-test-key-unique-ghi"
        path = "/api/v1/success-endpoint"
        composite = hashlib.sha256(f"{path}:{key}".encode()).hexdigest()

        success_body = b'{"id":"new-resource"}'
        success_response = make_response(201, success_body, "application/json")
        call_next = AsyncMock(return_value=success_response)

        req = make_request(method="POST", path=path, idempotency_key=key)
        req.headers.get.return_value = key

        try:
            result = await middleware.dispatch(req, call_next)
            assert result.status_code == 201
            # Now the key should be in cache
            cached = _memory_store.get(composite)
            assert cached is not None
            cached_status, cached_body, _ = cached
            assert cached_status == 201
            assert cached_body == success_body
        finally:
            _memory_store._store.pop(composite, None)
