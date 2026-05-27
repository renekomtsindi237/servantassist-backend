"""
Tests unitaires pour le service de contributions (ECONOME).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.application.services.contribution_service import ContributionService
from src.core.entities.contribution import Contribution, PaymentMode, PaymentStatus
from src.core.entities.user import User, UserRole
from src.presentation.schemas.contribution import (
    ContributionCreate,
    ContributionUpdate,
    FinancialReportRequest,
)


@pytest.fixture
def mock_contribution_repo():
    """Mock du repository de contributions."""
    return AsyncMock()


@pytest.fixture
def mock_user_repo():
    """Mock du repository d'utilisateurs."""
    return AsyncMock()


@pytest.fixture
def contribution_service(mock_contribution_repo, mock_user_repo):
    """Service de contributions avec mocks."""
    return ContributionService(mock_contribution_repo, mock_user_repo)


@pytest.fixture
def sample_servant():
    """Servant de test."""
    return User(
        id=uuid4(),
        email="servant@test.com",
        first_name="Jean",
        last_name="Dupont",
        role=UserRole.SERVANT,
        is_active=True,
    )


@pytest.fixture
def sample_econome():
    """Econome de test."""
    return User(
        id=uuid4(),
        email="econome@test.com",
        first_name="Marie",
        last_name="Martin",
        role=UserRole.SERVANT,
        is_active=True,
    )


@pytest.fixture
def sample_contribution(sample_servant, sample_econome):
    """Contribution de test."""
    return Contribution(
        id=uuid4(),
        servant_id=sample_servant.id,
        amount=500.0,
        payment_mode=PaymentMode.MONTHLY,
        payment_date=datetime(2026, 2, 10, tzinfo=timezone.utc),
        month=2,
        year=2026,
        recorded_by=sample_econome.id,
        notes="Test",
    )


