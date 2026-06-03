"""Unit tests for ConnectionManager WebSocket manager."""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.websocket.connection_manager import ConnectionManager, _WsConn


def _make_ws(send_ok=True) -> AsyncMock:
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.close = AsyncMock()
    if not send_ok:
        ws.send_json.side_effect = Exception("Connection closed")
    return ws


# ─── _WsConn ──────────────────────────────────────────────────────────────────


def test_ws_conn_init():
    ws = _make_ws()
    conn = _WsConn(ws, "user_1")
    assert conn.user_id == "user_1"
    assert conn.ws is ws
    assert conn.last_pong <= time.monotonic()


# ─── ConnectionManager basics ─────────────────────────────────────────────────


def test_initial_state():
    mgr = ConnectionManager()
    assert mgr.total_connections == 0
    assert mgr.connected_users == 0


@pytest.mark.asyncio
async def test_connect_registers_websocket():
    mgr = ConnectionManager()
    ws = _make_ws()

    await mgr.connect(ws, "user_1")

    ws.accept.assert_called_once()
    assert mgr.total_connections == 1
    assert mgr.connected_users == 1


@pytest.mark.asyncio
async def test_connect_multiple_for_same_user():
    mgr = ConnectionManager()
    ws1 = _make_ws()
    ws2 = _make_ws()

    await mgr.connect(ws1, "user_1")
    await mgr.connect(ws2, "user_1")

    assert mgr.total_connections == 2
    assert mgr.connected_users == 1  # same user


@pytest.mark.asyncio
async def test_connect_multiple_users():
    mgr = ConnectionManager()
    await mgr.connect(_make_ws(), "user_1")
    await mgr.connect(_make_ws(), "user_2")

    assert mgr.total_connections == 2
    assert mgr.connected_users == 2


@pytest.mark.asyncio
async def test_disconnect_removes_connection():
    mgr = ConnectionManager()
    ws = _make_ws()
    await mgr.connect(ws, "user_1")

    await mgr.disconnect(ws, "user_1")

    assert mgr.total_connections == 0
    assert mgr.connected_users == 0


@pytest.mark.asyncio
async def test_disconnect_unknown_user_no_error():
    mgr = ConnectionManager()
    await mgr.disconnect(_make_ws(), "nonexistent")
    assert mgr.total_connections == 0


@pytest.mark.asyncio
async def test_disconnect_one_of_two_sockets():
    mgr = ConnectionManager()
    ws1 = _make_ws()
    ws2 = _make_ws()
    await mgr.connect(ws1, "user_1")
    await mgr.connect(ws2, "user_1")

    await mgr.disconnect(ws1, "user_1")

    assert mgr.total_connections == 1
    assert mgr.connected_users == 1


# ─── send_to_user ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_to_user_no_connections():
    mgr = ConnectionManager()
    sent = await mgr.send_to_user("user_x", {"type": "msg"})
    assert sent == 0


@pytest.mark.asyncio
async def test_send_to_user_success():
    mgr = ConnectionManager()
    ws = _make_ws()
    await mgr.connect(ws, "user_1")

    sent = await mgr.send_to_user("user_1", {"type": "notification", "body": "hello"})

    assert sent == 1
    ws.send_json.assert_called_once_with({"type": "notification", "body": "hello"})


@pytest.mark.asyncio
async def test_send_to_user_dead_connection_removed():
    mgr = ConnectionManager()
    ws = _make_ws(send_ok=False)
    await mgr.connect(ws, "user_1")

    sent = await mgr.send_to_user("user_1", {"type": "msg"})

    assert sent == 0
    assert mgr.total_connections == 0  # dead connection removed


@pytest.mark.asyncio
async def test_send_to_user_one_dead_one_alive():
    mgr = ConnectionManager()
    ws_dead = _make_ws(send_ok=False)
    ws_alive = _make_ws()
    await mgr.connect(ws_dead, "user_1")
    await mgr.connect(ws_alive, "user_1")

    sent = await mgr.send_to_user("user_1", {"data": "x"})

    assert sent == 1
    assert mgr.total_connections == 1


# ─── broadcast ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_broadcast_multiple_users():
    mgr = ConnectionManager()
    ws1 = _make_ws()
    ws2 = _make_ws()
    await mgr.connect(ws1, "user_1")
    await mgr.connect(ws2, "user_2")

    sent = await mgr.broadcast(["user_1", "user_2"], {"type": "alert"})

    assert sent == 2


@pytest.mark.asyncio
async def test_broadcast_empty_list():
    mgr = ConnectionManager()
    assert await mgr.broadcast([], {"type": "msg"}) == 0


@pytest.mark.asyncio
async def test_broadcast_all():
    mgr = ConnectionManager()
    ws1 = _make_ws()
    ws2 = _make_ws()
    await mgr.connect(ws1, "u1")
    await mgr.connect(ws2, "u2")

    sent = await mgr.broadcast_all({"type": "global"})
    assert sent == 2


# ─── record_pong ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_pong_updates_timestamp():
    mgr = ConnectionManager()
    ws = _make_ws()
    await mgr.connect(ws, "user_1")

    old_time = mgr._connections["user_1"][0].last_pong
    await asyncio.sleep(0.01)
    mgr.record_pong(ws, "user_1")
    new_time = mgr._connections["user_1"][0].last_pong

    assert new_time >= old_time


@pytest.mark.asyncio
async def test_record_pong_unknown_user():
    mgr = ConnectionManager()
    mgr.record_pong(_make_ws(), "nobody")  # Should not raise


# ─── heartbeat ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_and_stop_heartbeat():
    mgr = ConnectionManager()
    await mgr.start_heartbeat()
    assert mgr._heartbeat_task is not None
    assert not mgr._heartbeat_task.done()

    await mgr.stop_heartbeat()
    assert mgr._heartbeat_task.done() or mgr._heartbeat_task.cancelled()


@pytest.mark.asyncio
async def test_start_heartbeat_idempotent():
    mgr = ConnectionManager()
    await mgr.start_heartbeat()
    task1 = mgr._heartbeat_task
    await mgr.start_heartbeat()  # Second call should reuse existing
    assert mgr._heartbeat_task is task1
    await mgr.stop_heartbeat()


@pytest.mark.asyncio
async def test_stop_heartbeat_no_task():
    mgr = ConnectionManager()
    await mgr.stop_heartbeat()  # No task → should not raise


# ─── _remove_dead ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_remove_dead_cleans_user_if_empty():
    mgr = ConnectionManager()
    ws = _make_ws()
    await mgr.connect(ws, "user_1")
    conn = mgr._connections["user_1"][0]

    await mgr._remove_dead("user_1", [conn])

    assert "user_1" not in mgr._connections
    assert mgr.total_connections == 0
