"""
Tests unitaires — FieldEncryptor et utilitaires de chiffrement PII.

Couvre :
  - Chiffrement / déchiffrement (round-trip, cas limites)
  - Caractère aléatoire des nonces (deux chiffrements → blobs distincts)
  - Index HMAC (déterminisme, normalisation)
  - Résistance à la corruption
  - Utilitaire decrypt_str_fields
  - Singleton get_encryptor
"""

import base64

import pytest

from src.infrastructure.security.field_encryption import (
    FieldEncryptor,
    decrypt_str_fields,
    get_encryptor,
)

TEST_KEY = "test-master-secret-for-unit-tests-only-!"


@pytest.fixture(autouse=True)
def reset_singleton():
    """Isole chaque test : repart d'un singleton vide."""
    import src.infrastructure.security.field_encryption as fe

    original = fe._encryptor_instance
    fe._encryptor_instance = None
    yield
    fe._encryptor_instance = original


@pytest.fixture()
def enc() -> FieldEncryptor:
    return FieldEncryptor(TEST_KEY)


# ═══════════════════════════════════════════════════════════════════════════
#  CHIFFREMENT / DÉCHIFFREMENT
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestEncryptDecrypt:
    def test_roundtrip_simple(self, enc):
        assert enc.decrypt(enc.encrypt("Jean NDAA")) == "Jean NDAA"

    def test_roundtrip_unicode(self, enc):
        assert enc.decrypt(enc.encrypt("Côme Ébénézer")) == "Côme Ébénézer"

    def test_roundtrip_long_string(self, enc):
        long = "A" * 10_000
        assert enc.decrypt(enc.encrypt(long)) == long

    def test_roundtrip_email(self, enc):
        assert enc.decrypt(enc.encrypt("servant@paroisse.cm")) == "servant@paroisse.cm"

    def test_roundtrip_phone(self, enc):
        assert enc.decrypt(enc.encrypt("+237699112233")) == "+237699112233"

    def test_encrypt_none_returns_none(self, enc):
        assert enc.encrypt(None) is None

    def test_encrypt_empty_returns_empty(self, enc):
        assert enc.encrypt("") == ""

    def test_decrypt_none_returns_none(self, enc):
        assert enc.decrypt(None) is None

    def test_decrypt_empty_returns_empty(self, enc):
        assert enc.decrypt("") == ""

    def test_ciphertext_is_base64url(self, enc):
        blob = enc.encrypt("test")
        # base64url : ne contient pas + ni /
        assert "+" not in blob
        assert "/" not in blob
        # décodable sans erreur
        base64.urlsafe_b64decode(blob.encode("ascii") + b"==")

    def test_ciphertext_is_not_plaintext(self, enc):
        plaintext = "Jean Dupont"
        blob = enc.encrypt(plaintext)
        assert plaintext not in blob
        assert blob != plaintext

    def test_two_encryptions_produce_different_blobs(self, enc):
        """Le nonce aléatoire garantit que deux chiffrements du même texte sont distincts."""
        a = enc.encrypt("même valeur")
        b = enc.encrypt("même valeur")
        assert a != b

    def test_decrypt_with_corrupted_blob_raises(self, enc):
        with pytest.raises(ValueError):
            enc.decrypt("pas-du-tout-un-blob-valide==")

    def test_decrypt_truncated_blob_raises(self, enc):
        blob = enc.encrypt("data")
        with pytest.raises(ValueError):
            enc.decrypt(blob[:5])

    def test_decrypt_wrong_key_raises(self, enc):
        blob = enc.encrypt("confidentiel")
        other_enc = FieldEncryptor("completely-different-key-!!")
        with pytest.raises(ValueError):
            other_enc.decrypt(blob)

    def test_different_instances_same_key_roundtrip(self):
        enc1 = FieldEncryptor(TEST_KEY)
        enc2 = FieldEncryptor(TEST_KEY)
        blob = enc1.encrypt("cross-instance")
        assert enc2.decrypt(blob) == "cross-instance"


