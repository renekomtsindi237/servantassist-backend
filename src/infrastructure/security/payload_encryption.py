"""
Chiffrement de charge utile — ECDH éphémère P-256 + AES-256-GCM + HKDF.

Conformité Loi 2024/017 (Cameroun) — Art. 22 al. 2 :
  Protection des données personnelles en transit entre les clients
  (application mobile, interface web) et le serveur API ServantAssist.

Schéma :
  1. Le serveur possède une paire de clés EC SECP256R1 longue durée.
     → Clé privée : PAYLOAD_ENCRYPTION_PRIVATE_KEY (.env, jamais transmise)
     → Clé publique : exposée via GET /api/v1/auth/server-pubkey

  2. Pour chaque requête sensible, le client :
     a) Génère une paire de clés éphémère EC SECP256R1
     b) Calcule ECDH(server_pub, eph_priv) → secret partagé
     c) Dérive une clé de session AES-256 via HKDF(shared, info="ServantAssist-payload-v1")
     d) Chiffre le corps avec AES-256-GCM (nonce 12 octets aléatoires)
     e) Envoie le corps chiffré + sa clé éphémère publique (header X-Client-Pubkey)

  3. Le serveur :
     a) Lit X-Client-Pubkey (point EC non-compressé, 65 octets, base64url)
     b) Calcule ECDH(server_priv, client_eph_pub) → même secret partagé
     c) Dérive la même clé de session via HKDF
     d) Déchiffre le corps → transmet en clair au handler de route

Propriétés de sécurité :
  - Perfect Forward Secrecy (PFS) : chaque requête a une clé unique
  - Authentification du serveur : seul le serveur possède la clé privée
  - Intégrité : GCM tag 128 bits — toute altération est détectée

Format du corps chiffré :
    JSON { "v": 1, "iv": "<base64url-12-octets>", "ct": "<base64url-ct+tag>" }

Header de requête :
    X-Client-Pubkey: <base64url-65-octets-point-non-compressé>
"""

import base64
import json
import os

from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDH,
    SECP256R1,
    EllipticCurvePublicNumbers,
    generate_private_key,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
    load_pem_private_key,
)

_NONCE_LEN = 12  # GCM nonce (96 bits)
_KEY_LEN = 32  # AES-256
_HKDF_INFO = b"ServantAssist-payload-v1"
_EC_PUBKEY_LEN = 65  # point non-compressé (0x04 || X 32B || Y 32B)
_PAYLOAD_VERSION = 1


# ── Helpers EC ───────────────────────────────────────────────────────────────


def _raw_bytes_to_ec_pubkey(raw: bytes):
    """Convertit 65 octets (point non-compressé) en EllipticCurvePublicKey."""
    if len(raw) != _EC_PUBKEY_LEN or raw[0] != 0x04:
        raise ValueError(
            f"Clé publique invalide : attendu {_EC_PUBKEY_LEN} octets commençant par 0x04, "
            f"reçu {len(raw)} octets commençant par 0x{raw[0]:02X}"
        )
    x = int.from_bytes(raw[1:33], "big")
    y = int.from_bytes(raw[33:65], "big")
    return EllipticCurvePublicNumbers(x=x, y=y, curve=SECP256R1()).public_key()


def _ec_pubkey_to_raw_bytes(pub_key) -> bytes:
    """Sérialise une clé publique EC en 65 octets (point non-compressé)."""
    return pub_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)


# ── Dérivation de clé de session ─────────────────────────────────────────────


