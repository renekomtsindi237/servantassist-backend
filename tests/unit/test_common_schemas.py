"""
Tests unitaires — src/presentation/schemas/common.py

Couvre :
  PageLinks              : modèle Pydantic de navigation
  PaginatedResponse[T]   : sérialisation / liens optionnels
  build_paginated_response : construction du dict avec et sans request
  ResourceLink / make_link : HATEOAS léger
  user_links / discipline_links / assignment_links / attendance_links
  ApiError / ErrorCode
"""

from uuid import UUID, uuid4

import pytest

from src.presentation.schemas.common import (
    API_V1_PREFIX,
    ApiError,
    ErrorCode,
    PageLinks,
    PaginatedResponse,
    ResourceLink,
    assignment_links,
    attendance_links,
    build_paginated_response,
    discipline_links,
    make_link,
    user_links,
)

# ═══════════════════════════════════════════════════════════════════════════
#  PageLinks
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPageLinks:
    def test_all_fields_optional(self):
        links = PageLinks()
        assert links.first is None
        assert links.prev is None
        assert links.self is None
        assert links.next is None
        assert links.last is None

    def test_set_values(self):
        links = PageLinks(
            first="/api/v1/users?page=1&page_size=20",
            last="/api/v1/users?page=5&page_size=20",
        )
        assert links.first == "/api/v1/users?page=1&page_size=20"
        assert links.last == "/api/v1/users?page=5&page_size=20"

    def test_json_serializable(self):
        links = PageLinks(first="/first", next="/next")
        data = links.model_dump()
        assert data["first"] == "/first"
        assert data["next"] == "/next"
        assert data["prev"] is None


# ═══════════════════════════════════════════════════════════════════════════
#  PaginatedResponse
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPaginatedResponse:
    def test_basic_construction(self):
        resp = PaginatedResponse[str](
            items=["a", "b"],
            total=2,
            page=1,
            page_size=20,
            total_pages=1,
        )
        assert resp.items == ["a", "b"]
        assert resp.total == 2
        assert resp.total_pages == 1
        assert resp.links is None

    def test_links_optional(self):
        resp = PaginatedResponse[int](items=[], total=0, page=1, page_size=20, total_pages=1)
        assert resp.links is None

    def test_with_links(self):
        links = PageLinks(first="/first", last="/last")
        resp = PaginatedResponse[str](items=[], total=0, page=1, page_size=20, total_pages=1, links=links)
        assert resp.links is not None
        assert resp.links.first == "/first"

    def test_model_dump_contains_links(self):
        links = PageLinks(first="/first")
        resp = PaginatedResponse[str](items=["x"], total=1, page=1, page_size=20, total_pages=1, links=links)
        data = resp.model_dump()
        assert "links" in data
        assert data["links"]["first"] == "/first"

    def test_generic_type_works_with_dicts(self):
        items = [{"id": 1, "name": "foo"}, {"id": 2, "name": "bar"}]
        resp = PaginatedResponse[dict](items=items, total=2, page=1, page_size=20, total_pages=1)
        assert resp.items[0]["name"] == "foo"
        assert len(resp.items) == 2


# ═══════════════════════════════════════════════════════════════════════════
#  build_paginated_response
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestBuildPaginatedResponse:
    def test_returns_dict(self):
        result = build_paginated_response(["a"], total=1, page=1, page_size=20)
        assert isinstance(result, dict)

    def test_required_keys_present(self):
        result = build_paginated_response([], total=0, page=1, page_size=20)
        assert "items" in result
        assert "total" in result
        assert "page" in result
        assert "page_size" in result
        assert "total_pages" in result

    def test_total_pages_computed(self):
        result = build_paginated_response([], total=55, page=1, page_size=20)
        assert result["total_pages"] == 3

    def test_total_pages_exact(self):
        result = build_paginated_response([], total=40, page=1, page_size=20)
        assert result["total_pages"] == 2

    def test_no_links_without_request(self):
        result = build_paginated_response([], total=100, page=1, page_size=20)
        assert result.get("links") is None

    def test_links_present_with_request(self):
        class MockURL:
            path = "/api/v1/users"

        class MockRequest:
            query_params = {}
            url = MockURL()

        result = build_paginated_response([], total=100, page=2, page_size=20, request=MockRequest())
        assert result["links"] is not None

    def test_links_first_page(self):
        class MockURL:
            path = "/api/v1/users"

        class MockRequest:
            query_params = {}
            url = MockURL()

        result = build_paginated_response([], total=100, page=1, page_size=20, request=MockRequest())
        links = result["links"]
        assert links.first is not None
        assert links.prev is None  # pas de page précédente
        assert links.next is not None

    def test_links_last_page(self):
        class MockURL:
            path = "/api/v1/users"

        class MockRequest:
            query_params = {}
            url = MockURL()

        result = build_paginated_response([], total=20, page=1, page_size=20, request=MockRequest())
        links = result["links"]
        assert links.next is None  # unique page

    def test_links_preserve_extra_query_params(self):
        class MockURL:
            path = "/api/v1/users"

        class MockRequest:
            query_params = {"role": "ADMIN", "page": "2", "page_size": "20"}
            url = MockURL()

        result = build_paginated_response([], total=100, page=2, page_size=20, request=MockRequest())
        links = result["links"]
        assert "role=ADMIN" in links.first
        assert "role=ADMIN" in links.last

    def test_links_self_has_current_page(self):
        class MockURL:
            path = "/api/v1/users"

        class MockRequest:
            query_params = {}
            url = MockURL()

        result = build_paginated_response([], total=100, page=3, page_size=20, request=MockRequest())
        links = result["links"]
        assert "page=3" in links.self


