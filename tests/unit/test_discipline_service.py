"""Unit tests for DisciplineService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.discipline_service import DisciplineService
from src.core.entities.attendance import AttendanceStatus, AttendanceType
from src.core.entities.discipline import (
    COUNCIL_POSTES,
    OFFENSE_DEFAULT_SEVERITY,
    DisciplineCase,
    DisciplineCaseStatus,
    OffenseCategory,
    SanctionSeverity,
    SanctionType,
)
from src.core.entities.responsable import PosteResponsable
from src.core.entities.user import User, UserRole
from src.presentation.schemas.discipline import (
    DisciplineCaseCreate,
    DisciplineConvocation,
    DisciplineVerdict,
    DisciplineVoteCast,
)

NOW = datetime(2026, 6, 1, 10, 0, 0)


# ── Factories ──────────────────────────────────────────────────────────────


def _make_user(role=UserRole.SERVANT, is_active=True) -> User:
    return User(
        id=uuid4(),
        first_name="Jean",
        last_name="Pierre",
        email="jean@test.com",
        hashed_password="x",
        role=role,
        is_active=is_active,
        created_at=NOW,
        updated_at=NOW,
    )


def _make_case(status=DisciplineCaseStatus.SIGNALE, **kwargs) -> DisciplineCase:
    return DisciplineCase(
        id=kwargs.pop("id", uuid4()),
        accused_user_id=kwargs.pop("accused_user_id", uuid4()),
        reported_by=kwargs.pop("reported_by", uuid4()),
        offense_category=kwargs.pop("offense_category", OffenseCategory.ABSENCE_NON_JUSTIFIEE),
        offense_description=kwargs.pop("offense_description", "Absent sans raison"),
        severity=kwargs.pop("severity", SanctionSeverity.MINEUR),
        status=status,
        sanction_type=kwargs.pop("sanction_type", SanctionType.AUCUNE),
        created_at=kwargs.pop("created_at", NOW),
        updated_at=kwargs.pop("updated_at", NOW),
        **kwargs,
    )


def _enriched_case(case: DisciplineCase) -> dict:
    return {
        "id": case.id,
        "accused_user_id": case.accused_user_id,
        "reported_by": case.reported_by,
        "offense_category": case.offense_category,
        "offense_description": case.offense_description,
        "offense_date": getattr(case, "offense_date", None),
        "severity": case.severity,
        "status": case.status,
        "convocation_date": getattr(case, "convocation_date", None),
        "convocation_notes": getattr(case, "convocation_notes", None),
        "sanction_type": case.sanction_type,
        "verdict_notes": getattr(case, "verdict_notes", None),
        "verdict_date": getattr(case, "verdict_date", None),
        "verdict_by": getattr(case, "verdict_by", None),
        "suspension_start": getattr(case, "suspension_start", None),
        "suspension_end": getattr(case, "suspension_end", None),
        "suspension_days": getattr(case, "suspension_days", None),
        "accused_first_name": None,
        "accused_last_name": None,
        "reporter_first_name": None,
        "reporter_last_name": None,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
    }


def _make_attendance(status=AttendanceStatus.ABSENT):
    a = MagicMock()
    a.status = status
    return a


def _make_vote(poste=PosteResponsable.DELEGUE, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE, **kwargs):
    v = MagicMock()
    v.poste = kwargs.pop("poste_value", poste.value)
    v.voter_user_id = kwargs.pop("voter_user_id", uuid4())
    v.sanction_type = sanction_type
    v.notes = kwargs.pop("notes", None)
    v.voted_at = kwargs.pop("voted_at", NOW)
    return v


def _make_nomination(poste):
    n = MagicMock()
    n.poste = poste
    return n


def _make_svc(case_repo=None, user_repo=None, attendance_repo=None, nomination_repo=None) -> DisciplineService:
    if case_repo is None:
        case_repo = MagicMock()
        case_repo.create = AsyncMock()
        case_repo.get = AsyncMock(return_value=None)
        case_repo.update = AsyncMock()
        case_repo.list_paginated = AsyncMock(return_value=([], 0))
        case_repo.enrich_case = AsyncMock(return_value={})
        case_repo.enrich_cases = AsyncMock(return_value=[])
        case_repo.count_sanctions_by_user = AsyncMock(return_value={})
        case_repo.count_active_cases = AsyncMock(return_value=0)
        case_repo.upsert_vote = AsyncMock()
        case_repo.list_votes = AsyncMock(return_value=[])
    if user_repo is None:
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=None)
        user_repo.update = AsyncMock()
    if attendance_repo is None:
        attendance_repo = MagicMock()
        attendance_repo.list_paginated = AsyncMock(return_value=([], 0))
    if nomination_repo is None:
        nomination_repo = MagicMock()
        nomination_repo.get_active_by_poste = AsyncMock(return_value=None)
        nomination_repo.get_active_by_user = AsyncMock(return_value=[])
    return DisciplineService(case_repo, user_repo, attendance_repo, nomination_repo)


# ── open_case ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_open_case_user_not_found():
    svc = _make_svc()
    svc.user_repo.get.return_value = None
    data = DisciplineCaseCreate(
        accused_user_id=uuid4(),
        offense_category=OffenseCategory.ABSENCE_NON_JUSTIFIEE,
        offense_description="Absent trois fois de suite",
    )
    with pytest.raises(Exception) as exc:
        await svc.open_case(data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_open_case_not_servant():
    svc = _make_svc()
    svc.user_repo.get.return_value = _make_user(role=UserRole.PARENT)
    data = DisciplineCaseCreate(
        accused_user_id=uuid4(),
        offense_category=OffenseCategory.INSUBORDINATION,
        offense_description="N'ecoute pas les ordres donnés",
    )
    with pytest.raises(Exception) as exc:
        await svc.open_case(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_open_case_success_auto_severity():
    servant = _make_user(role=UserRole.SERVANT)
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.user_repo.get.return_value = servant
    svc.case_repo.create.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)

    data = DisciplineCaseCreate(
        accused_user_id=servant.id,
        offense_category=OffenseCategory.ABSENCE_NON_JUSTIFIEE,
        offense_description="Absent trois fois de suite sans justification",
        severity=None,
    )
    result = await svc.open_case(data, uuid4())
    assert result.id == case.id
    svc.case_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_open_case_success_explicit_severity():
    servant = _make_user(role=UserRole.SERVANT)
    case = _make_case(severity=SanctionSeverity.GRAVE)
    svc = _make_svc()
    svc.user_repo.get.return_value = servant
    svc.case_repo.create.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)

    data = DisciplineCaseCreate(
        accused_user_id=servant.id,
        offense_category=OffenseCategory.BAGARRE_VIOLENCE,
        offense_description="A frappé un autre servant lors de la messe",
        severity=SanctionSeverity.GRAVE,
    )
    result = await svc.open_case(data, uuid4())
    assert result.severity == SanctionSeverity.GRAVE


# ── convoke ────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_convoke_not_found():
    svc = _make_svc()
    svc.case_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.convoke(uuid4(), DisciplineConvocation(convocation_date=NOW))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_convoke_wrong_status():
    case = _make_case(status=DisciplineCaseStatus.CONVOQUE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    with pytest.raises(Exception) as exc:
        await svc.convoke(case.id, DisciplineConvocation(convocation_date=NOW))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_convoke_success():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    result = await svc.convoke(
        case.id, DisciplineConvocation(convocation_date=NOW, convocation_notes="Présence requise")
    )
    assert result.id == case.id


# ── start_hearing ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_hearing_not_found():
    svc = _make_svc()
    svc.case_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.start_hearing(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_start_hearing_wrong_status():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    with pytest.raises(Exception) as exc:
        await svc.start_hearing(case.id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_start_hearing_success():
    case = _make_case(status=DisciplineCaseStatus.CONVOQUE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    result = await svc.start_hearing(case.id)
    assert result.id == case.id


# ── render_verdict ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_render_verdict_not_found():
    svc = _make_svc()
    svc.case_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.render_verdict(
            uuid4(), DisciplineVerdict(sanction_type=SanctionType.AUCUNE), _make_user(role=UserRole.AUMÔNIER)
        )
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_render_verdict_wrong_status():
    case = _make_case(status=DisciplineCaseStatus.EXECUTE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    with pytest.raises(Exception) as exc:
        await svc.render_verdict(
            case.id, DisciplineVerdict(sanction_type=SanctionType.AUCUNE), _make_user(role=UserRole.AUMÔNIER)
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_render_verdict_avertissement():
    case = _make_case(status=DisciplineCaseStatus.EN_AUDIENCE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    result = await svc.render_verdict(
        case.id,
        DisciplineVerdict(sanction_type=SanctionType.AVERTISSEMENT_VERBAL, verdict_notes="1ère faute"),
        _make_user(role=UserRole.AUMÔNIER),
    )
    assert result.id == case.id


@pytest.mark.asyncio
async def test_render_verdict_suspension_sets_dates():
    case = _make_case(status=DisciplineCaseStatus.EN_AUDIENCE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    await svc.render_verdict(
        case.id,
        DisciplineVerdict(sanction_type=SanctionType.SUSPENSION_TEMPORAIRE, suspension_days=14),
        _make_user(role=UserRole.AUMÔNIER),
    )
    svc.case_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_render_verdict_from_convoque_status():
    case = _make_case(status=DisciplineCaseStatus.CONVOQUE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    result = await svc.render_verdict(
        case.id,
        DisciplineVerdict(sanction_type=SanctionType.AVERTISSEMENT_ECRIT),
        _make_user(role=UserRole.AUMÔNIER),
    )
    assert result.id == case.id


# ── render_verdict : autorisation par poste (Art. 39-44, 51) ───────────────


@pytest.mark.asyncio
async def test_render_verdict_censeur_can_set_any_sanction():
    """Le Censeur peut prononcer n'importe quelle sanction, y compris la radiation (Art. 51)."""
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.side_effect = lambda c: _enriched_case(c)
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.CENSEUR)]
    result = await svc.render_verdict(
        case.id,
        DisciplineVerdict(sanction_type=SanctionType.EXCLUSION_DEFINITIVE),
        _make_user(),
    )
    assert result.sanction_type == SanctionType.EXCLUSION_DEFINITIVE


