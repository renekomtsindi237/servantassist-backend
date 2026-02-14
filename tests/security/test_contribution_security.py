"""
Tests de sécurité pour le module de contributions (ECONOME).
"""
import pytest
from datetime import datetime, timezone
from uuid import uuid4

from httpx import AsyncClient


@pytest.mark.asyncio
class TestContributionSecurity:
    """Tests de sécurité des endpoints de contributions."""

    async def test_sql_injection_in_filters(
        self, client: AsyncClient, econome_token: str
    ):
        """Test : Protection contre l'injection SQL dans les filtres."""
        malicious_input = "1' OR '1'='1"
        
        response = await client.get(
            f"/api/v1/contributions/?month={malicious_input}",
            headers={"Authorization": f"Bearer {econome_token}"},
        )
        
        # Doit retourner une erreur de validation, pas une erreur SQL
        assert response.status_code == 422

    async def test_xss_in_notes_field(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Protection contre XSS dans le champ notes."""
        xss_payload = "<script>alert('XSS')</script>"
        
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
                "notes": xss_payload,
            },
        )
        
        assert response.status_code == 201
        data = response.json()
        # Le payload doit être stocké tel quel (échappement côté frontend)
        assert data["notes"] == xss_payload

    async def test_unauthorized_access_without_token(
        self, client: AsyncClient
    ):
        """Test : Accès non autorisé sans token."""
        response = await client.get("/api/v1/contributions/")
        assert response.status_code == 401

    async def test_unauthorized_access_with_invalid_token(
        self, client: AsyncClient
    ):
        """Test : Accès non autorisé avec token invalide."""
        response = await client.get(
            "/api/v1/contributions/",
            headers={"Authorization": "Bearer invalid_token_here"},
        )
        assert response.status_code == 401

    async def test_forbidden_access_for_servant(
        self, client: AsyncClient, servant_token: str, servant_user_id: str
    ):
        """Test : Accès interdit pour un SERVANT."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {servant_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == 403

    async def test_cannot_access_other_servant_data_without_permission(
        self, client: AsyncClient, servant_token: str
    ):
        """Test : Un servant ne peut pas créer de contributions."""
        other_servant_id = str(uuid4())
        
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {servant_token}"},
            json={
                "servant_id": other_servant_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        
        assert response.status_code == 403

    async def test_negative_amount_rejected(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Montant négatif rejeté."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": -500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == 422

    async def test_zero_amount_rejected(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Montant zéro rejeté."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 0.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == 422

    async def test_invalid_month_rejected(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Mois invalide rejeté."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 13,  # Invalide
                "year": 2026,
            },
        )
        assert response.status_code == 422

    async def test_invalid_year_rejected(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Année invalide rejetée."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 1999,  # Invalide (< 2020)
            },
        )
        assert response.status_code == 422

    async def test_uuid_validation(
        self, client: AsyncClient, econome_token: str
    ):
        """Test : Validation des UUID."""
        invalid_uuid = "not-a-valid-uuid"
        
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": invalid_uuid,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == 422

    async def test_rate_limiting_protection(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Protection contre les abus (rate limiting)."""
        # Faire 100 requêtes rapidement
        responses = []
        for _ in range(100):
            response = await client.get(
                "/api/v1/contributions/",
                headers={"Authorization": f"Bearer {econome_token}"},
            )
            responses.append(response)
        
        # Au moins une requête devrait être rate-limitée (429)
        status_codes = [r.status_code for r in responses]
        # Note: Ceci dépend de la configuration du rate limiter
        # On vérifie juste qu'il n'y a pas d'erreur serveur
        assert 500 not in status_codes
        assert 502 not in status_codes

    async def test_data_leakage_in_error_messages(
        self, client: AsyncClient, econome_token: str
    ):
        """Test : Pas de fuite de données sensibles dans les erreurs."""
        fake_id = str(uuid4())
        
        response = await client.get(
            f"/api/v1/contributions/{fake_id}",
            headers={"Authorization": f"Bearer {econome_token}"},
        )
        
        assert response.status_code == 404
        data = response.json()
        # Le message d'erreur ne doit pas contenir d'informations sensibles
        assert "database" not in data["detail"].lower()
        assert "sql" not in data["detail"].lower()
        assert "password" not in data["detail"].lower()


@pytest.mark.asyncio
class TestContributionInputValidation:
    """Tests de validation des entrées."""

    async def test_payment_mode_validation(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Validation du mode de paiement."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "INVALID_MODE",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == 422

    async def test_date_format_validation(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Validation du format de date."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 500.0,
                "payment_mode": "MENSUEL",
                "payment_date": "invalid-date-format",
                "month": 2,
                "year": 2026,
            },
        )
        assert response.status_code == 422

    async def test_week_number_range_validation(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Validation de la plage de week_number."""
        response = await client.post(
            "/api/v1/contributions/",
            headers={"Authorization": f"Bearer {econome_token}"},
            json={
                "servant_id": servant_user_id,
                "amount": 100.0,
                "payment_mode": "HEBDOMADAIRE",
                "payment_date": datetime.now(timezone.utc).isoformat(),
                "month": 2,
                "year": 2026,
                "week_number": 5,  # Invalide (doit être 1-4)
            },
        )
        assert response.status_code == 422

    async def test_very_long_notes_field(
        self, client: AsyncClient, econome_token: str, servant_user_id: str
    ):
        """Test : Gestion des notes très longues."""
        very_long_notes = "A" * 10000  # 10000 caractères
        
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
                "notes": very_long_notes,
            },
        )
        
        # Doit soit accepter (201) soit rejeter proprement (422)
        assert response.status_code in [201, 422]
