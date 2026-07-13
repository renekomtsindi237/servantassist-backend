"""
Unit tests for API endpoint routers:
- analytics.py
- api_keys.py
- classement.py
- dashboard.py
- email.py

All dependencies (auth, services, sessions) are mocked.
"""

from datetime import datetime
from typing import List
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.entities.user import User, UserRole


# ─── Shared helpers ───────────────────────────────────────────────────────────


def _make_user(role: UserRole = UserRole.ADMIN) -> User:
    return User(
        id=uuid4(),
        first_name="Test",
        last_name="User",
        email=f"{uuid4().hex[:6]}@test.com",
        role=role,
        is_active=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  analytics.py endpoints
# ═══════════════════════════════════════════════════════════════════════════════


def _analytics_app(admin_user: User = None):
    """Build a FastAPI app with analytics router, overriding auth and services."""
    from src.presentation.api.v1.analytics import router
    from src.presentation.dependencies.auth_deps import get_current_admin_user

    app = FastAPI()
    user = admin_user or _make_user(UserRole.ADMIN)
    app.dependency_overrides[get_current_admin_user] = lambda: user
    app.include_router(router, prefix="/analytics")
    return app


def test_analytics_realtime_no_redis_returns_data():
    app = _analytics_app()
    data = {"active_users": 42, "events": 10}

    with patch("src.presentation.api.v1.analytics._redis", new=AsyncMock(return_value=None)):
        with patch("src.presentation.api.v1.analytics.get_realtime", new=AsyncMock(return_value=data)):
            with patch("src.presentation.api.v1.analytics.get_settings") as mock_settings:
                settings = MagicMock()
                settings.GOOGLE_SA_JSON = "fake_sa"
                settings.GA4_PROPERTY_ID = "123"
                mock_settings.return_value = settings

                client = TestClient(app)
                r = client.get("/analytics/realtime")

    assert r.status_code == 200
    assert r.json()["active_users"] == 42


def test_analytics_realtime_with_redis_cache_hit():
    import json

    app = _analytics_app()
    cached_data = {"active_users": 7}

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_data))

    with patch("src.presentation.api.v1.analytics._redis", new=AsyncMock(return_value=mock_redis)):
        client = TestClient(app)
        r = client.get("/analytics/realtime")

    assert r.status_code == 200
    assert r.json()["active_users"] == 7


def test_analytics_summary_no_redis():
    app = _analytics_app()
    data = {"sessions": 100, "users": 50}

    with patch("src.presentation.api.v1.analytics._redis", new=AsyncMock(return_value=None)):
        with patch("src.presentation.api.v1.analytics.get_today_summary", new=AsyncMock(return_value=data)):
            with patch("src.presentation.api.v1.analytics.get_settings") as mock_settings:
                settings = MagicMock()
                settings.GOOGLE_SA_JSON = "fake_sa"
                settings.GA4_PROPERTY_ID = "123"
                mock_settings.return_value = settings

                client = TestClient(app)
                r = client.get("/analytics/summary")

    assert r.status_code == 200
    assert r.json()["sessions"] == 100


def test_analytics_summary_with_redis_cache_hit():
    import json

    app = _analytics_app()
    cached = {"sessions": 200, "users": 90}

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(cached))

    with patch("src.presentation.api.v1.analytics._redis", new=AsyncMock(return_value=mock_redis)):
        client = TestClient(app)
        r = client.get("/analytics/summary")

    assert r.status_code == 200
    assert r.json()["sessions"] == 200


def test_analytics_connections_returns_list():
    from src.presentation.api.v1.analytics import router
    from src.presentation.dependencies.auth_deps import (
        get_current_admin_user,
        get_current_active_user,
    )
    from src.infrastructure.database.session import get_db_session

    user = _make_user(UserRole.ADMIN)
    app = FastAPI()
    app.dependency_overrides[get_current_admin_user] = lambda: user
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    app.include_router(router, prefix="/analytics")

    geo_data = [{"lat": 3.8, "lon": 11.5, "city": "Yaoundé"}]

    with patch(
        "src.infrastructure.repositories.connection_log_repository.ConnectionLogRepository.get_geo_points",
        new=AsyncMock(return_value=geo_data),
    ):
        with patch(
            "src.presentation.api.v1.analytics.ConnectionLogRepository"
        ) as MockRepo:
            mock_repo_instance = AsyncMock()
            mock_repo_instance.get_geo_points = AsyncMock(return_value=geo_data)
            MockRepo.return_value = mock_repo_instance

            client = TestClient(app)
            r = client.get("/analytics/connections?days=7")

    assert r.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
