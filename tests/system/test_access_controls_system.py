"""
System tests for critical access control paths.
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from src.core.entities.attendance import Attendance, AttendanceStatus, AttendanceType
from src.core.entities.report import Report, ReportAttachment, ReportStatus, ReportType
from tests.conftest import make_access_token


@pytest.mark.system
async def test_report_attachments_access_control(
    client,
    db_session,
    secretaire_user,
    secretaire_token,
    servant_token,
):
    report_draft = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Brouillon",
        content="Draft content",
        report_date=datetime.now(timezone.utc),
        location="Salle",
        status=ReportStatus.DRAFT,
        created_by=secretaire_user.id,
    )
    report_published = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Publie",
        content="Published content",
        report_date=datetime.now(timezone.utc),
        location="Salle",
        status=ReportStatus.PUBLISHED,
        created_by=secretaire_user.id,
    )
    db_session.add(report_draft)
    db_session.add(report_published)
    await db_session.commit()

    attachment_draft = ReportAttachment(
        id=uuid4(),
        report_id=report_draft.id,
        filename="draft.pdf",
        file_url="https://example.com/draft.pdf",
        file_type="application/pdf",
        file_size=1234,
        uploaded_by=secretaire_user.id,
    )
    attachment_published = ReportAttachment(
        id=uuid4(),
        report_id=report_published.id,
        filename="pub.pdf",
        file_url="https://example.com/pub.pdf",
        file_type="application/pdf",
        file_size=1234,
        uploaded_by=secretaire_user.id,
    )
    db_session.add(attachment_draft)
    db_session.add(attachment_published)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/reports/{report_draft.id}/attachments",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert resp.status_code == 403

    resp = await client.get(
        f"/api/v1/reports/{report_draft.id}/attachments",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )
    assert resp.status_code == 200

    resp = await client.get(
        f"/api/v1/reports/{report_published.id}/attachments",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert resp.status_code == 200


@pytest.mark.system
async def test_attendance_detail_access_control(
    client,
    db_session,
    admin_user,
    admin_token,
    servant_user,
    servant_token,
    parent_user,
):
    attendance = Attendance(
        user_id=servant_user.id,
        attendance_type=AttendanceType.REUNION_ORDINAIRE,
        attendance_date=datetime.now(timezone.utc),
        title="Reunion",
        status=AttendanceStatus.PRESENT,
        recorded_by=admin_user.id,
    )
    db_session.add(attendance)
    await db_session.commit()

    resp = await client.get(
        f"/api/v1/attendance/{attendance.id}",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert resp.status_code == 200

    parent_token = make_access_token(parent_user)
    resp = await client.get(
        f"/api/v1/attendance/{attendance.id}",
        headers={"Authorization": f"Bearer {parent_token}"},
    )
    assert resp.status_code == 403

    resp = await client.get(
        f"/api/v1/attendance/{attendance.id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200


@pytest.mark.system
async def test_attendance_sessions_list_accessible(client, servant_token, censeur_token):
    # All authenticated users can view sessions (servants need to see their attendance)
    resp = await client.get(
        "/api/v1/attendance-sessions/",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert resp.status_code == 200

    resp = await client.get(
        "/api/v1/attendance-sessions/",
        headers={"Authorization": f"Bearer {censeur_token}"},
    )
    assert resp.status_code == 200
