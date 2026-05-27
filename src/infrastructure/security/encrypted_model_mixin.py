"""
Mixin générique de chiffrement des champs PII pour les repositories.

Usage dans un repository :
    class MyRepository(EncryptedModelMixin):
        ENCRYPTED_FIELDS = ("first_name", "last_name", "notes")
        HMAC_INDEX_MAP   = {"email": "email_hmac", "phone": "phone_hmac"}

        async def create(self, obj):
            self._encrypt_model(obj)
            self.session.add(obj)
            await self.session.commit()
            await self.session.refresh(obj)
            self._decrypt_model(obj)
            return obj

Architecture :
  - ENCRYPTED_FIELDS  : champs dont la valeur brute est remplacée par un blob
                        AES-256-GCM encodé en base64url.
  - HMAC_INDEX_MAP    : pour les champs sur lesquels on fait des lookups SQL
                        (email, téléphone), on calcule un index HMAC-SHA256
                        déterministe AVANT de chiffrer le plaintext.  Le HMAC
                        est stocké dans la colonne nommée par la valeur du dict.
  - La clé est lue une seule fois depuis FIELD_ENCRYPTION_KEY (.env) et mise
    en cache dans get_encryptor().
"""

from typing import Any, Dict, Optional, Sequence, Tuple

from sqlalchemy.orm.attributes import set_committed_value
from sqlmodel import SQLModel

from src.infrastructure.security.field_encryption import get_encryptor


class EncryptedModelMixin:
    """
    Mixin pour les repositories ayant des champs PII à chiffrer.

    Sous-classes : déclarez ENCRYPTED_FIELDS et HMAC_INDEX_MAP.
    Appelez _encrypt_model() avant session.add() et _decrypt_model()
    après session.refresh() dans chaque méthode CRUD.
    """

    ENCRYPTED_FIELDS: Tuple[str, ...] = ()
    HMAC_INDEX_MAP: Dict[str, str] = {}

    # ── Chiffrement ────────────────────────────────────────────────────

    def _encrypt_model(self, model: Any) -> None:
        """
        Chiffre les champs PII en place et calcule les index HMAC.
        Ordre garanti : HMAC calculé sur le plaintext, PUIS chiffrement.
        """
        enc = get_encryptor()

        # 1. Calculer les index HMAC depuis le plaintext (avant de chiffrer)
        for plain_field, hmac_col in self.HMAC_INDEX_MAP.items():
            val = getattr(model, plain_field, None)
            setattr(model, hmac_col, enc.hmac_index(val))

        # 2. Chiffrer les champs
        for field in self.ENCRYPTED_FIELDS:
            val = getattr(model, field, None)
            if val is not None:
                setattr(model, field, enc.encrypt(str(val)))

    # ── Déchiffrement ──────────────────────────────────────────────────

    def _decrypt_model(self, model: Any) -> None:
        """Déchiffre les champs PII en place après lecture DB.
        Uses set_committed_value so SQLAlchemy doesn't mark the fields dirty."""
        enc = get_encryptor()
        for field in self.ENCRYPTED_FIELDS:
            val = getattr(model, field, None)
            if val:
                try:
                    decrypted = enc.decrypt(val)
                except (ValueError, Exception):
                    continue  # Donnée non chiffrée (avant migration) : laisser tel quel
                try:
                    set_committed_value(model, field, decrypted)
                except Exception:
                    setattr(model, field, decrypted)  # Fallback pour les objets non-SA

    def _decrypt_list(self, models: Sequence[Any]) -> None:
        """Déchiffre tous les modèles d'une liste en place."""
        for model in models:
            self._decrypt_model(model)
