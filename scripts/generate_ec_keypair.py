#!/usr/bin/env python3
"""
Génère la paire de clés EC P-256 pour le chiffrement de charge utile ServantAssist.

Conformité Loi 2024/017 (Cameroun) — chiffrement ECDH éphémère + AES-256-GCM
des corps de requête HTTP entre les clients (mobile, web) et le serveur.

Usage :
    python scripts/generate_ec_keypair.py

Sortie :
    - Clé privée PEM  → variable .env  PAYLOAD_ENCRYPTION_PRIVATE_KEY
    - Clé publique (base64url, 65 octets non-compressés)
        → Flutter  --dart-define=SERVER_PAYLOAD_PUBKEY=<valeur>
        → Angular  environment.ts  serverPayloadPubkey: '<valeur>'
"""
import base64
import textwrap

from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, generate_private_key
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def main() -> None:
    private_key = generate_private_key(SECP256R1())

    # ── Clé privée (PEM PKCS#8) ──────────────────────────────────────────────
    priv_pem = private_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.PKCS8,
        NoEncryption(),
    ).decode("utf-8")

    # ── Clé publique — point non-compressé (0x04 || X || Y), 65 octets ───────
    pub_raw = private_key.public_key().public_bytes(
        Encoding.X962,
        PublicFormat.UncompressedPoint,
    )
    pub_b64 = base64.urlsafe_b64encode(pub_raw).decode("ascii")

    # ── Affichage ─────────────────────────────────────────────────────────────
    sep = "=" * 70

    print(f"\n{sep}")
    print("  CLÉS GÉNÉRÉES — GARDER EN LIEU SÛR, NE JAMAIS COMMITTER")
    print(f"{sep}\n")

    print("1. CLEF PRIVÉE — ajouter dans .env (sur une seule ligne) :")
    print("-" * 50)
    # Encode la clé PEM sur une ligne pour le fichier .env
    pem_b64 = base64.b64encode(priv_pem.encode()).decode()
    print(f'PAYLOAD_ENCRYPTION_PRIVATE_KEY="{pem_b64}"')

    print()
    print("2. CLEF PUBLIQUE — distribuer aux clients :")
    print("-" * 50)
    print(f"  Longueur : {len(pub_raw)} octets -> {len(pub_b64)} caracteres base64url\n")

    print("  Flutter (dart-define au build) :")
    print(f'    --dart-define=SERVER_PAYLOAD_PUBKEY="{pub_b64}"')
    print()
    print("  Angular (src/environments/environment.ts) :")
    print(f'    serverPayloadPubkey: "{pub_b64}",')
    print()

    print(f"{sep}")
    print("  RAPPEL SÉCURITÉ")
    print(f"{sep}")
    print("  - La clé PRIVÉE ne doit JAMAIS quitter le serveur.")
    print("  - La clé PUBLIQUE est intégrée dans les binaires clients (normal).")
    print("  - En cas de compromission, regénérez une nouvelle paire et redéployez.")
    print(f"{sep}\n")


if __name__ == "__main__":
    main()
