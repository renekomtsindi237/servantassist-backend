"""
Service de gestion des API Keys.

Génère des clés sécurisées (préfixe + secret), stocke uniquement le hash.
"""
import secrets
from typing import List, Optional, Tuple
from uuid import UUID

from fastapi import HTTPException, status

from src.core.entities.api_key import ApiKey
from src.core.interfaces.repositories import IApiKeyRepository
from src.infrastructure.security.utils import SecurityUtils

_PREFIX = "sa_"   # ServantAssist prefix
_KEY_BYTES = 32   # 256 bits d'entropie


class ApiKeyService:
    def __init__(self, repo: IApiKeyRepository) -> None:
        self.repo = repo

    def _generate_raw_key(self) -> str:
        """Génère une clé brute : préfixe + secret hex."""
        return _PREFIX + secrets.token_hex(_KEY_BYTES)

    async def create_key(
        self,
        user_id: UUID,
        name: str,
        scopes: Optional[List[str]] = None,
    ) -> Tuple[ApiKey, str]:
        """
        Crée une nouvelle API Key.

        Returns:
            (ApiKey sauvegardée, clé brute en clair) — la clé brute ne doit
            être transmise qu'une seule fois et jamais stockée côté serveur.
        """
        raw_key = self._generate_raw_key()
        key_hash = SecurityUtils.get_password_hash(raw_key)

        api_key = ApiKey(
            name=name,
            key_hash=key_hash,
            user_id=user_id,
            scopes=scopes or [],
            is_active=True,
        )
        saved = await self.repo.create(api_key)
        return saved, raw_key

    async def verify_key(self, raw_key: str) -> Optional[ApiKey]:
        """Vérifie une clé brute et retourne l'entité si valide et active."""
        if not raw_key.startswith(_PREFIX):
            return None

        all_keys = await self.repo.list_all(limit=1000)
        for key in all_keys:
            if not key.is_active:
                continue
            if SecurityUtils.verify_password(raw_key, key.key_hash):
                await self.repo.touch(key.id)
                return key
        return None

    async def list_user_keys(self, user_id: UUID) -> List[ApiKey]:
        return await self.repo.get_by_user(user_id)

    async def list_all_keys(self, limit: int = 50, offset: int = 0) -> List[ApiKey]:
        return await self.repo.list_all(limit=limit, offset=offset)

    async def revoke_key(self, key_id: UUID, requester_id: UUID, is_admin: bool) -> ApiKey:
        key = await self.repo.get_by_id(key_id)
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clé introuvable")
        if not is_admin and key.user_id != requester_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
        revoked = await self.repo.revoke(key_id)
        return revoked

    async def delete_key(self, key_id: UUID, requester_id: UUID, is_admin: bool) -> None:
        key = await self.repo.get_by_id(key_id)
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Clé introuvable")
        if not is_admin and key.user_id != requester_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé")
        await self.repo.delete(key_id)
