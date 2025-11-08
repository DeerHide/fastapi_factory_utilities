"""Tests for JWT bearer token objects."""

import datetime
from typing import Any

import pytest
from pydantic import ValidationError

from fastapi_factory_utilities.core.security.jwt.objects import (
    JWTPayload,
    validate_string_list_field,
    validate_timestamp_field,
)


class TestValidateStringListField:
    """Various tests for the validate_string_list_field function."""

    def test_with_space_separated_string(self) -> None:
        """Test validation with space-separated string."""
        result = validate_string_list_field("read write admin")
        assert result == ["read", "write", "admin"]

    def test_with_space_separated_string_uppercase(self) -> None:
        """Test validation with uppercase space-separated string converts to lowercase."""
        result = validate_string_list_field("READ WRITE ADMIN")
        assert result == ["read", "write", "admin"]

    def test_with_space_separated_string_mixed_case(self) -> None:
        """Test validation with mixed case space-separated string converts to lowercase."""
        result = validate_string_list_field("Read Write Admin")
        assert result == ["read", "write", "admin"]

    def test_with_list_of_strings(self) -> None:
        """Test validation with list of strings."""
        result = validate_string_list_field(["read", "write", "admin"])
        assert result == ["read", "write", "admin"]

    def test_with_list_of_strings_uppercase(self) -> None:
        """Test validation with uppercase list of strings converts to lowercase."""
        result = validate_string_list_field(["READ", "WRITE", "ADMIN"])
        assert result == ["read", "write", "admin"]

    def test_with_list_of_strings_mixed_case(self) -> None:
        """Test validation with mixed case list of strings converts to lowercase."""
        result = validate_string_list_field(["Read", "Write", "Admin"])
        assert result == ["read", "write", "admin"]

    def test_with_list_containing_none_values(self) -> None:
        """Test validation with list containing None values filters them out."""
        result = validate_string_list_field(["read", None, "write", None, "admin"])
        assert result == ["read", "write", "admin"]

    def test_with_list_containing_non_string_values(self) -> None:
        """Test validation with list containing non-string values converts them to strings."""
        result = validate_string_list_field(["read", 123, "write", True])
        assert result == ["read", "123", "write", "true"]

    def test_with_string_containing_extra_whitespace(self) -> None:
        """Test validation with string containing extra whitespace."""
        result = validate_string_list_field("  read   write  admin  ")
        assert result == ["read", "write", "admin"]

    def test_with_list_containing_whitespace_strings(self) -> None:
        """Test validation with list containing whitespace-only strings filters them out."""
        result = validate_string_list_field(["read", "  ", "write", "\t", "admin"])
        assert result == ["read", "write", "admin"]

    def test_with_empty_string_raises_value_error(self) -> None:
        """Test validation with empty string raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value: empty list after processing"):
            validate_string_list_field("")

    def test_with_empty_list_raises_value_error(self) -> None:
        """Test validation with empty list raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value: empty list after processing"):
            validate_string_list_field([])

    def test_with_list_containing_only_none_raises_value_error(self) -> None:
        """Test validation with list containing only None values raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value: empty list after processing"):
            validate_string_list_field([None, None, None])

    def test_with_list_containing_only_whitespace_raises_value_error(self) -> None:
        """Test validation with list containing only whitespace strings raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value: empty list after processing"):
            validate_string_list_field(["  ", "\t", "\n"])

    def test_with_invalid_type_raises_value_error(self) -> None:
        """Test validation with invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value type: expected str or list"):
            validate_string_list_field(123)

    def test_with_dict_raises_value_error(self) -> None:
        """Test validation with dict raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value type: expected str or list"):
            validate_string_list_field({"key": "value"})

    def test_with_single_string(self) -> None:
        """Test validation with single string."""
        result = validate_string_list_field("read")
        assert result == ["read"]

    def test_with_single_item_list(self) -> None:
        """Test validation with single item list."""
        result = validate_string_list_field(["read"])
        assert result == ["read"]


