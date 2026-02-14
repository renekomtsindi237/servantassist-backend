"""
Tests de performance pour le module SECRETAIRE - Rapports.
"""
import pytest
from datetime import datetime
from uuid import uuid4
import time


@pytest.mark.asyncio
async def test_create_report_performance(client, secretaire_token):
    """Test performance création de rapport."""
    start_time = time.time()
    
    response = await client.post(
        "/api/v1/reports/",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "type": "REUNION",
            "title": "Réunion test",
            "content": "Contenu de test",
            "report_date": "2026-02-08T15:00:00",
            "location": "Salle paroissiale",
            "participants": ["Jean Dupont", "Pierre Martin"],
        },
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 201
    assert elapsed < 1.0  # Moins d'1 seconde


@pytest.mark.asyncio
async def test_list_reports_performance(client, secretaire_token, db_session):
    """Test performance liste des rapports."""
    from src.core.entities.report import Report, ReportType, ReportStatus
    
    # Créer 100 rapports
    for i in range(100):
        report = Report(
            id=uuid4(),
            type=ReportType.MEETING,
            title=f"Rapport {i}",
            content="Contenu test",
            report_date=datetime(2026, 2, 8, 15, 0),
            location="Salle",
            participants=[],
            status=ReportStatus.PUBLISHED,
            created_by=uuid4(),
            published_at=datetime.utcnow(),
        )
        db_session.add(report)
    
    await db_session.commit()
    
    start_time = time.time()
    
    response = await client.get(
        "/api/v1/reports/?limit=100",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 200
    assert elapsed < 2.0  # Moins de 2 secondes


@pytest.mark.asyncio
async def test_get_report_detail_performance(client, secretaire_token, sample_report):
    """Test performance récupération détail."""
    start_time = time.time()
    
    response = await client.get(
        f"/api/v1/reports/{sample_report.id}",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 200
    assert elapsed < 0.5  # Moins de 500ms


@pytest.mark.asyncio
async def test_update_report_performance(client, secretaire_token, sample_report):
    """Test performance modification."""
    start_time = time.time()
    
    response = await client.patch(
        f"/api/v1/reports/{sample_report.id}",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "title": "Titre modifié",
            "content": "Contenu modifié",
        },
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 200
    assert elapsed < 0.5  # Moins de 500ms


@pytest.mark.asyncio
async def test_publish_report_performance(client, secretaire_token, sample_report):
    """Test performance publication."""
    start_time = time.time()
    
    response = await client.post(
        f"/api/v1/reports/{sample_report.id}/publish",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 200
    assert elapsed < 0.5  # Moins de 500ms


@pytest.mark.asyncio
async def test_add_attachment_performance(client, secretaire_token, sample_report):
    """Test performance ajout pièce jointe."""
    start_time = time.time()
    
    response = await client.post(
        f"/api/v1/reports/{sample_report.id}/attachments",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "filename": "test.pdf",
            "file_url": "https://example.com/test.pdf",
            "file_type": "application/pdf",
            "file_size": 1024000,
        },
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 201
    assert elapsed < 1.0  # Moins d'1 seconde


@pytest.mark.asyncio
async def test_get_attachments_performance(client, secretaire_token, sample_report, db_session):
    """Test performance récupération pièces jointes."""
    from src.core.entities.report import ReportAttachment
    
    # Créer 20 pièces jointes
    for i in range(20):
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
    
    start_time = time.time()
    
    response = await client.get(
        f"/api/v1/reports/{sample_report.id}/attachments",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 200
    assert elapsed < 1.0  # Moins d'1 seconde


@pytest.mark.asyncio
async def test_filter_reports_performance(client, secretaire_token, db_session):
    """Test performance filtrage."""
    from src.core.entities.report import Report, ReportType, ReportStatus
    
    # Créer 50 rapports de différents types
    for i in range(50):
        report = Report(
            id=uuid4(),
            type=ReportType.MEETING if i % 2 == 0 else ReportType.ACTIVITY,
            title=f"Rapport {i}",
            content="Contenu",
            report_date=datetime(2026, 2, i % 28 + 1, 15, 0),
            location="Salle",
            participants=[],
            status=ReportStatus.PUBLISHED,
            created_by=uuid4(),
            published_at=datetime.utcnow(),
        )
        db_session.add(report)
    
    await db_session.commit()
    
    start_time = time.time()
    
    response = await client.get(
        "/api/v1/reports/?report_type=REUNION&start_date=2026-02-01T00:00:00&end_date=2026-02-28T23:59:59",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 200
    assert elapsed < 1.5  # Moins de 1.5 secondes


@pytest.mark.asyncio
async def test_pagination_performance(client, secretaire_token, db_session):
    """Test performance pagination."""
    from src.core.entities.report import Report, ReportType, ReportStatus
    
    # Créer 200 rapports
    for i in range(200):
        report = Report(
            id=uuid4(),
            type=ReportType.MEETING,
            title=f"Rapport {i}",
            content="Contenu",
            report_date=datetime(2026, 2, 8, 15, 0),
            location="Salle",
            participants=[],
            status=ReportStatus.PUBLISHED,
            created_by=uuid4(),
            published_at=datetime.utcnow(),
        )
        db_session.add(report)
    
    await db_session.commit()
    
    # Tester plusieurs pages
    start_time = time.time()
    
    for page in range(4):  # 4 pages de 50
        response = await client.get(
            f"/api/v1/reports/?skip={page * 50}&limit=50",
            headers={"Authorization": f"Bearer {secretaire_token}"},
        )
        assert response.status_code == 200
    
    elapsed = time.time() - start_time
    
    # 4 requêtes en moins de 4 secondes
    assert elapsed < 4.0


@pytest.mark.asyncio
async def test_my_reports_performance(client, secretaire_token, secretaire_user, db_session):
    """Test performance mes rapports."""
    from src.core.entities.report import Report, ReportType, ReportStatus
    
    # Créer 50 rapports pour le secrétaire
    for i in range(50):
        report = Report(
            id=uuid4(),
            type=ReportType.MEETING,
            title=f"Mon rapport {i}",
            content="Contenu",
            report_date=datetime(2026, 2, 8, 15, 0),
            location="Salle",
            participants=[],
            status=ReportStatus.DRAFT if i % 3 == 0 else ReportStatus.PUBLISHED,
            created_by=secretaire_user.id,
            published_at=datetime.utcnow() if i % 3 != 0 else None,
        )
        db_session.add(report)
    
    await db_session.commit()
    
    start_time = time.time()
    
    response = await client.get(
        "/api/v1/reports/me/list",
        headers={"Authorization": f"Bearer {secretaire_token}"},
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 200
    assert elapsed < 1.0  # Moins d'1 seconde


@pytest.mark.asyncio
async def test_concurrent_report_creation(client, secretaire_token):
    """Test performance création concurrente."""
    import asyncio
    
    async def create_one(index):
        return await client.post(
            "/api/v1/reports/",
            headers={"Authorization": f"Bearer {secretaire_token}"},
            json={
                "type": "REUNION",
                "title": f"Rapport concurrent {index}",
                "content": "Contenu",
                "report_date": "2026-02-08T15:00:00",
                "location": "Salle",
            },
        )
    
    start_time = time.time()
    
    # Créer 10 rapports en parallèle
    tasks = [create_one(i) for i in range(10)]
    responses = await asyncio.gather(*tasks)
    
    elapsed = time.time() - start_time
    
    # Tous devraient réussir
    assert all(r.status_code == 201 for r in responses)
    # Devrait être plus rapide que séquentiel
    assert elapsed < 5.0  # Moins de 5 secondes pour 10 rapports


@pytest.mark.asyncio
async def test_large_content_performance(client, secretaire_token):
    """Test performance avec contenu volumineux."""
    # Contenu de 10KB
    large_content = "Lorem ipsum dolor sit amet. " * 400
    
    start_time = time.time()
    
    response = await client.post(
        "/api/v1/reports/",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "type": "REUNION",
            "title": "Rapport volumineux",
            "content": large_content,
            "report_date": "2026-02-08T15:00:00",
            "location": "Salle",
        },
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 201
    assert elapsed < 2.0  # Moins de 2 secondes


@pytest.mark.asyncio
async def test_many_participants_performance(client, secretaire_token):
    """Test performance avec beaucoup de participants."""
    # 100 participants
    participants = [f"Participant {i}" for i in range(100)]
    
    start_time = time.time()
    
    response = await client.post(
        "/api/v1/reports/",
        headers={"Authorization": f"Bearer {secretaire_token}"},
        json={
            "type": "REUNION",
            "title": "Grande réunion",
            "content": "Contenu",
            "report_date": "2026-02-08T15:00:00",
            "location": "Salle",
            "participants": participants,
        },
    )
    
    elapsed = time.time() - start_time
    
    assert response.status_code == 201
    assert elapsed < 1.5  # Moins de 1.5 secondes
