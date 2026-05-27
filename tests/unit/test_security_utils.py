"""
Tests unitaires — src/infrastructure/security/utils.py

Couvre :
  SecurityUtils.verify_password / get_password_hash
  SecurityUtils.create_access_token  : structure JWT, claims obligatoires
  SecurityUtils.create_refresh_token : claim "type" = "refresh"
  SecurityUtils.create_reset_token   : courte durée de vie
  SecurityUtils.sanitize_html        : protection XSS
"""
import pytest
from datetime import timedelta

from jose import jwt

from src.infrastructure.config.settings import get_settings
from src.infrastructure.security.utils import SecurityUtils


settings = get_settings()


# ═══════════════════════════════════════════════════════════════════════════
#  Hachage de mots de passe
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestPasswordHashing:

    def test_hash_is_not_plaintext(self):
        hashed = SecurityUtils.get_password_hash("MySecret1!")
        assert hashed != "MySecret1!"

    def test_hash_looks_like_bcrypt(self):
        hashed = SecurityUtils.get_password_hash("MySecret1!")
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    def test_verify_correct_password(self):
        hashed = SecurityUtils.get_password_hash("CorrectP@ss1")
        assert SecurityUtils.verify_password("CorrectP@ss1", hashed) is True

    def test_verify_wrong_password(self):
        hashed = SecurityUtils.get_password_hash("CorrectP@ss1")
        assert SecurityUtils.verify_password("WrongP@ss1", hashed) is False

    def test_two_hashes_are_different(self):
        # bcrypt randomise le salt → deux hachages du même mot de passe diffèrent
        h1 = SecurityUtils.get_password_hash("SamePass1!")
        h2 = SecurityUtils.get_password_hash("SamePass1!")
        assert h1 != h2

    def test_verify_empty_password_fails(self):
        hashed = SecurityUtils.get_password_hash("NotEmpty1!")
        assert SecurityUtils.verify_password("", hashed) is False


# ═══════════════════════════════════════════════════════════════════════════
#  Access token
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestAccessToken:

    def _decode(self, token: str) -> dict:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

    def test_token_is_string(self):
        token = SecurityUtils.create_access_token("user-id-123", "SERVANT")
        assert isinstance(token, str)
        assert len(token) > 20

    def test_sub_claim(self):
        token = SecurityUtils.create_access_token("user-abc", "SERVANT")
        payload = self._decode(token)
        assert payload["sub"] == "user-abc"

    def test_role_claim(self):
        token = SecurityUtils.create_access_token("user-abc", "ADMIN")
        payload = self._decode(token)
        assert payload["role"] == "ADMIN"

    def test_jti_is_unique(self):
        t1 = SecurityUtils.create_access_token("uid", "SERVANT")
        t2 = SecurityUtils.create_access_token("uid", "SERVANT")
        assert self._decode(t1)["jti"] != self._decode(t2)["jti"]

    def test_iss_is_app_name(self):
        token = SecurityUtils.create_access_token("uid", "SERVANT")
        assert self._decode(token)["iss"] == settings.APP_NAME

    def test_exp_claim_present(self):
        token = SecurityUtils.create_access_token("uid", "SERVANT")
        payload = self._decode(token)
        assert "exp" in payload

    def test_custom_expiry(self):
        import time
        token = SecurityUtils.create_access_token(
            "uid", "SERVANT", expires_delta=timedelta(seconds=5)
        )
        payload = self._decode(token)
        remaining = payload["exp"] - time.time()
        assert 0 < remaining <= 10  # entre 0 et 10 secondes


# ═══════════════════════════════════════════════════════════════════════════
#  Refresh token
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestRefreshToken:

    def _decode(self, token: str) -> dict:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

    def test_type_claim_is_refresh(self):
        token = SecurityUtils.create_refresh_token("uid", "SERVANT")
        assert self._decode(token)["type"] == "refresh"

    def test_sub_claim(self):
        token = SecurityUtils.create_refresh_token("uid", "SERVANT")
        assert self._decode(token)["sub"] == "uid"

    def test_jti_is_unique(self):
        t1 = SecurityUtils.create_refresh_token("uid", "SERVANT")
        t2 = SecurityUtils.create_refresh_token("uid", "SERVANT")
        assert self._decode(t1)["jti"] != self._decode(t2)["jti"]

    def test_access_and_refresh_jti_different(self):
        at = SecurityUtils.create_access_token("uid", "SERVANT")
        rt = SecurityUtils.create_refresh_token("uid", "SERVANT")
        at_payload = self._decode(at)
        rt_payload = self._decode(rt)
        assert at_payload["jti"] != rt_payload["jti"]


# ═══════════════════════════════════════════════════════════════════════════
#  Reset token
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestResetToken:

    def _decode(self, token: str) -> dict:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

    def test_type_claim_is_reset(self):
        token = SecurityUtils.create_reset_token("uid")
        assert self._decode(token)["type"] == "reset"

    def test_short_lived_by_default(self):
        import time
        token = SecurityUtils.create_reset_token("uid")
        payload = self._decode(token)
        remaining = payload["exp"] - time.time()
        # Par défaut 15 min → doit rester < 16 min
        assert remaining < 960

    def test_jti_present(self):
        token = SecurityUtils.create_reset_token("uid")
        assert "jti" in self._decode(token)


# ═══════════════════════════════════════════════════════════════════════════
#  Sanitize HTML (anti-XSS)
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestSanitizeHtml:

    def test_strips_script_tag(self):
        result = SecurityUtils.sanitize_html("<script>alert(1)</script>Hello")
        assert "<script>" not in result
        assert "alert" not in result

    def test_strips_img_onerror(self):
        result = SecurityUtils.sanitize_html('<img src=x onerror="alert(1)">')
        assert "onerror" not in result

    def test_plain_text_unchanged(self):
        result = SecurityUtils.sanitize_html("Hello world")
        assert result == "Hello world"

    def test_empty_string_returned_as_is(self):
        assert SecurityUtils.sanitize_html("") == ""

    def test_none_like_falsy_returned(self):
        # Comportement actuel : retourne la valeur falsy telle quelle
        assert SecurityUtils.sanitize_html(None) is None  # type: ignore[arg-type]

    def test_strips_a_href(self):
        result = SecurityUtils.sanitize_html('<a href="http://evil.com">click</a>')
        assert "<a" not in result

    def test_strips_style_attribute(self):
        result = SecurityUtils.sanitize_html('<p style="color:red">text</p>')
        assert "style=" not in result