class TestValidateTimestampField:
    """Various tests for the validate_timestamp_field function."""

    def test_with_datetime_object(self) -> None:
        """Test validation with datetime object returns it as-is."""
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.UTC)
        result = validate_timestamp_field(dt)
        assert result == dt
        assert result.tzinfo == datetime.UTC

    def test_with_datetime_object_no_timezone(self) -> None:
        """Test validation with datetime without timezone assumes UTC."""
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
        result = validate_timestamp_field(dt)
        assert isinstance(result, datetime.datetime)
        # The datetime is returned as-is, but should be in UTC when used
        assert result == dt

    def test_with_integer_timestamp(self) -> None:
        """Test validation with integer Unix timestamp."""
        timestamp = 1704110400  # 2024-01-01 12:00:00 UTC
        result = validate_timestamp_field(timestamp)
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo == datetime.UTC
        assert result.year == 2024  # noqa: PLR2004
        assert result.month == 1
        assert result.day == 1

    def test_with_string_timestamp(self) -> None:
        """Test validation with string Unix timestamp."""
        timestamp_str = "1704110400"
        result = validate_timestamp_field(timestamp_str)
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo == datetime.UTC
        assert result.year == 2024  # noqa: PLR2004

    def test_with_string_timestamp_negative(self) -> None:
        """Test validation with negative string timestamp."""
        timestamp_str = "-1704110400"
        result = validate_timestamp_field(timestamp_str)
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo == datetime.UTC

    def test_with_invalid_string_timestamp_raises_value_error(self) -> None:
        """Test validation with invalid string timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Invalid timestamp string"):
            validate_timestamp_field("not-a-number")

    def test_with_invalid_integer_timestamp_raises_value_error(self) -> None:
        """Test validation with invalid integer timestamp raises ValueError."""
        # Use a timestamp that's too large for the platform (exceeds system time_t limits)
        invalid_timestamp = 2**62  # Very large timestamp that exceeds platform limits
        with pytest.raises(ValueError, match="Invalid timestamp value"):
            validate_timestamp_field(invalid_timestamp)

    def test_with_negative_integer_timestamp(self) -> None:
        """Test validation with negative integer timestamp."""
        timestamp = -1704110400
        result = validate_timestamp_field(timestamp)
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo == datetime.UTC

    def test_with_invalid_type_raises_value_error(self) -> None:
        """Test validation with invalid type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value type: expected int, str, or datetime"):
            validate_timestamp_field([])

    def test_with_dict_raises_value_error(self) -> None:
        """Test validation with dict raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value type: expected int, str, or datetime"):
            validate_timestamp_field({"timestamp": 123})

    def test_with_float_timestamp_raises_value_error(self) -> None:
        """Test validation with float timestamp raises ValueError."""
        with pytest.raises(ValueError, match="Invalid value type: expected int, str, or datetime"):
            validate_timestamp_field(1704110400.5)

    def test_with_zero_timestamp(self) -> None:
        """Test validation with zero timestamp."""
        result = validate_timestamp_field(0)
        assert isinstance(result, datetime.datetime)
        assert result.tzinfo == datetime.UTC
        # Zero timestamp is 1970-01-01 00:00:00 UTC
        assert result.year == 1970  # noqa: PLR2004
        assert result.month == 1
        assert result.day == 1


class TestJWTPayload:
    """Various tests for the JWTPayload class."""

    def test_valid_payload_creation(self) -> None:
        """Test creating a valid JWTPayload."""
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)
        nbf = now - datetime.timedelta(minutes=5)

        payload = JWTPayload(
            scope="read write",
            aud="api1 api2",
            iss="https://example.com",
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(nbf.timestamp()),
            sub="user123",
        )

        assert payload.scope == ["read", "write"]
        assert payload.aud == ["api1", "api2"]
        assert payload.iss == "https://example.com"
        assert payload.exp.tzinfo == datetime.UTC
        assert payload.iat.tzinfo == datetime.UTC
        assert payload.nbf.tzinfo == datetime.UTC
        assert payload.sub == "user123"

    def test_valid_payload_creation_with_list_fields(self) -> None:
        """Test creating a JWTPayload with list fields."""
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)

        payload = JWTPayload(
            scope=["read", "write", "admin"],
            aud=["api1", "api2"],
            iss="https://example.com",
            exp=exp,
            iat=now,
            nbf=now,
            sub="user123",
        )

        assert payload.scope == ["read", "write", "admin"]
        assert payload.aud == ["api1", "api2"]

    def test_valid_payload_creation_with_uppercase_fields(self) -> None:
        """Test creating a JWTPayload with uppercase fields converts to lowercase."""
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)

        payload = JWTPayload(
            scope="READ WRITE ADMIN",
            aud="API1 API2",
            iss="https://example.com",
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            sub="user123",
        )

        assert payload.scope == ["read", "write", "admin"]
        assert payload.aud == ["api1", "api2"]

    def test_payload_creation_with_string_timestamps(self) -> None:
        """Test creating a JWTPayload with string timestamps."""
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)

        payload = JWTPayload(
            scope="read",
            aud="api1",
            iss="https://example.com",
            exp=str(int(exp.timestamp())),
            iat=str(int(now.timestamp())),
            nbf=str(int(now.timestamp())),
            sub="user123",
        )

        assert isinstance(payload.exp, datetime.datetime)
        assert isinstance(payload.iat, datetime.datetime)
        assert isinstance(payload.nbf, datetime.datetime)
        assert payload.exp.tzinfo == datetime.UTC

    def test_payload_creation_with_datetime_objects(self) -> None:
        """Test creating a JWTPayload with datetime objects."""
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)

        payload = JWTPayload(
            scope="read",
            aud="api1",
            iss="https://example.com",
            exp=exp,
            iat=now,
            nbf=now,
            sub="user123",
        )

        assert payload.exp == exp
        assert payload.iat == now
        assert payload.nbf == now

    def test_payload_missing_required_field_raises_validation_error(self) -> None:
        """Test creating a JWTPayload with missing required field raises ValidationError."""
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(ValidationError):
            JWTPayload(
                scope="read",
                aud="api1",
                iss="https://example.com",
                exp=int(now.timestamp()),
                iat=int(now.timestamp()),
                nbf=int(now.timestamp()),
                # Missing sub field
            )

    def test_payload_with_empty_scope_raises_validation_error(self) -> None:
        """Test creating a JWTPayload with empty scope raises ValidationError."""
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(ValidationError):
            JWTPayload(
                scope="",
                aud="api1",
                iss="https://example.com",
                exp=int(now.timestamp()),
                iat=int(now.timestamp()),
                nbf=int(now.timestamp()),
                sub="user123",
            )

    def test_payload_with_empty_aud_raises_validation_error(self) -> None:
        """Test creating a JWTPayload with empty aud raises ValidationError."""
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(ValidationError):
            JWTPayload(
                scope="read",
                aud="",
                iss="https://example.com",
                exp=int(now.timestamp()),
                iat=int(now.timestamp()),
                nbf=int(now.timestamp()),
                sub="user123",
            )

    def test_payload_with_invalid_timestamp_raises_validation_error(self) -> None:
        """Test creating a JWTPayload with invalid timestamp raises ValidationError."""
        with pytest.raises(ValidationError):
            JWTPayload(
                scope="read",
                aud="api1",
                iss="https://example.com",
                exp="invalid-timestamp",
                iat=1704110400,
                nbf=1704110400,
                sub="user123",
            )

    def test_payload_with_invalid_scope_type_raises_validation_error(self) -> None:
        """Test creating a JWTPayload with invalid scope type raises ValidationError."""
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(ValidationError):
            JWTPayload(
                scope=123,  # type: ignore[arg-type]
                aud="api1",
                iss="https://example.com",
                exp=int(now.timestamp()),
                iat=int(now.timestamp()),
                nbf=int(now.timestamp()),
                sub="user123",
            )

    def test_payload_extra_fields_ignored(self) -> None:
        """Test that extra fields in JWTPayload are ignored."""
        now = datetime.datetime.now(tz=datetime.UTC)

        payload = JWTPayload(
            scope="read",
            aud="api1",
            iss="https://example.com",
            exp=int(now.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            sub="user123",
            extra_field="should be ignored",  # type: ignore[arg-type]
            another_extra=123,  # type: ignore[arg-type]
        )

        # Extra fields should not be accessible
        assert not hasattr(payload, "extra_field")
        assert not hasattr(payload, "another_extra")

    def test_payload_is_frozen(self) -> None:
        """Test that JWTPayload is frozen and cannot be modified."""
        now = datetime.datetime.now(tz=datetime.UTC)

        payload = JWTPayload(
            scope="read",
            aud="api1",
            iss="https://example.com",
            exp=int(now.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            sub="user123",
        )

        # Attempting to modify should raise an error
        with pytest.raises(Exception):  # Pydantic raises ValidationError or TypeError
            payload.sub = "new_user"  # type: ignore[misc]

    def test_payload_model_validate(self) -> None:
        """Test creating JWTPayload using model_validate."""
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)

        data: dict[str, Any] = {
            "scope": "read write",
            "aud": "api1 api2",
            "iss": "https://example.com",
            "exp": int(exp.timestamp()),
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "sub": "user123",
        }

        payload = JWTPayload.model_validate(data)

        assert payload.scope == ["read", "write"]
        assert payload.aud == ["api1", "api2"]
        assert payload.iss == "https://example.com"
        assert payload.sub == "user123"

    def test_payload_model_validate_json(self) -> None:
        """Test creating JWTPayload using model_validate_json."""
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)

        json_data = f"""{{
            "scope": "read write",
            "aud": "api1 api2",
            "iss": "https://example.com",
            "exp": {int(exp.timestamp())},
            "iat": {int(now.timestamp())},
            "nbf": {int(now.timestamp())},
            "sub": "user123"
        }}"""

        payload = JWTPayload.model_validate_json(json_data)

        assert payload.scope == ["read", "write"]
        assert payload.aud == ["api1", "api2"]
        assert payload.iss == "https://example.com"
        assert payload.sub == "user123"

    def test_payload_model_dump(self) -> None:
        """Test serializing JWTPayload using model_dump."""
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)

        payload = JWTPayload(
            scope="read write",
            aud="api1 api2",
            iss="https://example.com",
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            sub="user123",
        )

        dumped = payload.model_dump()

        assert isinstance(dumped, dict)
        assert dumped["scope"] == ["read", "write"]
        assert dumped["aud"] == ["api1", "api2"]
        assert dumped["iss"] == "https://example.com"
        assert dumped["sub"] == "user123"
        assert isinstance(dumped["exp"], datetime.datetime)
        assert isinstance(dumped["iat"], datetime.datetime)
        assert isinstance(dumped["nbf"], datetime.datetime)

    def test_payload_model_dump_json(self) -> None:
        """Test serializing JWTPayload using model_dump_json."""
        now = datetime.datetime.now(tz=datetime.UTC)
        exp = now + datetime.timedelta(hours=1)

        payload = JWTPayload(
            scope="read write",
            aud="api1 api2",
            iss="https://example.com",
            exp=int(exp.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            sub="user123",
        )

        json_str = payload.model_dump_json()

        assert isinstance(json_str, str)
        assert "read" in json_str
        assert "write" in json_str
        assert "api1" in json_str
        assert "user123" in json_str

    def test_payload_with_single_scope(self) -> None:
        """Test creating a JWTPayload with single scope."""
        now = datetime.datetime.now(tz=datetime.UTC)

        payload = JWTPayload(
            scope="read",
            aud="api1",
            iss="https://example.com",
            exp=int(now.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            sub="user123",
        )

        assert payload.scope == ["read"]

    def test_payload_with_single_aud(self) -> None:
        """Test creating a JWTPayload with single audience."""
        now = datetime.datetime.now(tz=datetime.UTC)

        payload = JWTPayload(
            scope="read",
            aud="api1",
            iss="https://example.com",
            exp=int(now.timestamp()),
            iat=int(now.timestamp()),
            nbf=int(now.timestamp()),
            sub="user123",
        )

        assert payload.aud == ["api1"]
