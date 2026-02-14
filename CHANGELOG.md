# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.16.1...HEAD
[0.16.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.16.0...v0.16.1
[0.16.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.15.1...v0.16.0
[0.15.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.15.0...v0.15.1
[0.15.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v0.14.0...v0.15.0
