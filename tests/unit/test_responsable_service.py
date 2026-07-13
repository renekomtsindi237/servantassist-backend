"""Unit tests for ResponsableService."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.services.responsable_service import ResponsableService
from src.core.entities.council_meeting import CouncilAttendanceStatus, CouncilMeeting
from src.core.entities.responsable import (
    ActionCategory,
    ActionStatus,
    Nomination,
    NominationStatus,
    PosteAction,
    PosteResponsable,
)
from src.core.entities.user import User, UserRole
from src.presentation.schemas.responsable import (
    CouncilAttendanceRecord,
    CouncilAttendanceRecordList,
    CouncilMeetingCreate,
    NominationCreate,
    PosteActionCreate,
    PosteActionUpdate,
)

NOW = datetime(2026, 6, 1, 10, 0, 0)
POSTE = PosteResponsable.DELEGUE


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


def _make_nomination(poste=POSTE, status=NominationStatus.ACTIVE, **kwargs) -> Nomination:
    return Nomination(
        id=kwargs.pop("id", uuid4()),
        user_id=kwargs.pop("user_id", uuid4()),
        poste=poste,
        status=status,
        nominated_by=kwargs.pop("nominated_by", uuid4()),
        nominated_at=kwargs.pop("nominated_at", NOW),
        **kwargs,
    )


def _enriched_nomination(nom: Nomination) -> dict:
    return {
        "id": nom.id,
        "user_id": nom.user_id,
        "poste": nom.poste,
        "poste_titre": None,
        "poste_slug": None,
        "status": nom.status,
        "nominated_by": nom.nominated_by,
        "notes": nom.notes,
        "nominated_at": nom.nominated_at,
        "revoked_at": nom.revoked_at,
        "revoked_by": nom.revoked_by,
        "user_first_name": None,
        "user_last_name": None,
        "user_email": None,
        "user_phone": None,
    }


def _make_action(poste=POSTE, created_by=None, **kwargs) -> PosteAction:
    return PosteAction(
        id=uuid4(),
        poste=poste,
        category=ActionCategory.DECISION,
        title="Décision importante",
        status=ActionStatus.BROUILLON,
        created_by=created_by or uuid4(),
        created_at=NOW,
        updated_at=NOW,
        **kwargs,
    )


def _enriched_action(action: PosteAction) -> dict:
    return {
        "id": action.id,
        "poste": action.poste,
        "category": action.category,
        "title": action.title,
        "content": action.content,
        "target_user_id": action.target_user_id,
        "target_event_id": action.target_event_id,
        "amount": action.amount,
        "action_date": action.action_date,
        "status": action.status,
        "extra_data": action.extra_data,
        "created_by": action.created_by,
        "created_at": action.created_at,
        "updated_at": action.updated_at,
        "author_first_name": None,
        "author_last_name": None,
        "target_user_name": None,
        "target_event_title": None,
    }


def _make_meeting() -> CouncilMeeting:
    return CouncilMeeting(
        id=uuid4(),
        meeting_date=NOW,
        location="Salle paroissiale",
        created_at=NOW,
        created_by=uuid4(),
    )


def _make_attendance_record(responsable_id=None, is_present=True):
    a = MagicMock()
    a.status = CouncilAttendanceStatus.PRESENT if is_present else CouncilAttendanceStatus.ABSENT
    return a


def _make_svc(nom_repo=None, action_repo=None, user_repo=None, council_repo=None) -> ResponsableService:
    if nom_repo is None:
        nom_repo = MagicMock()
        nom_repo.create = AsyncMock()
        nom_repo.get = AsyncMock(return_value=None)
        nom_repo.update = AsyncMock()
        nom_repo.get_active_by_poste = AsyncMock(return_value=None)
        nom_repo.get_active_by_user = AsyncMock(return_value=[])
        nom_repo.get_active_by_user_and_poste = AsyncMock(return_value=None)
        nom_repo.list_all_active = AsyncMock(return_value=[])
        nom_repo.list_history = AsyncMock(return_value=[])
        nom_repo.enrich_nomination = AsyncMock(return_value={})
        nom_repo.enrich_nominations = AsyncMock(return_value=[])
    if action_repo is None:
        action_repo = MagicMock()
        action_repo.create = AsyncMock()
        action_repo.get = AsyncMock(return_value=None)
        action_repo.update = AsyncMock()
        action_repo.delete = AsyncMock()
        action_repo.list_by_poste = AsyncMock(return_value=([], 0))
        action_repo.enrich_action = AsyncMock(return_value={})
        action_repo.enrich_actions = AsyncMock(return_value=[])
        action_repo.count_by_poste_and_status = AsyncMock(return_value={})
        action_repo.get_recent_by_poste = AsyncMock(return_value=[])
    if user_repo is None:
        user_repo = MagicMock()
        user_repo.get = AsyncMock(return_value=None)
    if council_repo is None:
        council_repo = MagicMock()
        council_repo.create_meeting = AsyncMock()
        council_repo.get_meeting = AsyncMock(return_value=None)
        council_repo.add_attendance = AsyncMock()
        council_repo.get_responsable_attendances = AsyncMock(return_value=[])
    return ResponsableService(nom_repo, action_repo, user_repo, council_repo)


# ── nominate ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_nominate_user_not_found():
    svc = _make_svc()
    svc.user_repo.get.return_value = None
    data = NominationCreate(user_id=uuid4(), poste=POSTE)
    with pytest.raises(Exception) as exc:
        await svc.nominate(data, uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_nominate_user_inactive():
    svc = _make_svc()
    svc.user_repo.get.return_value = _make_user(is_active=False)
    data = NominationCreate(user_id=uuid4(), poste=POSTE)
    with pytest.raises(Exception) as exc:
        await svc.nominate(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_nominate_not_servant():
    svc = _make_svc()
    svc.user_repo.get.return_value = _make_user(role=UserRole.ADMIN)
    data = NominationCreate(user_id=uuid4(), poste=POSTE)
    with pytest.raises(Exception) as exc:
        await svc.nominate(data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_nominate_poste_already_occupied():
    servant = _make_user(role=UserRole.SERVANT)
    existing_nom = _make_nomination(poste=POSTE)
    svc = _make_svc()
    svc.user_repo.get.return_value = servant
    svc.nomination_repo.get_active_by_poste.return_value = existing_nom
    data = NominationCreate(user_id=servant.id, poste=POSTE)
    with pytest.raises(Exception) as exc:
        await svc.nominate(data, uuid4())
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_nominate_servant_already_has_poste():
    servant = _make_user(role=UserRole.SERVANT)
    existing_nom = _make_nomination(poste=PosteResponsable.CENSEUR, user_id=servant.id)
    svc = _make_svc()
    svc.user_repo.get.return_value = servant
    svc.nomination_repo.get_active_by_poste.return_value = None
    svc.nomination_repo.get_active_by_user.return_value = [existing_nom]
    data = NominationCreate(user_id=servant.id, poste=POSTE)
    with pytest.raises(Exception) as exc:
        await svc.nominate(data, uuid4())
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_nominate_success():
    servant = _make_user(role=UserRole.SERVANT)
    nom = _make_nomination(user_id=servant.id)
    svc = _make_svc()
    svc.user_repo.get.return_value = servant
    svc.nomination_repo.get_active_by_poste.return_value = None
    svc.nomination_repo.get_active_by_user.return_value = []
    svc.nomination_repo.create.return_value = nom
    svc.nomination_repo.enrich_nomination.return_value = _enriched_nomination(nom)
    data = NominationCreate(user_id=servant.id, poste=POSTE)
    result = await svc.nominate(data, uuid4())
    assert result.id == nom.id


# ── revoke ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_not_found():
    svc = _make_svc()
    svc.nomination_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.revoke(uuid4(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_revoke_already_revoquee():
    nom = _make_nomination(status=NominationStatus.REVOQUEE)
    svc = _make_svc()
    svc.nomination_repo.get.return_value = nom
    with pytest.raises(Exception) as exc:
        await svc.revoke(nom.id, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_revoke_success():
    nom = _make_nomination(status=NominationStatus.ACTIVE)
    svc = _make_svc()
    svc.nomination_repo.get.return_value = nom
    svc.nomination_repo.update.return_value = nom
    svc.nomination_repo.enrich_nomination.return_value = _enriched_nomination(nom)
    result = await svc.revoke(nom.id, uuid4())
    assert result.id == nom.id


# ── list_active_nominations ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_active_nominations_empty():
    svc = _make_svc()
    svc.nomination_repo.list_all_active.return_value = []
    svc.nomination_repo.enrich_nominations.return_value = []
    result = await svc.list_active_nominations()
    assert result == []


@pytest.mark.asyncio
async def test_list_active_nominations_with_items():
    nom = _make_nomination()
    svc = _make_svc()
    svc.nomination_repo.list_all_active.return_value = [nom]
    svc.nomination_repo.enrich_nominations.return_value = [_enriched_nomination(nom)]
    result = await svc.list_active_nominations()
    assert len(result) == 1


# ── get_my_nominations ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_my_nominations_empty():
    svc = _make_svc()
    svc.nomination_repo.get_active_by_user.return_value = []
    svc.nomination_repo.enrich_nominations.return_value = []
    result = await svc.get_my_nominations(uuid4())
    assert result == []


# ── get_nomination_history ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_nomination_history():
    nom = _make_nomination()
    svc = _make_svc()
    svc.nomination_repo.list_history.return_value = [nom]
    svc.nomination_repo.enrich_nominations.return_value = [_enriched_nomination(nom)]
    result = await svc.get_nomination_history()
    assert len(result) == 1


# ── list_postes ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_postes_all_vacant():
    svc = _make_svc()
    svc.nomination_repo.get_active_by_poste.return_value = None
    result = await svc.list_postes()
    assert result.postes_pourvus == 0
    assert result.postes_vacants == result.total_postes


@pytest.mark.asyncio
async def test_list_postes_one_occupied():
    nom = _make_nomination()
    svc = _make_svc()
    svc.nomination_repo.enrich_nomination.return_value = _enriched_nomination(nom)

    call_count = 0

    async def get_active_by_poste(poste):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return nom
        return None

    svc.nomination_repo.get_active_by_poste.side_effect = get_active_by_poste
    result = await svc.list_postes()
    assert result.postes_pourvus == 1


# ── get_poste_detail ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_poste_detail_vacant():
    svc = _make_svc()
    svc.nomination_repo.get_active_by_poste.return_value = None
    result = await svc.get_poste_detail(POSTE)
    assert result.poste == POSTE
    assert result.titulaire is None


@pytest.mark.asyncio
async def test_get_poste_detail_occupied():
    nom = _make_nomination()
    svc = _make_svc()
    svc.nomination_repo.get_active_by_poste.return_value = nom
    svc.nomination_repo.enrich_nomination.return_value = _enriched_nomination(nom)
    result = await svc.get_poste_detail(POSTE)
    assert result.titulaire is not None


# ── create_action ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_action_category_not_allowed():
    svc = _make_svc()
    # COLLECTE is not in DELEGUE's allowed categories
    data = PosteActionCreate(
        category=ActionCategory.COLLECTE,
        title="Collecte du dimanche",
    )
    with pytest.raises(Exception) as exc:
        await svc.create_action(PosteResponsable.DELEGUE, data, uuid4())
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_action_success():
    action = _make_action(poste=POSTE)
    svc = _make_svc()
    svc.action_repo.create.return_value = action
    svc.action_repo.enrich_action.return_value = _enriched_action(action)

    data = PosteActionCreate(
        category=ActionCategory.DECISION,
        title="Décision du conseil",
    )
    result = await svc.create_action(POSTE, data, uuid4())
    assert result.id == action.id


# ── list_actions ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_actions_empty():
    svc = _make_svc()
    svc.action_repo.list_by_poste.return_value = ([], 0)
    svc.action_repo.enrich_actions.return_value = []
    result = await svc.list_actions(POSTE)
    assert result.total == 0


@pytest.mark.asyncio
async def test_list_actions_with_items():
    action = _make_action()
    svc = _make_svc()
    svc.action_repo.list_by_poste.return_value = ([action], 1)
    svc.action_repo.enrich_actions.return_value = [_enriched_action(action)]
    result = await svc.list_actions(POSTE)
    assert result.total == 1


# ── get_action ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_action_not_found():
    svc = _make_svc()
    svc.action_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.get_action(uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_action_success():
    action = _make_action()
    svc = _make_svc()
    svc.action_repo.get.return_value = action
    svc.action_repo.enrich_action.return_value = _enriched_action(action)
    result = await svc.get_action(action.id)
    assert result.id == action.id


# ── update_action ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_update_action_not_found():
    svc = _make_svc()
    svc.action_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.update_action(uuid4(), PosteActionUpdate(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_action_not_owner():
    creator_id = uuid4()
    other_id = uuid4()
    action = _make_action(created_by=creator_id)
    svc = _make_svc()
    svc.action_repo.get.return_value = action
    with pytest.raises(Exception) as exc:
        await svc.update_action(action.id, PosteActionUpdate(), other_id)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_update_action_success():
    creator_id = uuid4()
    action = _make_action(created_by=creator_id)
    svc = _make_svc()
    svc.action_repo.get.return_value = action
    svc.action_repo.update.return_value = action
    svc.action_repo.enrich_action.return_value = _enriched_action(action)
    data = PosteActionUpdate(title="Nouveau titre", status=ActionStatus.PUBLIE)
    result = await svc.update_action(action.id, data, creator_id)
    assert result.id == action.id


# ── delete_action ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_action_not_found():
    svc = _make_svc()
    svc.action_repo.get.return_value = None
    with pytest.raises(Exception) as exc:
        await svc.delete_action(uuid4(), uuid4())
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_action_not_owner():
    creator_id = uuid4()
    action = _make_action(created_by=creator_id)
    svc = _make_svc()
    svc.action_repo.get.return_value = action
    with pytest.raises(Exception) as exc:
        await svc.delete_action(action.id, uuid4())
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_delete_action_success():
    creator_id = uuid4()
    action = _make_action(created_by=creator_id)
    svc = _make_svc()
    svc.action_repo.get.return_value = action
    await svc.delete_action(action.id, creator_id)
    svc.action_repo.delete.assert_called_once_with(action.id)


# ── get_dashboard ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_dashboard():
    svc = _make_svc()
    svc.action_repo.count_by_poste_and_status.return_value = {
        ActionStatus.BROUILLON.value: 2,
        ActionStatus.PUBLIE.value: 3,
        ActionStatus.EN_COURS.value: 1,
        ActionStatus.TERMINE.value: 4,
    }
    svc.action_repo.get_recent_by_poste.return_value = []
    svc.action_repo.enrich_actions.return_value = []
    result = await svc.get_dashboard(POSTE)
    assert result.poste == POSTE
    assert result.total_actions == 10
    assert result.actions_brouillon == 2


# ── monitor_council_attendance ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_monitor_council_attendance_not_enough_data():
    svc = _make_svc()
    svc.council_repo.get_responsable_attendances.return_value = [
        _make_attendance_record(is_present=False),
        _make_attendance_record(is_present=False),
    ]
    result = await svc.monitor_council_attendance(uuid4())
    assert result["destituted"] is False
    assert result["reason"] == "Not enough data"


@pytest.mark.asyncio
async def test_monitor_council_attendance_three_absences_destitutes():
    nom = _make_nomination()
    svc = _make_svc()
    svc.council_repo.get_responsable_attendances.return_value = [
        _make_attendance_record(is_present=False),
        _make_attendance_record(is_present=False),
        _make_attendance_record(is_present=False),
    ]
    svc.nomination_repo.get_active_by_user.return_value = [nom]
    result = await svc.monitor_council_attendance(uuid4())
    assert result["destituted"] is True
    assert result["reason"] == "3 consecutive absences"
    svc.nomination_repo.update.assert_called_once()


@pytest.mark.asyncio
async def test_monitor_council_attendance_not_all_absent():
    svc = _make_svc()
    svc.council_repo.get_responsable_attendances.return_value = [
        _make_attendance_record(is_present=True),
        _make_attendance_record(is_present=False),
        _make_attendance_record(is_present=False),
    ]
    result = await svc.monitor_council_attendance(uuid4())
    assert result["destituted"] is False


# ── create_council_meeting ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_council_meeting():
    meeting = _make_meeting()
    svc = _make_svc()
    svc.council_repo.create_meeting.return_value = meeting
    data = CouncilMeetingCreate(
        meeting_date=NOW,
        location="Salle paroissiale",
        agenda="Points divers",
    )
    result = await svc.create_council_meeting(data, uuid4())
    assert result.id == meeting.id


# ── record_council_attendance ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_council_attendance_meeting_not_found():
    svc = _make_svc()
    svc.council_repo.get_meeting.return_value = None
    data = CouncilAttendanceRecordList(
        attendances=[
            CouncilAttendanceRecord(responsable_id=uuid4(), is_present=True),
        ]
    )
    with pytest.raises(Exception) as exc:
        await svc.record_council_attendance(uuid4(), data)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_record_council_attendance_success():
    meeting = _make_meeting()
    svc = _make_svc()
    svc.council_repo.get_meeting.return_value = meeting
    r1_id = uuid4()
    r2_id = uuid4()
    data = CouncilAttendanceRecordList(
        attendances=[
            CouncilAttendanceRecord(responsable_id=r1_id, is_present=True),
            CouncilAttendanceRecord(responsable_id=r2_id, is_present=False, excuse="Malade"),
        ]
    )
    results = await svc.record_council_attendance(meeting.id, data)
    assert len(results) == 2
    assert svc.council_repo.add_attendance.call_count == 2
