"""
Tests E2E — Upload et suppression de photo de profil (/api/v1/users/me/photo).

Couvre :
- Upload d'une photo valide (JPEG, PNG, WebP)
- Remplacement d'une photo existante
- Suppression de la photo
- Rejet des fichiers invalides (taille, type)
- Permissions (authentification requise)
"""
import io

import pytest
from httpx import AsyncClient

from src.core.entities.user import User
from tests.conftest import make_auth_header


def _make_fake_image(content_type: str = "image/jpeg", size: int = 1024) -> tuple:
    """Cree un faux fichier image pour les tests."""
    ext_map = {
        "image/jpeg": "test.jpg",
        "image/png": "test.png",
        "image/webp": "test.webp",
    }
    filename = ext_map.get(content_type, "test.bin")
    # Cree un contenu minimal (pas une vraie image mais suffit pour le test de service)
    data = b"\xff\xd8\xff" + b"\x00" * (size - 3)  # JPEG magic bytes
    return filename, data, content_type


@pytest.mark.e2e
class TestProfilePhotoUpload:
    """Upload de photo de profil."""

    async def test_upload_photo_success(self, client: AsyncClient, servant_user: User):
        """Upload reussi d'une photo JPEG."""
        filename, data, ct = _make_fake_image("image/jpeg", 2048)
        resp = await client.post(
            "/api/v1/users/me/photo",
            files={"file": (filename, io.BytesIO(data), ct)},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["profile_photo_url"] is not None
        assert "profile" in body["profile_photo_url"]

    async def test_upload_png(self, client: AsyncClient, servant_user: User):
        """Upload reussi d'une photo PNG."""
        filename, data, ct = _make_fake_image("image/png", 2048)
        resp = await client.post(
            "/api/v1/users/me/photo",
            files={"file": (filename, io.BytesIO(data), ct)},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200

    async def test_upload_webp(self, client: AsyncClient, servant_user: User):
        """Upload reussi d'une photo WebP."""
        filename, data, ct = _make_fake_image("image/webp", 2048)
        resp = await client.post(
            "/api/v1/users/me/photo",
            files={"file": (filename, io.BytesIO(data), ct)},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 200

    async def test_upload_replaces_existing(self, client: AsyncClient, servant_user: User):
        """Un second upload remplace la photo existante."""
        _, data1, ct = _make_fake_image("image/jpeg", 1024)
        _, data2, ct2 = _make_fake_image("image/png", 2048)

        resp1 = await client.post(
            "/api/v1/users/me/photo",
            files={"file": ("first.jpg", io.BytesIO(data1), ct)},
            headers=make_auth_header(servant_user),
        )
        url1 = resp1.json()["profile_photo_url"]

        resp2 = await client.post(
            "/api/v1/users/me/photo",
            files={"file": ("second.png", io.BytesIO(data2), ct2)},
            headers=make_auth_header(servant_user),
        )
        url2 = resp2.json()["profile_photo_url"]

        assert url1 != url2

    async def test_invalid_content_type_rejected(self, client: AsyncClient, servant_user: User):
        """Type de fichier non autorise -> 400."""
        resp = await client.post(
            "/api/v1/users/me/photo",
            files={"file": ("doc.pdf", io.BytesIO(b"fakepdf"), "application/pdf")},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 400

    async def test_file_too_large_rejected(self, client: AsyncClient, servant_user: User):
        """Fichier trop gros (>5Mo) -> 400."""
        large_data = b"\x00" * (6 * 1024 * 1024)  # 6 Mo
        resp = await client.post(
            "/api/v1/users/me/photo",
            files={"file": ("large.jpg", io.BytesIO(large_data), "image/jpeg")},
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 400

    async def test_unauthenticated_upload_401(self, client: AsyncClient):
        """Sans authentification -> 401."""
        resp = await client.post(
            "/api/v1/users/me/photo",
            files={"file": ("test.jpg", io.BytesIO(b"\xff\xd8\xff"), "image/jpeg")},
        )
        assert resp.status_code == 401


@pytest.mark.e2e
class TestProfilePhotoDelete:
    """Suppression de photo de profil."""

    async def test_delete_photo(self, client: AsyncClient, servant_user: User):
        """Suppression reussie apres upload."""
        _, data, ct = _make_fake_image("image/jpeg", 1024)

        # Upload d'abord
        await client.post(
            "/api/v1/users/me/photo",
            files={"file": ("test.jpg", io.BytesIO(data), ct)},
            headers=make_auth_header(servant_user),
        )

        # Supprimer
        resp = await client.delete(
            "/api/v1/users/me/photo",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 204

        # Verifier que le profil n'a plus de photo
        profile = await client.get(
            "/api/v1/users/me",
            headers=make_auth_header(servant_user),
        )
        assert profile.json()["profile_photo_url"] is None

    async def test_delete_no_photo_404(self, client: AsyncClient, servant_user: User):
        """Suppression sans photo existante -> 404."""
        resp = await client.delete(
            "/api/v1/users/me/photo",
            headers=make_auth_header(servant_user),
        )
        assert resp.status_code == 404
