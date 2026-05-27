"""
Tests unitaires pour le service de gestion des rapports (SECRETAIRE).
"""
from datetime import datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.application.services.report_service import ReportService
from src.core.entities.report import Report, ReportAttachment, ReportStatus, ReportType


@pytest.fixture
def mock_report_repo():
    """Mock du repository de rapports."""
    return AsyncMock()


@pytest.fixture
def mock_attachment_repo():
    """Mock du repository de pièces jointes."""
    return AsyncMock()


@pytest.fixture
def service(mock_report_repo, mock_attachment_repo):
    """Service avec repositories mockés."""
    return ReportService(mock_report_repo, mock_attachment_repo)


@pytest.fixture
def sample_report():
    """Rapport de test."""
    return Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Réunion hebdomadaire",
        content="Ordre du jour...",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle paroissiale",
        participants=["Jean Dupont"],
        status=ReportStatus.DRAFT,
        created_by=uuid4(),
    )


# ── Tests création de rapport ────────────────────────────────────────────
@pytest.mark.asyncio
async def test_create_report_meeting(service, mock_report_repo):
    """Test création d'un rapport de réunion."""
    report_id = uuid4()
    created_by = uuid4()

    mock_report_repo.create.return_value = Report(
        id=report_id,
        type=ReportType.MEETING,
        title="Réunion test",
        content="Contenu test",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        participants=["Jean"],
        status=ReportStatus.DRAFT,
        created_by=created_by,
    )

    result = await service.create_report(
        type=ReportType.MEETING,
        title="Réunion test",
        content="Contenu test",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=created_by,
        participants=["Jean"],
    )

    assert result.type == ReportType.MEETING
    assert result.status == ReportStatus.DRAFT
    mock_report_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_report_activity(service, mock_report_repo):
    """Test création d'un rapport d'activité."""
    report_id = uuid4()
    created_by = uuid4()

    mock_report_repo.create.return_value = Report(
        id=report_id,
        type=ReportType.ACTIVITY,
        title="Sortie",
        content="Sortie au sanctuaire",
        report_date=datetime(2026, 2, 15, 9, 0),
        location="Sanctuaire",
        participants=[],
        status=ReportStatus.DRAFT,
        created_by=created_by,
    )

    result = await service.create_report(
        type=ReportType.ACTIVITY,
        title="Sortie",
        content="Sortie au sanctuaire",
        report_date=datetime(2026, 2, 15, 9, 0),
        location="Sanctuaire",
        created_by=created_by,
    )

    assert result.type == ReportType.ACTIVITY


@pytest.mark.asyncio
async def test_create_report_with_decisions(service, mock_report_repo):
    """Test création avec décisions et actions."""
    report_id = uuid4()
    created_by = uuid4()

    mock_report_repo.create.return_value = Report(
        id=report_id,
        type=ReportType.MEETING,
        title="Réunion",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        participants=[],
        decisions="Décision importante",
        action_items="Action à mener",
        status=ReportStatus.DRAFT,
        created_by=created_by,
    )

    result = await service.create_report(
        type=ReportType.MEETING,
        title="Réunion",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=created_by,
        decisions="Décision importante",
        action_items="Action à mener",
    )

    assert result.decisions == "Décision importante"
    assert result.action_items == "Action à mener"


# ── Tests récupération ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_report_success(service, mock_report_repo, sample_report):
    """Test récupération d'un rapport."""
    mock_report_repo.get_by_id.return_value = sample_report

    result = await service.get_report(sample_report.id)

    assert result.id == sample_report.id
    mock_report_repo.get_by_id.assert_called_once_with(sample_report.id)


@pytest.mark.asyncio
async def test_get_report_not_found(service, mock_report_repo):
    """Test récupération d'un rapport inexistant."""
    mock_report_repo.get_by_id.return_value = None

    result = await service.get_report(uuid4())

    assert result is None


# ── Tests liste ───────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_list_reports(service, mock_report_repo):
    """Test liste des rapports."""
    reports = [
        Report(
            id=uuid4(),
            type=ReportType.MEETING,
            title=f"Rapport {i}",
            content="Contenu",
            report_date=datetime(2026, 2, 8, 15, 0),
            location="Salle",
            participants=[],
            status=ReportStatus.PUBLISHED,
            created_by=uuid4(),
        )
        for i in range(5)
    ]

    mock_report_repo.list_reports.return_value = (reports, 5)

    result, total = await service.list_reports(skip=0, limit=10)

    assert len(result) == 5
    assert total == 5


