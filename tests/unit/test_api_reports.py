"""
Unit tests for reports.py API router.
Uses FastAPI TestClient with mocked ReportService.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_user(role_str="ADMIN"):
    user = MagicMock()
    user.id = uuid4()
    # Use a MagicMock for role so .value works
    user.role = MagicMock()
    user.role.value = role_str
    user.is_active = True
    return user


def _make_report_response():
    from src.core.entities.report import ReportStatus, ReportType
    from src.presentation.schemas.report import ReportResponse

    return ReportResponse(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Réunion de bureau",
        content="Contenu du rapport.",
        report_date=datetime(2026, 6, 20, 10, 0),
        location="Salle principale",
        participants=["Jean Dupont"],
        decisions=None,
        action_items=None,
        status=ReportStatus.DRAFT,
        created_by=uuid4(),
        published_at=None,
        watermark_logo="logo.png",
        created_at=datetime(2026, 6, 20, 10, 0),
        updated_at=datetime(2026, 6, 20, 10, 0),
    )


def _make_attachment_response(report_id=None):
    from src.presentation.schemas.report import AttachmentResponse

    return AttachmentResponse(
        id=uuid4(),
        report_id=report_id or uuid4(),
        filename="test.pdf",
        file_url="https://example.com/test.pdf",
        file_type="application/pdf",
        file_size=1024,
        uploaded_by=uuid4(),
        created_at=datetime(2026, 6, 20, 10, 0),
    )


def _build_client(role_str="ADMIN", mock_service=None):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from src.infrastructure.database.session import get_db_session
    from src.presentation.api.v1.reports import get_report_service, router
    from src.presentation.dependencies.auth_deps import (
        get_current_active_user,
        get_current_responsable,
        require_secretaire,
    )

    app = FastAPI()
    app.include_router(router, prefix="/reports")

    session = AsyncMock()
    current_user = _make_user(role_str)

    if mock_service is None:
        mock_service = MagicMock()

    app.dependency_overrides[get_current_active_user] = lambda: current_user
    app.dependency_overrides[get_current_responsable] = lambda: current_user
    app.dependency_overrides[require_secretaire] = lambda: current_user
    app.dependency_overrides[get_db_session] = lambda: session
    app.dependency_overrides[get_report_service] = lambda: mock_service

    return TestClient(app), session, current_user, mock_service


# ─────────────────────────────────────────────────────────────────────────────
#  POST /
# ─────────────────────────────────────────────────────────────────────────────


def test_create_report():
    report = _make_report_response()
    mock_service = MagicMock()
    mock_service.create_report = AsyncMock(return_value=report)
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    response = client.post(
        "/reports/",
        json={
            "type": "MEETING",
            "title": "Réunion de bureau",
            "content": "Contenu du rapport.",
            "report_date": "2026-06-20T10:00:00",
            "location": "Salle principale",
            "participants": [],
        },
    )

    assert response.status_code == 201


# ─────────────────────────────────────────────────────────────────────────────
#  GET /
# ─────────────────────────────────────────────────────────────────────────────


def test_list_reports():
    report = _make_report_response()
    mock_service = MagicMock()
    mock_service.list_reports = AsyncMock(
        return_value={
            "items": [report],
            "total": 1,
            "skip": 0,
            "limit": 20,
        }
    )
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    # Non-SERVANT user: _is_secretaire returns early with False (no DB call)
    response = client.get("/reports/")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /my-reports
# ─────────────────────────────────────────────────────────────────────────────


def test_get_my_reports():
    report = _make_report_response()
    mock_service = MagicMock()
    mock_service.get_my_reports = AsyncMock(return_value=[report])
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    response = client.get("/reports/my-reports")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  GET /{report_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_get_report():
    report = _make_report_response()
    mock_service = MagicMock()
    mock_service.get_report = AsyncMock(return_value=report)
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    # Admin role => _is_secretaire returns early (role.value != 'SERVANT')
    response = client.get(f"/reports/{report.id}")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  PATCH /{report_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_update_report():
    report = _make_report_response()
    mock_service = MagicMock()
    mock_service.update_report = AsyncMock(return_value=report)
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    response = client.patch(f"/reports/{report.id}", json={"title": "Updated"})

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /{report_id}
# ─────────────────────────────────────────────────────────────────────────────


def test_delete_report():
    mock_service = MagicMock()
    mock_service.delete_report = AsyncMock(return_value=None)
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    response = client.delete(f"/reports/{uuid4()}")

    assert response.status_code == 204


# ─────────────────────────────────────────────────────────────────────────────
#  POST /{report_id}/publish
# ─────────────────────────────────────────────────────────────────────────────


def test_publish_report():
    report = _make_report_response()
    mock_service = MagicMock()
    mock_service.publish_report = AsyncMock(return_value=report)
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    response = client.post(f"/reports/{report.id}/publish", json={"publish": True})

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /{report_id}/archive
# ─────────────────────────────────────────────────────────────────────────────


def test_archive_report():
    report = _make_report_response()
    mock_service = MagicMock()
    mock_service.archive_report = AsyncMock(return_value=report)
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    response = client.post(f"/reports/{report.id}/archive")

    assert response.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /{report_id}/attachments (add link)
# ─────────────────────────────────────────────────────────────────────────────


def test_add_attachment():
    report_id = uuid4()
    att = _make_attachment_response(report_id)
    mock_service = MagicMock()
    mock_service.add_attachment = AsyncMock(return_value=att)
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    response = client.post(
        f"/reports/{report_id}/attachments",
        json={
            "filename": "test.pdf",
            "file_url": "https://example.com/test.pdf",
            "file_type": "application/pdf",
            "file_size": 1024,
        },
    )

    assert response.status_code in (200, 201)


# ─────────────────────────────────────────────────────────────────────────────
#  GET /{report_id}/attachments
# ─────────────────────────────────────────────────────────────────────────────


def test_get_attachments():
    report_id = uuid4()
    att = _make_attachment_response(report_id)
    mock_service = MagicMock()
    mock_service.get_attachments = AsyncMock(return_value=[att])
    client, session, user, _ = _build_client(role_str="ADMIN", mock_service=mock_service)

    response = client.get(f"/reports/{report_id}/attachments")

    assert response.status_code == 200
