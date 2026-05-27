"""
Gestionnaire de connexions WebSocket avec heartbeat.

Maintient un registre des connexions actives par user_id.
Envoie des pings périodiques et déconnecte les clients inactifs.

Usage :
    # Dans main.py lifespan :
    app.state.ws_manager = ConnectionManager()
    await app.state.ws_manager.start_heartbeat()

    # Dans un endpoint WebSocket :
    await app.state.ws_manager.connect(websocket, str(user.id))

    # Dans NotificationService pour pusher :
    if hasattr(request.app.state, "ws_manager"):
        await request.app.state.ws_manager.send_to_user(user_id, payload)
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional, Tuple

from fastapi import WebSocket

logger = logging.getLogger(__name__)

_HEARTBEAT_INTERVAL = 30  # Secondes entre chaque ping
_HEARTBEAT_TIMEOUT = 60  # Secondes max sans pong avant déconnexion


class _WsConn:
    """Enveloppe autour d'un WebSocket avec suivi du dernier pong."""

    __slots__ = ("ws", "last_pong", "user_id")

    def __init__(self, ws: WebSocket, user_id: str) -> None:
        self.ws = ws
        self.user_id = user_id
        self.last_pong: float = time.monotonic()


class ConnectionManager:
    """Gestionnaire de connexions WebSocket thread-safe pour un processus."""

    def __init__(self) -> None:
        # user_id → liste de _WsConn
        self._connections: Dict[str, List[_WsConn]] = {}
        self._lock = asyncio.Lock()
        self._heartbeat_task: Optional[asyncio.Task] = None

    # ── Cycle de vie ───────────────────────────────────────────────────────

    async def start_heartbeat(self) -> None:
        """Démarre la tâche de heartbeat en arrière-plan."""
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info(
                "WebSocket heartbeat démarré (interval=%ds, timeout=%ds)",
                _HEARTBEAT_INTERVAL,
                _HEARTBEAT_TIMEOUT,
            )

    async def stop_heartbeat(self) -> None:
        """Arrête la tâche de heartbeat proprement."""
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("WebSocket heartbeat arrêté")

    # ── Connexion / déconnexion ────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accepte et enregistre une connexion WebSocket."""
        await websocket.accept()
        conn = _WsConn(websocket, user_id)
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = []
            self._connections[user_id].append(conn)
        logger.info(
            "WebSocket connecté: user_id=%s total=%d", user_id, self.total_connections
        )

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Désenregistre une connexion WebSocket."""
        async with self._lock:
            conns = self._connections.get(user_id, [])
            self._connections[user_id] = [c for c in conns if c.ws is not websocket]
            if not self._connections.get(user_id):
                self._connections.pop(user_id, None)
        logger.info("WebSocket déconnecté: user_id=%s", user_id)

    # ── Envoi ──────────────────────────────────────────────────────────────

    async def send_to_user(self, user_id: str, message: dict) -> int:
        """
        Envoie un message JSON à toutes les connexions d'un utilisateur.

        Returns:
            Nombre de connexions ayant reçu le message.
        """
        sent = 0
        dead: List[_WsConn] = []
        conns = list(self._connections.get(user_id, []))
        for conn in conns:
            try:
                await conn.ws.send_json(message)
                sent += 1
            except Exception as exc:
                logger.debug("WebSocket send échoué user=%s: %s", user_id, exc)
                dead.append(conn)
        if dead:
            await self._remove_dead(user_id, dead)
        return sent

    async def broadcast(self, user_ids: List[str], message: dict) -> int:
        """Envoie un message à une liste d'utilisateurs."""
        total = 0
        for uid in user_ids:
            total += await self.send_to_user(uid, message)
        return total

    async def broadcast_all(self, message: dict) -> int:
        """Envoie un message à tous les utilisateurs connectés."""
        return await self.broadcast(list(self._connections.keys()), message)

    # ── Mise à jour du pong ────────────────────────────────────────────────

    def record_pong(self, websocket: WebSocket, user_id: str) -> None:
        """Enregistre un pong reçu d'un client."""
        for conn in self._connections.get(user_id, []):
            if conn.ws is websocket:
                conn.last_pong = time.monotonic()
                break

    # ── Métriques ──────────────────────────────────────────────────────────

    @property
    def total_connections(self) -> int:
        return sum(len(v) for v in self._connections.values())

    @property
    def connected_users(self) -> int:
        return len(self._connections)

    # ── Privé ──────────────────────────────────────────────────────────────

    async def _remove_dead(self, user_id: str, dead: List[_WsConn]) -> None:
        async with self._lock:
            conns = self._connections.get(user_id, [])
            self._connections[user_id] = [c for c in conns if c not in dead]
            if not self._connections.get(user_id):
                self._connections.pop(user_id, None)

    async def _heartbeat_loop(self) -> None:
        """
        Boucle périodique :
        1. Envoie un ping à tous les clients.
        2. Déconnecte les clients qui n'ont pas répondu depuis > timeout.
        """
        while True:
            await asyncio.sleep(_HEARTBEAT_INTERVAL)
            now = time.monotonic()
            all_user_ids = list(self._connections.keys())

            for user_id in all_user_ids:
                conns = list(self._connections.get(user_id, []))
                dead: List[_WsConn] = []

                for conn in conns:
                    # Déconnecter si le dernier pong est trop ancien
                    if now - conn.last_pong > _HEARTBEAT_TIMEOUT:
                        logger.info(
                            "WebSocket timeout (pas de pong): user_id=%s", user_id
                        )
                        try:
                            await conn.ws.close(code=1001, reason="heartbeat timeout")
                        except Exception:
                            pass
                        dead.append(conn)
                        continue

                    # Envoyer un ping
                    try:
                        await conn.ws.send_json({"type": "ping"})
                    except Exception as exc:
                        logger.debug("Ping échoué user=%s: %s", user_id, exc)
                        dead.append(conn)

                if dead:
                    await self._remove_dead(user_id, dead)
