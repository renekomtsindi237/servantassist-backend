"""
Unit tests for TrainingService (CHARGE_LITURGIE).
Covers sessions, participations, materials, and error paths.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.services.training_service import TrainingService
from src.core.entities.training import (
    MaterialType,
    ParticipationStatus,
    SessionMaterial,
    TrainingLevel,
    TrainingMaterial,
    TrainingParticipation,
    TrainingSession,
    TrainingStatus,
)

# ── Factories ──────────────────────────────────────────────────────────────


def _make_session(**kwargs) -> TrainingSession:
    defaults = dict(
        id=uuid4(),
        title="Formation Test",
        description="Description",
        level=TrainingLevel.DEBUTANT,
        date=datetime.now(timezone.utc),
        start_time="14:00",
        end_time="16:00",
        duration_minutes=120,
        location="Salle A",
        trainer_id=uuid4(),
        status=TrainingStatus.PLANIFIEE,
        created_by=uuid4(),
    )
    defaults.update(kwargs)
    return TrainingSession(**defaults)


def _make_participation(**kwargs) -> TrainingParticipation:
    defaults = dict(
        id=uuid4(),
        session_id=uuid4(),
        servant_id=uuid4(),
        status=ParticipationStatus.INSCRIT,
        registered_by=uuid4(),
    )
    defaults.update(kwargs)
    return TrainingParticipation(**defaults)


def _make_material(**kwargs) -> TrainingMaterial:
    defaults = dict(
        id=uuid4(),
        title="Support PDF",
        description="Document pédagogique",
        type=MaterialType.DOCUMENT,
        file_url="http://cdn/doc.pdf",
        file_type="application/pdf",
        file_size=1024,
        uploaded_by=uuid4(),
    )
    defaults.update(kwargs)
    return TrainingMaterial(**defaults)


def _make_svc(
    session_repo=None,
    participation_repo=None,
    material_repo=None,
    session_material_repo=None,
) -> TrainingService:
    return TrainingService(
        session_repo=session_repo or AsyncMock(),
        participation_repo=participation_repo or AsyncMock(),
        material_repo=material_repo or AsyncMock(),
        session_material_repo=session_material_repo or AsyncMock(),
    )


# ══════════════════════════════════════════════════════════════════
#  Existing tests (kept)
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_session():
    session_repo = AsyncMock()
    session = _make_session()
    session_repo.create.return_value = session
    session_repo.enrich_session.return_value = session

    svc = _make_svc(session_repo=session_repo)
    result = await svc.create_session(
        title=session.title,
        description=session.description,
        level=session.level,
        date=session.date,
        start_time=session.start_time,
        end_time=session.end_time,
        duration_minutes=session.duration_minutes,
        location=session.location,
        trainer_id=session.trainer_id,
        created_by=session.created_by,
    )

    assert result.title == session.title
    session_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_register_participant_success():
    session_repo = AsyncMock()
    participation_repo = AsyncMock()
    session = _make_session(max_participants=0)
    session_repo.get_by_id.return_value = session
    participation_repo.get_by_session_and_servant.return_value = None
    participation_repo.list_by_session.return_value = []
    participation = _make_participation(session_id=session.id)
    participation_repo.create.return_value = participation
    participation_repo.enrich_participation.return_value = participation

    svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
    result = await svc.register_participant(
        session_id=session.id,
        servant_id=participation.servant_id,
        registered_by=participation.registered_by,
    )

    assert result.servant_id == participation.servant_id
    participation_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_register_participant_session_full():
    session_repo = AsyncMock()
    participation_repo = AsyncMock()
    session = _make_session(max_participants=1)
    session_repo.get_by_id.return_value = session
    participation_repo.get_by_session_and_servant.return_value = None
    participation_repo.list_by_session.return_value = [MagicMock()]

    svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
    with pytest.raises(HTTPException) as exc:
        await svc.register_participant(session_id=session.id, servant_id=uuid4(), registered_by=uuid4())
    assert exc.value.status_code == 400
    assert "Session is full" in exc.value.detail


@pytest.mark.asyncio
async def test_evaluate_participant():
    participation_repo = AsyncMock()
    participation = _make_participation(status=ParticipationStatus.PRESENT)
    participation_repo.get_by_id.return_value = participation
    participation_repo.update.return_value = participation
    participation_repo.enrich_participation.return_value = participation

    svc = _make_svc(participation_repo=participation_repo)
    result = await svc.evaluate_participant(
        participation_id=participation.id,
        evaluation_score=90,
        evaluation_comments="Excellent",
        certificate_issued=True,
    )

    assert result.evaluation_score == 90
    assert result.certificate_issued is True
    participation_repo.update.assert_called_once()


# ══════════════════════════════════════════════════════════════════
#  Session CRUD
# ══════════════════════════════════════════════════════════════════


class TestGetSession:
    @pytest.mark.asyncio
    async def test_returns_enriched_session(self):
        session_repo = AsyncMock()
        session = _make_session()
        session_repo.get_by_id.return_value = session
        session_repo.enrich_session.return_value = session

        svc = _make_svc(session_repo=session_repo)
        result = await svc.get_session(session.id)
        assert result is session
        session_repo.enrich_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = None

        svc = _make_svc(session_repo=session_repo)
        result = await svc.get_session(uuid4())
        assert result is None


class TestListSessions:
    @pytest.mark.asyncio
    async def test_enriches_and_returns_list(self):
        session_repo = AsyncMock()
        sessions = [_make_session(), _make_session()]
        session_repo.list_sessions.return_value = (sessions, 2)
        session_repo.enrich_session.side_effect = sessions

        svc = _make_svc(session_repo=session_repo)
        result, total = await svc.list_sessions()
        assert total == 2
        assert len(result) == 2
        assert session_repo.enrich_session.call_count == 2


class TestUpdateSession:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = None

        svc = _make_svc(session_repo=session_repo)
        result = await svc.update_session(uuid4(), title="New")
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_fields(self):
        session_repo = AsyncMock()
        session = _make_session()
        session_repo.get_by_id.return_value = session
        session_repo.update.return_value = session
        session_repo.enrich_session.return_value = session

        svc = _make_svc(session_repo=session_repo)
        await svc.update_session(
            session.id,
            title="Nouveau titre",
            status=TrainingStatus.EN_COURS,
            max_participants=30,
        )

        assert session.title == "Nouveau titre"
        assert session.status == TrainingStatus.EN_COURS
        assert session.max_participants == 30


class TestDeleteSession:
    @pytest.mark.asyncio
    async def test_raises_400_when_has_participants(self):
        session_repo = AsyncMock()
        participation_repo = AsyncMock()
        session = _make_session()
        participation_repo.list_by_session.return_value = [MagicMock()]

        svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.delete_session(session.id)
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_deletes_when_no_participants(self):
        session_repo = AsyncMock()
        participation_repo = AsyncMock()
        participation_repo.list_by_session.return_value = []
        session_repo.delete.return_value = True

        svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
        result = await svc.delete_session(uuid4())
        assert result is True
        session_repo.delete.assert_called_once()


class TestGetMySessions:
    @pytest.mark.asyncio
    async def test_enriches_and_returns_list(self):
        session_repo = AsyncMock()
        session = _make_session()
        session_repo.get_by_created_by.return_value = ([session], 1)
        session_repo.enrich_session.return_value = session

        svc = _make_svc(session_repo=session_repo)
        result, total = await svc.get_my_sessions(uuid4())
        assert total == 1
        assert len(result) == 1


# ══════════════════════════════════════════════════════════════════
#  Participation management
# ══════════════════════════════════════════════════════════════════


class TestGetParticipation:
    @pytest.mark.asyncio
    async def test_returns_participation(self):
        participation_repo = AsyncMock()
        participation = _make_participation()
        participation_repo.get_by_id.return_value = participation

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.get_participation(participation.id)
        assert result is participation

    @pytest.mark.asyncio
    async def test_returns_none(self):
        participation_repo = AsyncMock()
        participation_repo.get_by_id.return_value = None

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.get_participation(uuid4())
        assert result is None


class TestRegisterParticipantErrors:
    @pytest.mark.asyncio
    async def test_raises_404_when_session_not_found(self):
        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = None

        svc = _make_svc(session_repo=session_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.register_participant(uuid4(), uuid4(), uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_session_terminee(self):
        session_repo = AsyncMock()
        session = _make_session(status=TrainingStatus.TERMINEE)
        session_repo.get_by_id.return_value = session

        svc = _make_svc(session_repo=session_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.register_participant(session.id, uuid4(), uuid4())
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_400_when_already_registered(self):
        session_repo = AsyncMock()
        participation_repo = AsyncMock()
        session = _make_session()
        session_repo.get_by_id.return_value = session
        participation_repo.get_by_session_and_servant.return_value = MagicMock()

        svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.register_participant(session.id, uuid4(), uuid4())
        assert exc.value.status_code == 400
        assert "already registered" in exc.value.detail


class TestRegisterParticipantsBatch:
    @pytest.mark.asyncio
    async def test_skips_errors_and_returns_successful(self):
        session_repo = AsyncMock()
        participation_repo = AsyncMock()
        session = _make_session(max_participants=0)
        session_repo.get_by_id.return_value = session
        participation_repo.get_by_session_and_servant.return_value = None
        participation = _make_participation(session_id=session.id)
        participation_repo.create.return_value = participation
        participation_repo.enrich_participation.return_value = participation

        svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
        result = await svc.register_participants_batch(
            session_id=session.id,
            servant_ids=[uuid4()],
            registered_by=uuid4(),
        )
        assert len(result) == 1


class TestMarkAttendance:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        participation_repo = AsyncMock()
        participation_repo.get_by_id.return_value = None

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.mark_attendance(uuid4(), ParticipationStatus.PRESENT, uuid4())
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_status(self):
        participation_repo = AsyncMock()
        participation = _make_participation(status=ParticipationStatus.INSCRIT)
        participation_repo.get_by_id.return_value = participation
        participation_repo.update.return_value = participation
        participation_repo.enrich_participation.return_value = participation

        svc = _make_svc(participation_repo=participation_repo)
        marked_by = uuid4()
        await svc.mark_attendance(participation.id, ParticipationStatus.PRESENT, marked_by)

        assert participation.status == ParticipationStatus.PRESENT
        assert participation.marked_by == marked_by


class TestGetSessionParticipants:
    @pytest.mark.asyncio
    async def test_enriches_list(self):
        participation_repo = AsyncMock()
        participations = [_make_participation(), _make_participation()]
        participation_repo.list_by_session.return_value = participations
        participation_repo.enrich_participation.side_effect = participations

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.get_session_participants(uuid4())
        assert len(result) == 2
        assert participation_repo.enrich_participation.call_count == 2


class TestGetServantParticipations:
    @pytest.mark.asyncio
    async def test_enriches_list(self):
        participation_repo = AsyncMock()
        participation = _make_participation()
        participation_repo.list_by_servant.return_value = [participation]
        participation_repo.enrich_participation.return_value = participation

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.get_servant_participations(uuid4())
        assert len(result) == 1


class TestCancelRegistration:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        participation_repo = AsyncMock()
        participation_repo.delete.return_value = True

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.cancel_registration(uuid4())
        assert result is True


class TestGetServantStats:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        participation_repo = AsyncMock()
        stats = MagicMock()
        participation_repo.get_servant_stats.return_value = stats

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.get_servant_stats(uuid4())
        assert result is stats


# ══════════════════════════════════════════════════════════════════
#  Training materials
# ══════════════════════════════════════════════════════════════════


class TestCreateMaterial:
    @pytest.mark.asyncio
    async def test_creates_and_enriches(self):
        material_repo = AsyncMock()
        material = _make_material()
        material_repo.create.return_value = material
        material_repo.enrich_material.return_value = material

        svc = _make_svc(material_repo=material_repo)
        result = await svc.create_material(
            title=material.title,
            description=material.description,
            type=material.type,
            file_url=material.file_url,
            file_type=material.file_type,
            file_size=material.file_size,
            uploaded_by=material.uploaded_by,
        )

        material_repo.create.assert_called_once()
        material_repo.enrich_material.assert_called_once()
        assert result.title == material.title


class TestGetMaterial:
    @pytest.mark.asyncio
    async def test_increments_view_and_returns(self):
        material_repo = AsyncMock()
        material = _make_material()
        material_repo.get_by_id.return_value = material
        material_repo.enrich_material.return_value = material

        svc = _make_svc(material_repo=material_repo)
        result = await svc.get_material(material.id)

        material_repo.increment_view_count.assert_called_once_with(material.id)
        assert result is material

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        material_repo = AsyncMock()
        material_repo.get_by_id.return_value = None

        svc = _make_svc(material_repo=material_repo)
        result = await svc.get_material(uuid4())
        assert result is None


class TestListMaterials:
    @pytest.mark.asyncio
    async def test_enriches_and_returns_list(self):
        material_repo = AsyncMock()
        material = _make_material()
        material_repo.list_materials.return_value = ([material], 1)
        material_repo.enrich_material.return_value = material

        svc = _make_svc(material_repo=material_repo)
        result, total = await svc.list_materials()
        assert total == 1
        assert len(result) == 1


class TestUpdateMaterial:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        material_repo = AsyncMock()
        material_repo.get_by_id.return_value = None

        svc = _make_svc(material_repo=material_repo)
        result = await svc.update_material(uuid4(), title="New")
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_fields(self):
        material_repo = AsyncMock()
        material = _make_material()
        material_repo.get_by_id.return_value = material
        material_repo.update.return_value = material
        material_repo.enrich_material.return_value = material

        svc = _make_svc(material_repo=material_repo)
        await svc.update_material(material.id, title="Updated", is_public=False)

        assert material.title == "Updated"
        assert material.is_public is False


class TestDeleteMaterial:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        material_repo = AsyncMock()
        material_repo.delete.return_value = True

        svc = _make_svc(material_repo=material_repo)
        result = await svc.delete_material(uuid4())
        assert result is True


# ══════════════════════════════════════════════════════════════════
#  Session-material association
# ══════════════════════════════════════════════════════════════════


class TestAddMaterialToSession:
    @pytest.mark.asyncio
    async def test_raises_404_when_session_not_found(self):
        session_repo = AsyncMock()
        session_repo.get_by_id.return_value = None

        svc = _make_svc(session_repo=session_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.add_material_to_session(uuid4(), uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_404_when_material_not_found(self):
        session_repo = AsyncMock()
        material_repo = AsyncMock()
        session = _make_session()
        session_repo.get_by_id.return_value = session
        material_repo.get_by_id.return_value = None

        svc = _make_svc(session_repo=session_repo, material_repo=material_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.add_material_to_session(session.id, uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_creates_session_material(self):
        session_repo = AsyncMock()
        material_repo = AsyncMock()
        session_material_repo = AsyncMock()
        session = _make_session()
        material = _make_material()
        sm = MagicMock(spec=SessionMaterial)
        session_repo.get_by_id.return_value = session
        material_repo.get_by_id.return_value = material
        session_material_repo.create.return_value = sm

        svc = _make_svc(
            session_repo=session_repo,
            material_repo=material_repo,
            session_material_repo=session_material_repo,
        )
        result = await svc.add_material_to_session(session.id, material.id)

        session_material_repo.create.assert_called_once()
        assert result is sm


class TestGetSessionMaterials:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        session_material_repo = AsyncMock()
        items = [MagicMock(), MagicMock()]
        session_material_repo.get_by_session.return_value = items

        svc = _make_svc(session_material_repo=session_material_repo)
        result = await svc.get_session_materials(uuid4())
        assert result is items


class TestRemoveMaterialFromSession:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        session_material_repo = AsyncMock()
        session_material_repo.delete.return_value = True

        svc = _make_svc(session_material_repo=session_material_repo)
        result = await svc.remove_material_from_session(uuid4())
        assert result is True


# =============================================================================
#  Coverage completion — generate_training_report + mark_attendance extras
# =============================================================================


class TestGenerateTrainingReport:

    @pytest.mark.asyncio
    async def test_empty_period(self):
        session_repo = AsyncMock()
        session_repo.list_sessions.return_value = ([], 0)
        participation_repo = AsyncMock()

        svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
        from datetime import timezone as tz

        result = await svc.generate_training_report(
            start_date=datetime(2026, 1, 1, tzinfo=tz.utc),
            end_date=datetime(2026, 6, 1, tzinfo=tz.utc),
            generated_by=uuid4(),
        )
        assert result.total_sessions == 0
        assert result.average_attendance_rate == 0.0

    @pytest.mark.asyncio
    async def test_with_sessions_and_participations(self):
        session = _make_session(status=TrainingStatus.TERMINEE)
        participation = _make_participation(
            session_id=session.id,
            status=ParticipationStatus.PRESENT,
        )
        participation.evaluation_score = 85.0
        participation.certificate_issued = True

        session_repo = AsyncMock()
        session_repo.list_sessions.return_value = ([session], 1)
        participation_repo = AsyncMock()
        participation_repo.list_by_session.return_value = [participation]

        svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
        from datetime import timezone as tz

        result = await svc.generate_training_report(
            start_date=datetime(2026, 1, 1, tzinfo=tz.utc),
            end_date=datetime(2026, 6, 1, tzinfo=tz.utc),
            generated_by=uuid4(),
        )
        assert result.total_sessions == 1
        assert result.completed_sessions == 1
        assert result.total_participants == 1
        assert result.average_attendance_rate == 100.0
        assert result.average_evaluation_score == 85.0
        assert result.certificates_issued == 1
        assert len(result.top_performers) == 1

    @pytest.mark.asyncio
    async def test_with_absent_participation(self):
        session = _make_session()
        participation = _make_participation(
            session_id=session.id,
            status=ParticipationStatus.ABSENT,
        )
        participation.evaluation_score = None
        participation.certificate_issued = False

        session_repo = AsyncMock()
        session_repo.list_sessions.return_value = ([session], 1)
        participation_repo = AsyncMock()
        participation_repo.list_by_session.return_value = [participation]

        svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
        from datetime import timezone as tz

        result = await svc.generate_training_report(
            start_date=datetime(2026, 1, 1, tzinfo=tz.utc),
            end_date=datetime(2026, 6, 1, tzinfo=tz.utc),
            generated_by=uuid4(),
        )
        assert result.average_attendance_rate == 0.0
        assert result.average_evaluation_score is None

    @pytest.mark.asyncio
    async def test_with_level_filter(self):
        session_repo = AsyncMock()
        session_repo.list_sessions.return_value = ([], 0)
        participation_repo = AsyncMock()

        svc = _make_svc(session_repo=session_repo, participation_repo=participation_repo)
        from datetime import timezone as tz

        result = await svc.generate_training_report(
            start_date=datetime(2026, 1, 1, tzinfo=tz.utc),
            end_date=datetime(2026, 6, 1, tzinfo=tz.utc),
            generated_by=uuid4(),
            level=TrainingLevel.AVANCE,
        )
        session_repo.list_sessions.assert_called_once_with(
            skip=0,
            limit=1000,
            level=TrainingLevel.AVANCE,
            start_date=datetime(2026, 1, 1, tzinfo=tz.utc),
            end_date=datetime(2026, 6, 1, tzinfo=tz.utc),
        )
