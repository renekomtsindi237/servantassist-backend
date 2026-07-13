"""
Storage tests for upload routing and URL prefixes.
"""

import pytest

from src.infrastructure.services.storage_service import StorageService


@pytest.mark.storage
@pytest.mark.asyncio
async def test_report_attachment_routing_pdf():
    storage = StorageService()
    url = await storage.upload_report_attachment(
        report_id="report-1",
        file_data=b"%PDF-1.4 test",
        content_type="application/pdf",
    )
    assert "/documents/reports/" in url


@pytest.mark.storage
@pytest.mark.asyncio
async def test_report_attachment_routing_image():
    storage = StorageService()
    url = await storage.upload_report_attachment(
        report_id="report-2",
        file_data=b"image-bytes",
        content_type="image/jpeg",
    )
    assert "/images/reports/" in url


@pytest.mark.storage
@pytest.mark.asyncio
async def test_profile_photo_routing():
    storage = StorageService()
    url = await storage.upload_profile_photo(
        user_id="user-1",
        file_data=b"image-bytes",
        content_type="image/png",
    )
    assert "/images/profiles/" in url
