# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [3.3.0] - 2026-04-11

### Added

- Queries: `QueryFieldOperation` accepts `T | list[T]` for `value` and validates that lists are only used with `in` / `nin` operators; ODM builder tests cover UUID `id` filters.

### Fixed

- Queries: `QueryResolver` coerces `typing.NewType` over any supported scalar supertype (for example `NewType(..., str)`), not only `uuid.UUID`.

## [3.2.1] - 2026-04-11

### Fixed

- ODM: `ODMQueryBuilder` maps filter field `id` to MongoDB `_id` so match documents align with Beanie primary key storage.

## [3.2.0] - 2026-04-11

### Added

- ODM: `PersistedEntity` mixes in `SearchableEntity` and `ApiResponseModelAbstract`; `id`, `created_at`, and `updated_at` use `ApiResponseField` and `SearchableField` so shared query and response model builders apply consistently.

## [3.1.1] - 2026-04-11

### Fixed

- Queries: `QueryResolver` preserves `typing.NewType` annotations when deriving field types so values such as `NewType(..., uuid.UUID)` coerce from query strings to `uuid.UUID` (not plain `str`).

## [3.1.0] - 2026-04-11

### Added

- Services: Audit (`AuditableEntity`, `AuditEventObject`), Hydra (`HydraTokenIntrospectObject`), and Kratos session/identity DTOs mix in `SearchableEntity` and `ApiResponseModelAbstract`, with fields marked via `Annotated[..., ApiResponseField, SearchableField]` for the shared query and response model builders.
- Tests: OpenTelemetry integration teardown flushes and shuts down the meter provider using the configured closing timeout.

## [3.0.0] - 2026-04-11

### Added

- API: `ApiResponseField` marker; `ApiResponseModelAbstract.build_response_model` derives exposed fields from `Annotated[..., ApiResponseField]` instead of `FIELDS_ALLOWED_FOR_RESPONSE`.
- Queries: `SearchableField` marker, `QueryFilterNestedAbstract`, and `SearchableEntity.build_nested_query_filter_model` for nested filter segments; `SearchableEntity.build_query_filter_model` derives searchable fields from `Annotated[..., SearchableField]` instead of `SEARCHABLE_FIELDS` or dotted path lists.
- Queries: `QueryResolver` coerces `uuid.UUID` (including `NewType` wrappers over `UUID`) from query strings.

### Changed

- **Breaking:** `ApiResponseModelAbstract` drops `FIELDS_ALLOWED_FOR_RESPONSE` and dotted nested path configuration; nest `ApiResponseModelAbstract` subclasses to shape nested responses.
- **Breaking:** `SearchableEntity` drops `SEARCHABLE_FIELDS` and dotted nested paths; nest `SearchableEntity` subclasses so nested filters map to inner models (with dotted query keys via existing resolver rules).

## [2.1.1] - 2026-04-10

### Changed

- Queries: `SearchableEntity.build_query_filter_model` subclasses `QueryAbstract`, so generated filter models include pagination and sort fields; the previous standalone `QueryFilterAbstract` model was removed and `QueryFilterAbstract` is now an alias to `QueryAbstract` in `core.utils.queries`.

## [2.1.0] - 2026-04-10

### Added

- Dynamic API response model builder (`ApiResponseModelAbstract`, `ApiResponseSchemaBase`) for nested Pydantic projections using dotted field paths.
- Shared `pydantic_path_fields` helpers to resolve dotted paths and detect prefix conflicts.
- `QueryFilterAbstract` and `SearchableEntity` to build optional `QueryField`-typed filter models from searchable field lists, with unit tests for API and query utilities.

## [2.0.1] - 2026-04-07

### Fixed

- Aiopika: listener decodes message bodies as UTF-8 JSON; malformed JSON, decode errors, and validation failures are logged and the delivery is rejected with requeue

### Added

- Tests: unit tests for `AbstractListener` setup, consume registration, close, and `_on_message` success and error paths

## [2.0.0] - 2026-04-06

### Added

- Audit: required `entity`, `domain`, and `service` on `AuditEventObject`; export `DomainName`, `EntityFunctionalEventName`, `EntityName`, and `ServiceName` from the audit package

### Changed

