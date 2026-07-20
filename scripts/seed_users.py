"""
Crée le socle d'utilisateurs de démonstration : 20 servants, 8 parents (avec
liens familiaux réalistes vers plusieurs servants), 1 aumônier. Le compte
ADMIN est créé séparément par scripts/init_db.py.

Utilisation : python scripts/seed_users.py
"""

import asyncio
import sys
from datetime import datetime

sys.path.append(".")

from src.core.entities.servant_parent import ServantParent
from src.core.entities.user import User, UserRole
from src.infrastructure.database.session import sessionmanager
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.utils import SecurityUtils

SEED_PASSWORD = "ServantTest2026!"

# (prénom, nom, téléphone, date de naissance)
SERVANTS = [
    ("Jean-Baptiste", "Ndongo", "+237699112233", datetime(2010, 3, 14)),
    ("Marie-Claire", "Owona", "+237699112234", datetime(2011, 7, 2)),
    ("Pierre", "Mballa", "+237699112235", datetime(2009, 11, 20)),
    ("Cécile", "Fouda", "+237699112236", datetime(2012, 1, 9)),
    ("Paul", "Essomba", "+237699112237", datetime(2010, 9, 5)),
    ("Solange", "Ateba", "+237699112238", datetime(2011, 4, 18)),
    ("Hervé", "Nkolo", "+237699112239", datetime(2009, 6, 30)),
    ("Christian", "Abega", "+237699112240", datetime(2010, 12, 3)),
    ("Brenda", "Mengue", "+237699112241", datetime(2011, 2, 27)),
    ("Yannick", "Onana", "+237699112242", datetime(2010, 8, 11)),
    ("Nadège", "Zambo", "+237699112243", datetime(2012, 5, 16)),
    ("Franck", "Bilongo", "+237699112244", datetime(2009, 10, 22)),
    ("Aurélie", "Ngo Bakoa", "+237699112245", datetime(2011, 1, 8)),
    ("Steve", "Ekwalla", "+237699112246", datetime(2010, 3, 29)),
    ("Larissa", "Tchoua", "+237699112247", datetime(2012, 7, 19)),
    ("Boris", "Mvondo", "+237699112248", datetime(2009, 9, 14)),
    ("Chantal", "Assiga", "+237699112249", datetime(2011, 11, 2)),
    ("Éric", "Nana", "+237699112250", datetime(2010, 6, 6)),
    ("Sandrine", "Belinga", "+237699112251", datetime(2012, 2, 24)),
    ("Rodrigue", "Ondoa", "+237699112252", datetime(2009, 4, 17)),
]

# (prénom, nom, téléphone, email, [index des servants liés dans SERVANTS])
PARENTS = [
    ("Marguerite", "Ndongo", "+237677445566", "marguerite.ndongo@example.cm", [0]),
    ("Antoine", "Owona", "+237677445567", "antoine.owona@example.cm", [1]),
    ("Bernadette", "Mballa", "+237677445568", "bernadette.mballa@example.cm", [2, 3]),
    ("Joseph", "Essomba", "+237677445569", "joseph.essomba@example.cm", [4, 5]),
    ("Élise", "Nkolo", "+237677445570", "elise.nkolo@example.cm", [6]),
    ("Martin", "Abega", "+237677445571", "martin.abega@example.cm", [7, 8]),
    ("Odile", "Onana", "+237677445572", "odile.onana@example.cm", [9]),
    ("Théodore", "Zambo", "+237677445573", "theodore.zambo@example.cm", [10, 11]),
]


async def main():
    async with sessionmanager.connect() as session:
        repo = UserRepository(session)

        servant_ids = []
        for first, last, phone, birth in SERVANTS:
            u = User(
                first_name=first, last_name=last, phone_number=phone,
                role=UserRole.SERVANT, is_active=True, birth_date=birth,
                hashed_password=SecurityUtils.get_password_hash(SEED_PASSWORD),
                terms_accepted_at=datetime.utcnow(), data_consent_at=datetime.utcnow(),
            )
            created = await repo.create(u)
            servant_ids.append(created.id)
        print(f"{len(servant_ids)} servants créés.")

        parent_count = 0
        link_count = 0
        for first, last, phone, email, child_idx in PARENTS:
            p = User(
                first_name=first, last_name=last, phone_number=phone, email=email,
                role=UserRole.PARENT, is_active=True,
                hashed_password=SecurityUtils.get_password_hash(SEED_PASSWORD),
                terms_accepted_at=datetime.utcnow(), data_consent_at=datetime.utcnow(),
            )
            created_parent = await repo.create(p)
            parent_count += 1
            for idx in child_idx:
                session.add(ServantParent(servant_id=servant_ids[idx], parent_id=created_parent.id))
                link_count += 1
            await session.commit()
        print(f"{parent_count} parents créés, {link_count} liens parent-servant établis.")

        aumonier = User(
            first_name="Emmanuel", last_name="Biya", email="emmanuel.biya@bmra-mvolye.cm",
            role=UserRole.AUMÔNIER, is_active=True,
            hashed_password=SecurityUtils.get_password_hash(SEED_PASSWORD),
            terms_accepted_at=datetime.utcnow(), data_consent_at=datetime.utcnow(),
        )
        await repo.create(aumonier)
        print("Aumônier créé.")

    await sessionmanager.close()


if __name__ == "__main__":
    asyncio.run(main())
