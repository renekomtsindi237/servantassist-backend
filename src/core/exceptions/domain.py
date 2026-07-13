"""
Exceptions métier — ServantAssist
Hiérarchie claire mappée sur les codes HTTP standard.
"""

from __future__ import annotations


class ServantAssistException(Exception):
    """Racine de toutes les exceptions applicatives."""

    http_status: int = 500
    default_message: str = "An internal error occurred."

    def __init__(self, message: str | None = None, detail: str | None = None):
        self.message = message or self.default_message
        self.detail = detail
        super().__init__(self.message)


# ── 400 Bad Request ────────────────────────────────────────────────────────
class ValidationException(ServantAssistException):
    """Données d'entrée invalides — règle métier ou format."""

    http_status = 400
    default_message = "Invalid input."


class BusinessRuleException(ServantAssistException):
    """Violation d'une règle métier (ex: doublon, état incompatible)."""

    http_status = 400
    default_message = "Operation not allowed by business rules."


# ── 401 Unauthorized ──────────────────────────────────────────────────────
class UnauthorizedException(ServantAssistException):
    """Token absent, expiré ou invalide."""

    http_status = 401
    default_message = "Authentication required."


class TokenExpiredException(UnauthorizedException):
    default_message = "Session expired. Please log in again."


class InvalidTokenException(UnauthorizedException):
    default_message = "Invalid or revoked token."


# ── 403 Forbidden ─────────────────────────────────────────────────────────
class ForbiddenException(ServantAssistException):
    """Authentifié mais sans les droits nécessaires."""

    http_status = 403
    default_message = "Access forbidden."


class InsufficientRoleException(ForbiddenException):
    default_message = "Your role does not allow this action."


# ── 404 Not Found ─────────────────────────────────────────────────────────
class NotFoundException(ServantAssistException):
    """Ressource introuvable."""

    http_status = 404
    default_message = "Resource not found."

    def __init__(self, resource: str = "Ressource", identifier: str | None = None):
        # Resource messages are English for tests and API consumers
        msg = f"{resource} not found."
        if identifier:
            msg = f"{resource} '{identifier}' not found."
        super().__init__(message=msg)


# ── 409 Conflict ──────────────────────────────────────────────────────────
class ConflictException(ServantAssistException):
    """Conflit d'état — doublon, version concurrente, etc."""

    http_status = 409
    default_message = "Conflict: the resource already exists or is being modified."


class DuplicateException(ConflictException):
    def __init__(self, resource: str = "Ressource", field: str | None = None):
        msg = f"{resource} already exists."
        if field:
            msg = f"{resource} with this {field} already exists."
        super().__init__(message=msg)


# ── 410 Gone ──────────────────────────────────────────────────────────────
class ResourceGoneException(ServantAssistException):
    """Ressource définitivement supprimée."""

    http_status = 410
    default_message = "This resource no longer exists."


# ── 422 Unprocessable Entity ──────────────────────────────────────────────
class UnprocessableException(ServantAssistException):
    """Données structurellement valides mais sémantiquement incorrectes."""

    http_status = 422
    default_message = "Unable to process the provided data."


# ── 429 Too Many Requests ─────────────────────────────────────────────────
class RateLimitException(ServantAssistException):
    """Trop de requêtes — rate limiting dépassé."""

    http_status = 429
    default_message = "Too many requests. Please try again later."


# ── 503 Service Unavailable ───────────────────────────────────────────────
class ExternalServiceException(ServantAssistException):
    """Échec d'un service externe (email, SMS, Supabase, R2…)."""

    http_status = 503
    default_message = "Service temporarily unavailable."

    def __init__(self, service: str = "Service externe", detail: str | None = None):
        super().__init__(
            message=f"{service} temporarily unavailable.",
            detail=detail,
        )


class DatabaseUnavailableException(ExternalServiceException):
    def __init__(self, detail: str | None = None):
        super().__init__(service="Database", detail=detail)