@pytest.mark.asyncio
async def test_list_reports_with_filters(service, mock_report_repo):
    """Test liste avec filtres."""
    mock_report_repo.list_reports.return_value = ([], 0)

    await service.list_reports(
        report_type=ReportType.MEETING,
        status=ReportStatus.PUBLISHED,
        start_date=datetime(2026, 2, 1),
        end_date=datetime(2026, 2, 28),
    )

    mock_report_repo.list_reports.assert_called_once()


# ── Tests modification ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_update_report_success(service, mock_report_repo, sample_report):
    """Test modification d'un rapport."""
    mock_report_repo.get_by_id.return_value = sample_report
    mock_report_repo.update.return_value = sample_report

    result = await service.update_report(
        report_id=sample_report.id,
        title="Nouveau titre",
        content="Nouveau contenu",
    )

    assert result.title == "Nouveau titre"
    assert result.content == "Nouveau contenu"


@pytest.mark.asyncio
async def test_update_published_report_fails(service, mock_report_repo):
    """Test qu'on ne peut pas modifier un rapport publié."""
    published_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        participants=[],
        status=ReportStatus.PUBLISHED,
        created_by=uuid4(),
        published_at=datetime.utcnow(),
    )

    mock_report_repo.get_by_id.return_value = published_report

    with pytest.raises(ValueError, match="brouillon"):
        await service.update_report(
            report_id=published_report.id,
            title="Nouveau titre",
        )


@pytest.mark.asyncio
async def test_update_report_not_found(service, mock_report_repo):
    """Test modification d'un rapport inexistant."""
    mock_report_repo.get_by_id.return_value = None

    result = await service.update_report(
        report_id=uuid4(),
        title="Nouveau titre",
    )

    assert result is None


# ── Tests suppression ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_delete_report_success(service, mock_report_repo, sample_report):
    """Test suppression d'un rapport."""
    mock_report_repo.get_by_id.return_value = sample_report
    mock_report_repo.delete.return_value = True

    result = await service.delete_report(sample_report.id)

    assert result is True


@pytest.mark.asyncio
async def test_delete_published_report_fails(service, mock_report_repo):
    """Test qu'on ne peut pas supprimer un rapport publié."""
    published_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        participants=[],
        status=ReportStatus.PUBLISHED,
        created_by=uuid4(),
        published_at=datetime.utcnow(),
    )

    mock_report_repo.get_by_id.return_value = published_report

    with pytest.raises(ValueError, match="brouillon"):
        await service.delete_report(published_report.id)


# ── Tests publication ─────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_publish_report_success(service, mock_report_repo, sample_report):
    """Test publication d'un rapport."""
    published_report = sample_report.model_copy()
    published_report.status = ReportStatus.PUBLISHED
    published_report.published_at = datetime.utcnow()

    mock_report_repo.get_by_id.return_value = sample_report
    mock_report_repo.publish.return_value = published_report

    result = await service.publish_report(sample_report.id)

    assert result.status == ReportStatus.PUBLISHED
    assert result.published_at is not None


@pytest.mark.asyncio
async def test_publish_already_published_fails(service, mock_report_repo):
    """Test qu'on ne peut pas republier."""
    published_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        participants=[],
        status=ReportStatus.PUBLISHED,
        created_by=uuid4(),
        published_at=datetime.utcnow(),
    )

    mock_report_repo.get_by_id.return_value = published_report

    with pytest.raises(ValueError, match="brouillon"):
        await service.publish_report(published_report.id)


# ── Tests archivage ───────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_archive_report_success(service, mock_report_repo):
    """Test archivage d'un rapport."""
    published_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        participants=[],
        status=ReportStatus.PUBLISHED,
        created_by=uuid4(),
        published_at=datetime.utcnow(),
    )

    archived_report = published_report.model_copy()
    archived_report.status = ReportStatus.ARCHIVED

    mock_report_repo.get_by_id.return_value = published_report
    mock_report_repo.archive.return_value = archived_report

    result = await service.archive_report(published_report.id)

    assert result.status == ReportStatus.ARCHIVED


@pytest.mark.asyncio
async def test_archive_draft_fails(service, mock_report_repo, sample_report):
    """Test qu'on ne peut pas archiver un brouillon."""
    mock_report_repo.get_by_id.return_value = sample_report

    with pytest.raises(ValueError, match="publié"):
        await service.archive_report(sample_report.id)


