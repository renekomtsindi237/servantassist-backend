"""
Tests E2E pour le module SECRETAIRE - Rapports.
"""
from datetime import datetime
from uuid import uuid4

import pytest


@pytest.mark.asyncio
async def test_create_report_success(client, secretaire_token):
    """Test création de rapport réussie."""
    response = await client.post(
        "/api/v1/reports/",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "type": "REUNION",
            "title": "Réunion hebdomadaire du 8 février",
            "content": "Ordre du jour: 1. Point sur les activités...",
            "report_date": "2026-02-08T15:00:00",
            "location": "Salle paroissiale",
            "participants": ["Jean Dupont", "Pierre Martin"],
            "decisions": "Décision de programmer une retraite",
            "action_items": "Action: Réserver le lieu pour la retraite",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "REUNION"
    assert data["title"] == "Réunion hebdomadaire du 8 février"
    assert data["status"] == "BROUILLON"
    assert data["watermark_logo"] == "logo_servant.jpeg"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_report_activity(client, secretaire_token):
    """Test création de rapport d'activité."""
    response = await client.post(
        "/api/v1/reports/",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "type": "ACTIVITE",
            "title": "Sortie au sanctuaire",
            "content": "Sortie organisée le samedi...",
            "report_date": "2026-02-15T09:00:00",
            "location": "Sanctuaire Notre-Dame",
            "participants": ["Tous les servants"],
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "ACTIVITE"


@pytest.mark.asyncio
async def test_create_report_unauthorized(client, servant_token):
    """Test qu'un servant normal ne peut pas créer de rapport."""
    response = await client.post(
        "/api/v1/reports/",
        headers={"Authorization": f"Bearer {servant_token}"},
        json={
            "type": "REUNION",
            "title": "Test",
            "content": "Test",
            "report_date": "2026-02-08T15:00:00",
            "location": "Test",
        },
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_reports_published_only(
    client, secretaire_token, servant_token, db_session
):
    """Test que les non-secrétaires ne voient que les rapports publiés."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    # Créer un rapport en brouillon
    draft_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport brouillon",
        content="Contenu brouillon",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.DRAFT,
    )
    db_session.add(draft_report)

    # Créer un rapport publié
    published_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport publié",
        content="Contenu publié",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    db_session.add(published_report)
    await db_session.commit()

    # Secrétaire voit tous les rapports
    response = await client.get(
        "/api/v1/reports/",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2

    # Servant ne voit que les rapports publiés
    response = await client.get(
        "/api/v1/reports/",
        headers={"Authorization": f"Bearer {servant_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    # Devrait voir au moins le rapport publié
    assert any(r["status"] == "PUBLIE" for r in data["items"])


@pytest.mark.asyncio
async def test_get_report_detail(client, secretaire_token, sample_report):
    """Test récupération du détail d'un rapport."""
    response = await client.get(
        f"/api/v1/reports/{sample_report.id}",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_report.id)
    assert data["title"] == sample_report.title


@pytest.mark.asyncio
async def test_get_report_not_found(client, secretaire_token):
    """Test récupération d'un rapport inexistant."""
    response = await client.get(
        f"/api/v1/reports/{uuid4()}",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_report_success(client, secretaire_token, sample_report):
    """Test modification d'un rapport."""
    response = await client.patch(
        f"/api/v1/reports/{sample_report.id}",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "title": "Titre modifié",
            "content": "Contenu modifié",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Titre modifié"
    assert data["content"] == "Contenu modifié"


@pytest.mark.asyncio
async def test_update_published_report_fails(client, secretaire_token, db_session):
    """Test qu'on ne peut pas modifier un rapport publié."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    # Créer un rapport publié
    report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport publié",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    db_session.add(report)
    await db_session.commit()

    response = await client.patch(
        f"/api/v1/reports/{report.id}",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={"title": "Nouveau titre"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_delete_report_success(client, secretaire_token, sample_report):
    """Test suppression d'un rapport."""
    response = await client.delete(
        f"/api/v1/reports/{sample_report.id}",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_published_report_fails(client, secretaire_token, db_session):
    """Test qu'on ne peut pas supprimer un rapport publié."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport publié",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    db_session.add(report)
    await db_session.commit()

    response = await client.delete(
        f"/api/v1/reports/{report.id}",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_publish_report_success(client, secretaire_token, sample_report):
    """Test publication d'un rapport."""
    response = await client.post(
        f"/api/v1/reports/{sample_report.id}/publish",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PUBLIE"
    assert data["published_at"] is not None


@pytest.mark.asyncio
async def test_publish_already_published_fails(client, secretaire_token, db_session):
    """Test qu'on ne peut pas republier un rapport déjà publié."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport publié",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    db_session.add(report)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/reports/{report.id}/publish",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_archive_report_success(client, secretaire_token, db_session):
    """Test archivage d'un rapport."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport publié",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    db_session.add(report)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/reports/{report.id}/archive",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ARCHIVE"


@pytest.mark.asyncio
async def test_archive_draft_fails(client, secretaire_token, sample_report):
    """Test qu'on ne peut pas archiver un brouillon."""
    response = await client.post(
        f"/api/v1/reports/{sample_report.id}/archive",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_my_reports(client, secretaire_token, secretaire_user, db_session):
    """Test récupération de mes rapports."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    # Créer des rapports pour le secrétaire
    for i in range(3):
        report = Report(
            id=uuid4(),
            type=ReportType.MEETING,
            title=f"Mon rapport {i}",
            content="Contenu",
            report_date=datetime(2026, 2, 8, 15, 0),
            location="Salle",
            created_by=secretaire_user.id,
            status=ReportStatus.DRAFT,
        )
        db_session.add(report)

    await db_session.commit()

    response = await client.get(
        "/api/v1/reports/me/list",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3


@pytest.mark.asyncio
async def test_add_attachment_success(client, secretaire_token, sample_report):
    """Test ajout d'une pièce jointe."""
    response = await client.post(
        f"/api/v1/reports/{sample_report.id}/attachments",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "filename": "compte_rendu.pdf",
            "file_url": "https://storage.example.com/files/compte_rendu.pdf",
            "file_type": "application/pdf",
            "file_size": 1024000,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "compte_rendu.pdf"
    assert data["report_id"] == str(sample_report.id)


@pytest.mark.asyncio
async def test_add_attachment_to_published_fails(client, secretaire_token, db_session):
    """Test qu'on ne peut pas ajouter de pièce jointe à un rapport publié."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Rapport publié",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    db_session.add(report)
    await db_session.commit()

    response = await client.post(
        f"/api/v1/reports/{report.id}/attachments",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "filename": "test.pdf",
            "file_url": "https://example.com/test.pdf",
            "file_type": "application/pdf",
            "file_size": 1024,
        },
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_attachments(client, secretaire_token, sample_report, db_session):
    """Test récupération des pièces jointes."""
    from src.core.entities.report import ReportAttachment

    # Créer des pièces jointes
    for i in range(2):
        attachment = ReportAttachment(
            id=uuid4(),
            report_id=sample_report.id,
            filename=f"file{i}.pdf",
            file_url=f"https://example.com/file{i}.pdf",
            file_type="application/pdf",
            file_size=1024,
            uploaded_by=uuid4(),
        )
        db_session.add(attachment)

    await db_session.commit()

    response = await client.get(
        f"/api/v1/reports/{sample_report.id}/attachments",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


@pytest.mark.asyncio
async def test_delete_attachment_success(client, secretaire_token, sample_attachment):
    """Test suppression d'une pièce jointe."""
    response = await client.delete(
        f"/api/v1/reports/attachments/{sample_attachment.id}",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_filter_reports_by_type(client, secretaire_token, db_session):
    """Test filtrage des rapports par type."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    # Créer des rapports de différents types
    meeting_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Réunion",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    activity_report = Report(
        id=uuid4(),
        type=ReportType.ACTIVITY,
        title="Activité",
        content="Contenu",
        report_date=datetime(2026, 2, 8, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    db_session.add(meeting_report)
    db_session.add(activity_report)
    await db_session.commit()

    # Filtrer par type REUNION
    response = await client.get(
        "/api/v1/reports/?report_type=REUNION",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert all(r["type"] == "REUNION" for r in data["items"])


@pytest.mark.asyncio
async def test_filter_reports_by_date_range(client, secretaire_token, db_session):
    """Test filtrage des rapports par période."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    # Créer des rapports à différentes dates
    old_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Ancien rapport",
        content="Contenu",
        report_date=datetime(2026, 1, 1, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    new_report = Report(
        id=uuid4(),
        type=ReportType.MEETING,
        title="Nouveau rapport",
        content="Contenu",
        report_date=datetime(2026, 2, 15, 15, 0),
        location="Salle",
        created_by=uuid4(),
        status=ReportStatus.PUBLISHED,
        published_at=datetime.utcnow(),
    )
    db_session.add(old_report)
    db_session.add(new_report)
    await db_session.commit()

    # Filtrer février uniquement
    response = await client.get(
        "/api/v1/reports/?start_date=2026-02-01T00:00:00&end_date=2026-02-28T23:59:59",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    # Devrait contenir le nouveau rapport mais pas l'ancien
    assert any(r["title"] == "Nouveau rapport" for r in data["items"])


@pytest.mark.asyncio
async def test_pagination(client, secretaire_token, db_session):
    """Test pagination de la liste des rapports."""
    from src.core.entities.report import Report, ReportStatus, ReportType

    # Créer 10 rapports
    for i in range(10):
        report = Report(
            id=uuid4(),
            type=ReportType.MEETING,
            title=f"Rapport {i}",
            content="Contenu",
            report_date=datetime(2026, 2, 8, 15, 0),
            location="Salle",
            created_by=uuid4(),
            status=ReportStatus.PUBLISHED,
            published_at=datetime.utcnow(),
        )
        db_session.add(report)

    await db_session.commit()

    # Première page
    response = await client.get(
        "/api/v1/reports/?skip=0&limit=5",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= 5
    assert data["skip"] == 0
    assert data["limit"] == 5
    assert data["total"] >= 10
