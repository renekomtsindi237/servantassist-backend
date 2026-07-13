"""
Tests unitaires — EncryptedModelMixin.

Vérifie que le mixin chiffre, déchiffre et indexe correctement les champs
déclarés dans ENCRYPTED_FIELDS et HMAC_INDEX_MAP, indépendamment de toute
entité SQLModel réelle.
"""

import pytest

from src.infrastructure.security.encrypted_model_mixin import EncryptedModelMixin
from src.infrastructure.security.field_encryption import FieldEncryptor

TEST_KEY = "test-master-secret-for-mixin-tests-!"


@pytest.fixture(autouse=True)
def inject_test_encryptor():
    """Force le singleton à utiliser la clé de test."""
    import src.infrastructure.security.field_encryption as fe

    original = fe._encryptor_instance
    fe._encryptor_instance = FieldEncryptor(TEST_KEY)
    yield
    fe._encryptor_instance = original


# ── Faux modèles pour les tests ──────────────────────────────────────────


class FakeModel:
    """Simule un modèle SQLModel avec des champs attributs."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class SimpleRepo(EncryptedModelMixin):
    ENCRYPTED_FIELDS = ("name", "notes")
    HMAC_INDEX_MAP = {}


class SearchableRepo(EncryptedModelMixin):
    ENCRYPTED_FIELDS = ("email", "phone")
    HMAC_INDEX_MAP = {"email": "email_hmac", "phone": "phone_hmac"}


# ═══════════════════════════════════════════════════════════════════════════
#  _encrypt_model
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestEncryptModel:
    def test_encrypts_declared_fields(self):
        repo = SimpleRepo()
        model = FakeModel(name="Jean", notes="Absent hier")

        repo._encrypt_model(model)

        assert model.name != "Jean"
        assert model.notes != "Absent hier"

    def test_does_not_touch_undeclared_fields(self):
        repo = SimpleRepo()
        model = FakeModel(name="Jean", notes="note", role="SERVANT")

        repo._encrypt_model(model)

        assert model.role == "SERVANT"

    def test_none_fields_left_as_none(self):
        repo = SimpleRepo()
        model = FakeModel(name=None, notes="note")

        repo._encrypt_model(model)

        assert model.name is None

    def test_hmac_computed_before_encryption(self):
        """email_hmac doit être le HMAC du texte clair, pas du blob chiffré."""
        from src.infrastructure.security.field_encryption import get_encryptor

        repo = SearchableRepo()
        model = FakeModel(
            email="test@example.com",
            phone="+237600000001",
            email_hmac=None,
            phone_hmac=None,
        )
        repo._encrypt_model(model)

        enc = get_encryptor()
        expected_hmac = enc.hmac_index("test@example.com")
        assert model.email_hmac == expected_hmac

    def test_hmac_phone_computed(self):
        from src.infrastructure.security.field_encryption import get_encryptor

        repo = SearchableRepo()
        model = FakeModel(email="x@x.cm", phone="+237699001122", email_hmac=None, phone_hmac=None)
        repo._encrypt_model(model)

        enc = get_encryptor()
        assert model.phone_hmac == enc.hmac_index("+237699001122")

    def test_hmac_none_when_field_is_none(self):
        repo = SearchableRepo()
        model = FakeModel(email=None, phone="+237699001122", email_hmac=None, phone_hmac=None)
        repo._encrypt_model(model)

        assert model.email_hmac is None

    def test_encrypted_field_is_base64url(self):
        import base64

        repo = SimpleRepo()
        model = FakeModel(name="Marie", notes="ok")
        repo._encrypt_model(model)

        base64.urlsafe_b64decode(model.name.encode("ascii") + b"==")


# ═══════════════════════════════════════════════════════════════════════════
#  _decrypt_model
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestDecryptModel:
    def test_roundtrip(self):
        repo = SimpleRepo()
        model = FakeModel(name="Côme", notes="Présent")

        repo._encrypt_model(model)
        repo._decrypt_model(model)

        assert model.name == "Côme"
        assert model.notes == "Présent"

    def test_decrypt_none_stays_none(self):
        repo = SimpleRepo()
        model = FakeModel(name=None, notes="ok")

        repo._encrypt_model(model)
        repo._decrypt_model(model)

        assert model.name is None

    def test_decrypt_ignores_plaintext_silently(self):
        """Un champ non chiffré (avant migration) ne doit pas lever d'erreur."""
        repo = SimpleRepo()
        model = FakeModel(name="texte clair", notes="ok")

        repo._decrypt_model(model)

        # Pas d'exception


# ═══════════════════════════════════════════════════════════════════════════
#  _decrypt_list
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestDecryptList:
    def test_decrypts_all_models(self):
        repo = SimpleRepo()
        models = [FakeModel(name=f"Name{i}", notes=f"Note{i}") for i in range(5)]

        for m in models:
            repo._encrypt_model(m)
        repo._decrypt_list(models)

        for i, m in enumerate(models):
            assert m.name == f"Name{i}"
            assert m.notes == f"Note{i}"

    def test_empty_list_does_nothing(self):
        repo = SimpleRepo()
        repo._decrypt_list([])

    def test_list_with_none_fields(self):
        repo = SimpleRepo()
        models = [
            FakeModel(name="Marie", notes=None),
            FakeModel(name=None, notes="note"),
        ]
        for m in models:
            repo._encrypt_model(m)
        repo._decrypt_list(models)

        assert models[0].name == "Marie"
        assert models[0].notes is None
        assert models[1].name is None
        assert models[1].notes == "note"


# ═══════════════════════════════════════════════════════════════════════════
#  ISOLATION : encrypt → encrypt ne double-chiffre pas
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestEncryptIdempotency:
    def test_double_encrypt_then_single_decrypt_fails(self):
        """Un double-chiffrement accidentel rend le déchiffrement impossible → bug détectable."""
        repo = SimpleRepo()
        model = FakeModel(name="Test", notes="ok")

        repo._encrypt_model(model)
        repo._encrypt_model(model)  # accidentel
        repo._decrypt_model(model)  # décrypte une fois

        # Après un seul decrypt, le résultat est encore un blob chiffré
        assert model.name != "Test", (
            "Si le test passe ici, le double-chiffrement est silencieusement absorbé — "
            "vérifiez que _encrypt_model n'est pas appelé deux fois."
        )
