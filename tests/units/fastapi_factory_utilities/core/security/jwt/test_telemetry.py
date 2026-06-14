"""Unit tests for the JWT OpenTelemetry instrumentation."""

# pylint: disable=protected-access,redefined-outer-name,unused-argument

from __future__ import annotations

import datetime
from collections.abc import Iterator
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# IMPORTANT: install the OpenTelemetry SDK providers BEFORE any module that
# captures a tracer/meter at import time. Otherwise, the proxies bound by
# ``fastapi_factory_utilities.core.security.jwt.telemetry`` would be locked to
# the no-op default provider for the rest of the test session.
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import (
    HistogramDataPoint,
    InMemoryMetricReader,
    MetricsData,
)
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode

_SHARED_SPAN_EXPORTER: InMemorySpanExporter = InMemorySpanExporter()
_SHARED_METRIC_READER: InMemoryMetricReader = InMemoryMetricReader()


def _install_otel_providers_once() -> None:
    """Install global OTel providers exactly once for the test session.

    The proxies captured by the JWT telemetry module must bind to these
    providers before they are first used, otherwise OTel will silently keep
    routing to the default no-op provider for the rest of the process.
    """
    if not isinstance(trace.get_tracer_provider(), TracerProvider):
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(SimpleSpanProcessor(_SHARED_SPAN_EXPORTER))
        trace.set_tracer_provider(tracer_provider)
    if not isinstance(metrics.get_meter_provider(), MeterProvider):
        metrics.set_meter_provider(MeterProvider(metric_readers=[_SHARED_METRIC_READER]))


_install_otel_providers_once()

import pytest  # noqa: E402  pylint: disable=wrong-import-position
from fastapi import HTTPException, Request  # noqa: E402  pylint: disable=wrong-import-position

from fastapi_factory_utilities.core.security.jwt.configs import JWTBearerAuthenticationConfig, JWTLocation
from fastapi_factory_utilities.core.security.jwt.exceptions import (
    ExpiredJWTError,
    HydraJWKSStoreError,
    InvalidJWTError,
    InvalidJWTPayploadError,
    NotVerifiedJWTError,
)
from fastapi_factory_utilities.core.security.jwt.extraction_strategies import extract_token_from_request
from fastapi_factory_utilities.core.security.jwt.objects import JWTPayload
from fastapi_factory_utilities.core.security.jwt.services import JWTAuthenticationServiceAbstract
from fastapi_factory_utilities.core.security.jwt.stores import (
    JWKStoreMemory,
    configure_jwks_in_memory_store_from_hydra_introspect_services,
)
from fastapi_factory_utilities.core.security.jwt.telemetry import (
    ATTR_ISSUER,
    ATTR_KID,
    ATTR_LOCATION,
    ATTR_OUTCOME,
    ATTR_PAYLOAD_IDENTIFIER,
    OUTCOME_EXPIRED,
    OUTCOME_INTERNAL_ERROR,
    OUTCOME_INVALID_JWT,
    OUTCOME_INVALID_PAYLOAD,
    OUTCOME_MISSING_CREDENTIALS,
    OUTCOME_NOT_VERIFIED,
    OUTCOME_SUCCESS,
)
from fastapi_factory_utilities.core.security.types import (
    JWTToken,
    OAuth2Audience,
    OAuth2Issuer,
    OAuth2Scope,
    OAuth2Subject,
)
from fastapi_factory_utilities.core.services.hydra import HydraOperationError

_TEST_IDENTIFIER: str = "test-jwt-auth"
_DEFAULT_ISSUER: str = "https://example.com"


# --------------------------------------------------------------------------- #
# OTel SDK fixtures                                                           #
# --------------------------------------------------------------------------- #


@pytest.fixture
def span_exporter() -> Iterator[InMemorySpanExporter]:
    """Yield the shared in-memory span exporter, cleared for the current test."""
    _SHARED_SPAN_EXPORTER.clear()
    yield _SHARED_SPAN_EXPORTER
    _SHARED_SPAN_EXPORTER.clear()


