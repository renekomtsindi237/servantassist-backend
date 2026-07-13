"""
Utilitaires partagés — package.

Re-exporte les helpers datetime pour la compatibilité avec tous les imports
existants du type ``from src.core.utils import utc_now``.
"""

from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Retourne un datetime UTC timezone-naive (compatible TIMESTAMP WITHOUT TIME ZONE)."""
    return datetime.utcnow()


def to_naive_utc(dt: datetime) -> datetime:
    """Normalise un datetime vers UTC sans tzinfo."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def maybe_to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Variante optionnelle pour champs nullable."""
    if dt is None:
        return None
    return to_naive_utc(dt)


__all__ = ["utc_now", "to_naive_utc", "maybe_to_naive_utc"]
