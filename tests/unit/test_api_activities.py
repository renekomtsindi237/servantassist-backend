"""
Unit tests for activities.py API router (events/activities).
Uses FastAPI TestClient with mocked EventService.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_user(role="SERVANT"):
    from src.core.entities.user import UserRole

    user = MagicMock()
    user.id = uuid4()
    user.role = UserRole.ADMIN if role == "ADMIN" else UserRole.SERVANT
    user.first_name = "Jean"
    user.last_name = "Dupont"
    user.email = "jean@example.com"
    user.is_active = True
    return user


def _make_event_detail(event_id=None):
    from src.core.entities.event import EventStatus, EventType
    from src.presentation.schemas.event import EventDetailResponse

    return EventDetailResponse(
        id=event_id or uuid4(),
        title="Messe du dimanche",
        start_time=datetime(2026, 6, 21, 9, 0),
        end_time=datetime(2026, 6, 21, 11, 0),
        location="Cathédrale",
        event_type=EventType.MESSE_DOMINICALE,
        status=EventStatus.PUBLIE,
        created_by=uuid4(),
        participants=[],
    )


def _make_event_response(event_id=None):
    from src.core.entities.event import EventStatus, EventType
    from src.presentation.schemas.event import EventResponse

    return EventResponse(
        id=event_id or uuid4(),
        title="Messe du dimanche",
        start_time=datetime(2026, 6, 21, 9, 0),
        end_time=datetime(2026, 6, 21, 11, 0),
        location="Cathédrale",
        event_type=EventType.MESSE_DOMINICALE,
        status=EventStatus.PUBLIE,
        created_by=uuid4(),
    )


def _make_participant_response():
    from src.core.entities.event import ParticipantRole, ParticipantStatus
    from src.presentation.schemas.event import ParticipantResponse

    return ParticipantResponse(
        id=uuid4(),
        event_id=uuid4(),
        user_id=uuid4(),
        participant_role=ParticipantRole.SERVANT,
        status=ParticipantStatus.PRESENT,
        added_by=uuid4(),
    )


def _build_client(role="SERVANT"):
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from src.presentation.api.v1.activities import router
    from src.presentation.dependencies.auth_deps import (
        get_current_active_user,
        get_current_admin_or_aumonier,
        get_current_admin_user,
    )
    from src.infrastructure.database.session import get_db_session

    app = FastAPI()
    app.include_router(router, prefix="/events")

    session = AsyncMock()
    current_user = _make_user(role)

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_current_admin_or_aumonier] = lambda: current_user
    app.dependency_overrides[get_current_admin_user] = lambda: current_user
    app.dependency_overrides[get_db_session] = lambda: session

    return TestClient(app), session, current_user


# ─────────────────────────────────────────────────────────────────────────────
#  GET /
# ─────────────────────────────────────────────────────────────────────────────

def test_list_events():
    client, session, user = _build_client(role="SERVANT")
    event = _make_event_response()

    mock_service = MagicMock()
    mock_service.list_events = AsyncMock(return_value={
        "items": [event],
        "total": 1,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
        "links": None,
    })

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.get("/events/")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /me
# ─────────────────────────────────────────────────────────────────────────────

def test_get_my_events():
    client, session, user = _build_client(role="SERVANT")
    event = _make_event_response()

    mock_service = MagicMock()
    mock_service.get_my_events = AsyncMock(return_value=[event])

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.get("/events/me")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /{event_id}
# ─────────────────────────────────────────────────────────────────────────────

def test_get_event():
    client, session, user = _build_client(role="SERVANT")
    event_id = uuid4()
    event = _make_event_detail(event_id)

    mock_service = MagicMock()
    mock_service.get_event = AsyncMock(return_value=event)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.get(f"/events/{event_id}")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /
# ─────────────────────────────────────────────────────────────────────────────

def test_create_event():
    client, session, user = _build_client(role="ADMIN")
    event = _make_event_detail()

    mock_service = MagicMock()
    mock_service.create_event = AsyncMock(return_value=event)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.post("/events/", json={
                    "title": "Messe du dimanche",
                    "description": "Messe dominicale",
                    "start_time": "2026-06-21T09:00:00",
                    "end_time": "2026-06-21T11:00:00",
                    "location": "Cathédrale",
                    "event_type": "MESSE_DOMINICALE",
                    "status": "PUBLIE",
                })

    assert response.status_code == 201


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /{event_id}
# ─────────────────────────────────────────────────────────────────────────────

def test_update_event():
    client, session, user = _build_client(role="ADMIN")
    event_id = uuid4()
    event = _make_event_detail(event_id)

    mock_service = MagicMock()
    mock_service.update_event = AsyncMock(return_value=event)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.patch(f"/events/{event_id}", json={"title": "Updated"})

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /{event_id}
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_event():
    client, session, user = _build_client(role="ADMIN")
    event_id = uuid4()

    mock_service = MagicMock()
    mock_service.delete_event = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.delete(f"/events/{event_id}")

    assert response.status_code == 204


# ─────────────────────────────────────────────────────────────────────────────
#  GET /{event_id}/participants
# ─────────────────────────────────────────────────────────────────────────────

def test_list_participants():
    client, session, user = _build_client(role="SERVANT")
    event_id = uuid4()
    participant = _make_participant_response()

    mock_service = MagicMock()
    mock_service.get_event_participants = AsyncMock(return_value=[participant])

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.get(f"/events/{event_id}/participants")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /{event_id}/participants
# ─────────────────────────────────────────────────────────────────────────────

def test_add_participant():
    client, session, user = _build_client(role="ADMIN")
    event_id = uuid4()
    participant = _make_participant_response()

    mock_service = MagicMock()
    mock_service.add_participant = AsyncMock(return_value=participant)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.post(f"/events/{event_id}/participants", json={
                    "user_id": str(uuid4()),
                    "participant_role": "SERVANT",
                })

    assert response.status_code == 201


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /{event_id}/participants/{user_id}
# ─────────────────────────────────────────────────────────────────────────────

def test_update_participant():
    client, session, user = _build_client(role="ADMIN")
    event_id = uuid4()
    user_id = uuid4()
    participant = _make_participant_response()

    mock_service = MagicMock()
    mock_service.update_participant = AsyncMock(return_value=participant)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.patch(f"/events/{event_id}/participants/{user_id}", json={
                    "status": "PRESENT",
                })

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /{event_id}/participants/{user_id}
# ─────────────────────────────────────────────────────────────────────────────

def test_remove_participant():
    client, session, user = _build_client(role="ADMIN")
    event_id = uuid4()
    user_id = uuid4()

    mock_service = MagicMock()
    mock_service.remove_participant = AsyncMock(return_value=None)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.delete(f"/events/{event_id}/participants/{user_id}")

    assert response.status_code == 204


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /{event_id}/my-participation
# ─────────────────────────────────────────────────────────────────────────────

def test_update_my_participation():
    client, session, user = _build_client(role="SERVANT")
    event_id = uuid4()
    participant = _make_participant_response()

    mock_service = MagicMock()
    mock_service.update_my_participation = AsyncMock(return_value=participant)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.patch(f"/events/{event_id}/my-participation?new_status=CONFIRME")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /{event_id}/export-ical
# ─────────────────────────────────────────────────────────────────────────────

def test_export_single_event_ical():
    try:
        import icalendar  # noqa: F401
    except ImportError:
        pytest.skip("icalendar package not installed")

    client, session, user = _build_client(role="SERVANT")
    event_id = uuid4()
    event = _make_event_detail(event_id)

    mock_service = MagicMock()
    mock_service.get_event = AsyncMock(return_value=event)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.get(f"/events/{event_id}/calendar.ics")

    assert response.status_code == 200
    assert "text/calendar" in response.headers.get("content-type", "")


# ─────────────────────────────────────────────────────────────────────────────
#  GET /{event_id}/qr-code (skip if qrcode not installed)
# ─────────────────────────────────────────────────────────────────────────────

def test_get_event_qr_code():
    try:
        import qrcode  # noqa: F401
    except ImportError:
        pytest.skip("qrcode package not installed")

    client, session, user = _build_client(role="ADMIN")
    event_id = uuid4()
    event = _make_event_detail(event_id)

    mock_service = MagicMock()
    mock_service.get_event = AsyncMock(return_value=event)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                with patch("src.presentation.api.v1.activities.get_settings") as mock_gs:
                    settings = MagicMock()
                    settings.JWT_SECRET_KEY = "secret"
                    settings.JWT_ALGORITHM = "HS256"
                    mock_gs.return_value = settings
                    response = client.get(f"/events/{event_id}/qr-code")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /{event_id}/check-in — missing token
# ─────────────────────────────────────────────────────────────────────────────

def test_check_in_event_missing_token():
    client, session, user = _build_client(role="SERVANT")
    event_id = uuid4()

    response = client.post(f"/events/{event_id}/check-in")

    assert response.status_code == 400


def test_check_in_event_invalid_token():
    client, session, user = _build_client(role="SERVANT")
    event_id = uuid4()

    # Sending a syntactically invalid JWT token => PyJWTError => 400
    response = client.post(
        f"/events/{event_id}/check-in",
        headers={"X-Checkin-Token": "not.a.valid.jwt.token"},
    )

    assert response.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
#  GET /calendar.ics (all events)
# ─────────────────────────────────────────────────────────────────────────────

def test_export_all_events_ical():
    try:
        import icalendar  # noqa: F401
    except ImportError:
        pytest.skip("icalendar package not installed")

    client, session, user = _build_client(role="SERVANT")
    event = _make_event_response()

    # Return a paginated-like object with items attr
    events_page = MagicMock()
    events_page.items = [event]

    mock_service = MagicMock()
    mock_service.list_events = AsyncMock(return_value=events_page)

    with patch("src.presentation.api.v1.activities.EventService", return_value=mock_service):
        with patch("src.presentation.api.v1.activities.EventRepository"):
            with patch("src.presentation.api.v1.activities.UserRepository"):
                response = client.get("/events/calendar.ics")

    assert response.status_code == 200
    assert "text/calendar" in response.headers.get("content-type", "")