# ═══════════════════════════════════════════════════════════════════════════
#  INDEX HMAC
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestHmacIndex:
    def test_deterministic(self, enc):
        h1 = enc.hmac_index("servant@paroisse.cm")
        h2 = enc.hmac_index("servant@paroisse.cm")
        assert h1 == h2

    def test_case_insensitive(self, enc):
        assert enc.hmac_index("SERVANT@paroisse.cm") == enc.hmac_index("servant@paroisse.cm")

    def test_strips_whitespace(self, enc):
        assert enc.hmac_index("  email@test.com  ") == enc.hmac_index("email@test.com")

    def test_different_values_different_hmac(self, enc):
        assert enc.hmac_index("a@test.com") != enc.hmac_index("b@test.com")

    def test_hmac_none_returns_none(self, enc):
        assert enc.hmac_index(None) is None

    def test_hmac_empty_returns_none(self, enc):
        assert enc.hmac_index("") is None

    def test_hmac_is_hex_string(self, enc):
        h = enc.hmac_index("test@test.com")
        assert len(h) == 64  # SHA-256 → 32 bytes → 64 hex chars
        int(h, 16)  # valide si c'est bien de l'hex

    def test_different_keys_different_hmac(self):
        enc1 = FieldEncryptor(TEST_KEY)
        enc2 = FieldEncryptor("other-master-key-!!")
        assert enc1.hmac_index("same@test.com") != enc2.hmac_index("same@test.com")


# ═══════════════════════════════════════════════════════════════════════════
#  UTILITAIRE decrypt_str_fields
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestDecryptStrFields:
    def test_decrypts_specified_fields(self, enc):
        import src.infrastructure.security.field_encryption as fe

        fe._encryptor_instance = enc

        class Fake:
            first_name = enc.encrypt("Marie")
            last_name = enc.encrypt("Dupont")

        obj = Fake()
        decrypt_str_fields(obj, ("first_name", "last_name"))
        assert obj.first_name == "Marie"
        assert obj.last_name == "Dupont"

    def test_ignores_none_fields(self, enc):
        import src.infrastructure.security.field_encryption as fe

        fe._encryptor_instance = enc

        class Fake:
            first_name = None
            last_name = enc.encrypt("Dupont")

        obj = Fake()
        decrypt_str_fields(obj, ("first_name", "last_name"))
        assert obj.first_name is None
        assert obj.last_name == "Dupont"

    def test_ignores_plaintext_fields_silently(self, enc):
        """Les champs non chiffrés (avant migration) ne doivent pas lever d'erreur."""
        import src.infrastructure.security.field_encryption as fe

        fe._encryptor_instance = enc

        class Fake:
            first_name = "Texte clair non chiffré"

        obj = Fake()
        decrypt_str_fields(obj, ("first_name",))
        # Pas d'exception levée — valeur inchangée ou silencieusement ignorée

    def test_missing_field_ignored(self, enc):
        import src.infrastructure.security.field_encryption as fe

        fe._encryptor_instance = enc

        class Fake:
            pass

        obj = Fake()
        decrypt_str_fields(obj, ("inexistant",))  # pas d'AttributeError


# ═══════════════════════════════════════════════════════════════════════════
#  SINGLETON get_encryptor
# ═══════════════════════════════════════════════════════════════════════════
@pytest.mark.unit
class TestGetEncryptor:
    def test_returns_field_encryptor_instance(self):
        enc = get_encryptor()
        assert isinstance(enc, FieldEncryptor)

    def test_singleton_same_instance(self):
        enc1 = get_encryptor()
        enc2 = get_encryptor()
        assert enc1 is enc2

    def test_singleton_raises_without_key(self, monkeypatch):
        import src.infrastructure.security.field_encryption as fe

        fe._encryptor_instance = None
        monkeypatch.setenv("FIELD_ENCRYPTION_KEY", "")
        from src.infrastructure.config.settings import get_settings

        get_settings.cache_clear()

        try:
            with pytest.raises(RuntimeError, match="FIELD_ENCRYPTION_KEY"):
                get_encryptor()
        finally:
            # Restore so other tests keep working
            get_settings.cache_clear()
