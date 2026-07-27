"""
Tests de performance — temps de réponse et charge concurrente.
"""

import asyncio
import time

import pytest
from httpx import AsyncClient
from sqlmodel import select

from src.core.entities.phone_verification_code import PhoneVerificationCode
from src.infrastructure.security.field_encryption import get_encryptor
from tests.conftest import VALID_PASSWORD, make_auth_header

# ═══════════════════════════════════════════════════════════════════════════
#  TEMPS DE RÉPONSE — ENDPOINTS INDIVIDUELS
# ═══════════════════════════════════════════════════════════════════════════
MAX_RESPONSE_TIME_MS = 800  # Seuil max acceptable pour l'env de test (ms)


async def _verify_phone(client: AsyncClient, db_session, phone_number: str) -> str:
    """Miroir de `_verify_phone` (tests/e2e/test_auth_endpoints.py) — l'inscription
    publique exige un `phone_verification_token` depuis l'ajout de la vérification
    téléphone à `POST /auth/register`."""
    resp = await client.post("/api/v1/auth/register/send-phone-code", json={"phone_number": phone_number})
    assert resp.status_code == 200

    phone_hmac = get_encryptor().hmac_index(phone_number)
    result = await db_session.exec(select(PhoneVerificationCode).where(PhoneVerificationCode.phone_hmac == phone_hmac))
    entry = result.first()
    assert entry is not None, "Code de vérification non trouvé en base"

    resp = await client.post(
        "/api/v1/auth/register/verify-phone-code",
        json={"phone_number": phone_number, "code": entry.code},
    )
    assert resp.status_code == 200
    return resp.json()["verification_token"]