# ═══════════════════════════════════════════════════════════════════════════
#  ResourceLink / make_link
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestResourceLink:
    def test_default_method_is_get(self):
        link = ResourceLink(href="/api/v1/users/1")
        assert link.method == "GET"

    def test_custom_method(self):
        link = ResourceLink(href="/api/v1/users/1", method="DELETE")
        assert link.method == "DELETE"

    def test_make_link_prepends_api_prefix(self):
        link = make_link("/users/123")
        assert link.href == f"{API_V1_PREFIX}/users/123"

    def test_make_link_custom_method(self):
        link = make_link("/users/123", method="PATCH")
        assert link.method == "PATCH"

    def test_make_link_get_default(self):
        link = make_link("/users")
        assert link.method == "GET"


# ═══════════════════════════════════════════════════════════════════════════
#  Helper link builders
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestLinkBuilders:
    def test_user_links_has_self(self):
        uid = uuid4()
        links = user_links(uid)
        assert "self" in links
        assert str(uid) in links["self"].href

    def test_user_links_has_assignments(self):
        uid = uuid4()
        links = user_links(uid)
        assert "assignments" in links
        assert str(uid) in links["assignments"].href

    def test_user_links_has_attendance(self):
        uid = uuid4()
        links = user_links(uid)
        assert "attendance" in links

    def test_user_links_has_cotisations(self):
        uid = uuid4()
        links = user_links(uid)
        assert "cotisations" in links

    def test_discipline_links_has_self_and_accused(self):
        case_id = uuid4()
        user_id = uuid4()
        links = discipline_links(case_id, user_id)
        assert "self" in links
        assert "accused" in links
        assert str(case_id) in links["self"].href
        assert str(user_id) in links["accused"].href

    def test_assignment_links_has_event(self):
        aid = uuid4()
        uid = uuid4()
        eid = uuid4()
        links = assignment_links(aid, uid, eid)
        assert "event" in links
        assert str(eid) in links["event"].href

    def test_attendance_links_has_user(self):
        att_id = uuid4()
        uid = uuid4()
        links = attendance_links(att_id, uid)
        assert "user" in links
        assert str(uid) in links["user"].href


# ═══════════════════════════════════════════════════════════════════════════
#  ApiError / ErrorCode
# ═══════════════════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestApiError:
    def test_minimal_construction(self):
        err = ApiError(detail="Something went wrong")
        assert err.detail == "Something went wrong"
        assert err.code is None
        assert err.field is None
        assert err.error_id is None

    def test_with_code(self):
        err = ApiError(detail="Not found", code=ErrorCode.NOT_FOUND)
        assert err.code == "NOT_FOUND"

    def test_with_field(self):
        err = ApiError(detail="Invalid", code=ErrorCode.VALIDATION_ERROR, field="email")
        assert err.field == "email"

    def test_with_error_id(self):
        err = ApiError(detail="Internal error", code=ErrorCode.INTERNAL, error_id="req-abc123")
        assert err.error_id == "req-abc123"

    def test_json_serializable(self):
        err = ApiError(detail="Forbidden", code=ErrorCode.FORBIDDEN)
        data = err.model_dump()
        assert data["detail"] == "Forbidden"
        assert data["code"] == "FORBIDDEN"


@pytest.mark.unit
class TestErrorCode:
    def test_not_found(self):
        assert ErrorCode.NOT_FOUND == "NOT_FOUND"

    def test_forbidden(self):
        assert ErrorCode.FORBIDDEN == "FORBIDDEN"

    def test_conflict(self):
        assert ErrorCode.CONFLICT == "CONFLICT"

    def test_validation_error(self):
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"

    def test_unauthorized(self):
        assert ErrorCode.UNAUTHORIZED == "UNAUTHORIZED"

    def test_internal(self):
        assert ErrorCode.INTERNAL == "INTERNAL_SERVER_ERROR"

    def test_unprocessable(self):
        assert ErrorCode.UNPROCESSABLE == "UNPROCESSABLE"
