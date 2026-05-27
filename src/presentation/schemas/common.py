"""
Schemas communs — réutilisables dans tous les modules.

Pagination
----------
  PaginatedResponse[T]   Réponse paginée générique avec liens RFC 5988.
  PageLinks              Navigation : first / prev / self / next / last.
  build_paginated_response()  Constructeur pratique pour les routers.

Références inter-ressources (HATEOAS léger)
-------------------------------------------
  ResourceLink           Un lien href + method.
  make_link()            Raccourci de construction.

Erreurs standardisées
---------------------
  ApiError               Corps uniforme pour tous les 4xx/5xx.

Bonnes pratiques appliquées
---------------------------
  - PaginatedResponse reste Generic[T] : zéro duplication dans les modules.
  - Les liens sont optionnels → aucun endpoint existant n'est cassé.
  - build_paginated_response() accepte une Request FastAPI pour déduire
    l'URL de base automatiquement.
"""

from math import ceil
from typing import Dict, Generic, List, Optional, TypeVar
from uuid import UUID

from fastapi import Request
from pydantic import BaseModel, Field

T = TypeVar("T")

# ── Constante de base de l'API ────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"


# ═══════════════════════════════════════════════════════════════════════════
#  PAGINATION
# ═══════════════════════════════════════════════════════════════════════════


class PageLinks(BaseModel):
    """Liens de navigation RFC 5988 pour les listes paginées."""

    first: Optional[str] = Field(default=None, description="Première page")
    prev: Optional[str] = Field(default=None, description="Page précédente")
    self: Optional[str] = Field(default=None, description="Page courante")
    next: Optional[str] = Field(default=None, description="Page suivante")
    last: Optional[str] = Field(default=None, description="Dernière page")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Réponse paginée générique.

    Utilisée par tous les endpoints de liste :
        GET /api/v1/users
        GET /api/v1/discipline
        GET /api/v1/attendance
        … etc.

    Le champ ``links`` est optionnel pour une compatibilité descendante totale :
    les routers qui passent un objet Request obtiendront les liens automatiquement
    via build_paginated_response() ; les autres continuent de fonctionner sans
    modification.
    """

    items: List[T]
    total: int = Field(description="Nombre total d'éléments (toutes pages)")
    page: int = Field(description="Numéro de la page courante (≥ 1)")
    page_size: int = Field(description="Nombre d'éléments par page")
    total_pages: int = Field(description="Nombre total de pages")
    links: Optional[PageLinks] = Field(
        default=None,
        description="Liens de navigation RFC 5988 (first/prev/self/next/last)",
    )

    model_config = {"populate_by_name": True}


def _build_page_links(base_url: str, page: int, page_size: int, total: int) -> PageLinks:
    total_pages = max(1, ceil(total / page_size))

    def _url(p: int) -> str:
        return f"{base_url}?page={p}&page_size={page_size}"

    return PageLinks(
        first=_url(1),
        prev=_url(page - 1) if page > 1 else None,
        self=_url(page),
        next=_url(page + 1) if page < total_pages else None,
        last=_url(total_pages),
    )


def build_paginated_response(
    items: List,
    total: int,
    page: int,
    page_size: int,
    request: Optional[Request] = None,
) -> dict:
    """
    Construit le dictionnaire d'une PaginatedResponse complète.

    Appelé depuis les routers :

        return build_paginated_response(users, total, page, page_size, request)

    Les liens sont ajoutés automatiquement si ``request`` est fourni.
    La base URL est l'URL courante sans les query params ``page`` / ``page_size``
    afin de préserver les autres filtres (role, search, …).
    """
    total_pages = max(1, ceil(total / page_size))
    result: dict = {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }

    if request is not None:
        # Conserver tous les query params sauf page / page_size (reconstruits dans les liens)
        params = dict(request.query_params)
        params.pop("page", None)
        params.pop("page_size", None)
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        base = str(request.url.path) + (f"?{qs}&" if qs else "?")
        base = base.rstrip("?")  # propre si qs est vide

        def _url(p: int) -> str:
            sep = "&" if qs else "?"
            return f"{str(request.url.path)}{'?' + qs if qs else ''}{sep}page={p}&page_size={page_size}"

        result["links"] = PageLinks(
            first=_url(1),
            prev=_url(page - 1) if page > 1 else None,
            self=_url(page),
            next=_url(page + 1) if page < total_pages else None,
            last=_url(total_pages),
        )

    return result


# ═══════════════════════════════════════════════════════════════════════════
#  RÉFÉRENCES INTER-RESSOURCES (HATEOAS LÉGER)
# ═══════════════════════════════════════════════════════════════════════════


class ResourceLink(BaseModel):
    """Lien vers une ressource liée."""

    href: str = Field(description="URL absolue de la ressource")
    method: str = Field(default="GET", description="Méthode HTTP recommandée")


def make_link(path: str, method: str = "GET") -> ResourceLink:
    """Construit un ResourceLink à partir d'un chemin relatif."""
    return ResourceLink(href=f"{API_V1_PREFIX}{path}", method=method)