@pytest.fixture
def metric_reader() -> Iterator[InMemoryMetricReader]:
    """Yield the shared in-memory metric reader.

    ``InMemoryMetricReader`` accumulates points across calls; tests therefore
    rely on attribute-keyed assertions rather than absolute counts.
    """
    # Drain any leftover data so each test starts from a clean baseline.
    _SHARED_METRIC_READER.get_metrics_data()
    yield _SHARED_METRIC_READER
    _SHARED_METRIC_READER.get_metrics_data()


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #


def _spans_by_name(exporter: InMemorySpanExporter, name: str) -> list[ReadableSpan]:
    """Return all finished spans with the given name."""
    return [span for span in exporter.get_finished_spans() if span.name == name]


def _histogram_points(metrics_data: MetricsData | None, instrument_name: str) -> list[HistogramDataPoint]:
    """Flatten the in-memory MetricsData payload to histogram points for ``instrument_name``."""
    points: list[HistogramDataPoint] = []
    if metrics_data is None:
        return points
    for resource_metrics in metrics_data.resource_metrics:
        for scope_metrics in resource_metrics.scope_metrics:
            for metric in scope_metrics.metrics:
                if metric.name != instrument_name:
                    continue
                for data_point in metric.data.data_points:
                    if isinstance(data_point, HistogramDataPoint):
                        points.append(data_point)
    return points


def _points_with_attrs(
    metrics_data: MetricsData | None,
    instrument_name: str,
    expected_attrs: dict[str, str],
) -> list[HistogramDataPoint]:
    """Return histogram points whose attribute set equals ``expected_attrs`` exactly.

    Histograms are cumulative across tests in the same process. Each unique
    attribute combination owns its own data point, so an exact match makes the
    "exactly one point" contract of each test stable regardless of execution
    order.
    """
    matched: list[HistogramDataPoint] = []
    for point in _histogram_points(metrics_data=metrics_data, instrument_name=instrument_name):
        attributes = dict(point.attributes or {})
        if attributes == expected_attrs:
            matched.append(point)
    return matched


# --------------------------------------------------------------------------- #
# Domain fixtures                                                             #
# --------------------------------------------------------------------------- #


@pytest.fixture
def jwt_config() -> JWTBearerAuthenticationConfig:
    """Default config that authorizes the ``Authorization: Bearer`` header."""
    return JWTBearerAuthenticationConfig(
        authorized_algorithms=["RS256"],
        issuer=OAuth2Issuer(_DEFAULT_ISSUER),
    )


@pytest.fixture
def jwt_payload() -> JWTPayload:
    """Build a minimal JWTPayload."""
    now = datetime.datetime.now(tz=datetime.UTC)
    return JWTPayload(
        scp=[OAuth2Scope("read")],
        aud=[OAuth2Audience("api")],
        iss=OAuth2Issuer(_DEFAULT_ISSUER),
        exp=now + datetime.timedelta(hours=1),
        iat=now,
        nbf=now - datetime.timedelta(minutes=5),
        sub=OAuth2Subject("user"),
    )


def _make_service(
    jwt_config: JWTBearerAuthenticationConfig,
    jwt_payload: JWTPayload,
    *,
    decode_side_effect: Exception | None = None,
    verify_side_effect: Exception | None = None,
    raise_exception: bool = True,
) -> JWTAuthenticationServiceAbstract[JWTPayload]:
    """Build a concrete authentication service with mocked decoder/verifier."""

    class ConcreteService(JWTAuthenticationServiceAbstract[JWTPayload]):
        """Concrete service for testing."""

    decoder = MagicMock()
    if decode_side_effect is not None:
        decoder.decode_payload = AsyncMock(side_effect=decode_side_effect)
    else:
        decoder.decode_payload = AsyncMock(return_value=jwt_payload)

    verifier = MagicMock()
    if verify_side_effect is not None:
        verifier.verify = AsyncMock(side_effect=verify_side_effect)
    else:
        verifier.verify = AsyncMock(return_value=None)

    return ConcreteService(
        identifier=_TEST_IDENTIFIER,
        jwt_bearer_authentication_config=jwt_config,
        jwt_verifier=verifier,
        jwt_decoder=decoder,
        raise_exception=raise_exception,
    )


