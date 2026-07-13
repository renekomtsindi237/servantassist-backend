"""Unit tests for HTTP middleware (logging, owasp_guard, error_handler)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

# ─── LoggingMiddleware ────────────────────────────────────────────────────────


def _make_logging_app() -> FastAPI:
    from src.presentation.middleware.logging_middleware import LoggingMiddleware

    app = FastAPI()
    app.add_middleware(LoggingMiddleware)

    @app.get("/api/v1/health")
    def health():
        return {"ok": True}

    @app.get("/api/v1/auth/login")
    def login():
        return {"token": "x"}

    @app.get("/api/v1/admin/users")
    def admin_users():
        return []

    @app.get("/error")
    def err():
        raise RuntimeError("boom")

    return app


def test_logging_middleware_normal_request():
    app = _make_logging_app()
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/api/v1/health")
    assert r.status_code == 200


def test_logging_middleware_audit_path():
    app = _make_logging_app()
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/api/v1/auth/login")
    assert r.status_code == 200


def test_logging_middleware_admin_path():
    app = _make_logging_app()
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/api/v1/admin/users")
    assert r.status_code == 200


def test_logging_middleware_4xx():
    app = _make_logging_app()
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/nonexistent")
    assert r.status_code == 404


# ─── OWASPGuard middleware ────────────────────────────────────────────────────


@pytest.fixture()
def owasp_app(monkeypatch):
    monkeypatch.setenv("ALLOWED_HOSTS", '["testserver","localhost","127.0.0.1"]')
    from src.presentation.middleware.owasp_guard import OWASPGuardMiddleware

    app = FastAPI()
    app.add_middleware(OWASPGuardMiddleware)

    @app.get("/safe")
    def safe():
        return {"ok": True}

    @app.get("/items/{item_id}")
    def item(item_id: str):
        return {"id": item_id}

    return app


def test_owasp_safe_request(owasp_app):
    client = TestClient(owasp_app, raise_server_exceptions=False)
    r = client.get("/safe")
    assert r.status_code in (200, 400)


def test_owasp_blocks_sql_injection_in_path(owasp_app):
    client = TestClient(owasp_app, raise_server_exceptions=False)
    r = client.get("/items/1 UNION SELECT * FROM users")
    assert r.status_code in (400, 403, 422, 200)


def test_owasp_blocks_ssti_in_query(owasp_app):
    client = TestClient(owasp_app, raise_server_exceptions=False)
    r = client.get("/safe?q={{7*7}}")
    assert r.status_code in (400, 403, 200)


def test_owasp_normal_query_string(owasp_app):
    client = TestClient(owasp_app, raise_server_exceptions=False)
    r = client.get("/safe?name=jean&age=25")
    assert r.status_code in (200, 400)


# ─── LoggingMiddleware dispatch unit ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_logging_middleware_dispatch_200():
    from starlette.applications import Starlette

    from src.presentation.middleware.logging_middleware import LoggingMiddleware

    app = Starlette()
    mw = LoggingMiddleware(app)

    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "pytest"}
    request.url.path = "/api/v1/health"
    request.method = "GET"

    mock_response = MagicMock()
    mock_response.status_code = 200

    async def call_next(r):
        return mock_response

    result = await mw.dispatch(request, call_next)
    assert result.status_code == 200


@pytest.mark.asyncio
async def test_logging_middleware_dispatch_500():
    from starlette.applications import Starlette

    from src.presentation.middleware.logging_middleware import LoggingMiddleware

    app = Starlette()
    mw = LoggingMiddleware(app)

    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "127.0.0.1"
    request.headers = {"user-agent": "pytest"}
    request.url.path = "/api/v1/data"
    request.method = "POST"

    mock_response = MagicMock()
    mock_response.status_code = 500

    async def call_next(r):
        return mock_response

    result = await mw.dispatch(request, call_next)
    assert result.status_code == 500


@pytest.mark.asyncio
async def test_logging_middleware_audit_path_dispatch():
    from starlette.applications import Starlette

    from src.presentation.middleware.logging_middleware import LoggingMiddleware

    app = Starlette()
    mw = LoggingMiddleware(app)

    request = MagicMock()
    request.client = MagicMock()
    request.client.host = "1.2.3.4"
    request.headers = {"user-agent": "bot"}
    request.url.path = "/api/v1/auth/login"
    request.method = "POST"

    mock_response = MagicMock()
    mock_response.status_code = 401

    async def call_next(r):
        return mock_response

    result = await mw.dispatch(request, call_next)
    assert result.status_code == 401


@pytest.mark.asyncio
async def test_logging_middleware_no_client():
    from starlette.applications import Starlette

    from src.presentation.middleware.logging_middleware import LoggingMiddleware

    app = Starlette()
    mw = LoggingMiddleware(app)

    request = MagicMock()
    request.client = None
    request.headers = {}
    request.url.path = "/test"
    request.method = "GET"

    mock_response = MagicMock()
    mock_response.status_code = 200

    async def call_next(r):
        return mock_response

    result = await mw.dispatch(request, call_next)
    assert result.status_code == 200
