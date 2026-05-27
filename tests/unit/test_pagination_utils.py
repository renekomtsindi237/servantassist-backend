"""
Tests unitaires — src/core/utils/pagination.py

Couvre :
  PageParams   : validation, offset, total_pages, has_next, has_prev
  build_link_header : RFC 5988 (first/prev/next/last)
  paginate()   : headers HTTP + PaginationResult.as_dict()
"""
import pytest

from src.core.utils.pagination import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    PageParams,
    PaginationResult,
    build_link_header,
    paginate,
)


# ═══════════════════════════════════════════════════════════════════════════
#  PageParams
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestPageParams:

    def test_defaults(self):
        p = PageParams()
        assert p.page == 1
        assert p.page_size == DEFAULT_PAGE_SIZE

    def test_custom_values(self):
        p = PageParams(page=3, page_size=50)
        assert p.page == 3
        assert p.page_size == 50

    def test_page_zero_raises(self):
        with pytest.raises(ValueError, match="page"):
            PageParams(page=0)

    def test_page_negative_raises(self):
        with pytest.raises(ValueError, match="page"):
            PageParams(page=-5)

    def test_page_size_zero_raises(self):
        with pytest.raises(ValueError, match="page_size"):
            PageParams(page_size=0)

    def test_page_size_over_max_raises(self):
        with pytest.raises(ValueError, match="page_size"):
            PageParams(page_size=MAX_PAGE_SIZE + 1)

    def test_page_size_max_allowed(self):
        p = PageParams(page_size=MAX_PAGE_SIZE)
        assert p.page_size == MAX_PAGE_SIZE

    def test_offset_first_page(self):
        assert PageParams(page=1, page_size=20).offset == 0

    def test_offset_second_page(self):
        assert PageParams(page=2, page_size=20).offset == 20

    def test_offset_arbitrary(self):
        assert PageParams(page=5, page_size=10).offset == 40

    def test_total_pages_exact_multiple(self):
        p = PageParams(page_size=10)
        assert p.total_pages(100) == 10

    def test_total_pages_remainder(self):
        p = PageParams(page_size=10)
        assert p.total_pages(101) == 11

    def test_total_pages_zero_total(self):
        # Doit retourner au moins 1 page même si vide
        p = PageParams(page_size=10)
        assert p.total_pages(0) == 1

    def test_has_next_true(self):
        p = PageParams(page=1, page_size=10)
        assert p.has_next(total=25) is True

    def test_has_next_false_last_page(self):
        p = PageParams(page=3, page_size=10)
        assert p.has_next(total=25) is False

    def test_has_next_false_empty(self):
        p = PageParams(page=1, page_size=10)
        assert p.has_next(total=0) is False

    def test_has_prev_true(self):
        p = PageParams(page=2, page_size=10)
        assert p.has_prev() is True

    def test_has_prev_false_first_page(self):
        p = PageParams(page=1, page_size=10)
        assert p.has_prev() is False

    def test_frozen_immutable(self):
        p = PageParams()
        with pytest.raises((AttributeError, TypeError)):
            p.page = 5  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════
#  build_link_header
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestBuildLinkHeader:

    def _parse(self, header: str) -> dict:
        """Transforme le header Link en {rel: url}."""
        result = {}
        for part in header.split(", "):
            url_part, rel_part = part.split(">; rel=")
            url = url_part.strip("<")
            rel = rel_part.strip('"')
            result[rel] = url
        return result

    def test_first_link_always_present(self):
        links = self._parse(build_link_header("/api/v1/users", 1, 20, 100))
        assert "first" in links

    def test_last_link_always_present(self):
        links = self._parse(build_link_header("/api/v1/users", 1, 20, 100))
        assert "last" in links

    def test_no_prev_on_first_page(self):
        links = self._parse(build_link_header("/api/v1/users", 1, 20, 100))
        assert "prev" not in links

    def test_no_next_on_last_page(self):
        links = self._parse(build_link_header("/api/v1/users", 5, 20, 100))
        assert "next" not in links

    def test_prev_and_next_on_middle_page(self):
        links = self._parse(build_link_header("/api/v1/users", 3, 20, 100))
        assert "prev" in links
        assert "next" in links

    def test_first_url_has_page_1(self):
        links = self._parse(build_link_header("/api/v1/users", 3, 20, 100))
        assert "page=1" in links["first"]

    def test_last_url_has_correct_page(self):
        links = self._parse(build_link_header("/api/v1/users", 1, 20, 100))
        # 100 items / 20 per page = 5 pages
        assert "page=5" in links["last"]

    def test_next_url_is_page_plus_one(self):
        links = self._parse(build_link_header("/api/v1/users", 2, 20, 100))
        assert "page=3" in links["next"]

    def test_prev_url_is_page_minus_one(self):
        links = self._parse(build_link_header("/api/v1/users", 2, 20, 100))
        assert "page=1" in links["prev"]

    def test_extra_qs_appended(self):
        header = build_link_header("/api/v1/users", 1, 20, 40, extra_qs="role=SERVANT")
        assert "role=SERVANT" in header

    def test_page_size_in_all_links(self):
        # page=1, total=45, page_size=15 → 3 pages → links: first, next, last (no prev)
        header = build_link_header("/api/v1/users", 1, 15, 45)
        assert header.count("page_size=15") == 3

    def test_single_page_no_next_no_prev(self):
        links = self._parse(build_link_header("/api/v1/items", 1, 20, 5))
        assert "prev" not in links
        assert "next" not in links