#  api_keys.py endpoints
# ═══════════════════════════════════════════════════════════════════════════════


def _api_keys_app(user: User = None, service: "MagicMock" = None):
    from src.application.services.api_key_service import ApiKeyService
    from src.infrastructure.database.session import get_db_session
    from src.presentation.api.v1.api_keys import _get_service, router
    from src.presentation.dependencies.auth_deps import (
        get_current_active_user,
        get_current_admin_user,
    )

    app = FastAPI()
    current_user = user or _make_user(UserRole.ADMIN)
    mock_service = service or MagicMock(spec=ApiKeyService)

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_current_admin_user] = lambda: current_user
    app.dependency_overrides[_get_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    app.include_router(router, prefix="/keys")
    return app, mock_service


def test_create_api_key_success():
    from datetime import datetime
    from src.core.entities.api_key import ApiKey

    user = _make_user(UserRole.ADMIN)
    app, svc = _api_keys_app(user=user)

    created_key = ApiKey(
        id=uuid4(),
        name="My Key",
        key_hash="$hash",
        user_id=user.id,
        scopes=["read"],
        is_active=True,
        last_used_at=None,
        created_at=datetime.utcnow(),
    )
    svc.create_key = AsyncMock(return_value=(created_key, "sa_raw_key"))

    client = TestClient(app)
    r = client.post("/keys/", json={"name": "My Key", "scopes": ["read"]})

    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "My Key"
    assert body["raw_key"] == "sa_raw_key"


def test_list_my_api_keys():
    from src.core.entities.api_key import ApiKey

    user = _make_user(UserRole.SERVANT)
    app, svc = _api_keys_app(user=user)

    keys = [
        ApiKey(
            id=uuid4(),
            name=f"Key {i}",
            key_hash="$hash",
            user_id=user.id,
            scopes=[],
            is_active=True,
            last_used_at=None,
            created_at=datetime.utcnow(),
        )
        for i in range(3)
    ]
    svc.list_user_keys = AsyncMock(return_value=keys)

    client = TestClient(app)
    r = client.get("/keys/me")

    assert r.status_code == 200
    assert len(r.json()) == 3


def test_list_all_api_keys_admin():
    from src.core.entities.api_key import ApiKey

    user = _make_user(UserRole.ADMIN)
    app, svc = _api_keys_app(user=user)

    keys = [
        ApiKey(
            id=uuid4(),
            name="Key",
            key_hash="$hash",
            user_id=uuid4(),
            scopes=[],
            is_active=True,
            last_used_at=None,
            created_at=datetime.utcnow(),
        )
    ]
    svc.list_all_keys = AsyncMock(return_value=keys)

    client = TestClient(app)
    r = client.get("/keys/?limit=50&offset=0")

    assert r.status_code == 200
    assert len(r.json()) == 1


def test_revoke_api_key():
    from src.core.entities.api_key import ApiKey

    user = _make_user(UserRole.ADMIN)
    app, svc = _api_keys_app(user=user)

    key_id = uuid4()
    revoked = ApiKey(
        id=key_id,
        name="Revoked",
        key_hash="$hash",
        user_id=user.id,
        scopes=[],
        is_active=False,
        last_used_at=None,
        created_at=datetime.utcnow(),
    )
    svc.revoke_key = AsyncMock(return_value=revoked)

    client = TestClient(app)
    r = client.post(f"/keys/{key_id}/revoke")

    assert r.status_code == 200
    assert r.json()["is_active"] is False


def test_delete_api_key():
    user = _make_user(UserRole.ADMIN)
    app, svc = _api_keys_app(user=user)

    key_id = uuid4()
    svc.delete_key = AsyncMock(return_value=None)

    client = TestClient(app)
    r = client.delete(f"/keys/{key_id}")

    assert r.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
#  email.py endpoints
# ═══════════════════════════════════════════════════════════════════════════════


def _email_app(admin_user: User = None):
    from src.presentation.api.v1.email import router
    from src.presentation.dependencies.auth_deps import get_current_admin_user

    app = FastAPI()
    user = admin_user or _make_user(UserRole.ADMIN)
    app.dependency_overrides[get_current_admin_user] = lambda: user
    app.include_router(router, prefix="/email")
    return app


def test_send_test_email_success():
    app = _email_app()

    with patch("src.presentation.api.v1.email.EmailService") as MockEmailSvc:
        instance = AsyncMock()
        instance.send_general_notification = AsyncMock(return_value=True)
        MockEmailSvc.return_value = instance

        client = TestClient(app)
        r = client.post(
            "/email/test",
            json={
                "to_email": "test@example.com",
                "subject": "Test",
                "message": "Hello",
            },
        )

    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["to"] == "test@example.com"


def test_send_test_email_failure():
    app = _email_app()

    with patch("src.presentation.api.v1.email.EmailService") as MockEmailSvc:
        instance = AsyncMock()
        instance.send_general_notification = AsyncMock(return_value=False)
        MockEmailSvc.return_value = instance

        client = TestClient(app)
        r = client.post(
            "/email/test",
            json={
                "to_email": "fail@example.com",
                "subject": "Test",
                "message": "Hello",
            },
        )

    assert r.status_code == 502


def test_send_notification_multiple_recipients():
    app = _email_app()

    with patch("src.presentation.api.v1.email.EmailService") as MockEmailSvc:
        instance = AsyncMock()
        instance.send_general_notification = AsyncMock(return_value=True)
        MockEmailSvc.return_value = instance

        client = TestClient(app)
        r = client.post(
            "/email/notify",
            json={
                "to_emails": ["a@example.com", "b@example.com"],
                "title": "Hello",
                "body": "World",
                "recipient_name": "Member",
            },
        )

    assert r.status_code == 200
    results = r.json()
    assert len(results) == 2
    assert all(res["success"] is True for res in results)


def test_send_notification_partial_failure():
    app = _email_app()

    call_count = 0

    async def alternating(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return call_count % 2 == 1  # True, False, True...

    with patch("src.presentation.api.v1.email.EmailService") as MockEmailSvc:
        instance = AsyncMock()
        instance.send_general_notification = alternating
        MockEmailSvc.return_value = instance

        client = TestClient(app)
        r = client.post(
            "/email/notify",
            json={
                "to_emails": ["ok@example.com", "bad@example.com"],
                "title": "Notice",
                "body": "Details",
            },
        )

    assert r.status_code == 200
    results = r.json()
    assert results[0]["success"] is True
    assert results[1]["success"] is False


# ═══════════════════════════════════════════════════════════════════════════════
#  dashboard.py endpoints
# ═══════════════════════════════════════════════════════════════════════════════


def _dashboard_app(user: User = None):
    from src.infrastructure.database.session import get_db_session
    from src.presentation.api.v1.dashboard import router
    from src.presentation.dependencies.auth_deps import (
        get_current_active_user,
        get_current_admin_or_aumonier,
    )

    app = FastAPI()
    current_user = user or _make_user(UserRole.ADMIN)
    mock_session = AsyncMock()

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_current_admin_or_aumonier] = lambda: current_user
    app.dependency_overrides[get_db_session] = lambda: mock_session
    app.include_router(router, prefix="/dashboard")
    return app


def test_dashboard_summary():
    from src.presentation.schemas.dashboard import DashboardSummary

    app = _dashboard_app()

    summary = DashboardSummary(
        total_servants=100,
        total_parents=20,
        total_active_users=120,
        total_events=20,
        total_assignments=150,
        attendance_rate_percent=75.0,
        cotisation_rate_percent=60.0,
        generated_at=datetime.utcnow(),
    )

    with patch("src.presentation.api.v1.dashboard.DashboardService") as MockSvc:
        instance = AsyncMock()
        instance.get_summary = AsyncMock(return_value=summary)
        MockSvc.return_value = instance

        client = TestClient(app)
        r = client.get("/dashboard/summary")

    assert r.status_code == 200
    body = r.json()
    assert body["total_servants"] == 100


def test_dashboard_attendance_trend():
    from src.presentation.schemas.dashboard import AttendanceTrend, AttendancePoint

    app = _dashboard_app()

    trend = AttendanceTrend(
        period_label="2026",
        points=[
            AttendancePoint(period="Jan", total=10, present=8, absent=2, rate_percent=80.0),
            AttendancePoint(period="Feb", total=10, present=9, absent=1, rate_percent=90.0),
        ],
        average_rate_percent=85.0,
    )

    with patch("src.presentation.api.v1.dashboard.DashboardService") as MockSvc:
        instance = AsyncMock()
        instance.get_attendance_trend = AsyncMock(return_value=trend)
        MockSvc.return_value = instance

        client = TestClient(app)
        r = client.get("/dashboard/attendance?group_by=month")

    assert r.status_code == 200
    body = r.json()
    assert body["average_rate_percent"] == 85.0


def test_dashboard_attendance_trend_defaults_invalid_group_by():
    from src.presentation.schemas.dashboard import AttendanceTrend

    app = _dashboard_app()
    trend = AttendanceTrend(period_label="2026", points=[], average_rate_percent=0.0)

    with patch("src.presentation.api.v1.dashboard.DashboardService") as MockSvc:
        instance = AsyncMock()
        instance.get_attendance_trend = AsyncMock(return_value=trend)
        MockSvc.return_value = instance

        client = TestClient(app)
        # group_by="invalid" should be silently corrected to "month"
        r = client.get("/dashboard/attendance?group_by=invalid")

    assert r.status_code == 200
    # Verify the service was called with group_by="month"
    instance.get_attendance_trend.assert_called_once()
    call_kwargs = instance.get_attendance_trend.call_args[1]
    assert call_kwargs.get("group_by") == "month"


def test_dashboard_cotisation_status():
    from src.presentation.schemas.dashboard import CotisationStatus

    app = _dashboard_app()

    cot_status = CotisationStatus(
        period_id=uuid4(),
        period_name="2026 Q1",
        total_members=50,
        paid_count=30,
        partial_count=10,
        unpaid_count=10,
        total_expected=500000.0,
        total_collected=300000.0,
        rate_percent=60.0,
    )

    with patch("src.presentation.api.v1.dashboard.DashboardService") as MockSvc:
        instance = AsyncMock()
        instance.get_cotisation_status = AsyncMock(return_value=cot_status)
        MockSvc.return_value = instance

        client = TestClient(app)
        r = client.get("/dashboard/cotisations")

    assert r.status_code == 200
    assert r.json()["rate_percent"] == 60.0


def test_dashboard_cotisation_status_none_returns_empty():
    app = _dashboard_app()

    with patch("src.presentation.api.v1.dashboard.DashboardService") as MockSvc:
        instance = AsyncMock()
        instance.get_cotisation_status = AsyncMock(return_value=None)
        MockSvc.return_value = instance

        client = TestClient(app)
        r = client.get("/dashboard/cotisations")

    assert r.status_code == 200
    body = r.json()
    assert body["total_members"] == 0
    assert body["period_name"] == "Aucune période"


def test_dashboard_upcoming_events():
    from src.presentation.schemas.dashboard import UpcomingEvent

    app = _dashboard_app()

    events = [
        UpcomingEvent(
            id=uuid4(),
            title="Event 1",
            event_date=datetime.utcnow(),
            location="Cathédrale",
            total_assignments=5,
            confirmed_assignments=3,
        ),
        UpcomingEvent(
            id=uuid4(),
            title="Event 2",
            event_date=datetime.utcnow(),
            location="Chapelle",
            total_assignments=3,
            confirmed_assignments=2,
        ),
    ]

    with patch("src.presentation.api.v1.dashboard.DashboardService") as MockSvc:
        instance = AsyncMock()
        instance.get_upcoming_events = AsyncMock(return_value=events)
        MockSvc.return_value = instance

        client = TestClient(app)
        r = client.get("/dashboard/events/upcoming?limit=5")

    assert r.status_code == 200
    assert len(r.json()) == 2


def test_dashboard_top_servants():
    from src.presentation.schemas.dashboard import TopServant

    app = _dashboard_app()

    servants = [
        TopServant(
            rank=1,
            user_id=uuid4(),
            full_name="Jean Doe",
            total_sessions=20,
            present_count=19,
            attendance_rate_percent=95.0,
        ),
        TopServant(
            rank=2,
            user_id=uuid4(),
            full_name="Marie Dupont",
            total_sessions=20,
            present_count=18,
            attendance_rate_percent=90.0,
        ),
    ]

    with patch("src.presentation.api.v1.dashboard.DashboardService") as MockSvc:
        instance = AsyncMock()
        instance.get_top_servants = AsyncMock(return_value=servants)
        MockSvc.return_value = instance

        client = TestClient(app)
        r = client.get("/dashboard/top-servants?limit=10")

    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.json()[0]["attendance_rate_percent"] == 95.0


# ═══════════════════════════════════════════════════════════════════════════════
#  classement.py endpoints
# ═══════════════════════════════════════════════════════════════════════════════


def _classement_app(user: User = None, service=None):
    from src.application.services.classement_service import ClassementService
    from src.infrastructure.database.session import get_db_session
    from src.presentation.api.v1.classement import get_service, require_classement_manager, router
    from src.presentation.dependencies.auth_deps import get_current_active_user

    app = FastAPI()
    current_user = user or _make_user(UserRole.ADMIN)
    mock_service = service or MagicMock(spec=ClassementService)

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[require_classement_manager] = lambda: current_user
    app.dependency_overrides[get_service] = lambda: mock_service
    app.dependency_overrides[get_db_session] = lambda: AsyncMock()
    app.include_router(router, prefix="/classements")
    return app, mock_service


def _make_classement_response(status="BROUILLON"):
    from src.core.entities.classement import ClassementStatus, ClassementType
    from src.presentation.schemas.classement import ClassementResponse

    return ClassementResponse(
        id=uuid4(),
        type=ClassementType.DIMANCHE,
        status=ClassementStatus(status),
        date=datetime.utcnow(),
        heure="10:00",
        lieu="Cathédrale",
        solennite=None,
        couleur_liturgique=None,
        semaine=None,
        annee=None,
        horaire=None,
        type_extra=None,
        participants=None,
        postes=[],
        created_by=uuid4(),
        published_at=None,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def test_list_published_classements():
    from src.presentation.api.v1.classement import get_service, router
    from src.presentation.dependencies.auth_deps import get_current_active_user

    user = _make_user(UserRole.SERVANT)
    app = FastAPI()
    mock_service = MagicMock()

    items = [_make_classement_response("PUBLIE")]
    mock_service.list = AsyncMock(return_value=(items, 1))

    app.dependency_overrides[get_current_active_user] = lambda: user
    app.dependency_overrides[get_service] = lambda: mock_service
    app.include_router(router, prefix="/classements")

    client = TestClient(app)
    r = client.get("/classements/published")

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1


def test_get_classement_found():
    app, svc = _classement_app()

    cid = uuid4()
    cl = _make_classement_response()
    svc.get = AsyncMock(return_value=cl)

    client = TestClient(app)
    r = client.get(f"/classements/{cid}")

    assert r.status_code == 200


def test_get_classement_not_found():
    app, svc = _classement_app()

    svc.get = AsyncMock(return_value=None)

    client = TestClient(app)
    r = client.get(f"/classements/{uuid4()}")

    assert r.status_code == 404


def test_list_classements():
    app, svc = _classement_app()

    items = [_make_classement_response()]
    svc.list = AsyncMock(return_value=(items, 1))

    client = TestClient(app)
    r = client.get("/classements/")

    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1


def test_create_classement():
    from src.core.entities.classement import ClassementType

    app, svc = _classement_app()
    cl = _make_classement_response()
    svc.create = AsyncMock(return_value=cl)

    client = TestClient(app)
    r = client.post(
        "/classements/",
        json={
            "type": "DIMANCHE",
            "date": "2026-06-22T08:00:00",
            "heure": "08:00",
            "lieu": "Cathédrale",
            "postes": [],
        },
    )

    assert r.status_code == 201


def test_update_classement_found():
    app, svc = _classement_app()

    cid = uuid4()
    updated = _make_classement_response()
    svc.update = AsyncMock(return_value=updated)

    client = TestClient(app)
    r = client.patch(f"/classements/{cid}", json={"lieu": "Nouvelle Cathédrale"})

    assert r.status_code == 200


def test_update_classement_not_found():
    app, svc = _classement_app()

    svc.update = AsyncMock(return_value=None)

    client = TestClient(app)
    r = client.patch(f"/classements/{uuid4()}", json={"lieu": "Somewhere"})

    assert r.status_code == 404


def test_advance_classement_found():
    app, svc = _classement_app()

    cid = uuid4()
    advanced = _make_classement_response("FINALISE")
    svc.advance_status = AsyncMock(return_value=advanced)

    client = TestClient(app)
    r = client.post(f"/classements/{cid}/advance")

    assert r.status_code == 200


def test_advance_classement_not_found():
    app, svc = _classement_app()

    svc.advance_status = AsyncMock(return_value=None)

    client = TestClient(app)
    r = client.post(f"/classements/{uuid4()}/advance")

    assert r.status_code == 404


def test_advance_classement_value_error():
    app, svc = _classement_app()

    svc.advance_status = AsyncMock(side_effect=ValueError("already published"))

    client = TestClient(app)
    r = client.post(f"/classements/{uuid4()}/advance")

    assert r.status_code == 400


def test_delete_classement_found():
    app, svc = _classement_app()

    cid = uuid4()
    svc.delete = AsyncMock(return_value=True)

    client = TestClient(app)
    r = client.delete(f"/classements/{cid}")

    assert r.status_code == 204


def test_delete_classement_not_found():
    app, svc = _classement_app()

    svc.delete = AsyncMock(return_value=False)

    client = TestClient(app)
    r = client.delete(f"/classements/{uuid4()}")

    assert r.status_code == 404


def test_delete_classement_value_error():
    app, svc = _classement_app()

    svc.delete = AsyncMock(side_effect=ValueError("cannot delete published"))

    client = TestClient(app)
    r = client.delete(f"/classements/{uuid4()}")

    assert r.status_code == 400


# ─── require_classement_manager helper tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_require_classement_manager_admin():
    from src.presentation.api.v1.classement import require_classement_manager

    admin = _make_user(UserRole.ADMIN)
    result = await require_classement_manager(admin, AsyncMock())
    assert result == admin


@pytest.mark.asyncio
async def test_require_classement_manager_aumonier():
    from src.presentation.api.v1.classement import require_classement_manager

    aumonier = _make_user(UserRole.AUMÔNIER)
    result = await require_classement_manager(aumonier, AsyncMock())
    assert result == aumonier


@pytest.mark.asyncio
async def test_require_classement_manager_non_servant_forbidden():
    from fastapi import HTTPException
    from src.presentation.api.v1.classement import require_classement_manager

    parent = _make_user(UserRole.PARENT)
    with pytest.raises(HTTPException) as exc_info:
        await require_classement_manager(parent, AsyncMock())
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_classement_manager_servant_without_nomination():
    from fastapi import HTTPException
    from src.presentation.api.v1.classement import require_classement_manager
    import src.infrastructure.repositories.responsable_repository as nom_module

    servant = _make_user(UserRole.SERVANT)
    mock_session = AsyncMock()

    mock_nom = AsyncMock()
    mock_nom.get_active_by_user = AsyncMock(return_value=[])

    with patch.object(nom_module, "NominationRepository", return_value=mock_nom):
        with pytest.raises(HTTPException) as exc_info:
            await require_classement_manager(servant, mock_session)

    assert exc_info.value.status_code == 403
