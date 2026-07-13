"""
Script de migration des codes d'invitation existants vers le chiffrement PII.

Usage (depuis la racine du backend) :
    python scripts/encrypt_existing_invitations.py

Ce script parcourt tous les codes d'invitation dont email_hmac est NULL
(= données en clair non encore chiffrées) et les chiffre en place.

Idempotent : il peut être relancé sans risque — il ignore les lignes
déjà chiffrées (email_hmac non NULL).

Prérequis :
  - La variable FIELD_ENCRYPTION_KEY doit être présente dans .env
  - La migration 023 doit avoir été appliquée (alembic upgrade 023)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from src.core.entities.invitation import InvitationCode
from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.field_encryption import get_encryptor


async def encrypt_all_invitations() -> None:
    settings = get_settings()
    enc = get_encryptor()

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.exec(
            select(InvitationCode).where(InvitationCode.email_hmac == None)  # noqa: E711
        )
        invitations = list(result.all())

        if not invitations:
            print("Aucun code d'invitation non chiffré trouvé. Migration déjà effectuée.")
            return

        print(f"{len(invitations)} code(s) d'invitation à chiffrer…")
        migrated = 0

        for inv in invitations:
            try:
                original_email = inv.email
                if inv.email:
                    inv.email = enc.encrypt(inv.email)
                    inv.email_hmac = enc.hmac_index(original_email)

                original_phone = inv.phone_number
                if inv.phone_number:
                    inv.phone_number = enc.encrypt(inv.phone_number)
                    inv.phone_hmac = enc.hmac_index(original_phone)

                session.add(inv)
                migrated += 1

            except Exception as exc:
                print(f"  Erreur invitation {inv.id}: {exc}")

        await session.commit()
        print(f"Terminé : {migrated}/{len(invitations)} code(s) chiffré(s).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(encrypt_all_invitations())