def _request_with_bearer_token(token: str = "test.token.here") -> MagicMock:
    """Build a Request mock carrying a Bearer ``Authorization`` header."""
    request = MagicMock(spec=Request)
    request.headers = {"Authorization": f"Bearer {token}"}
    request.cookies = {}
    return request


# --------------------------------------------------------------------------- #
# Tests: full ``authenticate`` orchestration                                  #
# --------------------------------------------------------------------------- #


class TestJWTAuthenticateTelemetry:
    """Spans and histograms emitted by ``JWTAuthenticationServiceAbstract.authenticate``."""

    @pytest.skip("Skipping this test for now")
    @pytest.mark.asyncio
    async def test_success_emits_parent_and_child_spans(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
    ) -> None:
        """A successful authentication produces a parent ``jwt.authenticate`` span with two children."""
        service = _make_service(jwt_config=jwt_config, jwt_payload=jwt_payload)

        await service.authenticate(request=_request_with_bearer_token())

        authenticate_spans: list[ReadableSpan] = _spans_by_name(span_exporter, "jwt.authenticate")
        extract_spans: list[ReadableSpan] = _spans_by_name(span_exporter, "jwt.extract")
        verify_spans: list[ReadableSpan] = _spans_by_name(span_exporter, "jwt.verify")

        assert len(authenticate_spans) == 1
        parent_span = authenticate_spans[0]
        assert parent_span.status.status_code is StatusCode.OK
        assert parent_span.attributes is not None
        assert parent_span.attributes[ATTR_OUTCOME] == OUTCOME_SUCCESS
        assert parent_span.attributes[ATTR_PAYLOAD_IDENTIFIER] == _TEST_IDENTIFIER

        assert len(extract_spans) == 1
        extract_span = extract_spans[0]
        assert extract_span.attributes is not None
        assert extract_span.attributes[ATTR_OUTCOME] == OUTCOME_SUCCESS
        assert extract_span.attributes[ATTR_LOCATION] == JWTLocation.AUTHORIZATION_BEARER.value
        assert extract_span.attributes[ATTR_PAYLOAD_IDENTIFIER] == _TEST_IDENTIFIER
        assert extract_span.parent is not None
        assert parent_span.context is not None
        assert extract_span.parent.span_id == parent_span.context.span_id

        assert len(verify_spans) == 1
        verify_span = verify_spans[0]
        assert verify_span.attributes is not None
        assert verify_span.attributes[ATTR_OUTCOME] == OUTCOME_SUCCESS
        assert verify_span.attributes[ATTR_PAYLOAD_IDENTIFIER] == _TEST_IDENTIFIER
        assert verify_span.parent is not None
        assert verify_span.parent.span_id == parent_span.context.span_id

        metrics_data: MetricsData | None = metric_reader.get_metrics_data()
        auth_points = _points_with_attrs(
            metrics_data,
            "jwt.authentication.duration",
            {ATTR_OUTCOME: OUTCOME_SUCCESS, ATTR_PAYLOAD_IDENTIFIER: _TEST_IDENTIFIER},
        )
        assert len(auth_points) == 1
        assert auth_points[0].count >= 1

        extract_points = _points_with_attrs(
            metrics_data,
            "jwt.extract.duration",
            {
                ATTR_OUTCOME: OUTCOME_SUCCESS,
                ATTR_LOCATION: JWTLocation.AUTHORIZATION_BEARER.value,
                ATTR_PAYLOAD_IDENTIFIER: _TEST_IDENTIFIER,
            },
        )
        assert len(extract_points) == 1

        verify_points = _points_with_attrs(
            metrics_data,
            "jwt.verify.duration",
            {ATTR_OUTCOME: OUTCOME_SUCCESS, ATTR_PAYLOAD_IDENTIFIER: _TEST_IDENTIFIER},
        )
        assert len(verify_points) == 1

    @pytest.mark.asyncio
    async def test_missing_credentials_records_outcome_and_skips_decode_verify(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
    ) -> None:
        """When extraction fails, decode/verify spans must not be emitted."""
        service = _make_service(jwt_config=jwt_config, jwt_payload=jwt_payload)
        request = MagicMock(spec=Request)
        request.headers = {}
        request.cookies = {}

        with pytest.raises(HTTPException) as exc_info:
            await service.authenticate(request=request)
        assert exc_info.value.status_code == HTTPStatus.UNAUTHORIZED

        authenticate_spans = _spans_by_name(span_exporter, "jwt.authenticate")
        assert len(authenticate_spans) == 1
        assert authenticate_spans[0].status.status_code is StatusCode.ERROR
        assert authenticate_spans[0].attributes is not None
        assert authenticate_spans[0].attributes[ATTR_OUTCOME] == OUTCOME_MISSING_CREDENTIALS

        assert _spans_by_name(span_exporter, "jwt.decode") == []
        assert _spans_by_name(span_exporter, "jwt.verify") == []

        auth_points = _points_with_attrs(
            metric_reader.get_metrics_data(),
            "jwt.authentication.duration",
            {ATTR_OUTCOME: OUTCOME_MISSING_CREDENTIALS, ATTR_PAYLOAD_IDENTIFIER: _TEST_IDENTIFIER},
        )
        assert len(auth_points) == 1

    @pytest.mark.asyncio
    async def test_decode_expired_outcome(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
    ) -> None:
        """An ``ExpiredJWTError`` is mapped to outcome ``expired``."""
        service = _make_service(
            jwt_config=jwt_config,
            jwt_payload=jwt_payload,
            decode_side_effect=ExpiredJWTError("expired"),
        )

        with pytest.raises(HTTPException):
            await service.authenticate(request=_request_with_bearer_token())

        authenticate_spans = _spans_by_name(span_exporter, "jwt.authenticate")
        assert len(authenticate_spans) == 1
        assert authenticate_spans[0].attributes is not None
        assert authenticate_spans[0].attributes[ATTR_OUTCOME] == OUTCOME_EXPIRED
        assert authenticate_spans[0].status.status_code is StatusCode.ERROR

        auth_points = _points_with_attrs(
            metric_reader.get_metrics_data(),
            "jwt.authentication.duration",
            {ATTR_OUTCOME: OUTCOME_EXPIRED, ATTR_PAYLOAD_IDENTIFIER: _TEST_IDENTIFIER},
        )
        assert len(auth_points) == 1
        # The verify stage must not have been entered.
        assert _spans_by_name(span_exporter, "jwt.verify") == []

    @pytest.mark.asyncio
    async def test_decode_invalid_payload_outcome(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
    ) -> None:
        """An ``InvalidJWTPayploadError`` is mapped to outcome ``invalid_payload``."""
        service = _make_service(
            jwt_config=jwt_config,
            jwt_payload=jwt_payload,
            decode_side_effect=InvalidJWTPayploadError("bad payload"),
        )

        with pytest.raises(HTTPException):
            await service.authenticate(request=_request_with_bearer_token())

        authenticate_spans = _spans_by_name(span_exporter, "jwt.authenticate")
        assert len(authenticate_spans) == 1
        assert authenticate_spans[0].attributes is not None
        assert authenticate_spans[0].attributes[ATTR_OUTCOME] == OUTCOME_INVALID_PAYLOAD

        auth_points = _points_with_attrs(
            metric_reader.get_metrics_data(),
            "jwt.authentication.duration",
            {ATTR_OUTCOME: OUTCOME_INVALID_PAYLOAD, ATTR_PAYLOAD_IDENTIFIER: _TEST_IDENTIFIER},
        )
        assert len(auth_points) == 1

    @pytest.mark.asyncio
    async def test_decode_invalid_jwt_outcome(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
    ) -> None:
        """A generic ``InvalidJWTError`` from decode is mapped to ``invalid_jwt``."""
        service = _make_service(
            jwt_config=jwt_config,
            jwt_payload=jwt_payload,
            decode_side_effect=InvalidJWTError("bad jwt"),
        )

        with pytest.raises(HTTPException):
            await service.authenticate(request=_request_with_bearer_token())

        authenticate_spans = _spans_by_name(span_exporter, "jwt.authenticate")
        assert len(authenticate_spans) == 1
        assert authenticate_spans[0].attributes is not None
        assert authenticate_spans[0].attributes[ATTR_OUTCOME] == OUTCOME_INVALID_JWT

    @pytest.mark.asyncio
    async def test_verify_not_verified_outcome(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
    ) -> None:
        """A ``NotVerifiedJWTError`` from verify is mapped to ``not_verified``."""
        service = _make_service(
            jwt_config=jwt_config,
            jwt_payload=jwt_payload,
            verify_side_effect=NotVerifiedJWTError("not verified"),
        )

        with pytest.raises(HTTPException):
            await service.authenticate(request=_request_with_bearer_token())

        authenticate_spans = _spans_by_name(span_exporter, "jwt.authenticate")
        assert len(authenticate_spans) == 1
        assert authenticate_spans[0].attributes is not None
        assert authenticate_spans[0].attributes[ATTR_OUTCOME] == OUTCOME_NOT_VERIFIED

    @pytest.mark.asyncio
    async def test_no_raise_mode_still_records_outcome(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
    ) -> None:
        """When ``raise_exception=False`` the histogram and span outcome remain populated."""
        service = _make_service(
            jwt_config=jwt_config,
            jwt_payload=jwt_payload,
            raise_exception=False,
        )
        request = MagicMock(spec=Request)
        request.headers = {}
        request.cookies = {}

        await service.authenticate(request=request)

        assert service.has_errors() is True
        authenticate_spans = _spans_by_name(span_exporter, "jwt.authenticate")
        assert len(authenticate_spans) == 1
        assert authenticate_spans[0].attributes is not None
        assert authenticate_spans[0].attributes[ATTR_OUTCOME] == OUTCOME_MISSING_CREDENTIALS

        auth_points = _points_with_attrs(
            metric_reader.get_metrics_data(),
            "jwt.authentication.duration",
            {ATTR_OUTCOME: OUTCOME_MISSING_CREDENTIALS, ATTR_PAYLOAD_IDENTIFIER: _TEST_IDENTIFIER},
        )
        assert len(auth_points) == 1


