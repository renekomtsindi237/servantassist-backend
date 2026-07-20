"""
Unit tests for src/infrastructure/tasks/reminder_tasks.py

Focus sur check_convocation_deadlines (Art. 49) — pas de DB ou worker Celery reel.
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


def _make_session_manager(mock_session) -> MagicMock:
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_sm = MagicMock()
    mock_sm.session.return_value = mock_session
    return mock_sm


@pytest.mark.asyncio
async def test_check_convocation_deadlines_no_expired():
    from src.infrastructure.tasks.reminder_tasks import _check_convocation_deadlines_async

    mock_session = AsyncMock()
    mock_sm = _make_session_manager(mock_session)

    mock_conv_repo = MagicMock()
    mock_conv_repo.list_pending_past_deadline = AsyncMock(return_value=[])
    mock_conv_repo.update = AsyncMock()
    mock_user_repo = MagicMock()

    import src.infrastructure.database.session as db_session_mod

    with patch.object(db_session_mod, "sessionmanager", mock_sm):
        with patch(
            "src.infrastructure.repositories.convocation_repository.ConvocationRepository",
            return_value=mock_conv_repo,
        ):
            with patch(
                "src.infrastructure.repositories.user_repository.UserRepository",
                return_value=mock_user_repo,
            ):
                result = await _check_convocation_deadlines_async()

    assert result["expired_convocations_processed"] == 0


@pytest.mark.asyncio
async def test_check_convocation_deadlines_suspends_servant():
    from src.core.entities.convocation import Convocation, ConvocationMotif, ConvocationStatus
    from src.infrastructure.tasks.reminder_tasks import _check_convocation_deadlines_async

    servant_id = uuid4()
    convocation = Convocation(
        id=uuid4(),
        servant_id=servant_id,
        motif=ConvocationMotif.NON_COTISATION,
        convened_by=uuid4(),
        status=ConvocationStatus.EN_ATTENTE,
    )
    servant = MagicMock()
    servant.id = servant_id
    servant.is_active = True

    mock_session = AsyncMock()
    mock_sm = _make_session_manager(mock_session)

    mock_conv_repo = MagicMock()
    mock_conv_repo.list_pending_past_deadline = AsyncMock(return_value=[convocation])
    mock_conv_repo.update = AsyncMock(return_value=convocation)
    mock_user_repo = MagicMock()
    mock_user_repo.get = AsyncMock(return_value=servant)
    mock_user_repo.update = AsyncMock()

    with patch(
        "src.infrastructure.repositories.convocation_repository.ConvocationRepository",
        return_value=mock_conv_repo,
    ):
        with patch(
            "src.infrastructure.repositories.user_repository.UserRepository",
            return_value=mock_user_repo,
        ):
            import src.infrastructure.database.session as db_session_mod

            with patch.object(db_session_mod, "sessionmanager", mock_sm):
                result = await _check_convocation_deadlines_async()

    assert result["expired_convocations_processed"] == 1
    assert convocation.status == ConvocationStatus.SANS_REPONSE
    mock_user_repo.update.assert_called_once()
    assert servant.is_active is False
