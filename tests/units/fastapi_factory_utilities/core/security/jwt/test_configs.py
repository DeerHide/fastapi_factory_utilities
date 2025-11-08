"""Provides unit tests for the JWT bearer token authentication configuration."""

import pytest
from jwt.algorithms import get_default_algorithms, requires_cryptography
from pydantic import ValidationError

from fastapi_factory_utilities.core.security.jwt.configs import JWTBearerAuthenticationConfig


class TestJWTBearerAuthenticationConfig:
    """Various tests for the JWTBearerAuthenticationConfig class."""

    def test_can_be_initialized_with_required_fields(self) -> None:
        """Test that the config can be initialized with required fields."""
        config = JWTBearerAuthenticationConfig(audience="test-audience")
        assert config.audience == "test-audience"
        assert config.authorized_algorithms is not None
        assert isinstance(config.authorized_algorithms, list)
        assert config.authorized_audiences is None
        assert config.authorized_issuers is None

    def test_default_authorized_algorithms(self) -> None:
        """Test that default authorized algorithms are set correctly."""
        config = JWTBearerAuthenticationConfig(audience="test-audience")
        expected_algorithms = list(get_default_algorithms().keys())
        assert config.authorized_algorithms == expected_algorithms

    def test_can_be_initialized_with_all_fields(self) -> None:
        """Test that the config can be initialized with all fields."""
        config = JWTBearerAuthenticationConfig(
            audience="test-audience",
            authorized_algorithms=["RS256", "ES256"],
            authorized_audiences=["aud1", "aud2"],
            authorized_issuers=["iss1", "iss2"],
        )
        assert config.audience == "test-audience"
        assert config.authorized_algorithms == ["RS256", "ES256"]
        assert config.authorized_audiences == ["aud1", "aud2"]
        assert config.authorized_issuers == ["iss1", "iss2"]

    def test_can_be_initialized_with_optional_fields(self) -> None:
        """Test that the config can be initialized with optional fields."""
        config = JWTBearerAuthenticationConfig(
            audience="test-audience",
            authorized_audiences=["aud1"],
            authorized_issuers=["iss1"],
        )
        assert config.audience == "test-audience"
        assert config.authorized_audiences == ["aud1"]
        assert config.authorized_issuers == ["iss1"]

    def test_audience_is_required(self) -> None:
        """Test that audience field is required."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig()  # type: ignore[call-overload]

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("audience",)
        assert errors[0]["type"] == "missing"

    def test_validates_authorized_algorithms_with_valid_algorithms(self) -> None:
        """Test that valid algorithms (requiring cryptography) are accepted."""
        valid_algorithms = list(requires_cryptography)
        config = JWTBearerAuthenticationConfig(
            audience="test-audience",
            authorized_algorithms=valid_algorithms,
        )
        assert config.authorized_algorithms == valid_algorithms

    def test_validates_authorized_algorithms_with_single_valid_algorithm(self) -> None:
        """Test that a single valid algorithm is accepted."""
        config = JWTBearerAuthenticationConfig(
            audience="test-audience",
            authorized_algorithms=["RS256"],
        )
        assert config.authorized_algorithms == ["RS256"]

    def test_validates_authorized_algorithms_raises_value_error_for_invalid_algorithms(
        self,
    ) -> None:
        """Test that invalid algorithms (not requiring cryptography) raise ValueError."""
        invalid_algorithms = ["HS256", "HS384", "HS512", "none"]
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                audience="test-audience",
                authorized_algorithms=invalid_algorithms,
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
                audience="test-audience",
                authorized_algorithms=mixed_algorithms,
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
                audience="test-audience",
                authorized_algorithms=[invalid_algorithm],
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
            audience="test-audience",
            authorized_algorithms=[valid_algorithm],
        )
        assert config.authorized_algorithms == [valid_algorithm]

    def test_config_is_frozen(self) -> None:
        """Test that the config is frozen and cannot be modified."""
        config = JWTBearerAuthenticationConfig(audience="test-audience")
        with pytest.raises(ValidationError):
            config.audience = "new-audience"  # type: ignore[misc]

    def test_config_forbids_extra_fields(self) -> None:
        """Test that the config forbids extra fields."""
        with pytest.raises(ValidationError) as exc_info:
            JWTBearerAuthenticationConfig(
                audience="test-audience",
                extra_field="extra",  # type: ignore[call-overload]
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("extra_field",)
        assert errors[0]["type"] == "extra_forbidden"

    def test_model_validate(self) -> None:
        """Test creating config using model_validate."""
        data: dict[str, str | list[str] | None] = {
            "audience": "test-audience",
            "authorized_algorithms": ["RS256", "ES256"],
            "authorized_audiences": ["aud1", "aud2"],
            "authorized_issuers": ["iss1", "iss2"],
        }

        config = JWTBearerAuthenticationConfig.model_validate(data)

        assert config.audience == "test-audience"
        assert config.authorized_algorithms == ["RS256", "ES256"]
        assert config.authorized_audiences == ["aud1", "aud2"]
        assert config.authorized_issuers == ["iss1", "iss2"]

    def test_model_validate_with_minimal_fields(self) -> None:
        """Test creating config using model_validate with minimal fields."""
        data: dict[str, str] = {
            "audience": "test-audience",
        }

        config = JWTBearerAuthenticationConfig.model_validate(data)

        assert config.audience == "test-audience"
        assert config.authorized_algorithms is not None
        assert config.authorized_audiences is None
        assert config.authorized_issuers is None

    def test_model_validate_json(self) -> None:
        """Test creating config using model_validate_json."""
        json_data = (
            '{"audience": "test-audience", "authorized_algorithms": ["RS256"], '
            '"authorized_audiences": ["aud1"], "authorized_issuers": ["iss1"]}'
        )

        config = JWTBearerAuthenticationConfig.model_validate_json(json_data)

        assert config.audience == "test-audience"
        assert config.authorized_algorithms == ["RS256"]
        assert config.authorized_audiences == ["aud1"]
        assert config.authorized_issuers == ["iss1"]

    def test_empty_authorized_algorithms_list_is_valid(self) -> None:
        """Test that empty authorized algorithms list is valid (no invalid algorithms)."""
        config = JWTBearerAuthenticationConfig(
            audience="test-audience",
            authorized_algorithms=[],
        )
        assert config.authorized_algorithms == []
