"""
Tests d'intégration — UserRepository avec chiffrement PII activé.

Vérifie le cycle complet : création → stockage chiffré → lecture déchiffrée
via HMAC index, sans jamais exposer le texte clair à la base de données.
"""

from uuid import uuid4

import pytest

from src.core.entities.user import User, UserRole
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.security.field_encryption import FieldEncryptor, get_encryptor
from src.infrastructure.security.utils import SecurityUtils


def _make_user(
    email: str = "integration@test.com",
    phone: str = "+237600001111",
    role: UserRole = UserRole.SERVANT,
) -> User:
    return User(
        id=uuid4(),
        email=email,
        hashed_password=SecurityUtils.get_password_hash("TestPass1"),
        first_name="Intégration",
        last_name="Test",
        role=role,
        is_active=True,
        phone_number=phone,
    )


@pytest.fixture(autouse=True)
def reset_encryptor_singleton():
    """Réinitialise le singleton entre chaque test pour éviter les effets de bord."""
    import src.infrastructure.security.field_encryption as fe

    original = fe._encryptor_instance
    fe._encryptor_instance = None
    yield
    fe._encryptor_instance = original


@pytest.mark.integration
async def test_create_and_get_by_id(db_session):
    """Création puis récupération par ID : noms déchiffrés correctement."""
    repo = UserRepository(db_session)
    user = _make_user()

    created = await repo.create(user)
    fetched = await repo.get(created.id)

    assert fetched is not None
    assert fetched.first_name == "Intégration"
    assert fetched.last_name == "Test"
    assert fetched.email == "integration@test.com"


@pytest.mark.integration
async def test_get_by_email_uses_hmac_index(db_session):
    """get_by_email retrouve l'utilisateur via l'index HMAC, pas le texte clair."""
    repo = UserRepository(db_session)
    user = _make_user(email="hmac@test.com")

    await repo.create(user)
    found = await repo.get_by_email("hmac@test.com")

    assert found is not None
    assert found.email == "hmac@test.com"
    assert found.first_name == "Intégration"


@pytest.mark.integration
async def test_get_by_email_wrong_address_returns_none(db_session):
    """Un email inconnu ne retourne pas un autre utilisateur."""
    repo = UserRepository(db_session)
    await repo.create(_make_user(email="real@test.com"))

    assert await repo.get_by_email("wrong@test.com") is None


@pytest.mark.integration
async def test_get_by_phone_uses_hmac_index(db_session):
    """get_by_phone retrouve l'utilisateur via l'index HMAC."""
    repo = UserRepository(db_session)
    user = _make_user(email="phone@test.com", phone="+237699887766")

    await repo.create(user)
    found = await repo.get_by_phone("+237699887766")

    assert found is not None
    assert found.phone_number == "+237699887766"


@pytest.mark.integration
async def test_db_stores_ciphertext_not_plaintext(db_session):
    """Le texte clair (nom, prénom, email) n'est JAMAIS stocké tel quel en base."""
    from sqlalchemy import text

    repo = UserRepository(db_session)
    user = _make_user(email="secret@test.com")
    created = await repo.create(user)

    row = (
        await db_session.execute(
            text("SELECT first_name, last_name, email FROM users WHERE id = :uid"),
            {"uid": created.id.hex},
        )
    ).one()

    assert row.first_name != "Intégration", "first_name stocké en clair !"
    assert row.last_name != "Test", "last_name stocké en clair !"
    assert row.email != "secret@test.com", "email stocké en clair !"
    # Les valeurs chiffrées sont des blobs base64url
    assert len(row.email) > 20


@pytest.mark.integration
async def test_email_hmac_stored_in_index_column(db_session):
    """email_hmac est rempli après la création."""
    from sqlalchemy import text

    repo = UserRepository(db_session)
    created = await repo.create(_make_user(email="hmacidx@test.com"))

    row = (
        await db_session.execute(
            text("SELECT email_hmac FROM users WHERE id = :uid"),
            {"uid": created.id.hex},
        )
    ).one()

    enc = get_encryptor()
    expected_hmac = enc.hmac_index("hmacidx@test.com")
    assert row.email_hmac == expected_hmac


@pytest.mark.integration
async def test_two_users_different_ciphertexts(db_session):
    """Deux utilisateurs avec le même prénom → ciphertexts différents (nonce aléatoire)."""
    from sqlalchemy import text

    repo = UserRepository(db_session)
    u1 = await repo.create(_make_user(email="u1@test.com", phone="+237600000001"))
    u2 = await repo.create(_make_user(email="u2@test.com", phone="+237600000002"))

    rows = (
        await db_session.execute(
            text("SELECT first_name FROM users WHERE id IN (:id1, :id2)"),
            {"id1": u1.id.hex, "id2": u2.id.hex},
        )
    ).all()

    fn1, fn2 = rows[0].first_name, rows[1].first_name
    assert fn1 != fn2, "Même ciphertext pour deux utilisateurs → le nonce n'est pas aléatoire !"
