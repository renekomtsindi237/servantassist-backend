"""
Script d'initialisation de l'administrateur principal.

Crée ou met à jour le compte ADMIN en base de données.

Utilisation :
  python scripts/init_db.py

Les credentials peuvent être surchargés via variables d'environnement :
  ADMIN_EMAIL=... ADMIN_PASSWORD=... ADMIN_FIRST_NAME=... ADMIN_LAST_NAME=... python scripts/init_db.py
"""
import asyncio
import os
import sys

# Add src to path
sys.path.append(".")

from sqlmodel import select

from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import sessionmanager
from src.infrastructure.security.field_encryption import get_encryptor
from src.infrastructure.security.utils import SecurityUtils

# Credentials par défaut — surchargeable via env vars
_DEFAULT_EMAIL = "renekomtsindi7@gmail.com"
_DEFAULT_PASSWORD = "Mbetoumou olive77"
_DEFAULT_FIRST_NAME = "René"
_DEFAULT_LAST_NAME = "Komtsindi"


async def init_db():
    print("ServantAssist — Initialisation de la base de données")
    print("=" * 50)

    admin_email = os.environ.get("ADMIN_EMAIL", _DEFAULT_EMAIL)
    admin_password = os.environ.get("ADMIN_PASSWORD", _DEFAULT_PASSWORD)
    admin_first_name = os.environ.get("ADMIN_FIRST_NAME", _DEFAULT_FIRST_NAME)
    admin_last_name = os.environ.get("ADMIN_LAST_NAME", _DEFAULT_LAST_NAME)

    print(f"Email admin  : {admin_email}")
    print(f"Prénom/Nom   : {admin_first_name} {admin_last_name}")
    print()

    enc = get_encryptor()
    email_hmac = enc.hmac_index(admin_email)
    encrypted_email = enc.encrypt(admin_email)
    encrypted_first = enc.encrypt(admin_first_name)
    encrypted_last = enc.encrypt(admin_last_name)
    hashed_pw = SecurityUtils.get_password_hash(admin_password)

    async with sessionmanager.connect() as session:
        stmt = select(User).where(User.role == UserRole.ADMIN)
        result = await session.exec(stmt)
        admin_user = result.first()

        if not admin_user:
            print("Création du compte ADMIN...")
            admin = User(
                email=encrypted_email,
                email_hmac=email_hmac,
                hashed_password=hashed_pw,
                first_name=encrypted_first,
                last_name=encrypted_last,
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            print(f"✓ Admin créé : {admin_email}")
        else:
            print("Mise à jour du compte ADMIN existant...")
            admin_user.email = encrypted_email
            admin_user.email_hmac = email_hmac
            admin_user.hashed_password = hashed_pw
            admin_user.first_name = encrypted_first
            admin_user.last_name = encrypted_last
            admin_user.is_active = True
            session.add(admin_user)
            await session.commit()
            print(f"✓ Admin mis à jour : {admin_email}")

    await sessionmanager.close()
    print()
    print("Initialisation terminée.")


if __name__ == "__main__":
    asyncio.run(init_db())