def user_links(user_id: UUID) -> Dict[str, ResourceLink]:
    """
    Ensemble de liens utiles pour un utilisateur donné.

    Inclus dans UserProfileResponse._links pour que l'app mobile
    sache exactement où naviguer sans hardcoder les URLs.
    """
    uid = str(user_id)
    return {
        "self": make_link(f"/users/{uid}"),
        "assignments": make_link(f"/assignments?user_id={uid}"),
        "attendance": make_link(f"/attendance?user_id={uid}"),
        "discipline_cases": make_link(f"/discipline/user/{uid}/stats"),
        "contributions": make_link(f"/contributions?servant_id={uid}"),
        "cotisations": make_link(f"/cotisations/user/{uid}/summary"),
    }


def discipline_links(case_id: UUID, accused_user_id: UUID) -> Dict[str, ResourceLink]:
    """Liens utiles pour un dossier disciplinaire."""
    return {
        "self": make_link(f"/discipline/{case_id}"),
        "accused": make_link(f"/users/{accused_user_id}"),
    }


def assignment_links(assignment_id: UUID, user_id: UUID, event_id: UUID) -> Dict[str, ResourceLink]:
    """Liens utiles pour une affectation liturgique."""
    return {
        "self": make_link(f"/assignments/{assignment_id}"),
        "user": make_link(f"/users/{user_id}"),
        "event": make_link(f"/events/{event_id}"),
    }


def attendance_links(attendance_id: UUID, user_id: UUID) -> Dict[str, ResourceLink]:
    """Liens utiles pour un enregistrement de présence."""
    return {
        "self": make_link(f"/attendance/{attendance_id}"),
        "user": make_link(f"/users/{user_id}"),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  ERREURS STANDARDISÉES
# ═══════════════════════════════════════════════════════════════════════════


class ApiError(BaseModel):
    """
    Format d'erreur uniforme pour tous les modules.

    Utilisé directement dans les responses_model des routers pour que
    la documentation OpenAPI affiche les codes d'erreur correctement.

    Exemples :
        {"detail": "Utilisateur introuvable.", "code": "NOT_FOUND"}
        {"detail": "Email invalide.", "code": "VALIDATION_ERROR", "field": "email"}
    """

    detail: str = Field(description="Message d'erreur lisible par l'humain")
    code: Optional[str] = Field(
        default=None,
        description="Code machine : NOT_FOUND, FORBIDDEN, CONFLICT, VALIDATION_ERROR, …",
    )
    field: Optional[str] = Field(
        default=None,
        description="Champ concerné (erreurs de validation uniquement)",
    )
    error_id: Optional[str] = Field(
        default=None,
        description="Identifiant de trace pour le support (erreurs 500)",
    )


# Codes d'erreur standard — utilisés dans les HTTPException.detail
class ErrorCode:
    NOT_FOUND = "NOT_FOUND"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL = "INTERNAL_SERVER_ERROR"
    GONE = "GONE"  # Ressource supprimée définitivement
    UNPROCESSABLE = "UNPROCESSABLE"  # Règle métier violée
