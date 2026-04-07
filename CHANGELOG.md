# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v2.0.1...HEAD
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
