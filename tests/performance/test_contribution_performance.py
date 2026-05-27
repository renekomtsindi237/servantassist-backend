"""
Tests de performance pour le module de contributions (ECONOME).
"""

import time
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient

from src.core.entities.contribution import PaymentMode
from src.core.entities.user import User


@pytest.mark.asyncio
class TestContributionPerformance:
    """Tests de performance des endpoints de contributions."""

    async def test_list_contributions_performance(self, client: AsyncClient, econome_token: str):
        """Test : Performance de la liste des contributions."""
        start_time = time.time()

        response = await client.get(
            "/api/v1/contributions/?page=1&page_size=50",
            headers={"Authorization": f"Bearer {econome_token}"},
        )

        end_time = time.time()
        duration = end_time - start_time

        assert response.status_code == 200
        assert duration < 1.0  # Doit répondre en moins de 1 seconde

    async def test_create_contribution_performance(self, client: AsyncClient, econome_token: str, servant_user_id: str):
        """Test : Performance de création d'une contribution."""
        start_time = time.time()

        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )

        end_time = time.time()
        duration = end_time - start_time

        assert response.status_code == 201
        assert duration < 0.5  # Doit créer en moins de 500ms

    async def test_monthly_summary_performance(self, client: AsyncClient, econome_token: str):
        """Test : Performance du résumé mensuel."""
        start_time = time.time()

        response = await client.get(
            "/api/v1/contributions/summary/2/2026",
            headers={"Authorization": f"Bearer {econome_token}"},
        )

        end_time = time.time()
        duration = end_time - start_time

        assert response.status_code == 200
        assert duration < 2.0  # Doit calculer en moins de 2 secondes

    async def test_financial_report_performance(self, client: AsyncClient, econome_token: str):
        """Test : Performance de génération de rapport."""
        start_time = time.time()

        response = await client.post(
            "/api/v1/contributions/report",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "start_date": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
                "end_date": datetime(2026, 12, 31, tzinfo=timezone.utc).isoformat(),
            },
        )

        end_time = time.time()
        duration = end_time - start_time

        assert response.status_code == 200
        assert duration < 3.0  # Doit générer en moins de 3 secondes

    async def test_bulk_contributions_query_performance(
        self,
        client: AsyncClient,
        econome_token: str,
        db_session,
        servant_user: User,
        econome_user: User,
    ):
        """Test : Performance avec un grand nombre de contributions."""
        # Créer 100 contributions
        from src.core.entities.contribution import Contribution

        contributions = []
        for i in range(100):
            contribution = Contribution(
                id=uuid4(),
                servant_id=servant_user.id,
                amount=100.0 if i % 4 == 0 else 500.0,
                payment_mode=PaymentMode.WEEKLY if i % 4 == 0 else PaymentMode.MONTHLY,
                payment_date=datetime(2026, 2, 1 + (i % 28), tzinfo=timezone.utc),
                month=2,
                year=2026,
                week_number=(i % 4) + 1 if i % 4 == 0 else None,
                recorded_by=econome_user.id,
            )
            contributions.append(contribution)

        for contrib in contributions:
            db_session.add(contrib)
        await db_session.commit()

        # Tester la performance de la requête
        start_time = time.time()

        response = await client.get(
            f"/api/v1/contributions/servant/{servant_user.id}",
            headers={"Authorization": f"Bearer {econome_token}"},
        )

        end_time = time.time()
        duration = end_time - start_time

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 100
        assert duration < 1.0  # Doit récupérer 100+ contributions en moins de 1 seconde


@pytest.mark.asyncio
class TestContributionConcurrency:
    """Tests de concurrence pour les contributions."""

    async def test_concurrent_contributions_creation(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Créations concurrentes de contributions."""
        import asyncio

        async def create_contribution(week: int):
            return await client.post(
                "/api/v1/contributions/",
                headers={"Authorization": f"Bearer {econome_token}"},
                json={
                    "servant_id": servant_user_id,
                    "amount": 100.0,
                    "payment_mode": "HEBDOMADAIRE",
                    "payment_date": datetime.now(timezone.utc).isoformat(),
                    "month": 2,
                    "year": 2026,
                    "week_number": week,
                },
            )

        # Créer 4 contributions en parallèle
        start_time = time.time()

        tasks = [create_contribution(i + 1) for i in range(4)]
        responses = await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time

        # Vérifier que toutes les créations ont réussi
        for response in responses:
            assert response.status_code == 201

        # Doit traiter 4 créations concurrentes en moins de 2 secondes
        assert duration < 2.0
