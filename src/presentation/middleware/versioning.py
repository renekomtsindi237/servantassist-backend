"""
Middleware de versioning API.

Injecte dans chaque réponse HTTP les en-têtes de traçabilité et de version :

  X-API-Version    Numéro sémantique de l'API courante.
  X-Request-ID     Identifiant unique de la requête (UUID hex).
                   Repris du header entrant si présent (trace distribuée),
                   sinon généré ici.
  Vary             Indique les dimensions de variation du cache.

Deprecation (futur) :
  Quand une v2 sera créée, les routes /api/v1/* recevront automatiquement :
    Deprecation: <date-ISO>
    Sunset:      <date-ISO>
    Link:        </api/v2/...>; rel="successor-version"
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Mettre à jour ces constantes à chaque release
API_VERSION = "1.0.0"
API_RELEASE_DATE = "2025-05-19"

# Préfixes de routes dépréciées → date de fin de vie
# Format : {"/api/v0": "2026-01-01"}
_DEPRECATED_PREFIXES: dict[str, str] = {}


class VersioningMiddleware(BaseHTTPMiddleware):
    """Ajoute les en-têtes de version et de traçabilité à chaque réponse."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        # Stocker dans le state pour que les routers puissent l'inclure dans les logs
        request.state.request_id = request_id

        response = await call_next(request)

        response.headers["X-API-Version"] = API_VERSION
        response.headers["X-Request-ID"] = request_id
        response.headers["Vary"] = "Accept, Accept-Encoding"

        # Ajouter les avertissements de dépréciation si applicable
        path = request.url.path
        for prefix, sunset_date in _DEPRECATED_PREFIXES.items():
            if path.startswith(prefix):
                response.headers["Deprecation"] = API_RELEASE_DATE
                response.headers["Sunset"] = sunset_date
                break

        return response
