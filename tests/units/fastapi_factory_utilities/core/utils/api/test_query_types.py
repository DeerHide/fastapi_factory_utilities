"""Unit tests for query types, enums, and resolver coercion."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum, IntEnum, IntFlag, StrEnum, auto
from typing import Any, NewType, cast

import pytest
from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from starlette.requests import Request

from fastapi_factory_utilities.core.utils.api import (
    QueryAbstract,
    QueryField,
    QueryFieldName,
    QueryFieldOperatorEnum,
    QueryResolver,
    QuerySort,
    QuerySortDirectionEnum,
    RawQueryFieldName,
    RawQuerySort,
)


def _request(query_string: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": query_string.encode("utf-8"),
        }
    )


_TestRealmId = NewType("_TestRealmId", uuid.UUID)
_TestChannelId = NewType("_TestChannelId", str)


class _NewTypeUuidQuery(QueryAbstract):
    """Query model with a ``typing.NewType`` wrapping ``uuid.UUID`` (Velmios-style ``RealmId``)."""

    realm_id: QueryField[_TestRealmId] | None = Field(default=None)


class _NewTypeStrQuery(QueryAbstract):
    """Query model with ``typing.NewType`` over ``str`` (e.g. YouTube channel id)."""

    channel_id: QueryField[_TestChannelId] | None = Field(default=None)


class _StrEnumKind(StrEnum):
    """Sample :class:`enum.StrEnum` for coercion tests."""

    SHORT = "short"
    LONG = "long"


class _IntEnumRank(IntEnum):
    """Sample :class:`enum.IntEnum` for coercion tests."""

    FIRST = 1
    SECOND = 2


class _PlainLabels(Enum):
    """Plain :class:`enum.Enum` with string values."""

    ALPHA = "alpha"
    BETA = "beta"


class _Access(IntFlag):
    """Sample :class:`enum.IntFlag` (``auto()`` values 1, 2, 4, …)."""

    R = auto()
    W = auto()
    X = auto()


_TestVideoKindNt = NewType("_TestVideoKindNt", _StrEnumKind)


class _EnumCoerceQuery(QueryAbstract):
    """Query model mixing enum kinds for :meth:`QueryResolver.from_model` coercion tests."""

    kind: QueryField[_StrEnumKind] | None = Field(default=None)
    rank: QueryField[_IntEnumRank] | None = Field(default=None)
    label: QueryField[_PlainLabels] | None = Field(default=None)
    access: QueryField[_Access] | None = Field(default=None)
    vid: QueryField[_TestVideoKindNt] | None = Field(default=None)


class _SampleQuery(QueryAbstract):
    """Concrete query model for :meth:`QueryResolver.from_model` tests."""

    label: str | None = None
    score: int | None = None


class _NestedObject1Filter(BaseModel):
    """Nested filter segment for dotted query keys."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    field1: QueryField[str] | None = Field(default=None)


class _RootNestedQuery(QueryAbstract):
    """Root query with nested filter model (``object1.field1``)."""

    object1: _NestedObject1Filter | None = Field(default=None)


class _FlatAliasDottedQuery(QueryAbstract):
    """Flat field: dotted key only via ``validation_alias``."""

    model_config = ConfigDict(populate_by_name=True)

    object1__field1: QueryField[str] | None = Field(
        default=None,
        validation_alias=AliasChoices("object1.field1"),
    )


