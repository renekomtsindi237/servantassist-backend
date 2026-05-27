"""
Classe de base pour tous les événements de domaine.

Un DomainEvent représente quelque chose qui s'est passé dans le domaine métier.
Il est immuable (frozen dataclass), identifiable (event_id) et horodaté.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    """Événement de domaine immuable."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
