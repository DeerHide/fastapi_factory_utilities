"""Unit tests for sparse fieldset projection (``fields`` query param)."""

from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from pytest import fixture, raises

from fastapi_factory_utilities.core.utils.api import fields_query_param, parse_fields_param, project


class TestParseFieldsParam:
    """Tests for :func:`parse_fields_param`."""

    def test_comma_separated_values(self) -> None:
        """Comma-separated tokens are split and normalized."""
        assert parse_fields_param(["name, tasks[].name"]) == ["name", "tasks.name"]

    def test_repeated_values(self) -> None:
        """Repeated query values are merged."""
        assert parse_fields_param(["name", "tasks[].name"]) == ["name", "tasks.name"]

    def test_both_comma_and_repeated(self) -> None:
        """Both comma-separated and repeated values are accepted."""
        assert parse_fields_param(["name,title", "book_type"]) == ["name", "title", "book_type"]

    def test_strips_bracket_notation(self) -> None:
        """``[]`` list notation is stripped from segments."""
        assert parse_fields_param(["tasks[].name"]) == ["tasks.name"]

    def test_drops_empty_tokens(self) -> None:
        """Empty tokens from trailing commas are dropped."""
        assert parse_fields_param(["name,,title"]) == ["name", "title"]

    def test_empty_input_returns_empty_list(self) -> None:
        """No values yields an empty path list."""
        assert not parse_fields_param([])

    def test_malformed_path_raises(self) -> None:
        """Empty path segments raise ``ValueError``."""
        with raises(ValueError, match="Invalid field path"):
            parse_fields_param(["name..title"])


class TestProject:
    """Tests for :func:`project`."""

    def test_empty_paths_returns_data_unchanged(self) -> None:
        """No paths returns the original payload."""
        data = [{"id": "1", "name": "Ada"}]
        assert project(data, []) is data

    def test_flat_selection(self) -> None:
        """Top-level scalar fields are kept."""
        data = [{"id": "1", "name": "Ada", "title": "Book"}]
        assert project(data, ["name"]) == [{"id": "1", "name": "Ada"}]

    def test_always_includes_id_on_search_items(self) -> None:
        """Each search result item keeps ``id`` even when not requested."""
        data = [{"id": "1", "name": "Ada"}, {"id": "2", "name": "Bob"}]
        assert project(data, ["name"]) == [{"id": "1", "name": "Ada"}, {"id": "2", "name": "Bob"}]

    def test_nested_dict(self) -> None:
        """Nested dotted paths project into nested objects."""
        data = [{"id": "1", "address": {"city": "Paris", "street": "Main"}}]
        assert project(data, ["address.city"]) == [{"id": "1", "address": {"city": "Paris"}}]

    def test_nested_list_via_bracket_notation(self) -> None:
        """List elements are projected element-wise (``tasks.name``)."""
        data = [{"id": "1", "tasks": [{"name": "t1", "done": True}, {"name": "t2", "done": False}]}]
        assert project(data, ["tasks.name"]) == [{"id": "1", "tasks": [{"name": "t1"}, {"name": "t2"}]}]

    def test_absent_field_is_silent_no_op(self) -> None:
        """Unknown paths do not add keys."""
        data = [{"id": "1", "name": "Ada"}]
        assert project(data, ["missing"]) == [{"id": "1"}]

    def test_conflicting_prefix_paths_raise(self) -> None:
        """Conflicting prefix paths raise ``ValueError``."""
        data = [{"id": "1", "address": {"city": "Paris"}}]
        with raises(ValueError, match="conflicts"):
            project(data, ["address", "address.city"])

    def test_single_dict_payload(self) -> None:
        """A single dict payload is supported."""
        data = {"id": "1", "name": "Ada", "title": "Book"}
        assert project(data, ["name"]) == {"id": "1", "name": "Ada"}


class TestFieldsQueryParam:
    """Tests for :func:`fields_query_param` FastAPI dependency."""

    @fixture(name="fields_app")
    def fields_app_fixture(self) -> FastAPI:
        """Create a FastAPI app exposing the ``fields`` dependency."""
        app = FastAPI()

        @app.get("/")
        def read_fields(fields: Annotated[list[str], Depends(fields_query_param)]) -> list[str]:
            return fields

        return app

    def test_dependency_parses_repeated_param(self, fields_app: FastAPI) -> None:
        """Repeated ``fields`` query values are parsed."""
        client = TestClient(fields_app)
        response = client.get("/?fields=name&fields=tasks[].name")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == ["name", "tasks.name"]

    def test_dependency_parses_comma_separated_param(self, fields_app: FastAPI) -> None:
        """Comma-separated ``fields`` values are parsed."""
        client = TestClient(fields_app)
        response = client.get("/?fields=name,title")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == ["name", "title"]

    def test_dependency_returns_empty_when_omitted(self, fields_app: FastAPI) -> None:
        """Missing ``fields`` yields an empty list."""
        client = TestClient(fields_app)
        response = client.get("/")
        assert response.status_code == HTTPStatus.OK
        assert response.json() == []