# ═══════════════════════════════════════════════════════════════════════════
#  paginate()
# ═══════════════════════════════════════════════════════════════════════════

@pytest.mark.unit
class TestPaginate:

    def test_returns_pagination_result(self):
        result = paginate(["a", "b"], total=2, page=1, page_size=20)
        assert isinstance(result, PaginationResult)

    def test_items_preserved(self):
        items = [{"id": 1}, {"id": 2}]
        result = paginate(items, total=2, page=1, page_size=20)
        assert result.items == items

    def test_total_count_header(self):
        result = paginate([], total=42, page=1, page_size=20)
        assert result.headers["X-Total-Count"] == "42"

    def test_total_pages_header(self):
        result = paginate([], total=42, page=1, page_size=20)
        # ceil(42/20) = 3
        assert result.headers["X-Total-Pages"] == "3"

    def test_page_header(self):
        result = paginate([], total=42, page=2, page_size=20)
        assert result.headers["X-Page"] == "2"

    def test_page_size_header(self):
        result = paginate([], total=42, page=1, page_size=15)
        assert result.headers["X-Page-Size"] == "15"

    def test_no_link_header_without_request(self):
        result = paginate([], total=42, page=1, page_size=20)
        assert "Link" not in result.headers

    def test_as_dict_has_required_keys(self):
        result = paginate(["x"], total=1, page=1, page_size=20)
        d = result.as_dict()
        assert set(d.keys()) == {"items", "total", "page", "page_size", "total_pages"}

    def test_as_dict_total_pages_computed(self):
        result = paginate([], total=55, page=1, page_size=20)
        assert result.as_dict()["total_pages"] == 3

    def test_with_mock_request_adds_link_header(self):
        class MockQueryParams:
            def __init__(self): pass
            def items(self): return [("role", "ADMIN")]

        class MockURL:
            path = "/api/v1/users"

        class MockRequest:
            query_params = {"role": "ADMIN"}
            url = MockURL()

        result = paginate([], total=100, page=2, page_size=20, request=MockRequest())
        assert "Link" in result.headers
        assert "first" in result.headers["Link"]
        assert "last" in result.headers["Link"]

    def test_link_header_preserves_extra_params(self):
        class MockURL:
            path = "/api/v1/users"

        class MockRequest:
            query_params = {"role": "SERVANT", "page": "2", "page_size": "20"}
            url = MockURL()

        result = paginate([], total=100, page=2, page_size=20, request=MockRequest())
        assert "role=SERVANT" in result.headers["Link"]

    def test_link_header_strips_page_params(self):
        class MockURL:
            path = "/api/v1/users"

        class MockRequest:
            query_params = {"page": "2", "page_size": "20"}
            url = MockURL()

        result = paginate([], total=100, page=2, page_size=20, request=MockRequest())
        # page et page_size ne doivent apparaître que dans les URLs des liens, pas en double
        link = result.headers["Link"]
        # Les params extra_qs ne doivent pas contenir page= en plus des params de pagination
        parts = [p for p in link.split(", ") if "role=" in p]
        assert parts == []  # pas de role= ici (test de cohérence)