- Audit (**breaking**): publisher and listener services use `AuditEventObject[AuditableEntity]`; routing-key pattern is documented as `{prefix}.{domain}.{service}.{what}.{why}`

### Fixed

- Aiopika: AMQP `connect_robust` failures are raised as `AiopikaPluginBaseError`

## [1.0.0] - 2026-04-06

### Added

- Aiopika: validated `PartStr`, `AbstractName`, `RoutingKey`, `QueueName`, and `ExchangeName`; fluent builders for routing keys, queue names, and exchange names; topic wildcard `*` support for listener-style patterns; unit tests for types, builders, `GenericMessage`, and `AbstractPublisher.publish`
- Audit: `AuditServiceError` includes `audit_event` and `routing_key` context when audit publish fails

### Changed

- Aiopika: `GenericMessage` initializes an optional incoming delivery reference; publisher treats failed serialization, broker errors, missing confirmation, and `Basic.Return` as `AiopikaPluginBaseError`

### Fixed

- Aiopika: `GenericMessage.ack` / `reject` behave when no incoming message is bound

### Removed

- Audit (**breaking**): `AuditableEntity` no longer uses private attributes for metadata; callers must pass `entity_name`, `domain_name`, and `service_name` (excluded from default serialization)

## [0.24.0] - 2026-04-05

### Added

- Core: `QueryResolver.from_model` registers query-string keys for nested filter models (non-`QueryAbstract` `BaseModel` fields produce dotted paths such as `object1.field1`) and for `Field` `validation_alias` / `AliasChoices`; optional-union nested models are supported when exactly one branch is such a model; self-referential nested graphs are skipped safely after the first visit
- Core: `QueryAbstract.get_fields` flattens nested filter models into entries keyed by each nested `QueryField` name (so ODM filters keep dotted Mongo paths)
- ODM: `ODMQueryBuilder` and `ODMFindQuery` in `odm_plugin.queries` to translate `QueryAbstract` into MongoDB match filters and Beanie `find` kwargs (`skip`, `limit`, `sort`), including multi-operation merge per field
- Tests: unit tests for the ODM query builder; integration tests with Beanie/MongoDB and a FastAPI-style resolver chain

## [0.23.0] - 2026-04-04

### Added

- Core: `core.utils.queries` package — `QueryField`, `QuerySort`, `QueryFieldOperatorEnum`, `QueryResolver`, and `QueryAbstract` for filter/sort query parsing and coercion from FastAPI requests
- Core: unit tests for query types, field names, resolver behavior, `QueryAbstract`, and docstring-aligned examples

### Changed

- Core: pagination helpers — `resolve_offset` moved to `paginations.helpers`; `paginations` re-exports `PaginationPageOffset`, `PaginationSize`, and `resolve_offset` only

## [0.22.1] - 2026-03-17

### Fixed

- JWT: raise dedicated `ExpiredJWTError` when bearer token is expired for clearer error handling and differentiation from generic invalid token errors

## [0.22.0] - 2026-03-14

### Added

- Core: CSRF exception handler with structured logging returning 403 on invalid token
- Core: `register_csrf_protect_exception_handler(app)` to register CSRF exception handler on FastAPI app
- Core: validation exception handler and `register_exception_handlers(app)` for FastAPI

### Changed

- Core: CSRF registration function renamed to `register_csrf_protect_exception_handler` (from `register_exception_handler`)

## [0.21.1] - 2026-03-14

### Removed

- Dev: explicit black dependency from pyproject.toml (formatting remains via pre-commit)

## [0.21.0] - 2026-03-13

### Added

- Core: CSRF configuration model and dependency helpers to integrate `fastapi-csrf-protect` via `RootConfig.csrf` and application state

## [0.20.0] - 2026-03-02

### Added

- JWT: configurable bearer token extraction strategies for bearer token resolution

## [0.19.2] - 2026-02-28

### Changed

- JWT: `audience` moved from `BaseApplicationConfig` to `JWTBearerAuthenticationConfig`; Hydra OAuth2 client credentials service now accepts `config` and `default_audience` instead of application config

## [0.19.1] - 2026-02-26

### Changed

- Aiohttp plugin: extracted `AioHttpResourceDepends.export_from_state` helper to reuse FastAPI application state export logic

## [0.19.0] - 2026-02-25

### Added

