"""Unit tests for core.pagination utilities."""

import pytest
from uuid import UUID, uuid4

from src.core.pagination import (
    CursorPage,
    OffsetPage,
    decode_cursor,
    encode_cursor,
)

# ─── encode_cursor / decode_cursor ───────────────────────────────────────────


def test_encode_decode_roundtrip():
    uid = uuid4()
    encoded = encode_cursor(uid)
    assert isinstance(encoded, str)
    decoded = decode_cursor(encoded)
    assert decoded == uid


def test_encode_cursor_is_url_safe():
    uid = uuid4()
    encoded = encode_cursor(uid)
    # No +, /, = characters (URL-safe base64)
    assert "+" not in encoded
    assert "/" not in encoded
    assert "=" not in encoded


def test_decode_cursor_none():
    assert decode_cursor(None) is None


def test_decode_cursor_empty_string():
    assert decode_cursor("") is None


def test_decode_cursor_invalid():
    assert decode_cursor("not-a-valid-cursor!!!") is None


def test_decode_cursor_short_invalid():
    assert decode_cursor("abc") is None


# ─── OffsetPage ──────────────────────────────────────────────────────────────


def test_offset_page_has_next_true():
    page = OffsetPage(items=[1, 2, 3], total=20, limit=5, offset=0)
    assert page.has_next is True


def test_offset_page_has_next_false():
    page = OffsetPage(items=[1], total=5, limit=5, offset=0)
    assert page.has_next is False


def test_offset_page_has_prev_false():
    page = OffsetPage(items=[1], total=10, limit=5, offset=0)
    assert page.has_prev is False


def test_offset_page_has_prev_true():
    page = OffsetPage(items=[1], total=10, limit=5, offset=5)
    assert page.has_prev is True


def test_offset_page_exact_last():
    # Exactly at last page (offset+limit == total)
    page = OffsetPage(items=[1, 2, 3, 4, 5], total=10, limit=5, offset=5)
    assert page.has_next is False
    assert page.has_prev is True


# ─── CursorPage ──────────────────────────────────────────────────────────────


def test_cursor_page_has_next_false():
    page = CursorPage(items=[1, 2, 3], next_cursor=None, limit=5)
    assert page.has_next is False


def test_cursor_page_has_next_true():
    page = CursorPage(items=[1, 2, 3], next_cursor="some_cursor", limit=5)
    assert page.has_next is True


def test_cursor_page_empty_items():
    page = CursorPage(items=[], next_cursor=None, limit=10)
    assert page.has_next is False
    assert page.items == []
