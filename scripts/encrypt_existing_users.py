"""
Script de migration des données existantes vers le chiffrement PII.

Usage (depuis la racine du backend) :
    python scripts/encrypt_existing_users.py

Ce script parcourt tous les utilisateurs dont email_hmac est NULL
(= données en clair non encore chiffrées) et les chiffre en place.

Idempotent : il peut être relancé sans risque — il ignore les lignes
déjà chiffrées (email_hmac non NULL).

Prérequis :
  - La variable FIELD_ENCRYPTION_KEY doit être présente dans .env
  - La migration 022 doit avoir été appliquée (alembic upgrade 022)
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import select

from src.core.entities.user import User
from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.field_encryption import get_encryptor


async def encrypt_all_users() -> None:
    settings = get_settings()
    enc = get_encryptor()

    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.exec(
            select(User).where(User.email_hmac == None)  # noqa: E711
        )
        users = list(result.all())

        if not users:
            print("Aucun utilisateur non chiffré trouvé. Migration déjà effectuée.")
            return

        print(f"{len(users)} utilisateur(s) à chiffrer…")
        migrated = 0

        for user in users:
            try:
                # Chiffrer les champs texte
                if user.first_name:
                    user.first_name = enc.encrypt(user.first_name)
                if user.last_name:
                    user.last_name = enc.encrypt(user.last_name)

                original_email = user.email
                if user.email:
                    user.email = enc.encrypt(user.email)
                    user.email_hmac = enc.hmac_index(original_email)

                original_phone = user.phone_number
                if user.phone_number:
                    user.phone_number = enc.encrypt(user.phone_number)
                    user.phone_hmac = enc.hmac_index(original_phone)

                # Chiffrer les dates (en ISO-8601 string)
                if user.birth_date and not isinstance(user.birth_date, str):
                    user.birth_date = enc.encrypt(user.birth_date.isoformat())
                if user.baptism_date and not isinstance(user.baptism_date, str):
                    user.baptism_date = enc.encrypt(user.baptism_date.isoformat())

                session.add(user)
                migrated += 1

            except Exception as exc:
                print(f"  Erreur utilisateur {user.id}: {exc}")

        await session.commit()
        print(f"Terminé : {migrated}/{len(users)} utilisateur(s) chiffré(s).")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(encrypt_all_users())