- JWT/Hydra: in-memory JWKS store configuration helper from Hydra introspect services and FastAPI dependency for Hydra JWKS store (`configure_jwks_in_memory_store_from_hydra_introspect_services`, `DependsHydraJWKStoreMemory`)

### Changed

- JWT: documentation and authentication abstractions updated to use `JWTAuthenticationServiceAbstract`, `GenericJWTBearerTokenDecoder`, issuer type `OAuth2Issuer`, and issuer-aware JWK stores

### Removed

- Repo: removed legacy `.cursor` configuration directory and `.gitmodules` metadata from version control

## [0.18.0] - 2026-02-23

### Added

- JWT: `JWTBearerAuthenticationConfigBuilder` to build config from application YAML
- JWT: `DependsJWTBearerAuthenticationConfig` for FastAPI state injection
- JWT: `JWTBearerAuthenticationConfigBuilderError` and `CONFIG_FILENAME` on `ApplicationAbstract`
- Unit tests for JWT config builder and dependency in `test_configs.py`

## [0.17.1] - 2026-02-23

### Changed

- JWT: single issuer in config, generic decoder/verifier, and issuer-by-kid in JWK stores

## [0.17.0] - 2026-02-16

### Added

- ODM plugin: `PersistedEntity` is now generic over entity ID type (`PersistedEntity[BookEntityId]`) for typed IDs with improved docstring and usage example

## [0.16.1] - 2026-02-14

### Fixed

- KratosSessionObject validation update

## [0.16.0] - 2026-01-25

### Added

- Pagination utilities module (`core/utils/paginations/`)
  - `PaginationSize` type with validation (1-200 range, default 50)
  - `PaginationPageOffset` type with validation (min 0, default 0)
  - `depends_pagination_page_offset()` for FastAPI dependency injection
  - `depends_pagination_page_size()` for FastAPI dependency injection
  - `resolve_offset()` utility function to calculate database offset from page offset and page size
  - Comprehensive unit test suite (191 lines, 5 test classes)
- Query filter helper module (`core/utils/query_helper.py`)
  - `QueryFilterHelper` class for validating and transforming query parameters in FastAPI endpoints
  - `QueryFilterValidationError` exception for invalid filter values
  - `QueryFilterUnauthorizedError` exception for unauthorized filter keys
  - Support for type transformation and validation of query parameters
  - Configurable error handling (raise on unauthorized/invalid filters)
  - Comprehensive unit test suite (530 lines)

## [0.15.1] - 2026-01-25

### Security

- Added exception for protobuf waiting fix in Grype configuration

## [0.15.0] - 2026-01-24

### Added

 - Exception mapping utilities module (`core/utils/exceptions.py`)
  - `ExceptionMapping` dataclass for defining source-to-target exception mappings
  - `exception_mapper` decorator for mapping exceptions in sync and async functions
  - `ExceptionMapper` class for wrapping method calls with exception mapping
  - `ExceptionMappingContext` context manager supporting both sync and async contexts
  - Support for context hooks (sync and async) to inject context into target exceptions
  - Exception chaining preserved via `raise ... from` syntax
  - Comprehensive test suite for exception mapping utilities (72 tests)

[Unreleased]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v3.3.0...HEAD
[3.3.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v3.2.1...v3.3.0
[3.2.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v3.2.0...v3.2.1
[3.2.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v3.1.1...v3.2.0
[3.1.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v3.1.0...v3.1.1
[3.1.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v3.0.0...v3.1.0
[3.0.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v2.1.1...v3.0.0
[2.1.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v2.0.1...v2.1.0
[2.0.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.24.0...v1.0.0
[0.24.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.23.0...v0.24.0
[0.23.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.22.1...v0.23.0
[0.22.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.22.0...v0.22.1
[0.22.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.21.1...v0.22.0
[0.21.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.21.0...v0.21.1
[0.21.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.20.0...v0.21.0
[0.20.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.19.2...v0.20.0
[0.19.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.19.1...v0.19.2
[0.19.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.19.0...v0.19.1
[0.19.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.18.0...v0.19.0
[0.18.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.17.1...v0.18.0
[0.17.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.17.0...v0.17.1
[0.17.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.16.1...v0.17.0
[0.16.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.16.0...v0.16.1
[0.16.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.15.1...v0.16.0
[0.15.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.14.0...v0.15.0