# ── Tests pièces jointes ──────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_add_attachment_success(
    service, mock_report_repo, mock_attachment_repo, sample_report
):
    """Test ajout d'une pièce jointe."""
    attachment = ReportAttachment(
        id=uuid4(),
        report_id=sample_report.id,
        filename="test.pdf",
        file_url="https://example.com/test.pdf",
        file_type="application/pdf",
        file_size=1024,
        uploaded_by=uuid4(),
    )

    mock_report_repo.get_by_id.return_value = sample_report
    mock_attachment_repo.create.return_value = attachment

    result = await service.add_attachment(
        report_id=sample_report.id,
        filename="test.pdf",
        file_url="https://example.com/test.pdf",
        file_type="application/pdf",
        file_size=1024,
        uploaded_by=uuid4(),
    )

    assert result.filename == "test.pdf"


@pytest.mark.asyncio
async def test_add_attachment_to_published_fails(service, mock_report_repo):
    """Test qu'on ne peut pas ajouter de pièce jointe à un rapport publié."""
    published_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        participants=[],
        status=ReportStatus.PUBLISHED,
        created_by=uuid4(),
        published_at=datetime.utcnow(),
    )

    mock_report_repo.get_by_id.return_value = published_report

    with pytest.raises(ValueError, match="brouillon"):
        await service.add_attachment(
            report_id=published_report.id,
            filename="test.pdf",
            file_url="https://example.com/test.pdf",
            file_type="application/pdf",
            file_size=1024,
            uploaded_by=uuid4(),
        )


@pytest.mark.asyncio
async def test_get_attachments(service, mock_attachment_repo):
    """Test récupération des pièces jointes."""
    report_id = uuid4()
    attachments = [
        ReportAttachment(
            id=uuid4(),
            report_id=report_id,
            filename=f"file{i}.pdf",
            file_url=f"https://example.com/file{i}.pdf",
            file_type="application/pdf",
            file_size=1024,
            uploaded_by=uuid4(),
        )
        for i in range(3)
    ]

    mock_attachment_repo.get_by_report.return_value = attachments

    result = await service.get_attachments(report_id)

    assert len(result) == 3


@pytest.mark.asyncio
async def test_delete_attachment_success(
    service, mock_report_repo, mock_attachment_repo, sample_report
):
    """Test suppression d'une pièce jointe."""
    attachment = ReportAttachment(
        id=uuid4(),
        report_id=sample_report.id,
        filename="test.pdf",
        file_url="https://example.com/test.pdf",
        file_type="application/pdf",
        file_size=1024,
        uploaded_by=uuid4(),
    )

    mock_attachment_repo.get_by_id.return_value = attachment
    mock_report_repo.get_by_id.return_value = sample_report
    mock_attachment_repo.delete.return_value = True

    result = await service.delete_attachment(attachment.id)

    assert result is True


@pytest.mark.asyncio
async def test_delete_attachment_from_published_fails(
    service, mock_report_repo, mock_attachment_repo
):
    """Test qu'on ne peut pas supprimer une pièce jointe d'un rapport publié."""
    published_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        participants=[],
        status=ReportStatus.PUBLISHED,
        created_by=uuid4(),
        published_at=datetime.utcnow(),
    )

    attachment = ReportAttachment(
        id=uuid4(),
        report_id=published_report.id,
        filename="test.pdf",
        file_url="https://example.com/test.pdf",
        file_type="application/pdf",
        file_size=1024,
        uploaded_by=uuid4(),
    )

    mock_attachment_repo.get_by_id.return_value = attachment
    mock_report_repo.get_by_id.return_value = published_report

    with pytest.raises(ValueError, match="brouillon"):
        await service.delete_attachment(attachment.id)


# ── Tests mes rapports ────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_my_reports(service, mock_report_repo):
    """Test récupération de mes rapports."""
    user_id = uuid4()
    reports = [
        Report(
            id=uuid4(),
            type=ReportType.MEETING,
            title=f"Mon rapport {i}",
            content="Contenu",
            report_date=datetime(2026, 2, 8, 15, 0),
            location="Salle",
            participants=[],
            status=ReportStatus.DRAFT,
            created_by=user_id,
        )
        for i in range(3)
    ]

    mock_report_repo.get_by_created_by.return_value = (reports, 3)

    result, total = await service.get_my_reports(user_id)

    assert len(result) == 3
    assert total == 3
    assert all(r.created_by == user_id for r in result)
