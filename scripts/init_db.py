import asyncio
import os
import sys

# Add src to path
sys.path.append(".")

from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import sessionmanager
from src.infrastructure.security.utils import SecurityUtils
from sqlmodel import select


async def init_db():
    print("Initializing Database...")

    # Credentials admin via variables d'environnement (obligatoires)
    admin_email = os.environ.get("renekomtsindi7@gmail.com")
    admin_password = os.environ.get("Mbetoumou olive77")

    if not admin_email or not admin_password:
        print("Les variables d'environnement ADMIN_EMAIL et ADMIN_PASSWORD sont requises.")
        print("Exemple: ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=Secret123 python scripts/init_db.py")
        sys.exit(1)

    async with sessionmanager.connect() as session:
        # Check if admin exists (UNIQUE - only one admin allowed)
        stmt = select(User).where(User.role == UserRole.ADMIN)
        result = await session.exec(stmt)
        admin_user = result.first()

        if not admin_user:
            print("👤 Creating Default Admin User...")
            admin = User(
                email=admin_email,
                hashed_password=SecurityUtils.get_password_hash(admin_password),
                first_name="Admin",
                last_name="System",
                role=UserRole.ADMIN,
                is_active=True,
            )
            session.add(admin)
            await session.commit()
            print(f"Admin created: {admin_email}")
        else:
            print("Admin already exists: " + admin_user.email)

    await sessionmanager.close()


if __name__ == "__main__":
    asyncio.run(init_db())
