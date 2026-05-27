"""
Handlers d'exceptions FastAPI — ServantAssist

Enregistrés via app.add_exception_handler() dans main.py.
Chaque handler intercepte un type d'exception précis et retourne
une réponse JSON uniforme, sécurisée (sans fuite d'infos internes).

Hiérarchie de traitement :
  1. RequestValidationError  → 422 (erreurs Pydantic sur les inputs)
  2. HTTPException           → code HTTP tel quel (FastAPI natif)
  3. ServantAssistException  → code HTTP défini sur la classe métier
  4. SQLAlchemyError         → 503 masqué (jamais de détail DB en prod)
  5. Exception               → 500 masqué (never-expose pattern)
"""
from __future__ import annotations

import uuid

from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError

from src.core.exceptions import ServantAssistException
from src.infrastructure.config.settings import get_settings


# ── Réponse uniforme ───────────────────────────────────────────────────────
def _error_response(
    status: int,
    message: str,
    detail: str | None = None,
    error_id: str | None = None,
    errors: list | None = None,
) -> JSONResponse:
    body: dict = {"detail": message}
    if error_id:
        body["error_id"] = error_id
    if detail:
        body["info"] = detail
    if errors:
        body["errors"] = errors
    return JSONResponse(status_code=status, content=body)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    return (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else "unknown")
    )


# ── Traduction des types d'erreurs Pydantic ───────────────────────────────
_PYDANTIC_MSG: dict[str, str] = {
    "missing": "Ce champ est obligatoire.",
    "string_too_short": "Ce champ est trop court.",
    "string_too_long": "Ce champ est trop long.",
    "value_error": "La valeur fournie est incorrecte.",
    "type_error": "Le type de donnée fourni est incorrect.",
    "int_parsing": "Ce champ doit être un nombre entier.",
    "float_parsing": "Ce champ doit être un nombre décimal.",
    "bool_parsing": "Ce champ doit être vrai ou faux.",
    "uuid_parsing": "Ce champ doit être un identifiant valide.",
    "enum": "La valeur choisie ne fait pas partie des options autorisées.",
    "value_error.email": "L'adresse e-mail fournie est invalide.",
    "value_error.url": "L'URL fournie est invalide.",
    "value_error.list.min_items": "La liste doit contenir au moins un élément.",
    "value_error.list.max_items": "La liste contient trop d'éléments.",
    "value_error.number.not_ge": "La valeur est trop petite.",
    "value_error.number.not_le": "La valeur est trop grande.",
    "string_pattern_mismatch": "Le format de ce champ est incorrect.",
    "literal_error": "La valeur fournie n'est pas acceptée pour ce champ.",
    "too_short": "Ce champ est trop court.",
    "too_long": "Ce champ est trop long.",
    "greater_than_equal": "La valeur doit être supérieure ou égale au minimum autorisé.",
    "less_than_equal": "La valeur doit être inférieure ou égale au maximum autorisé.",
    "greater_than": "La valeur doit être strictement supérieure au minimum.",
    "less_than": "La valeur doit être strictement inférieure au maximum.",
    "json_invalid": "Le contenu envoyé n'est pas un JSON valide.",
    "date_from_datetime_parsing": "Ce champ doit être une date valide (ex: 2024-01-15).",
    "datetime_parsing": "Ce champ doit être une date/heure valide (ex: 2024-01-15T10:00:00).",
}

_FIELD_LABELS: dict[str, str] = {
    "email": "l'adresse e-mail",
    "password": "le mot de passe",
    "phone_number": "le numéro de téléphone",
    "first_name": "le prénom",
    "last_name": "le nom de famille",
    "role": "le rôle",
    "title": "le titre",
    "description": "la description",
    "date": "la date",
    "amount": "le montant",
    "code": "le code",
}


def _translate_pydantic(err: dict) -> str:
    err_type = err.get("type", "")
    raw_msg = err.get("msg", "")

    # Priorité : correspondance exacte sur le type
    if err_type in _PYDANTIC_MSG:
        return _PYDANTIC_MSG[err_type]

    # Fallback : correspondance partielle
    for key, msg in _PYDANTIC_MSG.items():
        if key in err_type or key in raw_msg.lower():
            return msg

    # Dernier recours : message original propre
    return raw_msg.replace("Value error, ", "").capitalize() or "Valeur non acceptée."


