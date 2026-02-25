"""Provides unit tests for the JWT bearer token authentication configuration."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from fastapi.datastructures import State
from jwt.algorithms import get_default_algorithms, requires_cryptography
from pydantic import ValidationError

from fastapi_factory_utilities.core.security.jwt.configs import (
    DependsJWTBearerAuthenticationConfig,
    JWTBearerAuthenticationConfig,
    JWTBearerAuthenticationConfigBuilder,
)
from fastapi_factory_utilities.core.security.jwt.exceptions import JWTBearerAuthenticationConfigBuilderError
from fastapi_factory_utilities.core.security.types import OAuth2Issuer
from fastapi_factory_utilities.core.utils.configs import (
    UnableToReadConfigFileError,
    ValueErrorConfigError,
)

_DEFAULT_ISSUER: OAuth2Issuer = OAuth2Issuer("https://example.com")


class TestJWTBearerAuthenticationConfig:
    """Various tests for the JWTBearerAuthenticationConfig class."""

    def test_can_be_initialized_with_required_fields(self) -> None:
        """Test that the config can be initialized with required fields."""
        config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        assert config.authorized_algorithms is not None
        assert isinstance(config.authorized_algorithms, list)
        assert config.authorized_audiences is None
        assert config.issuer == _DEFAULT_ISSUER

    def test_default_authorized_algorithms(self) -> None:
        """Test that default authorized algorithms are set correctly."""
        config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        expected_algorithms = list(get_default_algorithms().keys())
        assert config.authorized_algorithms == expected_algorithms

    def test_can_be_initialized_with_all_fields(self) -> None:
        """Test that the config can be initialized with all fields."""
        config = JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256", "ES256"],
            authorized_audiences=["aud1", "aud2"],
            issuer=OAuth2Issuer("https://issuer.example"),
        )
        assert config.authorized_algorithms == ["RS256", "ES256"]
        assert config.authorized_audiences is not None
        assert set(config.authorized_audiences) == {"aud1", "aud2"}
        assert config.issuer == OAuth2Issuer("https://issuer.example")

    def test_can_be_initialized_with_optional_fields(self) -> None:
        """Test that the config can be initialized with optional fields."""
        config = JWTBearerAuthenticationConfig(
            authorized_audiences=["aud1"],
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_audiences == ["aud1"]
        assert config.issuer == _DEFAULT_ISSUER

    def test_can_be_initialized_with_minimal_required_fields(self) -> None:
        """Test that the config can be initialized with minimal required fields (issuer)."""
        config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        assert config.authorized_algorithms is not None
        assert config.authorized_audiences is None
        assert config.issuer == _DEFAULT_ISSUER

    def test_raises_validation_error_when_issuer_missing_in_model_validate(self) -> None:
        """Test that model_validate raises ValidationError when issuer is omitted."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig.model_validate({})

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("issuer",) for e in errors)

    def test_raises_validation_error_when_issuer_omitted_in_constructor(self) -> None:
        """Test that constructor raises ValidationError when issuer is not provided."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig()  # type: ignore[call-arg]

        errors = exc_info.value.errors()
        assert any(e["loc"] == ("issuer",) for e in errors)

    def test_validates_authorized_algorithms_with_valid_algorithms(self) -> None:
        """Test that valid algorithms (requiring cryptography) are accepted."""
        valid_algorithms = list(requires_cryptography)
        config = JWTBearerAuthenticationConfig(
            authorized_algorithms=valid_algorithms,
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_algorithms == valid_algorithms

    def test_validates_authorized_algorithms_with_single_valid_algorithm(self) -> None:
        """Test that a single valid algorithm is accepted."""
        config = JWTBearerAuthenticationConfig(
            authorized_algorithms=["RS256"],
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_algorithms == ["RS256"]

    def test_validates_authorized_algorithms_raises_value_error_for_invalid_algorithms(
        self,
    ) -> None:
        """Test that invalid algorithms (not requiring cryptography) raise ValueError."""
        invalid_algorithms = ["HS256", "HS384", "HS512", "none"]
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                authorized_algorithms=invalid_algorithms,
                issuer=_DEFAULT_ISSUER,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("authorized_algorithms",)
        assert errors[0]["type"] == "value_error"
        assert "Invalid algorithms" in str(errors[0]["msg"])

    def test_validates_authorized_algorithms_raises_value_error_for_mixed_algorithms(
        self,
    ) -> None:
        """Test that mixed valid and invalid algorithms raise ValueError."""
        mixed_algorithms = ["RS256", "HS256", "ES256", "none"]
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                authorized_algorithms=mixed_algorithms,
                issuer=_DEFAULT_ISSUER,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("authorized_algorithms",)
        assert errors[0]["type"] == "value_error"
        assert "Invalid algorithms" in str(errors[0]["msg"])

    @pytest.mark.parametrize(
        "invalid_algorithm",
        [
            "HS256",
            "HS384",
            "HS512",
            "none",
            "invalid_algorithm",
        ],
    )
    def test_validates_authorized_algorithms_raises_value_error_for_each_invalid_algorithm(
        self,
        invalid_algorithm: str,
    ) -> None:
        """Test that each invalid algorithm raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                authorized_algorithms=[invalid_algorithm],
                issuer=_DEFAULT_ISSUER,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("authorized_algorithms",)
        assert errors[0]["type"] == "value_error"
        assert "Invalid algorithms" in str(errors[0]["msg"])
        assert invalid_algorithm in str(errors[0]["msg"])

    @pytest.mark.parametrize(
        "valid_algorithm",
        [
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
            "PS256",
            "PS384",
            "PS512",
            "EdDSA",
        ],
    )
    def test_validates_authorized_algorithms_accepts_valid_algorithms(
        self,
        valid_algorithm: str,
    ) -> None:
        """Test that each valid algorithm is accepted."""
        config = JWTBearerAuthenticationConfig(
            authorized_algorithms=[valid_algorithm],
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_algorithms == [valid_algorithm]

    def test_config_is_frozen(self) -> None:
        """Test that the config is frozen and cannot be modified."""
        config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        with pytest.raises(ValidationError):
            config.authorized_algorithms = ["HS256"]  # type: ignore[misc]

    def test_config_forbids_extra_fields(self) -> None:
        """Test that the config forbids extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                issuer=_DEFAULT_ISSUER,
                extra_field="extra",  # type: ignore[call-overload]
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("extra_field",)
        assert errors[0]["type"] == "extra_forbidden"

    def test_model_validate(self) -> None:
        """Test creating config using model_validate."""
        data: dict[str, str | list[str] | None] = {
            "authorized_algorithms": ["RS256", "ES256"],
            "authorized_audiences": ["aud1", "aud2"],
            "issuer": "https://issuer.example",
        }

        config = JWTBearerAuthenticationConfig.model_validate(data)

        assert config.authorized_algorithms == ["RS256", "ES256"]
        assert config.authorized_audiences is not None
        assert set(config.authorized_audiences) == {"aud1", "aud2"}
        assert config.issuer == OAuth2Issuer("https://issuer.example")

    def test_model_validate_with_minimal_fields(self) -> None:
        """Test creating config using model_validate with minimal fields."""
        data: dict[str, str] = {"issuer": "https://example.com"}

        config = JWTBearerAuthenticationConfig.model_validate(data)

        assert config.authorized_algorithms is not None
        assert config.authorized_audiences is None
        assert config.issuer == OAuth2Issuer("https://example.com")

    def test_model_validate_json(self) -> None:
        """Test creating config using model_validate_json."""
        json_data = (
            '{"authorized_algorithms": ["RS256"], "authorized_audiences": ["aud1"], "issuer": "https://example.com"}'
        )

        config = JWTBearerAuthenticationConfig.model_validate_json(json_data)

        assert config.authorized_algorithms == ["RS256"]
        assert config.authorized_audiences == ["aud1"]
        assert config.issuer == OAuth2Issuer("https://example.com")

    def test_empty_authorized_algorithms_list_is_valid(self) -> None:
        """Test that empty authorized algorithms list is valid (no invalid algorithms)."""
        config = JWTBearerAuthenticationConfig(
            authorized_algorithms=[],
            issuer=_DEFAULT_ISSUER,
        )
        assert not config.authorized_algorithms

    def test_validate_authorized_audiences_accepts_comma_separated_string(self) -> None:
        """Test that comma-separated string is converted to list."""
        config = JWTBearerAuthenticationConfig(
            authorized_audiences="aud1,aud2,aud3",  # type: ignore[arg-type]
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_audiences is not None
        assert set(config.authorized_audiences) == {"aud1", "aud2", "aud3"}
        assert len(config.authorized_audiences) == 3  # noqa: PLR2004

    def test_validate_authorized_audiences_strips_whitespace(self) -> None:
        """Test that whitespace is stripped from comma-separated values."""
        config = JWTBearerAuthenticationConfig(
            authorized_audiences=" aud1 , aud2 , aud3 ",  # type: ignore[arg-type]
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_audiences is not None
        assert set(config.authorized_audiences) == {"aud1", "aud2", "aud3"}
        assert len(config.authorized_audiences) == 3  # noqa: PLR2004

    def test_validate_authorized_audiences_strips_whitespace_from_single_value(self) -> None:
        """Test that whitespace is stripped from single value."""
        config = JWTBearerAuthenticationConfig(
            authorized_audiences=" aud1 ",  # type: ignore[arg-type]
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_audiences == ["aud1"]

    def test_validate_authorized_audiences_removes_duplicates_from_string(self) -> None:
        """Test that duplicate values are removed from comma-separated string."""
        config = JWTBearerAuthenticationConfig(
            authorized_audiences="aud1,aud2,aud1",  # type: ignore[arg-type]
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_audiences is not None
        assert set(config.authorized_audiences) == {"aud1", "aud2"}
        assert len(config.authorized_audiences) == 2  # noqa: PLR2004

    def test_validate_authorized_audiences_removes_duplicates_from_list(self) -> None:
        """Test that duplicate values are removed from list."""
        config = JWTBearerAuthenticationConfig(
            authorized_audiences=["aud1", "aud2", "aud1"],
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_audiences is not None
        assert set(config.authorized_audiences) == {"aud1", "aud2"}
        assert len(config.authorized_audiences) == 2  # noqa: PLR2004

    def test_validate_authorized_audiences_filters_empty_strings_from_comma_separated(
        self,
    ) -> None:
        """Test that empty strings are filtered from comma-separated string."""
        config = JWTBearerAuthenticationConfig(
            authorized_audiences="aud1,,aud2, ,aud3",  # type: ignore[arg-type]
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_audiences is not None
        assert set(config.authorized_audiences) == {"aud1", "aud2", "aud3"}
        assert len(config.authorized_audiences) == 3  # noqa: PLR2004

    def test_validate_authorized_audiences_filters_empty_strings_from_list(self) -> None:
        """Test that empty strings are filtered from list."""
        config = JWTBearerAuthenticationConfig(
            authorized_audiences=["aud1", "", "aud2", " ", "aud3"],
            issuer=_DEFAULT_ISSUER,
        )
        assert config.authorized_audiences is not None
        assert set(config.authorized_audiences) == {"aud1", "aud2", "aud3"}
        assert len(config.authorized_audiences) == 3  # noqa: PLR2004

    def test_validate_authorized_audiences_raises_error_for_empty_string(self) -> None:
        """Test that empty string raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                authorized_audiences="",  # type: ignore[arg-type]
                issuer=_DEFAULT_ISSUER,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("authorized_audiences",)
        assert errors[0]["type"] == "value_error"
        assert "Invalid value: empty list after processing" in str(errors[0]["msg"])

    def test_validate_authorized_audiences_raises_error_for_whitespace_only_string(
        self,
    ) -> None:
        """Test that whitespace-only string raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                authorized_audiences="   ",  # type: ignore[arg-type]
                issuer=_DEFAULT_ISSUER,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("authorized_audiences",)
        assert errors[0]["type"] == "value_error"
        assert "Invalid value: empty list after processing" in str(errors[0]["msg"])

    def test_validate_authorized_audiences_raises_error_for_comma_only_string(self) -> None:
        """Test that comma-only string raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                authorized_audiences=",,,",  # type: ignore[arg-type]
                issuer=_DEFAULT_ISSUER,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("authorized_audiences",)
        assert errors[0]["type"] == "value_error"
        assert "Invalid value: empty list after processing" in str(errors[0]["msg"])

    def test_validate_authorized_audiences_raises_error_for_empty_list(self) -> None:
        """Test that empty list raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                authorized_audiences=[],
                issuer=_DEFAULT_ISSUER,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("authorized_audiences",)
        assert errors[0]["type"] == "value_error"
        assert "Invalid value: empty list after processing" in str(errors[0]["msg"])

    def test_validate_authorized_audiences_raises_error_for_list_with_only_empty_strings(
        self,
    ) -> None:
        """Test that list with only empty strings raises ValueError."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                authorized_audiences=["", " ", "  "],
                issuer=_DEFAULT_ISSUER,
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("authorized_audiences",)
        assert errors[0]["type"] == "value_error"
        assert "Invalid value: empty list after processing" in str(errors[0]["msg"])


class TestJWTBearerAuthenticationConfigBuilder:
    """Unit tests for JWTBearerAuthenticationConfigBuilder."""

    def test_init_raises_when_key_is_empty_string(self) -> None:
        """Builder raises JWTBearerAuthenticationConfigBuilderError when key is empty."""
        with pytest.raises(JWTBearerAuthenticationConfigBuilderError) as exc_info:
            JWTBearerAuthenticationConfigBuilder("")
        assert "Key cannot be empty" in str(exc_info.value)

    def test_init_accepts_valid_key(self) -> None:
        """Builder accepts a non-empty key and uses it when building from YAML."""
        builder = JWTBearerAuthenticationConfigBuilder("my_jwt")
        # Key is used in yaml_base_key when building; see test_build_loads_from_yaml_when_path_set
        assert builder.APPLICATION_YAML_BASE_JWT_CONFIG_KEY == "jwt_configs"

    def test_add_application_yaml_path_returns_self_and_sets_path(self) -> None:
        """add_application_yaml_path returns self so build() can load from YAML."""
        builder = JWTBearerAuthenticationConfigBuilder("my_jwt")
        result = builder.add_application_yaml_path(
            package_name="my_package",
            filename="application.yaml",
        )
        assert result is builder
        # Path is used in build(); see test_build_loads_from_yaml_when_path_set

    def test_build_raises_when_no_config_and_no_yaml_path(self) -> None:
        """build() raises when neither config nor YAML path is set."""
        builder = JWTBearerAuthenticationConfigBuilder("my_jwt")
        with pytest.raises(JWTBearerAuthenticationConfigBuilderError) as exc_info:
            builder.build()
        assert "Neither a JWT bearer authentication configuration" in str(exc_info.value)

    @patch("fastapi_factory_utilities.core.security.jwt.configs.build_config_from_file_in_package")
    def test_build_loads_from_yaml_when_path_set(
        self,
        mock_build_config: MagicMock,
    ) -> None:
        """build() loads config from YAML when package and filename are set."""
        expected_config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        mock_build_config.return_value = expected_config

        builder = JWTBearerAuthenticationConfigBuilder("my_jwt").add_application_yaml_path(
            package_name="pkg", filename="app.yaml"
        )
        result = builder.build()

        assert result is expected_config
        mock_build_config.assert_called_once_with(
            package_name="pkg",
            filename="app.yaml",
            config_class=JWTBearerAuthenticationConfig,
            yaml_base_key="jwt_configs.my_jwt",
        )

    @patch("fastapi_factory_utilities.core.security.jwt.configs.build_config_from_file_in_package")
    def test_build_returns_cached_config_on_second_call(
        self,
        mock_build_config: MagicMock,
    ) -> None:
        """build() returns same config on second call without calling YAML again."""
        expected_config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        mock_build_config.return_value = expected_config

        builder = JWTBearerAuthenticationConfigBuilder("my_jwt").add_application_yaml_path(
            package_name="pkg", filename="app.yaml"
        )
        first = builder.build()
        second = builder.build()

        assert first is second is expected_config
        mock_build_config.assert_called_once()

    @pytest.mark.parametrize(
        "exception",
        [UnableToReadConfigFileError("file not found"), ValueErrorConfigError("invalid")],
        ids=["UnableToReadConfigFileError", "ValueErrorConfigError"],
    )
    @patch("fastapi_factory_utilities.core.security.jwt.configs.build_config_from_file_in_package")
    def test_build_wraps_config_errors(
        self,
        mock_build_config: MagicMock,
        exception: Exception,
    ) -> None:
        """build() wraps UnableToReadConfigFileError and ValueErrorConfigError."""
        mock_build_config.side_effect = exception

        builder = JWTBearerAuthenticationConfigBuilder("my_jwt").add_application_yaml_path(
            package_name="pkg", filename="app.yaml"
        )
        with pytest.raises(JWTBearerAuthenticationConfigBuilderError) as exc_info:
            builder.build()
        assert "Failed to read the application YAML file" in str(exc_info.value)
        assert exc_info.value.__cause__ is exception

    def test_config_property_raises_when_not_built(self) -> None:
        """Config property raises when build() was never called."""
        builder = JWTBearerAuthenticationConfigBuilder("my_jwt")
        with pytest.raises(JWTBearerAuthenticationConfigBuilderError) as exc_info:
            _ = builder.config
        assert "No configuration found" in str(exc_info.value)

    @patch("fastapi_factory_utilities.core.security.jwt.configs.build_config_from_file_in_package")
    def test_config_property_returns_config_after_build(
        self,
        mock_build_config: MagicMock,
    ) -> None:
        """Config property returns config after successful build()."""
        expected_config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        mock_build_config.return_value = expected_config

        builder = JWTBearerAuthenticationConfigBuilder("my_jwt").add_application_yaml_path(
            package_name="pkg", filename="app.yaml"
        )
        builder.build()
        assert builder.config is expected_config


class TestDependsJWTBearerAuthenticationConfig:
    """Unit tests for DependsJWTBearerAuthenticationConfig."""

    def test_init_accepts_key(self) -> None:
        """Dependency accepts a key used for state lookup in __call__."""
        dep = DependsJWTBearerAuthenticationConfig("my_jwt")
        assert dep is not None
        assert DependsJWTBearerAuthenticationConfig.STATE_PREFIX_KEY == "jwt_configs"

    def test_export_from_state_raises_when_key_missing(self) -> None:
        """export_from_state raises when config is not in state."""
        state: State = MagicMock(spec=State)
        with pytest.raises(JWTBearerAuthenticationConfigBuilderError) as exc_info:
            DependsJWTBearerAuthenticationConfig.export_from_state(state=state, key="missing")
        assert "not found in the state" in str(exc_info.value)

    def test_export_from_state_raises_when_attribute_is_none(self) -> None:
        """export_from_state raises when state attribute is explicitly None."""
        state: State = MagicMock(spec=State)
        setattr(state, "jwt_configs.missing", None)
        with pytest.raises(JWTBearerAuthenticationConfigBuilderError) as exc_info:
            DependsJWTBearerAuthenticationConfig.export_from_state(state=state, key="missing")
        assert "not found in the state" in str(exc_info.value)

    def test_export_from_state_returns_config_when_present(self) -> None:
        """export_from_state returns config when state has it."""
        config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        state: State = MagicMock(spec=State)
        setattr(state, "jwt_configs.my_jwt", config)

        result = DependsJWTBearerAuthenticationConfig.export_from_state(state=state, key="my_jwt")
        assert result is config

    def test_import_to_state_sets_attribute(self) -> None:
        """import_to_state sets state attribute so export_from_state can read it."""
        config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        state: State = MagicMock(spec=State)

        DependsJWTBearerAuthenticationConfig.import_to_state(state=state, config=config, key="my_jwt")
        assert getattr(state, "jwt_configs.my_jwt") is config

    def test_call_returns_config_from_request_app_state(self) -> None:
        """__call__ returns config from request.app.state using the dependency key."""
        config = JWTBearerAuthenticationConfig(issuer=_DEFAULT_ISSUER)
        app_state: State = MagicMock(spec=State)
        setattr(app_state, "jwt_configs.my_jwt", config)

        request = MagicMock(spec=Request)
        request.app.state = app_state

        dep = DependsJWTBearerAuthenticationConfig("my_jwt")
        result = dep(request)
        assert result is config
