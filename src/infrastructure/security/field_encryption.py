"""
Chiffrement symétrique des champs PII — AES-256-GCM.

Conformité Loi 2024/017 (Cameroun) :
  - Les champs nominatifs (nom, prénom, email, téléphone, dates de naissance
    et de baptême) sont chiffrés AVANT tout stockage sur Supabase/Contabo.
  - Un index HMAC-SHA256 déterministe est calculé pour les champs où un
    lookup exact est nécessaire (email, téléphone), permettant les requêtes
    SQL sans jamais exposer la valeur en clair au serveur.
  - La clé maître reste dans le .env du développeur (membre interne) et
    n'est jamais transmise à l'hébergeur étranger.
  - En cas de violation de la base de données, les données restent
    inintelligibles (Art. 22 al. 2 de la loi).

Format de stockage d'un champ chiffré :
    base64url( nonce[12 octets] || ciphertext_avec_tag_GCM )
"""

import base64
import hashlib
import hmac as hmac_lib
import os
from typing import Any, Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_SALT_ENC = b"servantassist-pii-enc-v1"
_SALT_HMAC = b"servantassist-pii-hmac-v1"
_KEY_LEN = 32    # AES-256
_NONCE_LEN = 12  # GCM nonce standard (96 bits)
_PBKDF2_ITER = 100_000


def _derive_aes_key(master_secret: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=_SALT_ENC,
        iterations=_PBKDF2_ITER,
    )
    return kdf.derive(master_secret.encode("utf-8"))


def _derive_hmac_key(master_secret: str) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        master_secret.encode("utf-8"),
        _SALT_HMAC,
        _PBKDF2_ITER,
    )


class FieldEncryptor:
    """
    Chiffrement/déchiffrement transparent des champs PII + index HMAC.

    Instancier une seule fois au démarrage (singleton via get_encryptor()).
    La clé AES et la clé HMAC sont dérivées une fois du secret maître.

    Exemple :
        enc = get_encryptor()
        blob = enc.encrypt("Jean NDAA")
        plain = enc.decrypt(blob)           # → "Jean NDAA"
        idx   = enc.hmac_index("699001122") # index pour lookup SQL
    """

    def __init__(self, master_secret: str) -> None:
        aes_key = _derive_aes_key(master_secret)
        self._aesgcm = AESGCM(aes_key)
        self._hmac_key = _derive_hmac_key(master_secret)

    def encrypt(self, plaintext: Optional[str]) -> Optional[str]:
        """
        Chiffre une chaîne de caractères.
        Retourne None si la valeur d'entrée est None ou vide.
        """
        if not plaintext:
            return plaintext
        nonce = os.urandom(_NONCE_LEN)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, ciphertext: Optional[str]) -> Optional[str]:
        """
        Déchiffre un blob produit par encrypt().
        Retourne None si l'entrée est None ou vide.
        Lève ValueError si le blob est invalide ou corrompu.
        """
        if not ciphertext:
            return ciphertext
        try:
            raw = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
            nonce, data = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
            return self._aesgcm.decrypt(nonce, data, None).decode("utf-8")
        except Exception as exc:
            raise ValueError(f"Déchiffrement impossible : {exc}") from exc

    def hmac_index(self, value: Optional[str]) -> Optional[str]:
        """
        Calcule un index HMAC-SHA256 déterministe pour un champ recherchable.
        La valeur est normalisée (strip + lower) avant le calcul afin que
        les lookups soient insensibles à la casse et aux espaces en début/fin.
        Retourne None si value est None ou vide.
        """
        if not value:
            return None
        normalized = value.strip().lower()
        digest = hmac_lib.new(
            self._hmac_key,
            normalized.encode("utf-8"),
            "sha256",
        ).hexdigest()
        return digest


_encryptor_instance: Optional[FieldEncryptor] = None


def decrypt_str_fields(model: Any, fields: tuple) -> None:
    """
    Déchiffre une liste de champs string sur n'importe quel modèle SQLModel.
    Utile quand un objet est chargé directement depuis la DB (sans passer
    par son repository propre) — ex : User chargé dans enrich_case().
    Les champs non chiffrés (avant migration) sont ignorés silencieusement.
    """
    enc = get_encryptor()
    for field in fields:
        val = getattr(model, field, None)
        if val:
            try:
                setattr(model, field, enc.decrypt(val))
            except (ValueError, Exception):
                pass


def get_encryptor() -> FieldEncryptor:
    """
    Retourne le singleton FieldEncryptor initialisé depuis les settings.
    Lève RuntimeError si FIELD_ENCRYPTION_KEY n'est pas configurée.
    """
    global _encryptor_instance
    if _encryptor_instance is None:
        from src.infrastructure.config.settings import get_settings
        key = get_settings().FIELD_ENCRYPTION_KEY
        if not key:
            raise RuntimeError(
                "FIELD_ENCRYPTION_KEY absente du fichier .env. "
                "Générez-en une avec : "
                "python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        _encryptor_instance = FieldEncryptor(key)
    return _encryptor_instance