@pytest.mark.asyncio
async def test_render_verdict_censeur_adjoint_cannot_radiate():
    """Le Censeur Adjoint peut decider les punitions courantes mais pas la radiation."""
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.CENSEUR_ADJOINT)]
    with pytest.raises(Exception) as exc:
        await svc.render_verdict(
            case.id,
            DisciplineVerdict(sanction_type=SanctionType.EXCLUSION_DEFINITIVE),
            _make_user(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_render_verdict_censeur_adjoint_can_set_minor_sanction():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.side_effect = lambda c: _enriched_case(c)
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.CENSEUR_ADJOINT)]
    result = await svc.render_verdict(
        case.id,
        DisciplineVerdict(sanction_type=SanctionType.AVERTISSEMENT_VERBAL),
        _make_user(),
    )
    assert result.sanction_type == SanctionType.AVERTISSEMENT_VERBAL


@pytest.mark.asyncio
async def test_render_verdict_secretaire_general_only_radiation():
    """Le Secretaire General ne peut prononcer qu'une radiation (Art. 51), rien d'autre."""
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.SECRETAIRE_GENERAL)]
    with pytest.raises(Exception) as exc:
        await svc.render_verdict(
            case.id,
            DisciplineVerdict(sanction_type=SanctionType.AVERTISSEMENT_VERBAL),
            _make_user(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_render_verdict_secretaire_general_can_radiate():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.side_effect = lambda c: _enriched_case(c)
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.SECRETAIRE_GENERAL)]
    result = await svc.render_verdict(
        case.id,
        DisciplineVerdict(sanction_type=SanctionType.EXCLUSION_DEFINITIVE),
        _make_user(),
    )
    assert result.sanction_type == SanctionType.EXCLUSION_DEFINITIVE


