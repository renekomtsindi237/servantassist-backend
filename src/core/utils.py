"""
Utilitaires partagés par les entités du domaine.
"""
from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Retourne un datetime UTC timezone-naive (compatible TIMESTAMP WITHOUT TIME ZONE)."""
    # Les migrations créent la majorité des colonnes en `TIMESTAMP WITHOUT TIME ZONE`.
    # Pour éviter l'erreur asyncpg "can't subtract offset-naive and offset-aware datetimes",
    # on stocke des datetime sans tzinfo (en UTC).
    return datetime.utcnow()


def to_naive_utc(dt: datetime) -> datetime:
    """
    Normalise un datetime vers UTC **sans tzinfo**.

    - Si `dt` est déjà naïf, on le considère déjà en UTC (comportement attendu côté API quand
      on envoie des timestamps sans offset).
    - Si `dt` est aware, on convertit vers UTC puis on retire le tzinfo.
    """
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def maybe_to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Variante optionnelle pour champs nullable."""
    if dt is None:
        return None
    return to_naive_utc(dt)
