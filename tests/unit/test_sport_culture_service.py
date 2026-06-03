"""
Unit tests for SportCultureService (CHARGE_SPORT_CULTURE).
Covers events, participations, results, teams, and error paths.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.services.sport_culture_service import SportCultureService
from src.core.entities.sport_culture import (
    EventParticipation,
    EventResult,
    EventStatus,
    EventTeam,
    EventType,
    ParticipationStatus,
    ResultType,
    SportCultureEvent,
    SportType,
)

# ── Factories ──────────────────────────────────────────────────────────────


def _make_event(**kwargs) -> SportCultureEvent:
    defaults = dict(
        id=uuid4(),
        title="Foot Inter-groupes",
        description="Match amical",
        event_type=EventType.MATCH,
        sport_type=SportType.FOOTBALL,
        date=datetime(2026, 3, 15, tzinfo=timezone.utc),
        start_time="15h00",
        end_time="17h30",
        location="Terrain ISJ",
        max_participants=22,
        status=EventStatus.PLANIFIE,
        created_by=uuid4(),
    )
    defaults.update(kwargs)
    return SportCultureEvent(**defaults)


def _make_participation(**kwargs) -> EventParticipation:
    defaults = dict(
        id=uuid4(),
        event_id=uuid4(),
        servant_id=uuid4(),
        registered_by=uuid4(),
    )
    defaults.update(kwargs)
    return EventParticipation(**defaults)


def _make_svc(
    event_repo=None,
    participation_repo=None,
    result_repo=None,
    team_repo=None,
) -> SportCultureService:
    return SportCultureService(
        event_repo=event_repo or AsyncMock(),
        participation_repo=participation_repo or AsyncMock(),
        result_repo=result_repo or AsyncMock(),
        team_repo=team_repo or AsyncMock(),
    )


# ══════════════════════════════════════════════════════════════════
#  Existing tests (kept)
# ══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_create_event():
    event_repo = AsyncMock()
    event = _make_event()
    event_repo.create.return_value = event

    svc = _make_svc(event_repo=event_repo)
    result = await svc.create_event(
        title=event.title,
        description=event.description,
        event_type=event.event_type,
        date=event.date,
        start_time=event.start_time,
        end_time=event.end_time,
        location=event.location,
        max_participants=event.max_participants,
        created_by=event.created_by,
        sport_type=event.sport_type,
        broadcast_notification=False,
    )

    assert result.title == event.title
    event_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_register_participant_success():
    event_repo = AsyncMock()
    participation_repo = AsyncMock()
    event = _make_event(max_participants=22)
    servant_id = uuid4()
    event_repo.get_by_id.return_value = event
    participation_repo.get_by_event_and_servant.return_value = None
    participation_repo.count_by_event.return_value = 5
    participation_repo.create.return_value = MagicMock()
    participation_repo.enrich_participation.return_value = MagicMock()

    svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
    await svc.register_participant(event.id, servant_id, uuid4())

    participation_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_add_result():
    event_repo = AsyncMock()
    result_repo = AsyncMock()
    event = _make_event()
    event_repo.get_by_id.return_value = event
    result_repo.create.return_value = MagicMock()

    svc = _make_svc(event_repo=event_repo, result_repo=result_repo)
    await svc.add_result(
        event_id=event.id,
        result_type=ResultType.VICTOIRE,
        description="Gagné 2-0",
        recorded_by=uuid4(),
    )

    result_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_create_team():
    event_repo = AsyncMock()
    team_repo = AsyncMock()
    event = _make_event()
    event_repo.get_by_id.return_value = event
    team = MagicMock()
    team_repo.create.return_value = team
    team_repo.enrich_team.return_value = team

    svc = _make_svc(event_repo=event_repo, team_repo=team_repo)
    await svc.create_team(
        event_id=event.id,
        team_name="Equipe A",
        captain_id=uuid4(),
        members=[uuid4(), uuid4()],
        created_by=uuid4(),
    )

    team_repo.create.assert_called_once()


# ══════════════════════════════════════════════════════════════════
#  Event CRUD
# ══════════════════════════════════════════════════════════════════


class TestGetEvent:
    @pytest.mark.asyncio
    async def test_returns_event(self):
        event_repo = AsyncMock()
        event = _make_event()
        event_repo.get_by_id.return_value = event

        svc = _make_svc(event_repo=event_repo)
        result = await svc.get_event(event.id)
        assert result is event

    @pytest.mark.asyncio
    async def test_returns_none(self):
        event_repo = AsyncMock()
        event_repo.get_by_id.return_value = None

        svc = _make_svc(event_repo=event_repo)
        result = await svc.get_event(uuid4())
        assert result is None


class TestListEvents:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        event_repo = AsyncMock()
        event = _make_event()
        event_repo.list_events.return_value = ([event], 1)

        svc = _make_svc(event_repo=event_repo)
        events, total = await svc.list_events()
        assert total == 1
        event_repo.list_events.assert_called_once()


class TestUpdateEvent:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        event_repo = AsyncMock()
        event_repo.get_by_id.return_value = None

        svc = _make_svc(event_repo=event_repo)
        result = await svc.update_event(uuid4(), title="New")
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_fields(self):
        event_repo = AsyncMock()
        event = _make_event()
        event_repo.get_by_id.return_value = event
        event_repo.update.return_value = event

        svc = _make_svc(event_repo=event_repo)
        await svc.update_event(
            event.id,
            title="Nouveau titre",
            status=EventStatus.EN_COURS,
            max_participants=30,
        )

        assert event.title == "Nouveau titre"
        assert event.status == EventStatus.EN_COURS
        assert event.max_participants == 30


class TestAddEventPhoto:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        event_repo = AsyncMock()
        event_repo.get_by_id.return_value = None

        svc = _make_svc(event_repo=event_repo)
        result = await svc.add_event_photo(uuid4(), "photo.jpg")
        assert result is None

    @pytest.mark.asyncio
    async def test_adds_photo(self):
        event_repo = AsyncMock()
        event = _make_event()
        event.photos = []
        event_repo.get_by_id.return_value = event
        event_repo.update.return_value = event

        svc = _make_svc(event_repo=event_repo)
        await svc.add_event_photo(event.id, "match.jpg")

        assert "match.jpg" in event.photos


class TestDeleteEvent:
    @pytest.mark.asyncio
    async def test_raises_400_when_has_participants(self):
        event_repo = AsyncMock()
        participation_repo = AsyncMock()
        participation_repo.get_by_event.return_value = [MagicMock()]

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.delete_event(uuid4())
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_deletes_when_no_participants(self):
        event_repo = AsyncMock()
        participation_repo = AsyncMock()
        participation_repo.get_by_event.return_value = []
        event_repo.delete.return_value = True

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        result = await svc.delete_event(uuid4())
        assert result is True


class TestGetUpcomingEvents:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        event_repo = AsyncMock()
        events = [_make_event()]
        event_repo.get_upcoming_events.return_value = events

        svc = _make_svc(event_repo=event_repo)
        result = await svc.get_upcoming_events(limit=5)
        assert result is events
        event_repo.get_upcoming_events.assert_called_once_with(5)


# ══════════════════════════════════════════════════════════════════
#  Participation management
# ══════════════════════════════════════════════════════════════════


class TestRegisterParticipantErrors:
    @pytest.mark.asyncio
    async def test_raises_404_when_event_not_found(self):
        event_repo = AsyncMock()
        event_repo.get_by_id.return_value = None

        svc = _make_svc(event_repo=event_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.register_participant(uuid4(), uuid4(), uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_already_registered(self):
        event_repo = AsyncMock()
        participation_repo = AsyncMock()
        event = _make_event()
        event_repo.get_by_id.return_value = event
        participation_repo.get_by_event_and_servant.return_value = MagicMock()

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.register_participant(event.id, uuid4(), uuid4())
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_raises_400_when_event_full(self):
        event_repo = AsyncMock()
        participation_repo = AsyncMock()
        event = _make_event(max_participants=5)
        event_repo.get_by_id.return_value = event
        participation_repo.get_by_event_and_servant.return_value = None
        participation_repo.count_by_event.return_value = 5  # at max

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.register_participant(event.id, uuid4(), uuid4())
        assert exc.value.status_code == 400


class TestRegisterParticipantsBatch:
    @pytest.mark.asyncio
    async def test_raises_404_when_event_not_found(self):
        event_repo = AsyncMock()
        event_repo.get_by_id.return_value = None

        svc = _make_svc(event_repo=event_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.register_participants_batch(uuid4(), [uuid4()], uuid4())
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_raises_400_when_not_enough_space(self):
        event_repo = AsyncMock()
        participation_repo = AsyncMock()
        event = _make_event(max_participants=5)
        event_repo.get_by_id.return_value = event
        participation_repo.count_by_event.return_value = 4  # only 1 spot left

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        with pytest.raises(HTTPException) as exc:
            await svc.register_participants_batch(event.id, [uuid4(), uuid4()], uuid4())
        assert exc.value.status_code == 400

    @pytest.mark.asyncio
    async def test_skips_already_registered(self):
        event_repo = AsyncMock()
        participation_repo = AsyncMock()
        event = _make_event(max_participants=0)
        event_repo.get_by_id.return_value = event
        participation_repo.get_by_event_and_servant.return_value = MagicMock()  # already registered
        participation_repo.create_batch.return_value = []

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        result = await svc.register_participants_batch(event.id, [uuid4()], uuid4())
        assert result == []


class TestGetEventParticipants:
    @pytest.mark.asyncio
    async def test_enriches_list(self):
        participation_repo = AsyncMock()
        participation = _make_participation()
        participation_repo.get_by_event.return_value = [participation]
        participation_repo.enrich_participation.return_value = participation

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.get_event_participants(uuid4())
        assert len(result) == 1
        participation_repo.enrich_participation.assert_called_once()


class TestGetServantParticipations:
    @pytest.mark.asyncio
    async def test_enriches_list(self):
        participation_repo = AsyncMock()
        participation = _make_participation()
        participation_repo.get_by_servant.return_value = [participation]
        participation_repo.enrich_participation.return_value = participation

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.get_servant_participations(uuid4())
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
        participation = _make_participation()
        participation_repo.get_by_id.return_value = participation
        participation_repo.update.return_value = participation
        participation_repo.enrich_participation.return_value = participation

        svc = _make_svc(participation_repo=participation_repo)
        marked_by = uuid4()
        await svc.mark_attendance(participation.id, ParticipationStatus.PRESENT, marked_by)

        assert participation.status == ParticipationStatus.PRESENT
        assert participation.marked_by == marked_by


class TestMarkPayment:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        participation_repo = AsyncMock()
        participation_repo.get_by_id.return_value = None

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.mark_payment(uuid4(), True)
        assert result is None

    @pytest.mark.asyncio
    async def test_marks_payment(self):
        participation_repo = AsyncMock()
        participation = _make_participation()
        participation_repo.get_by_id.return_value = participation
        participation_repo.update.return_value = participation
        participation_repo.enrich_participation.return_value = participation

        svc = _make_svc(participation_repo=participation_repo)
        await svc.mark_payment(participation.id, True, notes="Payé en espèces")

        assert participation.payment_status is True
        assert participation.notes == "Payé en espèces"


class TestCancelRegistration:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        participation_repo = AsyncMock()
        participation_repo.delete.return_value = True

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.cancel_registration(uuid4())
        assert result is True


# ══════════════════════════════════════════════════════════════════
#  Results
# ══════════════════════════════════════════════════════════════════


class TestAddResultErrors:
    @pytest.mark.asyncio
    async def test_returns_none_when_event_not_found(self):
        event_repo = AsyncMock()
        event_repo.get_by_id.return_value = None

        svc = _make_svc(event_repo=event_repo)
        result = await svc.add_result(
            event_id=uuid4(),
            result_type=ResultType.VICTOIRE,
            description="Test",
            recorded_by=uuid4(),
        )
        assert result is None


class TestGetEventResults:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        result_repo = AsyncMock()
        results = [MagicMock(), MagicMock()]
        result_repo.get_by_event.return_value = results

        svc = _make_svc(result_repo=result_repo)
        result = await svc.get_event_results(uuid4())
        assert result is results


class TestDeleteResult:
    @pytest.mark.asyncio
    async def test_delegates_to_repo(self):
        result_repo = AsyncMock()
        result_repo.delete.return_value = True

        svc = _make_svc(result_repo=result_repo)
        result = await svc.delete_result(uuid4())
        assert result is True


# ══════════════════════════════════════════════════════════════════
#  Teams
# ══════════════════════════════════════════════════════════════════


class TestCreateTeamErrors:
    @pytest.mark.asyncio
    async def test_returns_none_when_event_not_found(self):
        event_repo = AsyncMock()
        event_repo.get_by_id.return_value = None

        svc = _make_svc(event_repo=event_repo)
        result = await svc.create_team(
            event_id=uuid4(),
            team_name="Equipe",
            captain_id=uuid4(),
            created_by=uuid4(),
        )
        assert result is None


class TestGetEventTeams:
    @pytest.mark.asyncio
    async def test_enriches_list(self):
        team_repo = AsyncMock()
        team = MagicMock()
        team_repo.get_by_event.return_value = [team]
        team_repo.enrich_team.return_value = team

        svc = _make_svc(team_repo=team_repo)
        result = await svc.get_event_teams(uuid4())
        assert len(result) == 1
        team_repo.enrich_team.assert_called_once()


class TestUpdateTeam:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        team_repo = AsyncMock()
        team_repo.get_by_id.return_value = None

        svc = _make_svc(team_repo=team_repo)
        result = await svc.update_team(uuid4(), team_name="New")
        assert result is None

    @pytest.mark.asyncio
    async def test_updates_fields(self):
        team_repo = AsyncMock()
        team = MagicMock()
        team_repo.get_by_id.return_value = team
        team_repo.update.return_value = team
        team_repo.enrich_team.return_value = team

        svc = _make_svc(team_repo=team_repo)
        new_captain = uuid4()
        await svc.update_team(uuid4(), team_name="Equipe B", captain_id=new_captain)

        assert team.team_name == "Equipe B"
        assert team.captain_id == new_captain


# ═══════════════════════════════════════════════════════════════════════════
#  Coverage completion — generate_report, get_statistics, get_servant_stats
# ═══════════════════════════════════════════════════════════════════════════


class TestGetStatistics:

    @pytest.mark.asyncio
    async def test_empty_events(self):
        event_repo = AsyncMock()
        event_repo.list_events.return_value = ([], 0)
        participation_repo = AsyncMock()

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        result = await svc.get_statistics()

        assert result["total_events"] == 0
        assert result["total_participants"] == 0
        assert result["average_participation_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_with_events(self):
        event = _make_event(status=EventStatus.PLANIFIE)
        event.date = datetime(2030, 6, 1)  # Future event

        participation = MagicMock()
        participation.status = ParticipationStatus.PRESENT

        event_repo = AsyncMock()
        event_repo.list_events.return_value = ([event], 1)

        participation_repo = AsyncMock()
        participation_repo.get_by_event.return_value = [participation]

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        result = await svc.get_statistics()

        assert result["total_events"] == 1
        assert result["total_participants"] == 1
        assert result["average_participation_rate"] == 100.0
        assert result["upcoming_events"] == 1


class TestGetServantStats:

    @pytest.mark.asyncio
    async def test_no_participations(self):
        participation_repo = AsyncMock()
        participation_repo.get_by_servant.return_value = []

        svc = _make_svc(participation_repo=participation_repo)
        result = await svc.get_servant_stats(uuid4())

        assert result["total_participations"] == 0
        assert result["events_attended"] == 0
        assert result["attendance_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_with_participations(self):
        event = _make_event()
        event.cost = 1000.0

        participation = MagicMock()
        participation.status = ParticipationStatus.PRESENT
        participation.payment_status = True
        participation.event_id = event.id

        event_repo = AsyncMock()
        event_repo.get_by_id.return_value = event

        participation_repo = AsyncMock()
        participation_repo.get_by_servant.return_value = [participation]

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        result = await svc.get_servant_stats(uuid4())

        assert result["total_participations"] == 1
        assert result["events_attended"] == 1
        assert result["attendance_rate"] == 100.0
        assert result["total_paid"] == 1000.0

    @pytest.mark.asyncio
    async def test_absent_participation(self):
        participation = MagicMock()
        participation.status = ParticipationStatus.ABSENT
        participation.payment_status = False
        participation.event_id = uuid4()

        event_repo = AsyncMock()
        event_repo.get_by_id.return_value = None

        participation_repo = AsyncMock()
        participation_repo.get_by_servant.return_value = [participation]

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        result = await svc.get_servant_stats(uuid4())

        assert result["events_missed"] == 1
        assert result["events_attended"] == 0


class TestGenerateReport:

    @pytest.mark.asyncio
    async def test_empty_period(self):
        event_repo = AsyncMock()
        event_repo.list_events.return_value = ([], 0)
        participation_repo = AsyncMock()
        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        from datetime import timezone

        result = await svc.generate_report(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
            generated_by=uuid4(),
        )

        assert result.total_events == 0
        assert result.average_participation_rate == 0.0

    @pytest.mark.asyncio
    async def test_with_events(self):
        event = _make_event()
        participation = MagicMock()
        participation.status = ParticipationStatus.PRESENT
        participation.payment_status = False
        participation.servant_id = uuid4()
        participation.servant_name = "Jean D."

        event_repo = AsyncMock()
        event_repo.list_events.return_value = ([event], 1)

        participation_repo = AsyncMock()
        participation_repo.get_by_event.return_value = [participation]

        svc = _make_svc(event_repo=event_repo, participation_repo=participation_repo)
        from datetime import timezone

        result = await svc.generate_report(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
            generated_by=uuid4(),
        )

        assert result.total_events == 1
        assert len(result.events_summary) == 1


class TestCreateEventWithNotification:

    @pytest.mark.asyncio
    async def test_create_event_with_broadcast(self):
        event = _make_event()
        event_repo = AsyncMock()
        event_repo.create.return_value = event
        event_repo.session = AsyncMock()

        svc = _make_svc(event_repo=event_repo)

        with __import__("unittest.mock", fromlist=["patch"]).patch(
            "src.application.services.notification_service.NotificationService.broadcast",
            new_callable=AsyncMock,
        ):
            result = await svc.create_event(
                title=event.title,
                description=event.description,
                event_type=event.event_type,
                sport_type=event.sport_type,
                date=event.date,
                start_time=event.start_time,
                end_time=event.end_time,
                location=event.location,
                max_participants=event.max_participants,
                created_by=event.created_by,
                broadcast_notification=True,
            )

        assert result.title == event.title
