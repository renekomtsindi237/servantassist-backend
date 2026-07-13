"""
Outil local de déchiffrement des données PII stockées sur le serveur.

Utilisation :
  # Déchiffrer une valeur unique
  python scripts/decrypt_tool.py "gAAAAAB..."

  # Déchiffrer plusieurs valeurs (une par ligne depuis stdin)
  echo "gAAAAAB..." | python scripts/decrypt_tool.py -

  # Inspecter un utilisateur directement depuis la DB (nécessite psql ou Python DB driver)
  python scripts/decrypt_tool.py --user <email_en_clair>

La clé est lue depuis :
  1. La variable d'environnement FIELD_ENCRYPTION_KEY
  2. Le fichier .env (ou .env.staging, .env.local) du répertoire courant

SÉCURITÉ : Ce script ne doit jamais être exécuté sur le serveur de production.
           La clé de déchiffrement ne doit jamais quitter votre poste local.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


# ── Lecture de la clé ──────────────────────────────────────────────────────────

def _load_key() -> str:
    # 1. Variable d'environnement
    key = os.environ.get("FIELD_ENCRYPTION_KEY", "")
    if key:
        return key

    # 2. Fichiers .env dans l'ordre de priorité
    candidates = [".env", ".env.local", ".env.staging", ".env.development"]
    for name in candidates:
        path = Path(name)
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("FIELD_ENCRYPTION_KEY="):
                    value = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if value:
                        return value

    raise SystemExit(
        "ERREUR : FIELD_ENCRYPTION_KEY introuvable.\n"
        "Définissez-la via la variable d'environnement ou dans un fichier .env local."
    )


# ── Chiffrement / déchiffrement (même logique que field_encryption.py) ─────────

def _make_encryptor(master_secret: str):
    import base64
    import hashlib
    import hmac as hmac_lib
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

    _SALT_ENC = b"servantassist-pii-enc-v1"
    _SALT_HMAC = b"servantassist-pii-hmac-v1"
    _KEY_LEN = 32
    _NONCE_LEN = 12
    _PBKDF2_ITER = 100_000

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=_KEY_LEN,
        salt=_SALT_ENC,
        iterations=_PBKDF2_ITER,
    )
    aes_key = kdf.derive(master_secret.encode("utf-8"))
    aesgcm = AESGCM(aes_key)

    hmac_key = hashlib.pbkdf2_hmac(
        "sha256",
        master_secret.encode("utf-8"),
        _SALT_HMAC,
        _PBKDF2_ITER,
    )

    def decrypt(blob: str) -> str:
        raw = base64.urlsafe_b64decode(blob.encode("ascii"))
        nonce, data = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
        return aesgcm.decrypt(nonce, data, None).decode("utf-8")

    def hmac_index(value: str) -> str:
        normalized = value.strip().lower()
        return hmac_lib.new(hmac_key, normalized.encode("utf-8"), "sha256").hexdigest()

    return decrypt, hmac_index


# ── Mode DB : requête directe via SQLAlchemy ────────────────────────────────────

def _query_user(email_plain: str, decrypt, hmac_index):
    """Cherche un utilisateur par email en clair et affiche ses champs déchiffrés."""
    try:
        from sqlalchemy import create_engine, text
    except ImportError:
        raise SystemExit("Installez sqlalchemy : pip install sqlalchemy psycopg2-binary")

    # Lire DATABASE_URL depuis .env
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        for name in [".env", ".env.local", ".env.staging"]:
            path = Path(name)
            if path.exists():
                for line in path.read_text().splitlines():
                    if line.startswith("DATABASE_URL="):
                        db_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            if db_url:
                break

    if not db_url:
        raise SystemExit("DATABASE_URL introuvable. Définissez-la dans .env ou en variable d'environnement.")

    idx = hmac_index(email_plain)
    engine = create_engine(db_url)
    with engine.connect() as conn:
        row = conn.execute(
            text('SELECT id, email, first_name, last_name, role, position, is_active, phone_number FROM "user" WHERE email_hmac = :idx'),
            {"idx": idx},
        ).fetchone()

    if row is None:
        print(f"Aucun utilisateur trouvé pour : {email_plain}")
        return

    fields = ["id", "email", "first_name", "last_name", "role", "position", "is_active", "phone_number"]
    encrypted_fields = {"email", "first_name", "last_name", "phone_number"}

    print(f"\n{'─' * 50}")
    print(f"Utilisateur — HMAC index : {idx[:16]}…")
    print(f"{'─' * 50}")
    for field, value in zip(fields, row):
        if field in encrypted_fields and value:
            try:
                value = decrypt(value)
            except Exception:
                value = f"[déchiffrement échoué] {value}"
        print(f"  {field:<15} : {value}")
    print(f"{'─' * 50}\n")


# ── Point d'entrée ──────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Déchiffre des valeurs PII chiffrées avec la clé FIELD_ENCRYPTION_KEY locale."
    )
    parser.add_argument(
        "blobs",
        nargs="*",
        help="Valeurs chiffrées à déchiffrer (base64url). Utilisez '-' pour lire depuis stdin.",
    )
    parser.add_argument(
        "--user",
        metavar="EMAIL",
        help="Inspecte un utilisateur par email en clair (requiert DATABASE_URL).",
    )
    parser.add_argument(
        "--hmac",
        metavar="VALUE",
        help="Calcule l'index HMAC d'une valeur (utile pour les requêtes SQL).",
    )
    args = parser.parse_args()

    key = _load_key()
    decrypt, hmac_index = _make_encryptor(key)
    print(f"Clé chargée — {len(key)} caractères\n")

    if args.hmac:
        idx = hmac_index(args.hmac)
        print(f"HMAC-SHA256 de '{args.hmac}' : {idx}")
        return

    if args.user:
        _query_user(args.user, decrypt, hmac_index)
        return

    blobs = args.blobs
    if not blobs:
        parser.print_help()
        return

    # Lecture depuis stdin si '-'
    if blobs == ["-"]:
        blobs = [line.strip() for line in sys.stdin if line.strip()]

    for blob in blobs:
        try:
            plain = decrypt(blob)
            print(f"  {blob[:24]}…  →  {plain}")
        except Exception as exc:
            print(f"  {blob[:24]}…  →  ERREUR: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
