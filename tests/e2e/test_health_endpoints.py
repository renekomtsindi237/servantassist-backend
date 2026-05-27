"""
Tests e2e — endpoints système : /health, /ready, /api/v1/version, /.

Ces tests démarrent la vraie stack FastAPI (ASGI) avec SQLite en mémoire
pour vérifier que l'application répond correctement aux sondes d'infrastructure
et expose les bons en-têtes de versioning.
"""
import pytest
from httpx import AsyncClient


# ═══════════════════════════════════════════════════════════════════════════
#  Endpoint racine  GET /
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
class TestRootEndpoint:

    async def test_root_returns_200(self, main_client: AsyncClient):
        response = await main_client.get("/")
        assert response.status_code == 200

    async def test_root_contains_api_name(self, main_client: AsyncClient):
        body = (await main_client.get("/")).json()
        assert "ServantAssist" in body.get("name", "")

    async def test_root_contains_health_link(self, main_client: AsyncClient):
        body = (await main_client.get("/")).json()
        assert "health" in body

    async def test_root_contains_version_link(self, main_client: AsyncClient):
        body = (await main_client.get("/")).json()
        assert "api_version" in body or "version" in body


# ═══════════════════════════════════════════════════════════════════════════
#  Readiness probe  GET /ready
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
class TestReadinessProbe:

    async def test_ready_returns_200_with_sqlite(self, main_client: AsyncClient):
        response = await main_client.get("/ready")
        assert response.status_code == 200

    async def test_ready_body_has_status_ready(self, main_client: AsyncClient):
        body = (await main_client.get("/ready")).json()
        assert body.get("status") == "ready"


# ═══════════════════════════════════════════════════════════════════════════
#  Health check  GET /health
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
class TestHealthCheck:

    async def test_health_returns_200_or_degraded(self, main_client: AsyncClient):
        response = await main_client.get("/health")
        # 200 = healthy/degraded (Redis absent en test = dégradé mais pas unhealthy)
        assert response.status_code == 200

    async def test_health_body_has_status(self, main_client: AsyncClient):
        body = (await main_client.get("/health")).json()
        assert "status" in body
        assert body["status"] in ("healthy", "degraded", "unhealthy")

    async def test_health_body_has_checks(self, main_client: AsyncClient):
        body = (await main_client.get("/health")).json()
        assert "checks" in body

    async def test_health_database_check_ok(self, main_client: AsyncClient):
        body = (await main_client.get("/health")).json()
        assert body["checks"].get("database", {}).get("status") == "ok"

    async def test_health_body_has_version(self, main_client: AsyncClient):
        body = (await main_client.get("/health")).json()
        assert "version" in body

    async def test_health_body_has_timestamp(self, main_client: AsyncClient):
        body = (await main_client.get("/health")).json()
        assert "timestamp" in body

    async def test_health_body_has_environment(self, main_client: AsyncClient):
        body = (await main_client.get("/health")).json()
        assert "environment" in body


# ═══════════════════════════════════════════════════════════════════════════
#  Version API  GET /api/v1/version
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
class TestApiVersion:

    async def test_version_returns_200(self, main_client: AsyncClient):
        response = await main_client.get("/api/v1/version")
        assert response.status_code == 200

    async def test_version_has_version_field(self, main_client: AsyncClient):
        body = (await main_client.get("/api/v1/version")).json()
        assert "version" in body
        # Doit ressembler à un semver X.Y.Z
        parts = body["version"].split(".")
        assert len(parts) == 3

    async def test_version_has_release_date(self, main_client: AsyncClient):
        body = (await main_client.get("/api/v1/version")).json()
        assert "release_date" in body

    async def test_version_has_environment(self, main_client: AsyncClient):
        body = (await main_client.get("/api/v1/version")).json()
        assert body.get("environment") == "testing"

    async def test_version_has_min_client_version(self, main_client: AsyncClient):
        body = (await main_client.get("/api/v1/version")).json()
        assert "min_client_version" in body

    async def test_version_has_deprecations_list(self, main_client: AsyncClient):
        body = (await main_client.get("/api/v1/version")).json()
        assert isinstance(body.get("deprecations"), list)


# ═══════════════════════════════════════════════════════════════════════════
#  Versioning middleware — en-têtes X-API-Version et X-Request-ID
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
class TestVersioningHeaders:

    async def test_every_response_has_x_api_version(self, main_client: AsyncClient):
        response = await main_client.get("/api/v1/version")
        assert "x-api-version" in response.headers

    async def test_x_request_id_generated_when_absent(self, main_client: AsyncClient):
        response = await main_client.get("/")
        assert "x-request-id" in response.headers
        assert len(response.headers["x-request-id"]) > 0

    async def test_x_request_id_propagated_when_provided(self, main_client: AsyncClient):
        my_id = "test-trace-id-abc123"
        response = await main_client.get("/", headers={"X-Request-ID": my_id})
        assert response.headers.get("x-request-id") == my_id

    async def test_x_api_version_is_semver(self, main_client: AsyncClient):
        response = await main_client.get("/")
        version = response.headers.get("x-api-version", "")
        parts = version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)


# ═══════════════════════════════════════════════════════════════════════════
#  Protection des routes — authentification requise
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.e2e
class TestAuthProtection:

    async def test_users_list_requires_auth(self, main_client: AsyncClient):
        # FastAPI peut répondre 307 (redirect trailing-slash) puis 401 en suivant
        response = await main_client.get("/api/v1/users/", follow_redirects=True)
        assert response.status_code == 401

    async def test_discipline_requires_auth(self, main_client: AsyncClient):
        response = await main_client.get("/api/v1/discipline/", follow_redirects=True)
        assert response.status_code == 401

    async def test_events_list_requires_auth(self, main_client: AsyncClient):
        response = await main_client.get("/api/v1/events/", follow_redirects=True)
        assert response.status_code == 401