def _derive_session_key(shared_secret: bytes) -> bytes:
    """HKDF-SHA256(shared_secret, info) → 32 octets AES-256."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=None,
        info=_HKDF_INFO,
    )
    return hkdf.derive(shared_secret)


# ── Classe principale ─────────────────────────────────────────────────────────


class PayloadEncryptor:
    """
    Singleton côté serveur.

    - Charge la clé privée EC depuis les settings au premier accès.
    - Expose la clé publique en base64url pour distribution aux clients.
    - Déchiffre les corps de requête des clients.
    """

    def __init__(self, private_key_b64_pem: str) -> None:
        """
        :param private_key_b64_pem: Clé privée PEM encodée en base64
                                    (valeur de PAYLOAD_ENCRYPTION_PRIVATE_KEY)
        """
        pem = base64.b64decode(private_key_b64_pem.encode("ascii"))
        self._private_key = load_pem_private_key(pem, password=None)
        # Pré-calcul de la clé publique sérialisée
        self._public_key_raw = _ec_pubkey_to_raw_bytes(self._private_key.public_key())
        self._public_key_b64 = base64.urlsafe_b64encode(self._public_key_raw).decode(
            "ascii"
        )

    # ── API publique ──────────────────────────────────────────────────────────

    @property
    def public_key_b64(self) -> str:
        """Clé publique en base64url — à distribuer aux clients."""
        return self._public_key_b64

    def decrypt_request(self, client_pub_b64: str, encrypted_body: bytes) -> bytes:
        """
        Déchiffre un corps de requête chiffré par le client.

        :param client_pub_b64: Header X-Client-Pubkey (base64url, 65 octets)
        :param encrypted_body: Corps JSON {"v":1,"iv":"...","ct":"..."}
        :returns: Corps en clair (bytes JSON originaux)
        :raises ValueError: Si le format, la version ou le tag GCM est invalide
        """
        # Décode la clé publique éphémère du client
        try:
            client_pub_raw = base64.urlsafe_b64decode(
                client_pub_b64.encode("ascii") + b"=="  # pad tolérant
            )
            client_pub_key = _raw_bytes_to_ec_pubkey(client_pub_raw)
        except Exception as exc:
            raise ValueError(f"X-Client-Pubkey invalide : {exc}") from exc

        # ECDH → secret partagé → clé de session
        shared = self._private_key.exchange(ECDH(), client_pub_key)
        session_key = _derive_session_key(shared)

        # Parse le corps JSON chiffré
        try:
            payload = json.loads(encrypted_body)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Corps chiffré JSON invalide : {exc}") from exc

        if payload.get("v") != _PAYLOAD_VERSION:
            raise ValueError(
                f"Version de chiffrement non supportée : {payload.get('v')} "
                f"(attendu {_PAYLOAD_VERSION})"
            )

        try:
            iv = base64.urlsafe_b64decode(payload["iv"].encode("ascii") + b"==")
            ct = base64.urlsafe_b64decode(payload["ct"].encode("ascii") + b"==")
        except (KeyError, Exception) as exc:
            raise ValueError(f"Champs iv/ct manquants ou invalides : {exc}") from exc

        # Déchiffrement AES-256-GCM
        try:
            aesgcm = AESGCM(session_key)
            plaintext = aesgcm.decrypt(iv, ct, None)
        except Exception as exc:
            raise ValueError(
                f"Déchiffrement GCM échoué (tag invalide ?) : {exc}"
            ) from exc

        return plaintext


# ── Singleton ─────────────────────────────────────────────────────────────────

_encryptor_instance: PayloadEncryptor | None = None


def get_payload_encryptor() -> PayloadEncryptor:
    """
    Retourne le singleton PayloadEncryptor.
    Lève RuntimeError si PAYLOAD_ENCRYPTION_PRIVATE_KEY est absente.
    """
    global _encryptor_instance
    if _encryptor_instance is None:
        from src.infrastructure.config.settings import get_settings

        key = get_settings().PAYLOAD_ENCRYPTION_PRIVATE_KEY
        if not key:
            raise RuntimeError(
                "PAYLOAD_ENCRYPTION_PRIVATE_KEY absente du fichier .env. "
                "Générez une paire avec : python scripts/generate_ec_keypair.py"
            )
        _encryptor_instance = PayloadEncryptor(key)
    return _encryptor_instance
