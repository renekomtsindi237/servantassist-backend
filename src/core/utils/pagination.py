"""
Utilitaires de pagination — couche domaine.

Ce module est volontairement sans dépendance FastAPI/Pydantic pour rester
utilisable dans les services applicatifs et les tests unitaires purs.

Exports principaux
------------------
  PageParams           Paramètres de pagination normalisés (page, page_size).
  PaginationResult     Tuple enrichi : items + méta + headers prêts à émettre.
  paginate()           Applique les paramètres à un (items, total) et produit
                       une PaginationResult complète.
  build_link_header()  Génère la valeur du header HTTP ``Link`` (RFC 5988).

Usage dans un router FastAPI :
    result = paginate(items, total, page, page_size, request)
    return JSONResponse(result.body, headers=result.headers)

    # Ou directement avec PaginatedResponse :
    return build_paginated_response(items, total, page, page_size, request)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil
from typing import Any, Dict, List, Optional

# ── Constantes ────────────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


# ═══════════════════════════════════════════════════════════════════════════
#  PageParams — objet de valeur validé
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class PageParams:
    """
    Paramètres de pagination normalisés et validés.

    Immutable par conception (frozen dataclass) : impossible de mutater
    accidentellement une instance passée entre couches.
    """

    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError("page doit être ≥ 1")
        if not (1 <= self.page_size <= MAX_PAGE_SIZE):
            raise ValueError(f"page_size doit être entre 1 et {MAX_PAGE_SIZE}")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    def total_pages(self, total: int) -> int:
        return max(1, ceil(total / self.page_size))

    def has_next(self, total: int) -> bool:
        return self.page < self.total_pages(total)

    def has_prev(self) -> bool:
        return self.page > 1


# ═══════════════════════════════════════════════════════════════════════════
#  PaginationResult — enveloppe prête à sérialiser
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PaginationResult:
    """
    Résultat complet de pagination.

    Contient à la fois le corps JSON et les en-têtes HTTP à émettre,
    ce qui permet au router de ne faire qu'un seul appel à ``paginate()``.
    """

    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int
    headers: Dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict:
        """Corps JSON sans les liens (compatible avec PaginatedResponse)."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": self.total_pages,
        }


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════

def build_link_header(base_path: str, page: int, page_size: int, total: int,
                      extra_qs: str = "") -> str:
    """
    Construit la valeur du header HTTP ``Link`` conforme RFC 5988.

    Exemple de sortie :
        </api/v1/users?page=1&page_size=20>; rel="first",
        </api/v1/users?page=3&page_size=20>; rel="prev",
        </api/v1/users?page=5&page_size=20>; rel="next",
        </api/v1/users?page=10&page_size=20>; rel="last"

    Args:
        base_path:  Chemin sans query string  ("/api/v1/users")
        page:       Page courante
        page_size:  Taille de page
        total:      Nombre total d'éléments
        extra_qs:   Query string supplémentaire sans ``&`` initial (ex: "role=SERVANT")
    """
    total_pages = max(1, ceil(total / page_size))
    sep = f"&{extra_qs}" if extra_qs else ""

    def _url(p: int) -> str:
        return f"{base_path}?page={p}&page_size={page_size}{sep}"

    parts = [f'<{_url(1)}>; rel="first"']

    if page > 1:
        parts.append(f'<{_url(page - 1)}>; rel="prev"')
    if page < total_pages:
        parts.append(f'<{_url(page + 1)}>; rel="next"')

    parts.append(f'<{_url(total_pages)}>; rel="last"')
    return ", ".join(parts)


def paginate(
    items: List[Any],
    total: int,
    page: int,
    page_size: int,
    request: Optional[Any] = None,  # fastapi.Request — optionnel pour garder ce module pur
) -> PaginationResult:
    """
    Construit un PaginationResult complet avec headers HTTP prêts à émettre.

    Headers inclus dans le résultat :
      X-Total-Count   Nombre total d'éléments (toutes pages).
      X-Total-Pages   Nombre de pages.
      X-Page          Page courante.
      X-Page-Size     Taille de page.
      Link            Liens RFC 5988 (first/prev/next/last).
    """
    total_pages = max(1, ceil(total / page_size))
    headers: Dict[str, str] = {
        "X-Total-Count": str(total),
        "X-Total-Pages": str(total_pages),
        "X-Page": str(page),
        "X-Page-Size": str(page_size),
    }

    if request is not None:
        # Reconstruit l'extra_qs en excluant les paramètres de pagination
        params = dict(request.query_params)
        params.pop("page", None)
        params.pop("page_size", None)
        extra_qs = "&".join(f"{k}={v}" for k, v in params.items())
        headers["Link"] = build_link_header(
            str(request.url.path), page, page_size, total, extra_qs
        )

    return PaginationResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        headers=headers,
    )