# ── Handler 1 : Erreurs de validation Pydantic (422) ──────────────────────
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """
    Transforme les erreurs Pydantic en messages lisibles en français.
    Masque les valeurs envoyées (peuvent contenir des données sensibles).
    """
    errors = []
    for err in exc.errors():
        locs = [str(loc) for loc in err["loc"] if loc != "body"]
        raw_field = locs[-1] if locs else "body"
        label = _FIELD_LABELS.get(raw_field, raw_field.replace("_", " "))
        errors.append(
            {
                "champ": label,
                "message": _translate_pydantic(err),
            }
        )

    logger.bind(
        event="validation_error",
        path=request.url.path,
        method=request.method,
        error_count=len(errors),
    ).info("Validation failed")

    return _error_response(
        status=422,
        message="Les données envoyées comportent des erreurs. Veuillez les corriger et réessayer.",
        errors=errors,
    )


# ── Handler 2 : HTTPException FastAPI/Starlette ───────────────────────────
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """
    Gère les HTTPException levées dans les routes et dépendances.
    Ajoute un error_id pour les 5xx.
    """
    error_id = _new_id() if exc.status_code >= 500 else None

    if exc.status_code >= 500:
        logger.bind(
            event="http_5xx",
            status=exc.status_code,
            path=request.url.path,
            client=_client_ip(request),
            error_id=error_id,
        ).error("HTTP {status}: {detail}", status=exc.status_code, detail=exc.detail)

    return _error_response(
        status=exc.status_code,
        message=str(exc.detail),
        error_id=error_id,
    )


# ── Handler 3 : Exceptions métier (ServantAssistException) ───────────────
async def domain_exception_handler(
    request: Request, exc: ServantAssistException
) -> JSONResponse:
    """
    Mappe les exceptions métier sur leur code HTTP.
    Les détails techniques ne sont exposés qu'en dev/staging.
    """
    settings = get_settings()
    error_id = _new_id() if exc.http_status >= 500 else None

    log = logger.bind(
        event="domain_exception",
        exception_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        status=exc.http_status,
        client=_client_ip(request),
        error_id=error_id,
    )

    if exc.http_status >= 500:
        log.error("Domain error: {msg}", msg=exc.message)
    else:
        log.info("Domain error: {msg}", msg=exc.message)

    detail = exc.detail if settings.APP_ENV != "production" else None

    return _error_response(
        status=exc.http_status,
        message=exc.message,
        detail=detail,
        error_id=error_id,
    )


# ── Handler 4 : Erreurs SQLAlchemy ───────────────────────────────────────
async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    """
    Masque totalement les erreurs DB en production (fuite de schéma).
    Expose l'IntegrityError comme un 409 Conflict lisible.
    """
    settings = get_settings()
    error_id = _new_id()

    logger.bind(
        event="db_error",
        exception_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        error_id=error_id,
    ).error("Database error: {exc}", exc=str(exc)[:300])

    # IntegrityError = doublon ou contrainte FK → 409 (sûr à exposer)
    if isinstance(exc, IntegrityError):
        return _error_response(
            status=409,
            message="Conflit : une ressource identique existe déjà.",
            error_id=error_id,
        )

    # OperationalError = DB injoignable → 503
    if isinstance(exc, OperationalError):
        return _error_response(
            status=503,
            message="Base de données temporairement indisponible.",
            error_id=error_id,
        )

    # Toute autre erreur SQLAlchemy → 500 masqué
    detail = str(exc)[:200] if settings.APP_ENV == "development" else None
    return _error_response(
        status=500,
        message="Erreur interne du serveur.",
        detail=detail,
        error_id=error_id,
    )


# ── Handler 5 : Exception générique non catchée ────────────────────────────
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Filet de sécurité final — ne laisse jamais fuiter de stack trace.
    Toujours loggé en ERROR pour Sentry / alerting.
    """
    import traceback

    settings = get_settings()
    error_id = _new_id()

    logger.bind(
        event="unhandled_exception",
        exception_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        client=_client_ip(request),
        error_id=error_id,
    ).error(
        "UNHANDLED: {exc}\n{tb}",
        exc=str(exc),
        tb=traceback.format_exc(),
    )

    if settings.APP_ENV == "production":
        return _error_response(
            status=500,
            message="Une erreur interne est survenue.",
            error_id=error_id,
        )

    return _error_response(
        status=500,
        message=str(exc),
        detail=type(exc).__name__,
        error_id=error_id,
    )