class _CycleNested(BaseModel):
    """Self-referential nested model (cycle guard)."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    child: _CycleNested | None = Field(default=None)
    leaf: QueryField[str] | None = Field(default=None)


class _CycleRootQuery(QueryAbstract):
    """Query with a nested graph that cycles on ``child``."""

    node: _CycleNested | None = Field(default=None)


class TestQueryFieldExtract:
    """Tests for :meth:`QueryField.extract_field_and_operator_from_query_field`."""

    @pytest.mark.parametrize(
        ("raw", "expected_name", "expected_op"),
        [
            ("field1", "field1", QueryFieldOperatorEnum.EQ),
            ("object1.field1", "object1.field1", QueryFieldOperatorEnum.EQ),
            ("field1[gt]", "field1", QueryFieldOperatorEnum.GT),
            ("field1[lt]", "field1", QueryFieldOperatorEnum.LT),
            ("field1[gte]", "field1", QueryFieldOperatorEnum.GTE),
            ("field1[lte]", "field1", QueryFieldOperatorEnum.LTE),
            ("field1[eq]", "field1", QueryFieldOperatorEnum.EQ),
            ("field1[neq]", "field1", QueryFieldOperatorEnum.NEQ),
            ("field1[in]", "field1", QueryFieldOperatorEnum.IN),
            ("field1[nin]", "field1", QueryFieldOperatorEnum.NIN),
            ("field1[contains]", "field1", QueryFieldOperatorEnum.CONTAINS),
            ("field1[not_contains]", "field1", QueryFieldOperatorEnum.NOT_CONTAINS),
            ("field1[starts_with]", "field1", QueryFieldOperatorEnum.STARTS_WITH),
            ("field1[ends_with]", "field1", QueryFieldOperatorEnum.ENDS_WITH),
        ],
    )
    def test_operators(self, raw: str, expected_name: str, expected_op: QueryFieldOperatorEnum) -> None:
        """Each documented operator maps to the correct enum."""
        name, op = QueryField.extract_field_and_operator_from_query_field(raw)
        assert str(name) == expected_name
        assert op is expected_op

    @pytest.mark.parametrize(
        "bad",
        [
            "field[",
            "field]",
            "field[gt",
            "fieldgt]",
            "field[[gt]]",
            "field[badop]",
            "field[gt]extra",
        ],
    )
    def test_malformed_or_unknown_operator(self, bad: str) -> None:
        """Malformed bracket forms or unknown operators raise ``ValueError``."""
        with pytest.raises(ValueError):
            QueryField.extract_field_and_operator_from_query_field(bad)


class TestQueryFieldNameAndRaw:
    """Validation for field name types."""

    def test_query_field_name_validates_on_construction(self) -> None:
        """``QueryFieldName`` enforces length and character rules."""
        QueryFieldName("ab")
        with pytest.raises(ValueError):
            QueryFieldName("a")
        with pytest.raises(ValueError):
            QueryFieldName("bad name")

    def test_raw_query_field_name_rejects_invalid(self) -> None:
        """``RawQueryFieldName`` rejects invalid characters."""
        RawQueryFieldName("ok[in]")
        with pytest.raises(ValueError):
            RawQueryFieldName("no spaces")


class TestQuerySort:
    """Tests for sort parsing."""

    @pytest.mark.parametrize(
        ("raw", "name", "direction"),
        [
            ("name", "name", QuerySortDirectionEnum.ASCENDING),
            ("-name", "name", QuerySortDirectionEnum.DESCENDING),
            ("+age", "age", QuerySortDirectionEnum.ASCENDING),
        ],
    )
    def test_directions(self, raw: str, name: str, direction: QuerySortDirectionEnum) -> None:
        """Prefix sets ascending or descending; default is ascending."""
        qs = QuerySort.model_validate(RawQuerySort(raw))
        assert str(qs.name) == name
        assert qs.direction is direction

    def test_raw_query_sort_invalid(self) -> None:
        """Invalid raw sort strings are rejected."""
        with pytest.raises(ValueError):
            RawQuerySort("+")


class TestCoerceValue:
    """Coercion is exercised via :meth:`QueryResolver.resolve`."""

    def test_scalar_and_list_int_via_resolver(self) -> None:
        """Scalar and ``[in]`` list values coerce to ``int``."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("num"), int)
        resolver.add_authorized_field(QueryFieldName("ids"), int)
        req = _request("num=42&ids[in]=1&ids[in]=2&ids[in]=3")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert fields["num"].operations[0].value == 42  # noqa: PLR2004
        assert fields["ids"].operations[0].value == [1, 2, 3]

    def test_bool_via_resolver(self) -> None:
        """``true`` / ``0`` coerce to booleans."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("active"), bool)
        resolver.resolve(_request("active=true"))
        assert cast(dict[str, QueryField[Any]], resolver.fields)["active"].operations[0].value is True
        r2 = QueryResolver()
        r2.add_authorized_field(QueryFieldName("active"), bool)
        r2.resolve(_request("active=0"))
        assert cast(dict[str, QueryField[Any]], r2.fields)["active"].operations[0].value is False

    def test_invalid_int_raises_via_resolver(self) -> None:
        """Non-numeric string for ``int`` field raises ``ValueError``."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("count"), int)
        with pytest.raises(ValueError, match="Invalid integer"):
            resolver.resolve(_request("count=x"))

    def test_datetime_iso_via_typeadapter_fallback(self) -> None:
        """Leaf types such as ``datetime`` coerce via :class:`~pydantic.TypeAdapter`."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("created"), datetime)
        resolver.resolve(_request("created=2024-01-15T12:30:00"))
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        value = fields["created"].operations[0].value
        assert value == datetime(2024, 1, 15, 12, 30, 0)


class TestCoerceEnumFlagAndFallback:
    """``Enum`` / ``Flag`` coercion and invalid enum raises ``ValueError`` (not ``TypeError``)."""

    def test_strenum_by_value_and_member_name(self) -> None:
        """:class:`enum.StrEnum` accepts the wire value and the member name."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("kind"), _StrEnumKind)
        resolver.resolve(_request("kind=short"))
        assert cast(dict[str, QueryField[Any]], resolver.fields)["kind"].operations[0].value is _StrEnumKind.SHORT
        r2 = QueryResolver()
        r2.add_authorized_field(QueryFieldName("kind"), _StrEnumKind)
        r2.resolve(_request("kind=LONG"))
        assert cast(dict[str, QueryField[Any]], r2.fields)["kind"].operations[0].value is _StrEnumKind.LONG

    def test_intenum_by_decimal_string_and_name(self) -> None:
        """:class:`enum.IntEnum` accepts numeric strings and member names."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("rank"), _IntEnumRank)
        resolver.resolve(_request("rank=2"))
        assert cast(dict[str, QueryField[Any]], resolver.fields)["rank"].operations[0].value is _IntEnumRank.SECOND
        r2 = QueryResolver()
        r2.add_authorized_field(QueryFieldName("rank"), _IntEnumRank)
        r2.resolve(_request("rank=FIRST"))
        assert cast(dict[str, QueryField[Any]], r2.fields)["rank"].operations[0].value is _IntEnumRank.FIRST

    def test_plain_enum_by_value(self) -> None:
        """Non-:class:`enum.StrEnum` :class:`enum.Enum` coerces via member name or value."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("label"), _PlainLabels)
        resolver.resolve(_request("label=beta"))
        assert cast(dict[str, QueryField[Any]], resolver.fields)["label"].operations[0].value is _PlainLabels.BETA

    def test_intflag_numeric_mask_and_composite_names(self) -> None:
        """:class:`enum.IntFlag` accepts an integer mask or combined member names."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("access"), _Access)
        resolver.resolve(_request("access=3"))
        v = cast(dict[str, QueryField[Any]], resolver.fields)["access"].operations[0].value
        assert v == (_Access.R | _Access.W)
        r2 = QueryResolver()
        r2.add_authorized_field(QueryFieldName("access"), _Access)
        r2.resolve(_request("access=R|W"))
        v2 = cast(dict[str, QueryField[Any]], r2.fields)["access"].operations[0].value
        assert v2 == (_Access.R | _Access.W)

    def test_newtype_over_strenum_recurses(self) -> None:
        """``typing.NewType`` over an enum coerces through ``__supertype__``."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("vid"), _TestVideoKindNt)
        resolver.resolve(_request("vid=long"))
        assert cast(dict[str, QueryField[Any]], resolver.fields)["vid"].operations[0].value == _StrEnumKind.LONG

    def test_invalid_strenum_raises_valueerror(self) -> None:
        """Unknown enum token raises ``ValueError``, not ``TypeError``."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("kind"), _StrEnumKind)
        with pytest.raises(ValueError, match="Invalid _StrEnumKind"):
            resolver.resolve(_request("kind=not-a-member"))

    def test_from_model_registers_enum_leaf_types(self) -> None:
        """``from_model`` + ``resolve`` coerces ``QueryField`` enums and ``NewType`` over enum."""
        resolver = QueryResolver().from_model(_EnumCoerceQuery)
        req = _request("kind=short&rank=SECOND&label=alpha&access=7&vid=LONG&page=0&page_size=10")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert fields["kind"].operations[0].value is _StrEnumKind.SHORT
        assert fields["rank"].operations[0].value is _IntEnumRank.SECOND
        assert fields["label"].operations[0].value is _PlainLabels.ALPHA
        assert fields["access"].operations[0].value == (_Access.R | _Access.W | _Access.X)
        assert fields["vid"].operations[0].value == _StrEnumKind.LONG


class TestQueryResolver:
    """Tests for :class:`QueryResolver`."""

    def test_in_collects_multiple_values(self) -> None:
        """Repeated ``field[in]=`` keys produce a list of strings then coercion."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("field1"), int)
        req = _request("field1[in]=1&field1[in]=2&field1[in]=3")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert list(fields.keys()) == ["field1"]
        assert fields["field1"].operations[0].operator is QueryFieldOperatorEnum.IN
        assert fields["field1"].operations[0].value == [1, 2, 3]

    def test_non_in_last_value_wins(self) -> None:
        """Duplicate keys for non-list operators keep the last value."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("status"), str)
        req = _request("status=a&status=b")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert fields["status"].operations[0].value == "b"

    def test_range_two_raw_keys(self) -> None:
        """Same base field with two operators: both appear under one :class:`QueryField` in request order."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("age"), int)
        req = _request("age[gt]=10&age[lt]=20")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert set(fields) == {"age"}
        ops = fields["age"].operations
        assert len(ops) == 2  # noqa: PLR2004
        assert ops[0].operator is QueryFieldOperatorEnum.GT
        assert ops[0].value == 10  # noqa: PLR2004
        assert ops[1].operator is QueryFieldOperatorEnum.LT
        assert ops[1].value == 20  # noqa: PLR2004

    def test_unauthorized_strict_raises(self) -> None:
        """Strict mode raises for unknown base field names."""
        resolver = QueryResolver(raise_on_unauthorized_field=True)
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("other=x")
        with pytest.raises(ValueError, match="Unauthorized field"):
            resolver.resolve(req)

    def test_unauthorized_permissive_drops(self) -> None:
        """Permissive mode omits unknown fields."""
        resolver = QueryResolver(raise_on_unauthorized_field=False)
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("name=ok&other=x")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert set(fields) == {"name"}
        assert fields["name"].operations[0].value == "ok"

    def test_excluded_params_not_in_fields(self) -> None:
        """Pagination and sort keys are not returned as filters; ``sort`` fills :attr:`sorts`."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("page=2&page_size=5&sort=name&name=Ann")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert set(fields) == {"name"}
        assert len(resolver.sorts) == 1
        assert str(resolver.sorts[0].name) == "name"
        assert resolver.sorts[0].direction is QuerySortDirectionEnum.ASCENDING

    def test_multiple_sort_preserves_order_and_direction(self) -> None:
        """Repeated ``sort`` parameters stay ordered; ``-`` / ``+`` set direction."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("name"), str)
        resolver.add_authorized_field(QueryFieldName("age"), int)
        req = _request("sort=-name&sort=%2Bage")
        resolver.resolve(req)
        assert len(resolver.sorts) == 2  # noqa: PLR2004
        assert str(resolver.sorts[0].name) == "name"
        assert resolver.sorts[0].direction is QuerySortDirectionEnum.DESCENDING
        assert str(resolver.sorts[1].name) == "age"
        assert resolver.sorts[1].direction is QuerySortDirectionEnum.ASCENDING

    def test_unauthorized_sort_strict_raises(self) -> None:
        """Strict mode raises for sort tokens whose field is not authorized."""
        resolver = QueryResolver(raise_on_unauthorized_field=True)
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("sort=other")
        with pytest.raises(ValueError, match="Unauthorized sort field"):
            resolver.resolve(req)

    def test_unauthorized_sort_permissive_drops_token(self) -> None:
        """Permissive mode keeps authorized sort tokens and drops unknown ones."""
        resolver = QueryResolver(raise_on_unauthorized_field=False)
        resolver.add_authorized_field(QueryFieldName("name"), str)
        req = _request("sort=name&sort=other")
        resolver.resolve(req)
        assert len(resolver.sorts) == 1
        assert str(resolver.sorts[0].name) == "name"

    def test_from_model_registers_types(self) -> None:
        """``from_model`` reads field names and unwraps optional annotations."""
        resolver = QueryResolver().from_model(_SampleQuery)
        req = _request("label=hi&score=7&page=1&page_size=10")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        assert fields["label"].operations[0].value == "hi"
        assert fields["score"].operations[0].value == 7  # noqa: PLR2004

    def test_from_model_newtype_uuid_string_coerces_to_uuid(self) -> None:
        """Query strings for ``NewType(..., uuid.UUID)`` must become ``UUID``, not ``str`` (Mongo parity)."""
        expected = uuid.uuid4()
        resolver = QueryResolver().from_model(_NewTypeUuidQuery)
        req = _request(f"realm_id={expected}&page=0&page_size=10")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        value = fields["realm_id"].operations[0].value
        assert value == expected
        assert isinstance(value, uuid.UUID)
        assert not isinstance(value, str)

    def test_from_model_newtype_uuid_invalid_raises(self) -> None:
        """Invalid UUID strings for a ``NewType``-UUID field raise ``ValueError``."""
        resolver = QueryResolver().from_model(_NewTypeUuidQuery)
        req = _request("realm_id=not-a-uuid&page=0&page_size=10")
        with pytest.raises(ValueError, match="Invalid UUID"):
            resolver.resolve(req)

    def test_from_model_newtype_str_coerces_via_constructor(self) -> None:
        """``NewType(..., str)`` query values coerce like ``str`` (runtime value is plain ``str``)."""
        raw = "UCv1E9DE0fopEQ-SVdlN07IQ"
        resolver = QueryResolver().from_model(_NewTypeStrQuery)
        req = _request(f"channel_id={raw}&page=0&page_size=10")
        resolver.resolve(req)
        fields = cast(dict[str, QueryField[Any]], resolver.fields)
        value = fields["channel_id"].operations[0].value
        assert value == raw
        assert isinstance(value, str)

    def test_coerce_failure_raises(self) -> None:
        """Invalid value for declared ``int`` field raises ``ValueError``."""
        resolver = QueryResolver()
        resolver.add_authorized_field(QueryFieldName("count"), int)
        req = _request("count=notint")
        with pytest.raises(ValueError, match="Invalid integer"):
            resolver.resolve(req)

    def test_from_model_nested_registers_dotted_query_key(self) -> None:
        """Nested ``BaseModel`` field registers ``parent.child`` for :meth:`QueryResolver.resolve`."""
        resolver = QueryResolver().from_model(_RootNestedQuery)
        req = _request("object1.field1=abc&page=0&page_size=10")
        resolver.resolve(req)
        key = QueryFieldName("object1.field1")
        assert key in resolver.fields
        assert resolver.fields[key].operations[0].value == "abc"

    def test_from_model_validation_alias_registers_dotted_key(self) -> None:
        """Leaf field with string ``validation_alias`` registers the dotted query name."""
        resolver = QueryResolver().from_model(_FlatAliasDottedQuery)
        req = _request("object1.field1=xyz&page=0&page_size=10")
        resolver.resolve(req)
        key = QueryFieldName("object1.field1")
        assert key in resolver.fields
        assert resolver.fields[key].operations[0].value == "xyz"

    def test_from_model_populate_by_name_also_authorizes_python_field_name(self) -> None:
        """With ``populate_by_name=True``, both alias and Python names are authorized."""
        resolver = QueryResolver().from_model(_FlatAliasDottedQuery)
        req = _request("object1__field1=via-python-name&page=0&page_size=10")
        resolver.resolve(req)
        key = QueryFieldName("object1__field1")
        assert key in resolver.fields
        assert resolver.fields[key].operations[0].value == "via-python-name"

    def test_from_model_cycle_on_nested_model_terminates(self) -> None:
        """Recursive model graphs do not loop forever; first-level leaves still register."""
        resolver = QueryResolver().from_model(_CycleRootQuery)
        req = _request("node.leaf=ok&page=0&page_size=10")
        resolver.resolve(req)
        assert QueryFieldName("node.leaf") in resolver.fields
        assert resolver.fields[QueryFieldName("node.leaf")].operations[0].value == "ok"
