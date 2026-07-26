"""
Unit tests for TrainingSessionRepository, TrainingParticipationRepository,
TrainingMaterialRepository, SessionMaterialRepository.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _mock_session():
    return AsyncMock()


def _sa_exec_result(scalar_one=None, scalars_list=None, scalar=None):
    r = MagicMock()
    r.scalar_one_or_none = MagicMock(return_value=scalar_one)
    r.scalar_one = MagicMock(return_value=scalar_one)
    r.scalar = MagicMock(return_value=scalar)
    scalars_obj = MagicMock()
    scalars_obj.all.return_value = scalars_list or []
    r.scalars.return_value = scalars_obj
    return r


def _make_training_session(**kw):
    from src.core.entities.training import TrainingLevel, TrainingStatus

    ts = MagicMock()
    ts.id = kw.get("id", uuid4())
    ts.level = kw.get("level", TrainingLevel.DEBUTANT)
    ts.status = kw.get("status", TrainingStatus.PLANIFIEE)
    ts.date = kw.get("date", datetime.utcnow())
    ts.trainer_id = kw.get("trainer_id", uuid4())
    ts.trainer_name = kw.get("trainer_name", None)
    ts.current_participants = kw.get("current_participants", 0)
    ts.created_by = kw.get("created_by", uuid4())
    ts.updated_at = kw.get("updated_at", datetime.utcnow())
    return ts


def _make_participation(**kw):
    from src.core.entities.training import ParticipationStatus

    p = MagicMock()
    p.id = kw.get("id", uuid4())
    p.session_id = kw.get("session_id", uuid4())
    p.servant_id = kw.get("servant_id", uuid4())
    p.status = kw.get("status", ParticipationStatus.INSCRIT)
    p.registration_date = kw.get("registration_date", datetime.utcnow())
    p.evaluation_score = kw.get("evaluation_score", None)
    p.certificate_issued = kw.get("certificate_issued", False)
    p.updated_at = kw.get("updated_at", datetime.utcnow())
    p.servant_name = kw.get("servant_name", None)
    return p


def _make_material(**kw):
    from src.core.entities.training import MaterialType, TrainingLevel

    m = MagicMock()
    m.id = kw.get("id", uuid4())
    m.type = kw.get("type", MaterialType.DOCUMENT)
    m.level = kw.get("level", TrainingLevel.DEBUTANT)
    m.is_public = kw.get("is_public", True)
    m.title = kw.get("title", "Formation liturgique")
    m.description = kw.get("description", None)
    m.view_count = kw.get("view_count", 0)
    m.uploaded_by = kw.get("uploaded_by", uuid4())
    m.uploaded_by_name = kw.get("uploaded_by_name", None)
    m.created_at = kw.get("created_at", datetime.utcnow())
    m.updated_at = kw.get("updated_at", datetime.utcnow())
    return m


def _make_session_material(**kw):
    sm = MagicMock()
    sm.id = kw.get("id", uuid4())
    sm.session_id = kw.get("session_id", uuid4())
    sm.material_id = kw.get("material_id", uuid4())
    sm.order = kw.get("order", 1)
    return sm


# ═══════════════════════════════════════════════════════════════════════════════
#  TrainingSessionRepository
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_training_session_create():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    ts = _make_training_session()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(ts)
    assert result is ts


@pytest.mark.asyncio
async def test_training_session_get_by_id_found():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    ts = _make_training_session()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=ts))

    result = await repo.get_by_id(ts.id)
    assert result is ts


@pytest.mark.asyncio
async def test_training_session_get_by_id_not_found():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.get_by_id(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_training_session_list():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    sessions = [_make_training_session(), _make_training_session()]
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=2),
            _sa_exec_result(scalars_list=sessions),
        ]
    )

    result, total = await repo.list_sessions()
    assert total == 2
    assert len(result) == 2


@pytest.mark.asyncio
async def test_training_session_list_with_filters():
    from src.core.entities.training import TrainingLevel, TrainingStatus
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    now = datetime.utcnow()
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=0),
            _sa_exec_result(scalars_list=[]),
        ]
    )

    result, total = await repo.list_sessions(
        level=TrainingLevel.DEBUTANT,
        status=TrainingStatus.PLANIFIEE,
        start_date=now,
        end_date=now + timedelta(days=7),
        trainer_id=uuid4(),
    )
    assert total == 0


@pytest.mark.asyncio
async def test_training_session_update():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    ts = _make_training_session()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(ts)
    assert result is ts


@pytest.mark.asyncio
async def test_training_session_delete_found():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    ts = _make_training_session()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=ts))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(ts.id)
    assert result is True


@pytest.mark.asyncio
async def test_training_session_delete_not_found():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_training_session_get_by_created_by():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    sessions = [_make_training_session()]
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=1),
            _sa_exec_result(scalars_list=sessions),
        ]
    )

    result, total = await repo.get_by_created_by(uuid4())
    assert total == 1


@pytest.mark.asyncio
async def test_training_session_enrich_with_trainer():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    ts = _make_training_session()

    trainer = MagicMock()
    trainer.first_name = "Joseph"
    trainer.last_name = "Kanga"
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar_one=trainer),  # trainer
            _sa_exec_result(scalar=5),  # participant count
        ]
    )

    with patch("src.infrastructure.repositories.training_repository.decrypt_str_fields"):
        await repo.enrich_session(ts)

    assert ts.trainer_name == "Joseph Kanga"
    assert ts.current_participants == 5


@pytest.mark.asyncio
async def test_training_session_enrich_no_trainer():
    from src.infrastructure.repositories.training_repository import TrainingSessionRepository

    session = _mock_session()
    repo = TrainingSessionRepository(session)
    ts = _make_training_session()
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar_one=None),  # no trainer
            _sa_exec_result(scalar=0),  # count
        ]
    )

    result = await repo.enrich_session(ts)
    assert result is ts


# ═══════════════════════════════════════════════════════════════════════════════
#  TrainingParticipationRepository
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_training_participation_create():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    p = _make_participation()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(p)
    assert result is p


@pytest.mark.asyncio
async def test_training_participation_create_batch():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    parts = [_make_participation(), _make_participation()]
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create_batch(parts)
    assert len(result) == 2
    assert session.add.call_count == 2


@pytest.mark.asyncio
async def test_training_participation_get_by_id():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    p = _make_participation()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=p))

    result = await repo.get_by_id(p.id)
    assert result is p


@pytest.mark.asyncio
async def test_training_participation_get_by_session_and_servant():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    p = _make_participation()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=p))

    result = await repo.get_by_session_and_servant(uuid4(), uuid4())
    assert result is p


@pytest.mark.asyncio
async def test_training_participation_list_by_session():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    parts = [_make_participation()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=parts))

    result = await repo.list_by_session(uuid4())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_training_participation_list_by_servant():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    parts = [_make_participation()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=parts))
    now = datetime.utcnow()

    result = await repo.list_by_servant(uuid4(), start_date=now, end_date=now + timedelta(days=30))
    assert len(result) == 1


@pytest.mark.asyncio
async def test_training_participation_update():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    p = _make_participation()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(p)
    assert result is p


@pytest.mark.asyncio
async def test_training_participation_delete_found():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    p = _make_participation()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=p))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(p.id)
    assert result is True


@pytest.mark.asyncio
async def test_training_participation_delete_not_found():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_training_participation_get_servant_stats_not_found():
    """Stats raise ValueError if servant not found."""
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    with pytest.raises(ValueError, match="Servant not found"):
        await repo.get_servant_stats(uuid4())


@pytest.mark.asyncio
async def test_training_participation_get_servant_stats_no_participations():
    """Stats with no participations returns zeros."""
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)

    servant = MagicMock()
    servant.first_name = "Jean"
    servant.last_name = "Nkolo"

    # First call: get servant; second: list_by_servant
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar_one=servant),  # servant
            _sa_exec_result(scalars_list=[]),  # participations
        ]
    )

    with patch("src.infrastructure.repositories.training_repository.decrypt_str_fields"):
        result = await repo.get_servant_stats(uuid4())

    assert result.total_sessions == 0
    assert result.attendance_rate == 0.0
    assert result.average_score is None


@pytest.mark.asyncio
async def test_training_participation_get_servant_stats_with_data():
    """Stats are correctly computed from participations."""
    from src.core.entities.training import ParticipationStatus
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)

    servant = MagicMock()
    servant.first_name = "Jean"
    servant.last_name = "Nkolo"

    p1 = _make_participation(status=ParticipationStatus.PRESENT, evaluation_score=85, certificate_issued=True)
    p2 = _make_participation(status=ParticipationStatus.ABSENT, evaluation_score=None, certificate_issued=False)

    last_session = MagicMock()
    last_session.date = datetime.utcnow()

    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar_one=servant),  # servant
            _sa_exec_result(scalars_list=[p1, p2]),  # participations
            _sa_exec_result(scalar_one=last_session),  # last session date lookup
        ]
    )

    with patch("src.infrastructure.repositories.training_repository.decrypt_str_fields"):
        result = await repo.get_servant_stats(uuid4())

    assert result.total_sessions == 2
    assert result.attended_sessions == 1
    assert result.certificates_earned == 1
    assert result.average_score == 85.0


@pytest.mark.asyncio
async def test_training_participation_enrich_found():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    p = _make_participation()

    servant = MagicMock()
    servant.first_name = "Anne"
    servant.last_name = "Bello"
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=servant))

    with patch("src.infrastructure.repositories.training_repository.decrypt_str_fields"):
        await repo.enrich_participation(p)

    assert p.servant_name == "Anne Bello"


@pytest.mark.asyncio
async def test_training_participation_enrich_not_found():
    from src.infrastructure.repositories.training_repository import TrainingParticipationRepository

    session = _mock_session()
    repo = TrainingParticipationRepository(session)
    p = _make_participation()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.enrich_participation(p)
    assert result is p


# ═══════════════════════════════════════════════════════════════════════════════
#  TrainingMaterialRepository
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_training_material_create():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    m = _make_material()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(m)
    assert result is m


@pytest.mark.asyncio
async def test_training_material_get_by_id():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    m = _make_material()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=m))

    result = await repo.get_by_id(m.id)
    assert result is m


@pytest.mark.asyncio
async def test_training_material_list():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    materials = [_make_material()]
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=1),
            _sa_exec_result(scalars_list=materials),
        ]
    )

    result, total = await repo.list_materials()
    assert total == 1
    assert len(result) == 1


@pytest.mark.asyncio
async def test_training_material_list_with_filters():
    from src.core.entities.training import MaterialType, TrainingLevel
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    session.execute = AsyncMock(
        side_effect=[
            _sa_exec_result(scalar=0),
            _sa_exec_result(scalars_list=[]),
        ]
    )

    result, total = await repo.list_materials(
        type=MaterialType.DOCUMENT,
        level=TrainingLevel.DEBUTANT,
        is_public=True,
        search="liturgie",
    )
    assert total == 0


@pytest.mark.asyncio
async def test_training_material_update():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    m = _make_material()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.update(m)
    assert result is m


@pytest.mark.asyncio
async def test_training_material_delete_found():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    m = _make_material()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=m))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(m.id)
    assert result is True


@pytest.mark.asyncio
async def test_training_material_delete_not_found():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_training_material_increment_view_found():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    m = _make_material(view_count=5)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=m))
    session.commit = AsyncMock()

    result = await repo.increment_view_count(m.id)
    assert result is True
    assert m.view_count == 6


@pytest.mark.asyncio
async def test_training_material_increment_view_not_found():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.increment_view_count(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_training_material_enrich_found():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    m = _make_material()

    uploader = MagicMock()
    uploader.first_name = "Chef"
    uploader.last_name = "Liturgie"
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=uploader))

    with patch("src.infrastructure.repositories.training_repository.decrypt_str_fields"):
        await repo.enrich_material(m)

    assert m.uploaded_by_name == "Chef Liturgie"


@pytest.mark.asyncio
async def test_training_material_enrich_not_found():
    from src.infrastructure.repositories.training_repository import TrainingMaterialRepository

    session = _mock_session()
    repo = TrainingMaterialRepository(session)
    m = _make_material()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.enrich_material(m)
    assert result is m


# ═══════════════════════════════════════════════════════════════════════════════
#  SessionMaterialRepository
# ═══════════════════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_session_material_create():
    from src.infrastructure.repositories.training_repository import SessionMaterialRepository

    session = _mock_session()
    repo = SessionMaterialRepository(session)
    sm = _make_session_material()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    result = await repo.create(sm)
    assert result is sm


@pytest.mark.asyncio
async def test_session_material_get_by_session():
    from src.infrastructure.repositories.training_repository import SessionMaterialRepository

    session = _mock_session()
    repo = SessionMaterialRepository(session)
    sms = [_make_session_material()]
    session.execute = AsyncMock(return_value=_sa_exec_result(scalars_list=sms))

    result = await repo.get_by_session(uuid4())
    assert len(result) == 1


@pytest.mark.asyncio
async def test_session_material_delete_found():
    from src.infrastructure.repositories.training_repository import SessionMaterialRepository

    session = _mock_session()
    repo = SessionMaterialRepository(session)
    sm = _make_session_material()
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=sm))
    session.delete = AsyncMock()
    session.commit = AsyncMock()

    result = await repo.delete(sm.id)
    assert result is True


@pytest.mark.asyncio
async def test_session_material_delete_not_found():
    from src.infrastructure.repositories.training_repository import SessionMaterialRepository

    session = _mock_session()
    repo = SessionMaterialRepository(session)
    session.execute = AsyncMock(return_value=_sa_exec_result(scalar_one=None))

    result = await repo.delete(uuid4())
    assert result is False
