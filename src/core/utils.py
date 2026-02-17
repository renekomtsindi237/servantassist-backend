"""
Utilitaires partagés par les entités du domaine.
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """Retourne un datetime UTC timezone-aware (remplace datetime.utcnow())."""
    return datetime.now(timezone.utc)