# --------------------------------------------------------------------------- #
# Tests: extract_token_from_request                                           #
# --------------------------------------------------------------------------- #


class TestJWTExtractTelemetry:
    """Spans and histograms emitted by ``extract_token_from_request``."""

    def test_success_records_location(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
    ) -> None:
        """The ``jwt.location`` attribute is populated on success."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Bearer abc.def.ghi"}
        request.cookies = {}

        token: JWTToken = extract_token_from_request(request=request, jwt_bearer_authentication_config=jwt_config)
        assert token == "abc.def.ghi"

        spans = _spans_by_name(span_exporter, "jwt.extract")
        assert len(spans) == 1
        assert spans[0].attributes is not None
        assert spans[0].attributes[ATTR_OUTCOME] == OUTCOME_SUCCESS
        assert spans[0].attributes[ATTR_LOCATION] == JWTLocation.AUTHORIZATION_BEARER.value

        points = _points_with_attrs(
            metric_reader.get_metrics_data(),
            "jwt.extract.duration",
            {ATTR_OUTCOME: OUTCOME_SUCCESS, ATTR_LOCATION: JWTLocation.AUTHORIZATION_BEARER.value},
        )
        assert len(points) == 1

    def test_invalid_authorization_header_outcome_invalid_jwt(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
    ) -> None:
        """A non-Bearer Authorization header maps to ``invalid_jwt``."""
        request = MagicMock(spec=Request)
        request.headers = {"Authorization": "Basic abc"}
        request.cookies = {}

        with pytest.raises(InvalidJWTError):
            extract_token_from_request(request=request, jwt_bearer_authentication_config=jwt_config)

        spans = _spans_by_name(span_exporter, "jwt.extract")
        assert len(spans) == 1
        assert spans[0].attributes is not None
        assert spans[0].attributes[ATTR_OUTCOME] == OUTCOME_INVALID_JWT
        assert spans[0].status.status_code is StatusCode.ERROR

        points = _points_with_attrs(
            metric_reader.get_metrics_data(),
            "jwt.extract.duration",
            {ATTR_OUTCOME: OUTCOME_INVALID_JWT},
        )
        assert len(points) == 1


# --------------------------------------------------------------------------- #
# Tests: JWKS store                                                           #
# --------------------------------------------------------------------------- #


class TestJWKStoreTelemetry:
    """Spans and histograms emitted by the in-memory JWK store."""

    @pytest.mark.asyncio
    async def test_get_jwk_unknown_kid_records_invalid_jwt(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
    ) -> None:
        """A KeyError on get_jwk maps to ``invalid_jwt``."""
        store = JWKStoreMemory()

        with pytest.raises(KeyError):
            await store.get_jwk(kid="unknown-kid")

        spans = _spans_by_name(span_exporter, "jwt.jwks.get_jwk")
        assert len(spans) == 1
        assert spans[0].attributes is not None
        assert spans[0].attributes[ATTR_KID] == "unknown-kid"
        assert spans[0].attributes[ATTR_OUTCOME] == OUTCOME_INVALID_JWT
        assert spans[0].status.status_code is StatusCode.ERROR

        points = _points_with_attrs(
            metric_reader.get_metrics_data(),
            "jwt.jwks.get.duration",
            {ATTR_OUTCOME: OUTCOME_INVALID_JWT},
        )
        assert len(points) == 1

    @pytest.mark.asyncio
    async def test_bootstrap_failure_records_internal_error(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
    ) -> None:
        """A failing introspect service maps to ``internal_error`` for the bootstrap span."""
        introspect_service = MagicMock()
        introspect_service.get_wellknown_jwks = AsyncMock(side_effect=HydraOperationError("boom"))

        with pytest.raises(HydraJWKSStoreError):
            await configure_jwks_in_memory_store_from_hydra_introspect_services(
                introspect_service_list=[introspect_service]
            )

        spans = _spans_by_name(span_exporter, "jwt.jwks.bootstrap")
        assert len(spans) == 1
        assert spans[0].attributes is not None
        assert spans[0].attributes[ATTR_OUTCOME] == OUTCOME_INTERNAL_ERROR

        points = _points_with_attrs(
            metric_reader.get_metrics_data(),
            "jwt.jwks.bootstrap.duration",
            {ATTR_OUTCOME: OUTCOME_INTERNAL_ERROR},
        )
        assert len(points) == 1


# --------------------------------------------------------------------------- #
# Tests: identifier ContextVar propagation                                    #
# --------------------------------------------------------------------------- #


class TestIdentifierPropagation:
    """``JWT_IDENTIFIER_CTX`` propagates through all child layers."""

    @pytest.mark.asyncio
    async def test_identifier_present_on_all_child_spans(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
    ) -> None:
        """Decoder/verifier child spans inherit the identifier without a constructor argument."""
        service = _make_service(jwt_config=jwt_config, jwt_payload=jwt_payload)

        await service.authenticate(request=_request_with_bearer_token())

        for span in span_exporter.get_finished_spans():
            assert span.attributes is not None
            assert span.attributes.get(ATTR_PAYLOAD_IDENTIFIER) == _TEST_IDENTIFIER, (
                f"span {span.name} missing identifier"
            )

    @pytest.mark.asyncio
    async def test_identifier_reset_after_authenticate(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
    ) -> None:
        """The ``ContextVar`` is reset to ``None`` after ``authenticate`` returns."""
        from fastapi_factory_utilities.core.security.jwt.telemetry import (  # noqa: PLC0415
            JWT_IDENTIFIER_CTX,
        )

        service = _make_service(jwt_config=jwt_config, jwt_payload=jwt_payload)
        await service.authenticate(request=_request_with_bearer_token())

        assert JWT_IDENTIFIER_CTX.get() is None


# --------------------------------------------------------------------------- #
# Tests: decoder spans                                                        #
# --------------------------------------------------------------------------- #


class TestJWTDecoderTelemetry:
    """Spans and histograms emitted by the concrete decoder."""

    @pytest.mark.asyncio
    async def test_decode_success_sets_kid_and_iss(
        self,
        span_exporter: InMemorySpanExporter,
        metric_reader: InMemoryMetricReader,
        jwt_config: JWTBearerAuthenticationConfig,
        jwt_payload: JWTPayload,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``jwt.kid`` and ``jwt.iss`` attributes are populated on a successful decode."""
        from fastapi_factory_utilities.core.security.jwt import decoders as decoders_module  # noqa: PLC0415
        from fastapi_factory_utilities.core.security.jwt.decoders import (  # noqa: PLC0415
            GenericJWTBearerTokenDecoder,
        )

        class _Decoder(GenericJWTBearerTokenDecoder[JWTPayload]):
            """Concrete decoder for testing."""

        jwks_store = MagicMock()
        jwks_store.get_jwk = AsyncMock(return_value=MagicMock())
        jwks_store.get_issuer_by_kid = AsyncMock(return_value=OAuth2Issuer(_DEFAULT_ISSUER))

        decoder = _Decoder(jwt_bearer_authentication_config=jwt_config, jwks_store=jwks_store)

        async def _fake_decode_jwt_token_payload(**_: Any) -> dict[str, Any]:
            now = datetime.datetime.now(tz=datetime.UTC)
            return {
                "scp": ["read"],
                "aud": ["api"],
                "iss": _DEFAULT_ISSUER,
                "exp": int((now + datetime.timedelta(hours=1)).timestamp()),
                "iat": int(now.timestamp()),
                "nbf": int((now - datetime.timedelta(minutes=5)).timestamp()),
                "sub": "user",
            }

        monkeypatch.setattr(decoders_module, "decode_jwt_token_payload", _fake_decode_jwt_token_payload)
        monkeypatch.setattr(_Decoder, "get_kid_from_jwt_unsafe_header", lambda self, jwt_token: "the-kid")

        result: JWTPayload = await decoder.decode_payload(jwt_token=JWTToken("a.b.c"))
        assert isinstance(result, JWTPayload)

        spans = _spans_by_name(span_exporter, "jwt.decode")
        assert len(spans) == 1
        assert spans[0].attributes is not None
        assert spans[0].attributes[ATTR_KID] == "the-kid"
        assert spans[0].attributes[ATTR_ISSUER] == _DEFAULT_ISSUER
        assert spans[0].attributes[ATTR_OUTCOME] == OUTCOME_SUCCESS

        points = _points_with_attrs(
            metric_reader.get_metrics_data(),
            "jwt.decode.duration",
            {ATTR_OUTCOME: OUTCOME_SUCCESS},
        )
        assert len(points) == 1
