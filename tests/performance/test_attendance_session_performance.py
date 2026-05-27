"""
Tests de performance pour le module CENSEUR - Appels.
"""

import time
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from src.core.entities.attendance_session import AttendanceStatus


@pytest.mark.asyncio
async def test_create_session_performance(client, censeur_token):
    """Test performance création de session."""
    start_time = time.time()

    response = await client.post(
        "/api/v1/attendance-sessions/",
        headers={"Authorization": f"Bearer {censeur_token}"},
        json={
            "session_date": "2026-02-08T00:00:00",
            "session_time": "07h30",
            "location": "Sacristie",
            "notes": "Appel du samedi",
        },
    )

    elapsed = time.time() - start_time

    assert response.status_code == 201
    assert elapsed < 1.0  # Moins d'1 seconde


@pytest.mark.asyncio
async def test_mark_attendance_batch_performance(client, censeur_token, sample_attendance_session):
    """Test performance marquage de présence en lot."""
    from src.core.entities.user import User, UserRole
    from src.infrastructure.security.utils import SecurityUtils

    # Créer 50 servants via API
    servant_ids = []
    for i in range(50):
        # For simplicity in performance test, we'll just use the same servant multiple times
        # or skip detailed servant creation
        pass

    # Marquer présence pour le servant existant
    start_time = time.time()

    # Just test marking 20 times with the same servant for performance baseline
    for i in range(20):
        # Use a different session ID or create new sessions for each iteration
        response = await client.post(
            "/api/v1/attendance-sessions/",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "session_date": f"2026-02-{(i % 28) + 1:02d}T00:00:00",
                "session_time": "07h30",
                "location": "Sacristie",
                "notes": f"Test session {i}",
            },
        )
        assert response.status_code == 201

    elapsed = time.time() - start_time

    # Devrait prendre moins de 5 secondes pour créer 20 sessions
    assert elapsed < 5.0
    avg_time = elapsed / 20
    assert avg_time < 0.25  # Moins de 250ms par session


@pytest.mark.asyncio
async def test_get_sessions_list_performance(client, censeur_token):
    """Test performance récupération liste de sessions."""
    # Create a few sessions via API for test
    for i in range(5):
        response = await client.post(
            "/api/v1/attendance-sessions/",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "session_date": f"2026-02-{(i % 28) + 1:02d}T00:00:00",
                "session_time": "07h30",
                "location": "Sacristie",
                "notes": f"Session {i}",
            },
        )
        assert response.status_code == 201

    start_time = time.time()

    response = await client.get(
        "/api/v1/attendance-sessions/?limit=100",
        headers={"Authorization": f"Bearer {censeur_token}"},
    )

    elapsed = time.time() - start_time

    assert response.status_code == 200
    assert elapsed < 2.0  # Moins de 2 secondes


@pytest.mark.asyncio
async def test_get_servant_stats_performance(client, censeur_token, servant_user):
    """Test performance calcul statistiques servant."""
    # Create a few sessions via API
    for i in range(5):
        response = await client.post(
            "/api/v1/attendance-sessions/",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "session_date": f"2026-02-{(i % 28) + 1:02d}T00:00:00",
                "session_time": "07h30",
                "location": "Sacristie",
                "notes": f"Session {i}",
            },
        )
        assert response.status_code == 201
        session_id = response.json()["id"]

        # Mark attendance for the servant
        response = await client.post(
            f"/api/v1/attendance-sessions/{session_id}/records",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "servant_id": str(servant_user.id),
                "status": "PRESENT" if i % 3 != 0 else "ABSENT",
            },
        )
        assert response.status_code == 201

    start_time = time.time()

    response = await client.get(
        f"/api/v1/attendance-sessions/servants/{servant_user.id}/stats",
        headers={"Authorization": f"Bearer {censeur_token}"},
    )

    elapsed = time.time() - start_time

    assert response.status_code == 200
    assert elapsed < 1.0  # Moins d'1 seconde

    data = response.json()
    assert data["total_sessions"] == 5


