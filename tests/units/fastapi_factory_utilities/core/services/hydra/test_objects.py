"""Unit tests for Hydra objects."""

import json
from typing import Any

import pytest
from pydantic import ValidationError

from fastapi_factory_utilities.core.services.hydra.objects import HydraTokenIntrospectObject


class TestHydraTokenIntrospectObject:
    """Unit tests for HydraTokenIntrospectObject."""

    def test_valid_creation_with_all_required_fields(self) -> None:
        """Test valid creation with all required fields."""
        # Arrange
        active = True
        aud = ["audience1", "audience2"]
        client_id = "test_client_id"
        exp = 1234567890
        iat = 1234567890
        iss = "https://hydra.example.com"
        nbf = 1234567890
        scope = "read write"
        sub = "test_subject"
        token_type = "Bearer"
        token_use = "access"

        # Act
        introspect_object = HydraTokenIntrospectObject(
            active=active,
            aud=aud,
            client_id=client_id,
            exp=exp,
            iat=iat,
            iss=iss,
            nbf=nbf,
            scope=scope,
            sub=sub,
            token_type=token_type,
            token_use=token_use,
        )

        # Assert
        assert introspect_object.active == active
        assert introspect_object.aud == aud
        assert introspect_object.client_id == client_id
        assert introspect_object.exp == exp
        assert introspect_object.iat == iat
        assert introspect_object.iss == iss
        assert introspect_object.nbf == nbf
        assert introspect_object.scope == scope
        assert introspect_object.sub == sub
        assert introspect_object.token_type == token_type
        assert introspect_object.token_use == token_use
        assert introspect_object.ext is None
        assert introspect_object.obfuscated_subject is None
        assert introspect_object.username is None

    def test_valid_creation_with_optional_fields(self) -> None:
        """Test valid creation with optional fields populated."""
        # Arrange
        active = True
        aud = ["audience1"]
        client_id = "test_client_id"
        exp = 1234567890
        ext = {"key1": "value1", "key2": "value2"}
        iat = 1234567890
        iss = "https://hydra.example.com"
        nbf = 1234567890
        obfuscated_subject = "obfuscated_subject_123"
        scope = "read"
        sub = "test_subject"
        token_type = "Bearer"
        token_use = "access"
        username = "test_user"

        # Act
        introspect_object = HydraTokenIntrospectObject(
            active=active,
            aud=aud,
            client_id=client_id,
            exp=exp,
            ext=ext,
            iat=iat,
            iss=iss,
            nbf=nbf,
            obfuscated_subject=obfuscated_subject,
            scope=scope,
            sub=sub,
            token_type=token_type,
            token_use=token_use,
            username=username,
        )

        # Assert
        assert introspect_object.ext == ext
        assert introspect_object.obfuscated_subject == obfuscated_subject
        assert introspect_object.username == username

    def test_missing_active_raises_validation_error(self) -> None:
        """Test that missing active raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HydraTokenIntrospectObject(
                aud=["audience1"],
                client_id="test_client_id",
                exp=1234567890,
                iat=1234567890,
                iss="https://hydra.example.com",
                nbf=1234567890,
                scope="read",
                sub="test_subject",
                token_type="Bearer",
                token_use="access",
            )  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("active",)

    def test_missing_client_id_raises_validation_error(self) -> None:
        """Test that missing client_id raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HydraTokenIntrospectObject(
                active=True,
                aud=["audience1"],
                exp=1234567890,
                iat=1234567890,
                iss="https://hydra.example.com",
                nbf=1234567890,
                scope="read",
                sub="test_subject",
                token_type="Bearer",
                token_use="access",
            )  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("client_id",)

    def test_invalid_active_type_raises_validation_error(self) -> None:
        """Test that invalid active type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HydraTokenIntrospectObject(
                active="not_a_boolean",  # type: ignore[arg-type]
                aud=["audience1"],
                client_id="test_client_id",
                exp=1234567890,
                iat=1234567890,
                iss="https://hydra.example.com",
                nbf=1234567890,
                scope="read",
                sub="test_subject",
                token_type="Bearer",
                token_use="access",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("active",)

    def test_invalid_aud_type_raises_validation_error(self) -> None:
        """Test that invalid aud type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HydraTokenIntrospectObject(
                active=True,
                aud="not_a_list",  # type: ignore[arg-type]
                client_id="test_client_id",
                exp=1234567890,
                iat=1234567890,
                iss="https://hydra.example.com",
                nbf=1234567890,
                scope="read",
                sub="test_subject",
                token_type="Bearer",
                token_use="access",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("aud",)

    def test_invalid_exp_type_raises_validation_error(self) -> None:
        """Test that invalid exp type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HydraTokenIntrospectObject(
                active=True,
                aud=["audience1"],
                client_id="test_client_id",
                exp="not_an_int",  # type: ignore[arg-type]
                iat=1234567890,
                iss="https://hydra.example.com",
                nbf=1234567890,
                scope="read",
                sub="test_subject",
                token_type="Bearer",
                token_use="access",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("exp",)

    def test_invalid_ext_type_raises_validation_error(self) -> None:
        """Test that invalid ext type raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            HydraTokenIntrospectObject(
                active=True,
                aud=["audience1"],
                client_id="test_client_id",
                exp=1234567890,
                ext="not_a_dict",  # type: ignore[arg-type]
                iat=1234567890,
                iss="https://hydra.example.com",
                nbf=1234567890,
                scope="read",
                sub="test_subject",
                token_type="Bearer",
                token_use="access",
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("ext",)

    def test_extra_fields_are_ignored(self) -> None:
        """Test that extra fields are ignored due to extra='ignore' config."""
        active = True
        aud = ["audience1"]
        client_id = "test_client_id"
        exp = 1234567890
        iat = 1234567890
        iss = "https://hydra.example.com"
        nbf = 1234567890
        scope = "read"
        sub = "test_subject"
        token_type = "Bearer"
        token_use = "access"

        introspect_object = HydraTokenIntrospectObject(
            active=active,
            aud=aud,
            client_id=client_id,
            exp=exp,
            iat=iat,
            iss=iss,
            nbf=nbf,
            scope=scope,
            sub=sub,
            token_type=token_type,
            token_use=token_use,
            extra_field="should be ignored",  # type: ignore[call-arg]
        )

        assert introspect_object.active == active
        assert not hasattr(introspect_object, "extra_field")

    def test_model_dump(self) -> None:
        """Test model serialization using model_dump."""
        active = True
        aud = ["audience1", "audience2"]
        client_id = "test_client_id"
        exp = 1234567890
        iat = 1234567890
        iss = "https://hydra.example.com"
        nbf = 1234567890
        scope = "read write"
        sub = "test_subject"
        token_type = "Bearer"
        token_use = "access"

        introspect_object = HydraTokenIntrospectObject(
            active=active,
            aud=aud,
            client_id=client_id,
            exp=exp,
            iat=iat,
            iss=iss,
            nbf=nbf,
            scope=scope,
            sub=sub,
            token_type=token_type,
            token_use=token_use,
        )
        dumped = introspect_object.model_dump()

        assert dumped["active"] == active
        assert dumped["aud"] == aud
        assert dumped["client_id"] == client_id
        assert dumped["exp"] == exp
        assert dumped["iat"] == iat
        assert dumped["iss"] == iss
        assert dumped["nbf"] == nbf
        assert dumped["scope"] == scope
        assert dumped["sub"] == sub
        assert dumped["token_type"] == token_type
        assert dumped["token_use"] == token_use
        assert dumped["ext"] is None
        assert dumped["obfuscated_subject"] is None
        assert dumped["username"] is None

    def test_model_dump_json(self) -> None:
        """Test model serialization using model_dump_json."""
        active = True
        aud = ["audience1"]
        client_id = "test_client_id"
        exp = 1234567890
        iat = 1234567890
        iss = "https://hydra.example.com"
        nbf = 1234567890
        scope = "read"
        sub = "test_subject"
        token_type = "Bearer"
        token_use = "access"

        introspect_object = HydraTokenIntrospectObject(
            active=active,
            aud=aud,
            client_id=client_id,
            exp=exp,
            iat=iat,
            iss=iss,
            nbf=nbf,
            scope=scope,
            sub=sub,
            token_type=token_type,
            token_use=token_use,
        )
        json_str = introspect_object.model_dump_json()

        assert isinstance(json_str, str)
        data = json.loads(json_str)
        assert data["active"] == active
        assert data["aud"] == aud
        assert data["client_id"] == client_id
        assert data["exp"] == exp
        assert data["iat"] == iat
        assert data["iss"] == iss
        assert data["nbf"] == nbf
        assert data["scope"] == scope
        assert data["sub"] == sub
        assert data["token_type"] == token_type
        assert data["token_use"] == token_use

    def test_model_validate(self) -> None:
        """Test model deserialization using model_validate."""
        active = True
        aud = ["audience1", "audience2"]
        client_id = "test_client_id"
        exp = 1234567890
        iat = 1234567890
        iss = "https://hydra.example.com"
        nbf = 1234567890
        scope = "read write"
        sub = "test_subject"
        token_type = "Bearer"
        token_use = "access"

        data: dict[str, Any] = {
            "active": active,
            "aud": aud,
            "client_id": client_id,
            "exp": exp,
            "iat": iat,
            "iss": iss,
            "nbf": nbf,
            "scope": scope,
            "sub": sub,
            "token_type": token_type,
            "token_use": token_use,
        }
        introspect_object = HydraTokenIntrospectObject.model_validate(data)

        assert introspect_object.active == active
        assert introspect_object.aud == aud
        assert introspect_object.client_id == client_id
        assert introspect_object.exp == exp
        assert introspect_object.iat == iat
        assert introspect_object.iss == iss
        assert introspect_object.nbf == nbf
        assert introspect_object.scope == scope
        assert introspect_object.sub == sub
        assert introspect_object.token_type == token_type
        assert introspect_object.token_use == token_use

    def test_model_validate_json(self) -> None:
        """Test model deserialization using model_validate_json."""
        active = True
        aud = ["audience1"]
        client_id = "test_client_id"
        exp = 1234567890
        iat = 1234567890
        iss = "https://hydra.example.com"
        nbf = 1234567890
        scope = "read"
        sub = "test_subject"
        token_type = "Bearer"
        token_use = "access"

        json_str = json.dumps(
            {
                "active": active,
                "aud": aud,
                "client_id": client_id,
                "exp": exp,
                "iat": iat,
                "iss": iss,
                "nbf": nbf,
                "scope": scope,
                "sub": sub,
                "token_type": token_type,
                "token_use": token_use,
            }
        )
        introspect_object = HydraTokenIntrospectObject.model_validate_json(json_str)

        assert introspect_object.active == active
        assert introspect_object.aud == aud
        assert introspect_object.client_id == client_id
        assert introspect_object.exp == exp
        assert introspect_object.iat == iat
        assert introspect_object.iss == iss
        assert introspect_object.nbf == nbf
        assert introspect_object.scope == scope
        assert introspect_object.sub == sub
        assert introspect_object.token_type == token_type
        assert introspect_object.token_use == token_use

    def test_round_trip_serialization(self) -> None:
        """Test round-trip serialization: create → serialize → deserialize."""
        active = True
        aud = ["audience1", "audience2"]
        client_id = "test_client_id"
        exp = 1234567890
        ext = {"key1": "value1"}
        iat = 1234567890
        iss = "https://hydra.example.com"
        nbf = 1234567890
        obfuscated_subject = "obfuscated_123"
        scope = "read write"
        sub = "test_subject"
        token_type = "Bearer"
        token_use = "access"
        username = "test_user"

        original = HydraTokenIntrospectObject(
            active=active,
            aud=aud,
            client_id=client_id,
            exp=exp,
            ext=ext,
            iat=iat,
            iss=iss,
            nbf=nbf,
            obfuscated_subject=obfuscated_subject,
            scope=scope,
            sub=sub,
            token_type=token_type,
            token_use=token_use,
            username=username,
        )
        dumped = original.model_dump()
        restored = HydraTokenIntrospectObject.model_validate(dumped)

        assert restored.active == original.active
        assert restored.aud == original.aud
        assert restored.client_id == original.client_id
        assert restored.exp == original.exp
        assert restored.ext == original.ext
        assert restored.iat == original.iat
        assert restored.iss == original.iss
        assert restored.nbf == original.nbf
        assert restored.obfuscated_subject == original.obfuscated_subject
        assert restored.scope == original.scope
        assert restored.sub == original.sub
        assert restored.token_type == original.token_type
        assert restored.token_use == original.token_use
        assert restored.username == original.username
