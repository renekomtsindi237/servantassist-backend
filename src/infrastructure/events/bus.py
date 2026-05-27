"""
Bus d'événements in-process asynchrone.

Architecture :
  service.publish(UserInvited(...))
      → EventBus.publish()
          → handler_1(event)   ← notification WhatsApp/email
          → handler_2(event)   ← audit log
          → handler_3(event)   ← WebSocket push

Les handlers sont enregistrés via @event_bus.handler(EventType)
ou via event_bus.subscribe(EventType, handler_func).

Le bus est « best-effort » : une exception dans un handler est loguée
mais ne fait pas échouer la transaction principale.
"""
import asyncio
import logging
from collections import defaultdict
from typing import Callable, Dict, List, Type

from src.core.events.base import DomainEvent

logger = logging.getLogger(__name__)


class EventBus:
    """Bus d'événements in-process. Thread-safe pour asyncio."""

    def __init__(self) -> None:
        self._handlers: Dict[Type[DomainEvent], List[Callable]] = defaultdict(list)

    def subscribe(self, event_type: Type[DomainEvent], handler: Callable) -> None:
        """Enregistre un handler pour un type d'événement."""
        self._handlers[event_type].append(handler)

    def handler(self, *event_types: Type[DomainEvent]) -> Callable:
        """Décorateur pour enregistrer une fonction comme handler."""

        def decorator(func: Callable) -> Callable:
            for et in event_types:
                self.subscribe(et, func)
            return func

        return decorator

    async def publish(self, event: DomainEvent) -> None:
        """
        Publie un événement à tous ses handlers.

        Chaque handler est appelé indépendamment : une erreur dans l'un
        ne bloque pas les autres. Les erreurs sont loguées mais silencieuses
        pour le service émetteur.
        """
        handlers = self._handlers.get(type(event), [])
        if not handlers:
            return

        for h in handlers:
            try:
                result = h(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception(
                    "EventBus handler %s failed for event %s",
                    getattr(h, "__name__", repr(h)),
                    type(event).__name__,
                )

    def clear(self) -> None:
        """Vide tous les handlers (utile pour les tests)."""
        self._handlers.clear()


# Singleton global — importé par les services et les handlers
event_bus = EventBus()