@pytest.mark.asyncio
async def test_render_verdict_ceremoniaire_minor_only():
    """Le Ceremoniaire peut sanctionner un trouble en messe (Art. 41), pas une radiation."""
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.CEREMONIAIRE)]
    with pytest.raises(Exception) as exc:
        await svc.render_verdict(
            case.id,
            DisciplineVerdict(sanction_type=SanctionType.SUSPENSION_TEMPORAIRE),
            _make_user(),
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_render_verdict_ceremoniaire_can_set_avertissement():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.side_effect = lambda c: _enriched_case(c)
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.CEREMONIAIRE)]
    result = await svc.render_verdict(
        case.id,
        DisciplineVerdict(sanction_type=SanctionType.AVERTISSEMENT_ECRIT),
        _make_user(),
    )
    assert result.sanction_type == SanctionType.AVERTISSEMENT_ECRIT


@pytest.mark.asyncio
async def test_render_verdict_no_relevant_poste_rejected():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.ECONOME)]
    with pytest.raises(Exception) as exc:
        await svc.render_verdict(
            case.id,
            DisciplineVerdict(sanction_type=SanctionType.AVERTISSEMENT_VERBAL),
            _make_user(),
        )
    assert exc.value.status_code == 403


# ── execute_sanction ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_execute_sanction_not_found():
    svc = _make_svc()
    svc.case_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.execute_sanction(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_execute_sanction_wrong_status():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    with pytest.raises(Exception) as exc:
        await svc.execute_sanction(case.id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_execute_sanction_standard():
    case = _make_case(status=DisciplineCaseStatus.VERDICT_RENDU)
    case.sanction_type = SanctionType.AVERTISSEMENT_VERBAL
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    result = await svc.execute_sanction(case.id)
    assert result.id == case.id


@pytest.mark.asyncio
async def test_execute_sanction_exclusion_deactivates_user():
    servant = _make_user(role=UserRole.SERVANT)
    case = _make_case(status=DisciplineCaseStatus.VERDICT_RENDU, accused_user_id=servant.id)
    case.sanction_type = SanctionType.EXCLUSION_DEFINITIVE
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    svc.user_repo.get.return_value = servant
    await svc.execute_sanction(case.id)
    svc.user_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_execute_sanction_exclusion_user_not_found():
    case = _make_case(status=DisciplineCaseStatus.VERDICT_RENDU)
    case.sanction_type = SanctionType.EXCLUSION_DEFINITIVE
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    svc.user_repo.get.return_value = None
    result = await svc.execute_sanction(case.id)
    svc.user_repo.update.assert_not_called()
    assert result.id == case.id


# ── dismiss_case ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_dismiss_case_not_found():
    svc = _make_svc()
    svc.case_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.dismiss_case(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_dismiss_case_already_executed():
    case = _make_case(status=DisciplineCaseStatus.EXECUTE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    with pytest.raises(Exception) as exc:
        await svc.dismiss_case(case.id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_dismiss_case_already_classe():
    case = _make_case(status=DisciplineCaseStatus.CLASSE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    with pytest.raises(Exception) as exc:
        await svc.dismiss_case(case.id)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_dismiss_case_success():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    result = await svc.dismiss_case(case.id, notes="Manque de preuves")
    assert result.id == case.id


@pytest.mark.asyncio
async def test_dismiss_case_success_no_notes():
    case = _make_case(status=DisciplineCaseStatus.CONVOQUE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.update.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    result = await svc.dismiss_case(case.id)
    assert result.id == case.id


# ── get_case ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_case_not_found():
    svc = _make_svc()
    svc.case_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_case(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_case_success():
    case = _make_case()
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.case_repo.enrich_case.return_value = _enriched_case(case)
    result = await svc.get_case(case.id)
    assert result.id == case.id


# ── list_cases ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_cases_empty():
    svc = _make_svc()
    svc.case_repo.list_paginated.return_value = ([], 0)
    svc.case_repo.enrich_cases.return_value = []
    result = await svc.list_cases()
    assert result.total == 0
    assert result.items == []


@pytest.mark.asyncio
async def test_list_cases_with_items():
    case = _make_case()
    svc = _make_svc()
    svc.case_repo.list_paginated.return_value = ([case], 1)
    svc.case_repo.enrich_cases.return_value = [_enriched_case(case)]
    result = await svc.list_cases()
    assert result.total == 1
    assert len(result.items) == 1


# ── get_user_discipline_stats ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_user_discipline_stats():
    user_id = uuid4()
    svc = _make_svc()
    svc.case_repo.count_sanctions_by_user.return_value = {
        SanctionType.AVERTISSEMENT_VERBAL.value: 2,
        SanctionType.AVERTISSEMENT_ECRIT.value: 1,
    }
    svc.case_repo.count_active_cases.return_value = 1
    result = await svc.get_user_discipline_stats(user_id)
    assert result.user_id == user_id
    assert result.avertissements_verbaux == 2
    assert result.avertissements_ecrits == 1
    assert result.cases_en_cours == 1
    assert result.total_cases == 4


# ── check_attendance_compliance ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_check_attendance_compliance_no_data():
    user_id = uuid4()
    svc = _make_svc()
    svc.attendance_repo.list_paginated.return_value = ([], 0)
    result = await svc.check_attendance_compliance(user_id)
    assert result["user_id"] == user_id
    assert result["two_consecutive_absences"] is False
    assert result["six_months_continuous_absence"] is True
    assert result["suggested_sanction"] == SanctionType.EXCLUSION_DEFINITIVE


@pytest.mark.asyncio
async def test_check_attendance_compliance_two_absences():
    user_id = uuid4()
    svc = _make_svc()
    abs1 = _make_attendance(AttendanceStatus.ABSENT)
    abs2 = _make_attendance(AttendanceStatus.ABSENT)
    svc.attendance_repo.list_paginated.side_effect = [
        ([abs1, abs2], 2),
        ([MagicMock()], 1),
    ]
    result = await svc.check_attendance_compliance(user_id)
    assert result["two_consecutive_absences"] is True
    assert result["six_months_continuous_absence"] is False
    assert result["suggested_sanction"] == SanctionType.SUSPENSION_TEMPORAIRE


@pytest.mark.asyncio
async def test_check_attendance_compliance_all_present():
    user_id = uuid4()
    svc = _make_svc()
    pres1 = _make_attendance(AttendanceStatus.PRESENT)
    pres2 = _make_attendance(AttendanceStatus.PRESENT)
    svc.attendance_repo.list_paginated.side_effect = [
        ([pres1, pres2], 2),
        ([MagicMock()], 1),
    ]
    result = await svc.check_attendance_compliance(user_id)
    assert result["two_consecutive_absences"] is False
    assert result["suggested_sanction"] == SanctionType.AUCUNE


# ── cast_vote / conseil de discipline (Art. 16-17) ─────────────────────────


@pytest.mark.asyncio
async def test_cast_vote_case_not_found():
    svc = _make_svc()
    svc.case_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.cast_vote(uuid4(), _make_user(), DisciplineVoteCast(sanction_type=SanctionType.AVERTISSEMENT_VERBAL))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_cast_vote_case_already_decided():
    case = _make_case(status=DisciplineCaseStatus.VERDICT_RENDU)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    with pytest.raises(Exception) as exc:
        await svc.cast_vote(case.id, _make_user(), DisciplineVoteCast(sanction_type=SanctionType.AVERTISSEMENT_VERBAL))
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_cast_vote_non_council_member_rejected():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.ECONOME)]
    with pytest.raises(Exception) as exc:
        await svc.cast_vote(case.id, _make_user(), DisciplineVoteCast(sanction_type=SanctionType.AVERTISSEMENT_VERBAL))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_cast_vote_single_vote_does_not_decide():
    """Un seul vote sur 7 sieges pourvus (majorite=4) ne rend pas de verdict."""
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    voter = _make_user()
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.DELEGUE)]
    # Les 7 sieges sont pourvus
    svc.nomination_repo.get_active_by_poste.side_effect = lambda poste: _make_nomination(poste)
    svc.case_repo.list_votes.return_value = [
        _make_vote(poste=PosteResponsable.DELEGUE, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE)
    ]
    svc.case_repo.enrich_case.return_value = _enriched_case(case)

    result = await svc.cast_vote(case.id, voter, DisciplineVoteCast(sanction_type=SanctionType.SUSPENSION_TEMPORAIRE))
    assert result.status == DisciplineCaseStatus.SIGNALE
    svc.case_repo.upsert_vote.assert_awaited_once()


@pytest.mark.asyncio
async def test_cast_vote_majority_renders_verdict():
    """4 votes identiques sur 6 sieges pourvus (1 vacant) rendent le verdict."""
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    voter = _make_user()
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.CENSEUR)]

    # CENSEUR_ADJOINT vacant, les 6 autres sieges pourvus
    filled = set(COUNCIL_POSTES) - {PosteResponsable.CENSEUR_ADJOINT}

    async def _get_active_by_poste(poste):
        return _make_nomination(poste) if poste in filled else None

    svc.nomination_repo.get_active_by_poste.side_effect = _get_active_by_poste
    svc.case_repo.list_votes.return_value = [
        _make_vote(poste=PosteResponsable.DELEGUE, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE),
        _make_vote(poste=PosteResponsable.VICE_DELEGUE, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE),
        _make_vote(poste=PosteResponsable.SECRETAIRE_GENERAL, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE),
        _make_vote(poste=PosteResponsable.CENSEUR, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE),
    ]
    decided_case = _make_case(
        status=DisciplineCaseStatus.VERDICT_RENDU, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE
    )
    svc.case_repo.update.return_value = decided_case
    svc.case_repo.enrich_case.return_value = _enriched_case(decided_case)

    result = await svc.cast_vote(case.id, voter, DisciplineVoteCast(sanction_type=SanctionType.SUSPENSION_TEMPORAIRE))
    assert result.status == DisciplineCaseStatus.VERDICT_RENDU
    assert result.sanction_type == SanctionType.SUSPENSION_TEMPORAIRE


@pytest.mark.asyncio
async def test_cast_vote_revoked_seat_vote_not_counted():
    """Un vote depose par un siege depuis revoque ne compte plus dans le quorum."""
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    voter = _make_user()
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.nomination_repo.get_active_by_user.return_value = [_make_nomination(PosteResponsable.DELEGUE)]

    # Seul DELEGUE est pourvu desormais (majorite = 1)
    async def _get_active_by_poste(poste):
        return _make_nomination(poste) if poste == PosteResponsable.DELEGUE else None

    svc.nomination_repo.get_active_by_poste.side_effect = _get_active_by_poste
    # Vote historique d'un siege CENSEUR desormais vacant + le nouveau vote DELEGUE
    svc.case_repo.list_votes.return_value = [
        _make_vote(poste=PosteResponsable.CENSEUR, sanction_type=SanctionType.AVERTISSEMENT_VERBAL),
        _make_vote(poste=PosteResponsable.DELEGUE, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE),
    ]
    decided_case = _make_case(
        status=DisciplineCaseStatus.VERDICT_RENDU, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE
    )
    svc.case_repo.update.return_value = decided_case
    svc.case_repo.enrich_case.return_value = _enriched_case(decided_case)

    result = await svc.cast_vote(case.id, voter, DisciplineVoteCast(sanction_type=SanctionType.SUSPENSION_TEMPORAIRE))
    # Majorite = 1 (un seul siege pourvu) et le seul vote valide (DELEGUE) suffit
    assert result.status == DisciplineCaseStatus.VERDICT_RENDU


# ── get_vote_status ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_vote_status_not_found():
    svc = _make_svc()
    svc.case_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_vote_status(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_vote_status_reports_quorum():
    case = _make_case(status=DisciplineCaseStatus.SIGNALE)
    svc = _make_svc()
    svc.case_repo.get.return_value = case
    svc.nomination_repo.get_active_by_poste.side_effect = lambda poste: _make_nomination(poste)
    svc.case_repo.list_votes.return_value = [
        _make_vote(poste=PosteResponsable.DELEGUE, sanction_type=SanctionType.SUSPENSION_TEMPORAIRE),
    ]
    svc.user_repo.get.return_value = _make_user()

    result = await svc.get_vote_status(case.id)
    assert result.seats_filled == len(COUNCIL_POSTES)
    assert result.majority_required == len(COUNCIL_POSTES) // 2 + 1
    assert result.is_decided is False
    assert len(result.votes) == 1
