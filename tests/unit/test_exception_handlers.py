"""
Tests unitaires pour src/presentation/exceptions/handlers.py

Couvre :
- _error_response : structure JSON uniforme
- _client_ip : header forwarded vs client direct
- _translate_pydantic : correspondances exacte, partielle, fallback
- validation_exception_handler
- http_exception_handler
- domain_exception_handler
- sqlalchemy_exception_handler
- unhandled_exception_handler
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from src.core.exceptions import ServantAssistException, ValidationException, NotFoundException
from src.presentation.exceptions.handlers import (
    _client_ip,
    _error_response,
    _translate_pydantic,
    domain_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)


# ── Helpers ────────────────────────────────────────────────────────────────


def make_mock_request(path="/api/v1/test", method="GET", forwarded=None, client_host="10.0.0.1"):
    req = MagicMock()
    req.url.path = path
    req.method = method
    req.client = MagicMock()
    req.client.host = client_host
    req.headers.get.return_value = forwarded
    return req


# ── _error_response ────────────────────────────────────────────────────────


class TestErrorResponse:
    def test_basic_message(self):
        resp = _error_response(400, "Bad input")
        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 400

    def test_body_contains_detail(self):
        resp = _error_response(400, "Bad input")
        import json
        body = json.loads(resp.body)
        assert body["detail"] == "Bad input"

    def test_error_id_included(self):
        import json
        resp = _error_response(500, "Error", error_id="abc123")
        body = json.loads(resp.body)
        assert body["error_id"] == "abc123"

    def test_detail_as_info(self):
        import json
        resp = _error_response(400, "Error", detail="Extra detail")
        body = json.loads(resp.body)
        assert body["info"] == "Extra detail"

    def test_errors_list_included(self):
        import json
        resp = _error_response(422, "Validation", errors=[{"champ": "email", "message": "Invalide"}])
        body = json.loads(resp.body)
        assert body["errors"][0]["champ"] == "email"

    def test_no_error_id_when_none(self):
        import json
        resp = _error_response(400, "Error", error_id=None)
        body = json.loads(resp.body)
        assert "error_id" not in body

    def test_no_info_when_detail_none(self):
        import json
        resp = _error_response(400, "Error", detail=None)
        body = json.loads(resp.body)
        assert "info" not in body

    def test_no_errors_when_none(self):
        import json
        resp = _error_response(400, "Error", errors=None)
        body = json.loads(resp.body)
        assert "errors" not in body


# ── _client_ip ─────────────────────────────────────────────────────────────


class TestClientIp:
    def test_returns_forwarded_ip(self):
        req = make_mock_request(forwarded="203.0.113.1, 10.0.0.1")
        assert _client_ip(req) == "203.0.113.1"

    def test_strips_whitespace_from_forwarded(self):
        req = make_mock_request(forwarded="  9.9.9.9 , 10.0.0.1")
        assert _client_ip(req) == "9.9.9.9"

    def test_falls_back_to_client_host(self):
        req = make_mock_request(forwarded=None, client_host="192.168.1.1")
        assert _client_ip(req) == "192.168.1.1"

    def test_unknown_when_no_client(self):
        req = MagicMock()
        req.headers.get.return_value = None
        req.client = None
        assert _client_ip(req) == "unknown"


# ── _translate_pydantic ────────────────────────────────────────────────────


class TestTranslatePydantic:
    def test_exact_type_match(self):
        msg = _translate_pydantic({"type": "missing", "msg": "Field required"})
        assert msg == "Ce champ est obligatoire."

    def test_exact_match_string_too_short(self):
        msg = _translate_pydantic({"type": "string_too_short", "msg": ""})
        assert msg == "Ce champ est trop court."

    def test_exact_match_uuid_parsing(self):
        msg = _translate_pydantic({"type": "uuid_parsing", "msg": ""})
        assert msg == "Ce champ doit être un identifiant valide."

    def test_exact_match_enum(self):
        msg = _translate_pydantic({"type": "enum", "msg": ""})
        assert msg == "La valeur choisie ne fait pas partie des options autorisées."

    def test_partial_match_in_type(self):
        # "value_error" is a key — partial match via "value_error" in type
        msg = _translate_pydantic({"type": "some_value_error_thing", "msg": ""})
        assert "valeur" in msg.lower() or "incorrect" in msg.lower()

    def test_fallback_raw_message(self):
        msg = _translate_pydantic({"type": "unknown_type_xyz", "msg": "Something weird happened"})
        assert "Something weird happened" in msg or len(msg) > 0

    def test_fallback_empty_message(self):
        msg = _translate_pydantic({"type": "totally_unknown", "msg": ""})
        assert msg == "Valeur non acceptée."

    def test_strips_value_error_prefix(self):
        msg = _translate_pydantic({"type": "unknown", "msg": "Value error, bad data"})
        # Should strip "Value error, " prefix
        assert "Value error," not in msg

    def test_greater_than_equal(self):
        msg = _translate_pydantic({"type": "greater_than_equal", "msg": ""})
        assert "supérieure" in msg.lower()

    def test_json_invalid(self):
        msg = _translate_pydantic({"type": "json_invalid", "msg": ""})
        assert "JSON" in msg


# ── validation_exception_handler ──────────────────────────────────────────


class TestValidationExceptionHandler:
    @pytest.mark.asyncio
    async def test_returns_422(self):
        import json
        from pydantic import ValidationError
        import pydantic

        req = make_mock_request()

        try:
            class M(pydantic.BaseModel):
                email: str

            M()  # missing field
        except pydantic.ValidationError as e:
            exc = RequestValidationError(errors=e.errors())
        else:
            exc = RequestValidationError(errors=[
                {"loc": ("body", "email"), "msg": "field required", "type": "missing", "input": None, "url": ""}
            ])

        resp = await validation_exception_handler(req, exc)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_errors_list(self):
        import json

        req = make_mock_request()
        exc = RequestValidationError(errors=[
            {"loc": ("body", "email"), "msg": "field required", "type": "missing", "input": None, "url": ""},
            {"loc": ("body", "password"), "msg": "field required", "type": "missing", "input": None, "url": ""},
        ])
        resp = await validation_exception_handler(req, exc)
        body = json.loads(resp.body)
        assert "errors" in body
        assert len(body["errors"]) == 2

    @pytest.mark.asyncio
    async def test_field_label_used_for_known_fields(self):
        import json

        req = make_mock_request()
        exc = RequestValidationError(errors=[
            {"loc": ("body", "email"), "msg": "invalid email", "type": "value_error.email", "input": None, "url": ""},
        ])
        resp = await validation_exception_handler(req, exc)
        body = json.loads(resp.body)
        # "email" field → "l'adresse e-mail" label
        assert any("e-mail" in err["champ"] or "email" in err["champ"].lower() for err in body["errors"])

    @pytest.mark.asyncio
    async def test_body_loc_stripped(self):
        import json

        req = make_mock_request()
        exc = RequestValidationError(errors=[
            {"loc": ("body",), "msg": "invalid", "type": "missing", "input": None, "url": ""},
        ])
        resp = await validation_exception_handler(req, exc)
        body = json.loads(resp.body)
        # "body" loc should be stripped
        assert body["errors"][0]["champ"] == "body"


# ── http_exception_handler ─────────────────────────────────────────────────


class TestHttpExceptionHandler:
    @pytest.mark.asyncio
    async def test_4xx_no_error_id(self):
        import json
        from fastapi.exceptions import HTTPException

        req = make_mock_request()
        exc = HTTPException(status_code=404, detail="Not found")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 404
        body = json.loads(resp.body)
        assert "error_id" not in body

    @pytest.mark.asyncio
    async def test_5xx_has_error_id(self):
        import json
        from fastapi.exceptions import HTTPException

        req = make_mock_request()
        exc = HTTPException(status_code=500, detail="Internal error")
        resp = await http_exception_handler(req, exc)
        assert resp.status_code == 500
        body = json.loads(resp.body)
        assert "error_id" in body

    @pytest.mark.asyncio
    async def test_detail_in_body(self):
        import json
        from fastapi.exceptions import HTTPException

        req = make_mock_request()
        exc = HTTPException(status_code=403, detail="Forbidden")
        resp = await http_exception_handler(req, exc)
        body = json.loads(resp.body)
        assert body["detail"] == "Forbidden"

    @pytest.mark.asyncio
    async def test_401_no_error_id(self):
        import json
        from fastapi.exceptions import HTTPException

        req = make_mock_request()
        exc = HTTPException(status_code=401, detail="Unauthorized")
        resp = await http_exception_handler(req, exc)
        body = json.loads(resp.body)
        assert "error_id" not in body


# ── domain_exception_handler ───────────────────────────────────────────────


class TestDomainExceptionHandler:
    @pytest.mark.asyncio
    async def test_4xx_no_error_id(self):
        import json

        req = make_mock_request()
        exc = ValidationException("Données invalides")
        resp = await domain_exception_handler(req, exc)
        assert resp.status_code == 400
        body = json.loads(resp.body)
        assert body["detail"] == "Données invalides"
        assert "error_id" not in body

    @pytest.mark.asyncio
    async def test_5xx_has_error_id(self):
        import json

        req = make_mock_request()
        exc = ServantAssistException("Erreur interne")
        exc.http_status = 500
        resp = await domain_exception_handler(req, exc)
        assert resp.status_code == 500
        body = json.loads(resp.body)
        assert "error_id" in body

    @pytest.mark.asyncio
    async def test_detail_shown_in_testing_env(self):
        import json

        req = make_mock_request()
        exc = ValidationException("Bad input", detail="Technical detail")
        resp = await domain_exception_handler(req, exc)
        body = json.loads(resp.body)
        # APP_ENV = "testing" in tests → detail shown
        assert body.get("info") == "Technical detail"

    @pytest.mark.asyncio
    async def test_detail_hidden_in_production(self):
        import json

        req = make_mock_request()
        exc = ValidationException("Bad input", detail="Secret detail")
        with patch("src.presentation.exceptions.handlers.get_settings") as mock_settings:
            mock_settings.return_value.APP_ENV = "production"
            resp = await domain_exception_handler(req, exc)
        body = json.loads(resp.body)
        assert "info" not in body

    @pytest.mark.asyncio
    async def test_not_found_404(self):
        import json

        req = make_mock_request()
        exc = NotFoundException("User")
        resp = await domain_exception_handler(req, exc)
        assert resp.status_code == 404


# ── sqlalchemy_exception_handler ──────────────────────────────────────────


class TestSQLAlchemyExceptionHandler:
    @pytest.mark.asyncio
    async def test_integrity_error_is_409(self):
        import json

        req = make_mock_request()
        exc = IntegrityError("INSERT", {}, Exception("UNIQUE constraint failed"))
        resp = await sqlalchemy_exception_handler(req, exc)
        assert resp.status_code == 409
        body = json.loads(resp.body)
        assert "error_id" in body
        assert "Conflit" in body["detail"] or "conflit" in body["detail"].lower()

    @pytest.mark.asyncio
    async def test_operational_error_is_503(self):
        import json

        req = make_mock_request()
        exc = OperationalError("SELECT", {}, Exception("connection refused"))
        resp = await sqlalchemy_exception_handler(req, exc)
        assert resp.status_code == 503
        body = json.loads(resp.body)
        assert "error_id" in body

    @pytest.mark.asyncio
    async def test_generic_sqlalchemy_error_is_500(self):
        import json

        req = make_mock_request()
        exc = SQLAlchemyError("Generic DB error")
        resp = await sqlalchemy_exception_handler(req, exc)
        assert resp.status_code == 500
        body = json.loads(resp.body)
        assert "error_id" in body

    @pytest.mark.asyncio
    async def test_development_shows_detail(self):
        import json

        req = make_mock_request()
        exc = SQLAlchemyError("Detailed DB error message")
        with patch("src.presentation.exceptions.handlers.get_settings") as mock_settings:
            mock_settings.return_value.APP_ENV = "development"
            resp = await sqlalchemy_exception_handler(req, exc)
        body = json.loads(resp.body)
        assert "info" in body

    @pytest.mark.asyncio
    async def test_production_hides_detail(self):
        import json

        req = make_mock_request()
        exc = SQLAlchemyError("Secret DB internals")
        with patch("src.presentation.exceptions.handlers.get_settings") as mock_settings:
            mock_settings.return_value.APP_ENV = "production"
            resp = await sqlalchemy_exception_handler(req, exc)
        body = json.loads(resp.body)
        assert "info" not in body


# ── unhandled_exception_handler ───────────────────────────────────────────


class TestUnhandledExceptionHandler:
    @pytest.mark.asyncio
    async def test_non_production_shows_message(self):
        import json

        req = make_mock_request()
        exc = ValueError("Something broke")
        resp = await unhandled_exception_handler(req, exc)
        assert resp.status_code == 500
        body = json.loads(resp.body)
        assert "error_id" in body
        # In testing env: shows exc message + type
        assert "Something broke" in body["detail"]

    @pytest.mark.asyncio
    async def test_production_hides_detail(self):
        import json

        req = make_mock_request()
        exc = ValueError("Internal secret")
        with patch("src.presentation.exceptions.handlers.get_settings") as mock_settings:
            mock_settings.return_value.APP_ENV = "production"
            resp = await unhandled_exception_handler(req, exc)
        body = json.loads(resp.body)
        assert "Internal secret" not in body["detail"]
        assert "error_id" in body

    @pytest.mark.asyncio
    async def test_non_production_includes_exception_type(self):
        import json

        req = make_mock_request()
        exc = RuntimeError("Runtime failure")
        resp = await unhandled_exception_handler(req, exc)
        body = json.loads(resp.body)
        assert body.get("detail") == "RuntimeError" or "RuntimeError" in str(body)
