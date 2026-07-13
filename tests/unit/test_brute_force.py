"""
Tests unitaires — Protection brute-force (account lockout).

Teste la facade BruteForceProtection en mode in-memory (sans Redis).
"""

import pytest

from src.infrastructure.security.brute_force import BruteForceProtection


@pytest.mark.unit
class TestBruteForceProtection:
    """Teste le mecanisme de verrouillage progressif."""

    def setup_method(self):
        """Instance fraiche pour chaque test."""
        self.guard = BruteForceProtection()

    @pytest.mark.asyncio
    async def test_first_attempt_not_locked(self):
        """Un identifiant sans echec n'est pas verrouille."""
        is_locked, remaining = await self.guard.check_locked("user@test.com")
        assert is_locked is False
        assert remaining is None

    @pytest.mark.asyncio
    async def test_single_failure_not_locked(self):
        """Un seul echec ne verrouille pas le compte."""
        locked, count, duration = await self.guard.record_failure("user@test.com")
        assert locked is False
        assert count == 1
        assert duration is None

    @pytest.mark.asyncio
    async def test_four_failures_not_locked(self):
        """4 echecs ne verrouillent pas (seuil a 5)."""
        for _ in range(4):
            await self.guard.record_failure("user@test.com")
        is_locked, _ = await self.guard.check_locked("user@test.com")
        assert is_locked is False

    @pytest.mark.asyncio
    async def test_five_failures_triggers_lockout(self):
        """5 echecs declenchent le verrouillage."""
        for i in range(5):
            locked, count, duration = await self.guard.record_failure("user@test.com")

        assert locked is True
        assert count == 5
        assert duration == 60  # 1 min au premier palier

    @pytest.mark.asyncio
    async def test_locked_account_detected(self):
        """Apres verrouillage, check_locked retourne True."""
        for _ in range(5):
            await self.guard.record_failure("user@test.com")
        is_locked, remaining = await self.guard.check_locked("user@test.com")
        assert is_locked is True
        assert remaining is not None
        assert remaining > 0

    @pytest.mark.asyncio
    async def test_ten_failures_longer_lockout(self):
        """10 echecs = verrouillage 5 min."""
        for i in range(10):
            await self.guard.record_failure("user@test.com")
        is_locked, remaining = await self.guard.check_locked("user@test.com")
        assert is_locked is True
        # Le dernier record_failure a mis locked_until a +300s

    @pytest.mark.asyncio
    async def test_success_resets_counter(self):
        """Un succes reinitialise le compteur d'echecs."""
        for _ in range(3):
            await self.guard.record_failure("user@test.com")
        await self.guard.record_success("user@test.com")

        # Apres reset, le compte n'est pas verrouille
        is_locked, _ = await self.guard.check_locked("user@test.com")
        assert is_locked is False

        # Et le compteur repart a zero
        remaining = await self.guard.get_remaining_attempts("user@test.com")
        assert remaining == 5  # Premier seuil

    @pytest.mark.asyncio
    async def test_different_identifiers_independent(self):
        """Les compteurs sont independants par identifiant."""
        for _ in range(5):
            await self.guard.record_failure("user1@test.com")
        is_locked_1, _ = await self.guard.check_locked("user1@test.com")
        is_locked_2, _ = await self.guard.check_locked("user2@test.com")
        assert is_locked_1 is True
        assert is_locked_2 is False

    @pytest.mark.asyncio
    async def test_remaining_attempts_decreases(self):
        """Les tentatives restantes diminuent a chaque echec."""
        assert await self.guard.get_remaining_attempts("u@t.com") == 5
        await self.guard.record_failure("u@t.com")
        assert await self.guard.get_remaining_attempts("u@t.com") == 4
        await self.guard.record_failure("u@t.com")
        assert await self.guard.get_remaining_attempts("u@t.com") == 3

    @pytest.mark.asyncio
    async def test_cleanup_removes_old_entries(self):
        """cleanup() sur le backend memoire supprime les entrees obsoletes."""
        await self.guard.record_failure("old@test.com")
        # Simuler une entree tres ancienne via le backend interne
        entry = self.guard._memory_backend._attempts["old@test.com"]
        entry.last_attempt = 0.0  # Epoch = tres ancien
        entry.locked_until = 0.0

        self.guard._memory_backend.cleanup(max_age=1)
        assert "old@test.com" not in self.guard._memory_backend._attempts

    @pytest.mark.asyncio
    async def test_success_on_unknown_identifier_no_error(self):
        """record_success sur un identifiant inconnu ne leve pas d'erreur."""
        await self.guard.record_success("unknown@test.com")  # Pas d'exception