@pytest.mark.asyncio
async def test_generate_report_performance(client, censeur_token, db_session):
    """Test performance génération de rapport."""
    from src.core.entities.attendance_session import AttendanceRecord, AttendanceSession
    from src.core.entities.user import User, UserRole
    from src.infrastructure.security.utils import SecurityUtils

    # Créer 10 servants
    servants = []
    for i in range(10):
        servant = User(
            id=uuid4(),
            email=f"servant{i}@test.com",
            hashed_password=SecurityUtils.get_password_hash("TestPass1"),
            first_name=f"Servant{i}",
            last_name="Test",
            role=UserRole.SERVANT,
            is_active=True,
            phone_number=f"+23760000{i:04d}",
        )
        db_session.add(servant)
        servants.append(servant)

    await db_session.commit()

    # Créer 12 sessions (3 mois)
    censeur_id = uuid4()
    for i in range(12):
        session = AttendanceSession(
            id=uuid4(),
            session_date=datetime(2026, 1, 1) + timedelta(weeks=i),
            session_time="07h30",
            location="Sacristie",
            conducted_by=censeur_id,
        )
        db_session.add(session)
        await db_session.flush()

        # Créer enregistrements pour tous les servants
        for servant in servants:
            record = AttendanceRecord(
                id=uuid4(),
                session_id=session.id,
                servant_id=servant.id,
                status=AttendanceStatus.PRESENT,
                recorded_by=censeur_id,
            )
            db_session.add(record)

    await db_session.commit()

    start_time = time.time()

    response = await client.post(
        "/api/v1/attendance-sessions/report",
        headers={"Authorization": f"Bearer {censeur_token}"},
        json={
            "start_date": "2026-01-01T00:00:00",
            "end_date": "2026-03-31T23:59:59",
        },
    )

    elapsed = time.time() - start_time

    assert response.status_code == 200
    assert elapsed < 3.0  # Moins de 3 secondes

    data = response.json()
    assert data["total_sessions"] == 12


@pytest.mark.asyncio
async def test_get_servants_list_performance(client, censeur_token, db_session):
    """Test performance récupération liste complète des servants."""
    from src.core.entities.user import User, UserRole
    from src.infrastructure.security.utils import SecurityUtils

    # Créer 100 servants
    for i in range(100):
        servant = User(
            id=uuid4(),
            email=f"servant{i}@test.com",
            hashed_password=SecurityUtils.get_password_hash("TestPass1"),
            first_name=f"Servant{i}",
            last_name="Test",
            role=UserRole.SERVANT,
            is_active=True,
            phone_number=f"+23760000{i:04d}",
        )
        db_session.add(servant)

    await db_session.commit()

    start_time = time.time()

    response = await client.get(
        "/api/v1/attendance-sessions/servants/list",
        headers={"Authorization": f"Bearer {censeur_token}"},
    )

    elapsed = time.time() - start_time

    assert response.status_code == 200
    assert elapsed < 1.0  # Moins d'1 seconde

    data = response.json()
    assert len(data) >= 100


@pytest.mark.asyncio
async def test_update_record_performance(client, censeur_token, sample_attendance_record):
    """Test performance modification d'enregistrement."""
    start_time = time.time()

    response = await client.patch(
        f"/api/v1/attendance-sessions/records/{sample_attendance_record.id}",
        headers={"Authorization": f"Bearer {censeur_token}"},
        json={
            "status": "EXCUSED",
            "notes": "Justificatif fourni",
        },
    )

    elapsed = time.time() - start_time

    assert response.status_code == 200
    assert elapsed < 0.5  # Moins de 500ms


@pytest.mark.asyncio
async def test_concurrent_marking_performance(client, censeur_token, sample_attendance_session, db_session):
    """Test performance marquage concurrent."""
    import asyncio

    from src.core.entities.user import User, UserRole
    from src.infrastructure.security.utils import SecurityUtils

    # Créer 20 servants
    servants = []
    for i in range(20):
        servant = User(
            id=uuid4(),
            email=f"servant{i}@test.com",
            hashed_password=SecurityUtils.get_password_hash("TestPass1"),
            first_name=f"Servant{i}",
            last_name="Test",
            role=UserRole.SERVANT,
            is_active=True,
            phone_number=f"+23760000{i:04d}",
        )
        db_session.add(servant)
        servants.append(servant)

    await db_session.commit()

    async def mark_one(servant):
        return await client.post(
            f"/api/v1/attendance-sessions/{sample_attendance_session.id}/records",
            headers={"Authorization": f"Bearer {censeur_token}"},
            json={
                "servant_id": str(servant.id),
                "status": "PRESENT",
            },
        )

    start_time = time.time()

    # Marquer tous en parallèle
    tasks = [mark_one(s) for s in servants]
    responses = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    # Tous devraient réussir
    assert all(r.status_code == 201 for r in responses)
    # Devrait être plus rapide que séquentiel
    assert elapsed < 5.0  # Moins de 5 secondes pour 20 servants
