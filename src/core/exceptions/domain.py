"""
Exceptions métier — ServantAssist
Hiérarchie claire mappée sur les codes HTTP standard.
"""
from __future__ import annotations


class ServantAssistException(Exception):
    """Racine de toutes les exceptions applicatives."""
    http_status: int = 500
    default_message: str = "Une erreur interne est survenue."

    def __init__(self, message: str | None = None, detail: str | None = None):
        self.message = message or self.default_message
        self.detail = detail
        super().__init__(self.message)


# ── 400 Bad Request ────────────────────────────────────────────────────────
class ValidationException(ServantAssistException):
    """Données d'entrée invalides — règle métier ou format."""
    http_status = 400
    default_message = "Données invalides."


class BusinessRuleException(ServantAssistException):
    """Violation d'une règle métier (ex: doublon, état incompatible)."""
    http_status = 400
    default_message = "Opération non autorisée par les règles métier."


# ── 401 Unauthorized ──────────────────────────────────────────────────────
class UnauthorizedException(ServantAssistException):
    """Token absent, expiré ou invalide."""
    http_status = 401
    default_message = "Authentification requise."


class TokenExpiredException(UnauthorizedException):
    default_message = "Session expirée. Veuillez vous reconnecter."


class InvalidTokenException(UnauthorizedException):
    default_message = "Token invalide ou révoqué."


# ── 403 Forbidden ─────────────────────────────────────────────────────────
class ForbiddenException(ServantAssistException):
    """Authentifié mais sans les droits nécessaires."""
    http_status = 403
    default_message = "Accès interdit."


class InsufficientRoleException(ForbiddenException):
    default_message = "Votre rôle ne permet pas cette action."


# ── 404 Not Found ─────────────────────────────────────────────────────────
class NotFoundException(ServantAssistException):
    """Ressource introuvable."""
    http_status = 404
    default_message = "Ressource introuvable."

    def __init__(self, resource: str = "Ressource", identifier: str | None = None):
        msg = f"{resource} introuvable."
        if identifier:
            msg = f"{resource} '{identifier}' introuvable."
        super().__init__(message=msg)


# ── 409 Conflict ──────────────────────────────────────────────────────────
class ConflictException(ServantAssistException):
    """Conflit d'état — doublon, version concurrente, etc."""
    http_status = 409
    default_message = "Conflit : la ressource existe déjà ou est en cours de modification."


class DuplicateException(ConflictException):
    def __init__(self, resource: str = "Ressource", field: str | None = None):
        msg = f"{resource} existe déjà."
        if field:
            msg = f"{resource} avec ce {field} existe déjà."
        super().__init__(message=msg)


# ── 410 Gone ──────────────────────────────────────────────────────────────
class ResourceGoneException(ServantAssistException):
    """Ressource définitivement supprimée."""
    http_status = 410
    default_message = "Cette ressource n'existe plus."


# ── 422 Unprocessable Entity ──────────────────────────────────────────────
class UnprocessableException(ServantAssistException):
    """Données structurellement valides mais sémantiquement incorrectes."""
    http_status = 422
    default_message = "Impossible de traiter les données fournies."


# ── 429 Too Many Requests ─────────────────────────────────────────────────
class RateLimitException(ServantAssistException):
    """Trop de requêtes — rate limiting dépassé."""
    http_status = 429
    default_message = "Trop de requêtes. Veuillez réessayer dans quelques instants."


# ── 503 Service Unavailable ───────────────────────────────────────────────
class ExternalServiceException(ServantAssistException):
    """Échec d'un service externe (email, SMS, Supabase, R2…)."""
    http_status = 503
    default_message = "Service temporairement indisponible."

    def __init__(self, service: str = "Service externe", detail: str | None = None):
        super().__init__(
            message=f"{service} temporairement indisponible.",
            detail=detail,
        )


class DatabaseUnavailableException(ExternalServiceException):
    def __init__(self, detail: str | None = None):
        super().__init__(service="Base de données", detail=detail)