class TestRecordPayment:
    """Tests de la méthode record_payment."""

    @pytest.mark.asyncio
    async def test_record_monthly_payment_success(
        self,
        contribution_service,
        mock_contribution_repo,
        mock_user_repo,
        sample_servant,
        sample_econome,
        sample_contribution,
    ):
        """Test : Enregistrer un paiement mensuel avec succès."""
        # Arrange
        mock_user_repo.get.return_value = sample_servant
        mock_contribution_repo.create.return_value = sample_contribution
        mock_contribution_repo.enrich_contribution.return_value = {
            **sample_contribution.model_dump(),
            "servant_name": "Jean Dupont",
            "recorded_by_name": "Marie Martin",
        }

        data = ContributionCreate(
            servant_id=sample_servant.id,
            amount=500.0,
            payment_mode=PaymentMode.MONTHLY,
            payment_date=datetime(2026, 2, 10, tzinfo=timezone.utc),
            month=2,
            year=2026,
        )

        # Act
        result = await contribution_service.record_payment(data, sample_econome.id)

        # Assert
        assert result.amount == 500.0
        assert result.payment_mode == PaymentMode.MONTHLY
        mock_contribution_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_weekly_payment_success(
        self,
        contribution_service,
        mock_contribution_repo,
        mock_user_repo,
        sample_servant,
        sample_econome,
    ):
        """Test : Enregistrer un paiement hebdomadaire avec succès."""
        # Arrange
        mock_user_repo.get.return_value = sample_servant
        weekly_contribution = Contribution(
            id=uuid4(),
            servant_id=sample_servant.id,
            amount=100.0,
            payment_mode=PaymentMode.WEEKLY,
            payment_date=datetime(2026, 2, 10, tzinfo=timezone.utc),
            month=2,
            year=2026,
            week_number=1,
            recorded_by=sample_econome.id,
        )
        mock_contribution_repo.create.return_value = weekly_contribution
        mock_contribution_repo.enrich_contribution.return_value = {
            **weekly_contribution.model_dump(),
            "servant_name": "Jean Dupont",
            "recorded_by_name": "Marie Martin",
        }

        data = ContributionCreate(
            servant_id=sample_servant.id,
            amount=100.0,
            payment_mode=PaymentMode.WEEKLY,
            payment_date=datetime(2026, 2, 10, tzinfo=timezone.utc),
            month=2,
            year=2026,
            week_number=1,
        )

        # Act
        result = await contribution_service.record_payment(data, sample_econome.id)

        # Assert
        assert result.amount == 100.0
        assert result.payment_mode == PaymentMode.WEEKLY
        assert result.week_number == 1

    @pytest.mark.asyncio
    async def test_record_payment_servant_not_found(
        self,
        contribution_service,
        mock_user_repo,
        sample_econome,
    ):
        """Test : Erreur si le servant n'existe pas."""
        # Arrange
        mock_user_repo.get.return_value = None
        fake_servant_id = uuid4()

        data = ContributionCreate(
            servant_id=fake_servant_id,
            amount=500.0,
            payment_mode=PaymentMode.MONTHLY,
            payment_date=datetime(2026, 2, 10, tzinfo=timezone.utc),
            month=2,
            year=2026,
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await contribution_service.record_payment(data, sample_econome.id)

        assert exc_info.value.status_code == 404
        assert "introuvable" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_record_payment_user_not_servant(
        self,
        contribution_service,
        mock_user_repo,
        sample_econome,
    ):
        """Test : Erreur si l'utilisateur n'est pas un servant."""
        # Arrange
        parent_user = User(
            id=uuid4(),
            email="parent@test.com",
            first_name="Parent",
            last_name="Test",
            role=UserRole.PARENT,
            is_active=True,
        )
        mock_user_repo.get.return_value = parent_user

        data = ContributionCreate(
            servant_id=parent_user.id,
            amount=500.0,
            payment_mode=PaymentMode.MONTHLY,
            payment_date=datetime(2026, 2, 10, tzinfo=timezone.utc),
            month=2,
            year=2026,
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await contribution_service.record_payment(data, sample_econome.id)

        assert exc_info.value.status_code == 400
        assert "servant" in exc_info.value.detail.lower()


class TestGetContribution:
    """Tests de la méthode get_contribution."""

    @pytest.mark.asyncio
    async def test_get_contribution_success(
        self,
        contribution_service,
        mock_contribution_repo,
        sample_contribution,
    ):
        """Test : Récupérer une contribution avec succès."""
        # Arrange
        mock_contribution_repo.get.return_value = sample_contribution
        mock_contribution_repo.enrich_contribution.return_value = {
            **sample_contribution.model_dump(),
            "servant_name": "Jean Dupont",
            "recorded_by_name": "Marie Martin",
        }

        # Act
        result = await contribution_service.get_contribution(sample_contribution.id)

        # Assert
        assert result.id == sample_contribution.id
        assert result.amount == 500.0

    @pytest.mark.asyncio
    async def test_get_contribution_not_found(
        self,
        contribution_service,
        mock_contribution_repo,
    ):
        """Test : Erreur si la contribution n'existe pas."""
        # Arrange
        mock_contribution_repo.get.return_value = None
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await contribution_service.get_contribution(fake_id)

        assert exc_info.value.status_code == 404


class TestUpdatePayment:
    """Tests de la méthode update_payment."""

    @pytest.mark.asyncio
    async def test_update_payment_success(
        self,
        contribution_service,
        mock_contribution_repo,
        sample_contribution,
    ):
        """Test : Modifier une contribution avec succès."""
        # Arrange
        mock_contribution_repo.get.return_value = sample_contribution
        updated_contribution = sample_contribution.model_copy()
        updated_contribution.notes = "Note modifiée"
        mock_contribution_repo.update.return_value = updated_contribution
        mock_contribution_repo.enrich_contribution.return_value = {
            **updated_contribution.model_dump(),
            "servant_name": "Jean Dupont",
            "recorded_by_name": "Marie Martin",
        }

        data = ContributionUpdate(notes="Note modifiée")

        # Act
        result = await contribution_service.update_payment(sample_contribution.id, data)

        # Assert
        assert result.notes == "Note modifiée"

    @pytest.mark.asyncio
    async def test_update_payment_not_found(
        self,
        contribution_service,
        mock_contribution_repo,
    ):
        """Test : Erreur si la contribution n'existe pas."""
        # Arrange
        mock_contribution_repo.get.return_value = None
        fake_id = uuid4()
        data = ContributionUpdate(notes="Test")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await contribution_service.update_payment(fake_id, data)

        assert exc_info.value.status_code == 404


class TestDeletePayment:
    """Tests de la méthode delete_payment."""

    @pytest.mark.asyncio
    async def test_delete_payment_success(
        self,
        contribution_service,
        mock_contribution_repo,
        sample_contribution,
    ):
        """Test : Supprimer une contribution avec succès."""
        # Arrange
        mock_contribution_repo.get.return_value = sample_contribution
        mock_contribution_repo.delete.return_value = True

        # Act
        await contribution_service.delete_payment(sample_contribution.id)

        # Assert
        mock_contribution_repo.delete.assert_called_once_with(sample_contribution.id)

    @pytest.mark.asyncio
    async def test_delete_payment_not_found(
        self,
        contribution_service,
        mock_contribution_repo,
    ):
        """Test : Erreur si la contribution n'existe pas."""
        # Arrange
        mock_contribution_repo.get.return_value = None
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await contribution_service.delete_payment(fake_id)

        assert exc_info.value.status_code == 404


class TestGenerateFinancialReport:
    """Tests de la méthode generate_financial_report."""

    @pytest.mark.asyncio
    async def test_generate_report_success(
        self,
        contribution_service,
        mock_contribution_repo,
        mock_user_repo,
        sample_econome,
    ):
        """Test : Générer un rapport financier avec succès."""
        # Arrange
        mock_contribution_repo.calculate_period_stats.return_value = {
            "total_expected": 10000.0,
            "total_collected": 8000.0,
            "collection_rate": 80.0,
            "servants_paid": 16,
            "servants_late": 4,
        }
        mock_user_repo.get.return_value = sample_econome

        request = FinancialReportRequest(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 12, 31, tzinfo=timezone.utc),
        )

        # Act
        result = await contribution_service.generate_financial_report(request, sample_econome.id)

        # Assert
        assert result.total_expected == 10000.0
        assert result.total_collected == 8000.0
        assert result.collection_rate == 80.0
        assert result.servants_paid == 16
        assert result.servants_late == 4
        assert result.watermark_logo == "logo_servant.jpeg"


class TestGetServantStats:
    """Tests de la méthode get_servant_stats."""

    @pytest.mark.asyncio
    async def test_get_servant_stats_success(
        self,
        contribution_service,
        mock_contribution_repo,
        mock_user_repo,
        sample_servant,
        sample_contribution,
    ):
        """Test : Calculer les statistiques d'un servant."""
        # Arrange
        mock_user_repo.get.return_value = sample_servant
        mock_contribution_repo.get_servant_contributions.return_value = [sample_contribution]

        # Act
        result = await contribution_service.get_servant_stats(
            sample_servant.id,
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 12, 31, tzinfo=timezone.utc),
        )

        # Assert
        assert result.servant_id == sample_servant.id
        assert result.total_paid == 500.0
        assert result.months_paid == 1

    @pytest.mark.asyncio
    async def test_get_servant_stats_servant_not_found(
        self,
        contribution_service,
        mock_user_repo,
    ):
        """Test : Erreur si le servant n'existe pas."""
        # Arrange
        mock_user_repo.get.return_value = None
        fake_id = uuid4()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await contribution_service.get_servant_stats(
                fake_id,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 12, 31, tzinfo=timezone.utc),
            )

        assert exc_info.value.status_code == 404