@pytest.mark.performance
class TestResponseTime:
    async def test_login_email_response_time(self, client: AsyncClient, admin_user):
        start = time.perf_counter()
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": VALID_PASSWORD},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert (
            elapsed_ms < MAX_RESPONSE_TIME_MS
        ), f"Login email trop lent : {elapsed_ms:.0f}ms > {MAX_RESPONSE_TIME_MS}ms"

    async def test_login_phone_response_time(self, client: AsyncClient, servant_user):
        start = time.perf_counter()
        resp = await client.post(
            "/api/v1/auth/login/phone",
            json={
                "phone_number": servant_user.phone_number,
                "password": VALID_PASSWORD,
            },
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert (
            elapsed_ms < MAX_RESPONSE_TIME_MS
        ), f"Login phone trop lent : {elapsed_ms:.0f}ms > {MAX_RESPONSE_TIME_MS}ms"

    async def test_register_response_time(self, client: AsyncClient, db_session):
        phone = "+237600000100"
        token = await _verify_phone(client, db_session, phone)

        start = time.perf_counter()
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "perftest@test.com",
                "password": "TestPass1",
                "first_name": "Perf",
                "last_name": "Test",
                "phone_number": phone,
                "role": "SERVANT",
                "phone_verification_token": token,
            },
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 201
        assert elapsed_ms < MAX_RESPONSE_TIME_MS, f"Register trop lent : {elapsed_ms:.0f}ms > {MAX_RESPONSE_TIME_MS}ms"

    async def test_refresh_token_response_time(self, client: AsyncClient, admin_user):
        # Obtenir un refresh token
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": VALID_PASSWORD},
        )
        refresh_token = login.json()["refresh_token"]

        start = time.perf_counter()
        resp = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert elapsed_ms < MAX_RESPONSE_TIME_MS, f"Refresh trop lent : {elapsed_ms:.0f}ms > {MAX_RESPONSE_TIME_MS}ms"

    async def test_admin_list_invitations_response_time(self, client: AsyncClient, admin_user, valid_invitation):
        start = time.perf_counter()
        resp = await client.get(
            "/api/v1/admin/invitations",
            headers=make_auth_header(admin_user),
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert (
            elapsed_ms < MAX_RESPONSE_TIME_MS
        ), f"List invitations trop lent : {elapsed_ms:.0f}ms > {MAX_RESPONSE_TIME_MS}ms"


# ═══════════════════════════════════════════════════════════════════════════
#  CHARGE CONCURRENTE
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.performance
class TestConcurrentLoad:
    async def test_concurrent_logins(self, client: AsyncClient, admin_user):
        """10 logins simultanés ne doivent pas échouer."""
        CONCURRENT = 10

        async def _login():
            return await client.post(
                "/api/v1/auth/login",
                data={"username": admin_user.email, "password": VALID_PASSWORD},
            )

        start = time.perf_counter()
        results = await asyncio.gather(*[_login() for _ in range(CONCURRENT)])
        total_ms = (time.perf_counter() - start) * 1000

        success = [r for r in results if r.status_code == 200]
        assert len(success) == CONCURRENT, f"Seulement {len(success)}/{CONCURRENT} logins réussis"
        avg_ms = total_ms / CONCURRENT
        assert (
            avg_ms < MAX_RESPONSE_TIME_MS
        ), f"Moyenne par login concurrent : {avg_ms:.0f}ms > {MAX_RESPONSE_TIME_MS}ms"

    async def test_sequential_registrations_throughput(self, client: AsyncClient, db_session):
        """10 inscriptions séquentielles — mesure le débit.

        Note : les requêtes concurrentes sur la même session SQLAlchemy de test
        causent des conflits d'état. En production, chaque requête a sa propre session.
        On teste donc le débit séquentiel ici.
        """
        COUNT = 10
        phones = [f"+23761{i:06d}" for i in range(COUNT)]
        tokens = [await _verify_phone(client, db_session, phone) for phone in phones]

        start = time.perf_counter()

        for i in range(COUNT):
            resp = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": f"sequential{i}@test.com",
                    "password": "TestPass1",
                    "first_name": f"User{i}",
                    "last_name": "Sequential",
                    "phone_number": phones[i],
                    "role": "SERVANT",
                    "phone_verification_token": tokens[i],
                },
            )
            assert resp.status_code == 201, f"Registration {i} failed: {resp.status_code}"

        total_ms = (time.perf_counter() - start) * 1000
        avg_ms = total_ms / COUNT
        assert avg_ms < MAX_RESPONSE_TIME_MS, f"Moyenne par inscription : {avg_ms:.0f}ms > {MAX_RESPONSE_TIME_MS}ms"

    async def test_concurrent_token_refresh(self, client: AsyncClient, admin_user):
        """10 refresh simultanés avec le même refresh token."""
        login = await client.post(
            "/api/v1/auth/login",
            data={"username": admin_user.email, "password": VALID_PASSWORD},
        )
        refresh_token = login.json()["refresh_token"]

        CONCURRENT = 10

        async def _refresh():
            return await client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": refresh_token},
            )

        results = await asyncio.gather(*[_refresh() for _ in range(CONCURRENT)])
        success = [r for r in results if r.status_code == 200]
        assert len(success) == CONCURRENT

    async def test_failed_login_doesnt_crash(self, client: AsyncClient):
        """20 logins échoués simultanés — l'API ne doit pas planter."""
        CONCURRENT = 20

        async def _bad_login(i: int):
            return await client.post(
                "/api/v1/auth/login",
                data={"username": f"nonexist{i}@test.com", "password": "wrong"},
            )

        results = await asyncio.gather(*[_bad_login(i) for i in range(CONCURRENT)])
        errors_401 = [r for r in results if r.status_code == 401]
        assert len(errors_401) == CONCURRENT, "Tous les logins échoués doivent retourner 401"


# ═══════════════════════════════════════════════════════════════════════════
#  THROUGHPUT — Nombre d'opérations en temps limité
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.performance
class TestThroughput:
    async def test_login_throughput(self, client: AsyncClient, admin_user):
        """Mesure le nombre de logins possibles en 2 secondes."""
        count = 0
        deadline = time.perf_counter() + 2.0

        while time.perf_counter() < deadline:
            resp = await client.post(
                "/api/v1/auth/login",
                data={"username": admin_user.email, "password": VALID_PASSWORD},
            )
            if resp.status_code == 200:
                count += 1

        # Au minimum 3 logins en 2s (conservateur pour env de test async)
        assert count >= 3, f"Seulement {count} logins en 2s — trop lent"
