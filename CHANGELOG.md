# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- CORS defaults are deny-by-default: ``allow_origins=[]``,
  ``allow_credentials=False``. ``FastAPIBuilder`` only installs
  ``CORSMiddleware`` when ``allow_origins`` is non-empty. Config validation
  rejects ``"*"`` combined with ``allow_credentials=True`` (closes the
  Starlette Origin-reflection footgun). **Breaking for consumers that relied
  on the previous ``["*"]`` + credentials defaults** — set explicit origins
  (and credentials if needed) in ``application.yaml``.
- Hydra JWT introspection cache keys are namespaced by configured issuer
  (``issuer`` + NUL + ``jti``), not ``jti`` alone, preventing cross-issuer
  cache confusion in a shared process. Cache hits also re-check ``exp``.
- Mark ``JWTNoneVerifier`` as a test-only no-op: renamed conceptually to
  ``JWTNoOpIntrospectionVerifier`` (preferred in ``__all__``), and warn on
  instantiation. Compatibility alias ``JWTNoneVerifier`` remains importable
  from ``fastapi_factory_utilities.core.security.jwt`` and ``.verifiers``,
  but is omitted from package ``__all__`` / star-import.

## [6.5.3] - 2026-08-29

### Fixed

- TaskiqPlugin: watch ``_scheduler_task`` the same way as ``_worker_task`` so a
  dead cron loop marks TASK_QUEUE not-ready and Kubernetes restarts the pod
  (receiver-only watch left readiness green while periodic jobs silently stopped).

## [6.5.2] - 2026-08-22

### Fixed

- Taskiq: pass ``maxlen=10_000`` (approximate) to ``RedisStreamBroker`` so
  Valkey Taskiq streams are trimmed on publish instead of growing without bound.

## [6.5.1] - 2026-08-21

### Fixed

- Grype: stop copying the shared node DB. Point `GRYPE_DB_CACHE_DIR` at the
  RO `/var/cache/grype-db` mount with `GRYPE_DB_AUTO_UPDATE=false` so scans
  no longer ENOSPC the 2Gi `$HOME/.cache` tmpfs (or waste RAM on `$RUNNER_TEMP`).

## [6.5.0] - 2026-08-21

### Removed

- ``fastapi_factory_utilities.core.testing``, the ``testing`` extra, and the
  ``pytest11`` plugin. A trial adoption in ``audit_backend`` did not collapse
  that service's plugin+testcontainer fixtures to configuration (the shipped
  doubles sit at the driver seam on a bare FastAPI app; AMQP broker tests
  still need a real RabbitMQ). Each consumer keeps its own fixtures.
  ``RepositoryContract`` remains in FFU's test suite and still runs against
  both mongomock and a real Mongo container.
- pylint (pre-commit hook, test-group dependency, ``pylintrc``). Current ruff
  (``D,F,E,W,I,UP,PL,N,RUF``) and pylint (rcfile with ``disable=R,`` plus
  in-source suppressions) both reported zero findings. Candidate extra ruff
  rules (``ARG``, ``BLE``, ``SLF``, ``TRY``) would add 247 new findings pylint
  was not enforcing. No ruff rule added.
- Example console script ``fastapi_factory_utilities-example``. The demo stays
  in the checkout (``python -m fastapi_factory_utilities.example``); it is not
  in the wheel.

### Changed

- Python constraint is ``>=3.12,<3.13``, matching the interpreter CI runs.
  ``example/`` is excluded from coverage measurement; the floor is 89%.
- ``Development Status`` classifier is ``5 - Production/Stable``.
- ``AbstractRepositoryInMemory`` is no longer deprecated. ``core.testing`` is
  gone and consumers still subclass it; the warning would have been
  indefinite. Prefer mongomock/testcontainer when the test needs a driver.
- Plugin counts, extras lists, and Python versions in prose point at
  ``pyproject.toml`` / ``core/plugins/`` instead of restating a number.
- CI installs from the committed ``poetry.lock``. Pre-push checks the lock
  (``poetry check --lock``) instead of ``poetry update``. SBOM/Grype read that
  lock. Weekly ``deps-canary`` workflow re-resolves independently.

### Added

- Distinction in module docs: ``core.exceptions`` is the library error base;
  ``core.utils.exceptions`` is the mapping machinery.

## [6.4.0] - 2026-08-15

### Changed

- Plugin packages follow ``<technology>_plugin``: ``taskiq_plugin`` (was
  ``taskiq_plugins``), ``aiohttp_plugin``, ``aiopika_plugin``. Old import paths
  remain as ``DeprecationWarning`` aliases until ``7.0.0``. Every plugin package
  now has ``plugins.py``, ``configs.py``, ``builder.py``, ``depends.py`` and
  ``exceptions.py``. Named HTTP/S3 depends share ``NamedResourceDepends``;
  startup connection warm-up shares ``PluginAbstract._warm_soft``.

## [6.3.0] - 2026-08-15

### Added

- Shared ``PluginStatusMixin`` for StatusService registration. ``AiopikaPlugin``
  and ``TaskiqPlugin`` now report readiness (broker / Redis backend). A
  disconnect arms not-ready after 15s so a single reconnect does not flap.
  aiohttp ``affects_readiness`` (default false) opts a named HTTP dependency
  onto the critical path. OpenTelemetry does not register a component (not a
  data path). AMQP telemetry is optional; if ``OpenTelemetryPlugin`` is
  registered it must appear before ``AiopikaPlugin``.

## [6.2.0] - 2026-08-14

### Added

- Application-state registry (``core.plugins.state``). Plugin writes and
  ``depends_*`` reads share named keys. A missing plugin raises
  ``PluginNotRegisteredError`` naming the plugin. A plugin used before
  ``set_application`` raises ``PluginNotBoundError``. OpenTelemetry
  accessors live in ``opentelemetry_plugin.depends``.

## [6.1.0] - 2026-08-14

### Added

- ``redis_plugin.exceptions``: ``RedisPluginConfigError`` and
  ``RedisPluginNotStartedError``. Accessing the Redis client before
  ``on_startup`` raises the latter instead of ``RuntimeError``.

### Changed

- Plugin YAML loading goes through ``build_config_from_file_in_package``
  (``error_type=``). Unset ``PACKAGE_NAME`` is always
  ``UnableToReadConfigFileError("PACKAGE_NAME is unset.")``. Malformed
  plugin config names the YAML base key.
- aiohttp ``dependencies.http.*`` uses the same helper, so environment
  injection is explicit (``YamlFileReader`` already defaulted it on;
  ``${ENV:default}`` placeholders already resolved).
- ``RedisCredentialsConfig`` lives in ``redis_plugin.configs``;
  ``RabbitMQCredentialsConfig`` in ``aiopika.configs``.
  ``core.utils.redis_configs`` and ``core.utils.rabbitmq_configs`` are
  deleted.
- ``OpenTelemetryPluginBaseException`` and ``ODMPluginBaseException`` now
  subclass ``FastAPIFactoryUtilitiesError``. An OTel config failure is
  catchable with ``except Exception`` and may degrade instead of crashing
  (it previously inherited ``BaseException`` and escaped startup handlers).

## [6.0.1] - 2026-08-14

### Fixed

- Mandatory-only CI job uses Poetry instead of ``python3.12 -m venv``.
  The runner has no ``ensurepip``, so the ``v6.0.0`` tag never reached
  PyPI. Install ``6.0.1``.
- Pre-push ``poetry update --sync`` no longer strips extras. Poetry 2.4
  ``update`` has no ``--extras``; the hook now locks, then
  ``sync --all-extras``.

## [6.0.0] - 2026-08-14

### Added

- Optional extras ``mongo``, ``amqp``, ``s3``, ``redis``, ``taskiq``, ``otel``,
  and ``all``. Backing technologies are no longer mandatory; importing a plugin
  without its extra raises ``MissingExtraError`` naming the extra to install.
- ``OpenTelemetryConfig.instrumentations`` selects which instrumentors to load.
  Absent target libraries are skipped with a log line.

### Changed

- **BREAKING:** install the extras you use
  (``fastapi_factory_utilities[mongo,otel]``, …). ``[all]`` restores the 5.x
  kitchen-sink set minus Granian/Hypercorn.
- **BREAKING:** Uvicorn is the only bundled ASGI server. ``granian.py`` and
  ``hypercorn.py`` are deleted (zero consumer importers). Bring your own server
  if you need a different one; FFU still exposes the ASGI app.
- OpenTelemetry instrumentors import lazily from configuration instead of
  eagerly at plugin import.
- **Required consumer action:** bump to ``fastapi-factory-utilities ^6.0.0``
  and declare the extras you actually import. A 5.x pin will not install
  6.0.0. Thin services that only see FFU through ``velmios_core`` wait for
  that wrapper to publish a 6.x line.

### Deprecated

- ``ExceptionMapper``, ``exception_mapper``, and ``MonitoredAbstract`` emit
  ``DeprecationWarning`` and will be removed in ``7.0.0``. Use
  ``ExceptionMappingContext`` and ``StatusService.register_component_instance``.

## [5.25.0] - 2026-08-14

### Added

- Package-root ``__init__.py`` so ``py.typed`` is carried by a regular package
  and PEP 561 types resolve from an installed wheel.
- Package-level re-exports of symbols consumers already deep-imported:
  ``ODMConfig``, ``OAuth2Scope`` / ``OAuth2Issuer`` / ``OAuth2Audience`` /
  ``OAuth2Subject``, ``KratosSessionAuthenticationService``, ``JWTLocation``,
  ``HydraJWKSStoreError``, ``DependsCsrfProtect``, ``RedisCredentialsConfig``,
  ``RabbitMQCredentialsConfig``. These are re-exports of existing symbols with
  no behaviour change. See README "Public API and deprecation".
- Optional ``connection_factory`` on ``AiopikaPlugin`` (defaults to
  ``connect_robust``) so tests can inject a double without patching a private
  module path.

### Changed

- Documented the public-API boundary: public means listed in an
  ``__init__.__all__``; private modules may move in minors without a shim; a
  public removal gets a ``DeprecationWarning`` naming the replacement, held at
  least one minor, removed no earlier than the next major.

## [5.24.0] - 2026-08-13

### Added

- CSFLE (Client-Side Field Level Encryption) support in the ODM plugin.
  Services declare encrypted field paths as data on the document class
  (``Settings.encrypted_fields``); ``ODMBuilder`` resolves those into a
  client-side ``schemaMap``, unwraps the local KMS master key from Vault
  Transit via the pod's projected ServiceAccount token
  (``ODMConfig.csfle_*`` fields), and provisions a per-service Data
  Encryption Key. Query analysis is delegated to ``mongocryptd``
  (installed by the consuming service via an Aptfile — not bundled by
  this library); ``ODMPlugin`` runs a throwaway encrypted round trip at
  startup so ``mongocryptd``'s lazy spawn happens before the first real
  request.
- ``pymongo[encryption]`` extra (``pymongocrypt``, ``pymongo-auth-aws``).

## [5.23.0] - 2026-08-09

### Added

- ``fastapi_factory_utilities.core.testing`` — infrastructure test doubles at the
  driver seam: mongomock via ``pymongo-async-mock`` (``build_mongomock_database``),
  ``fakeredis``, moto ``ThreadedMotoServer`` for S3, ``taskiq.InMemoryBroker`` for
  Taskiq, OTel in-memory exporters, plus a recording-only ``InMemoryPublisher`` and
  ``build_incoming_message`` for AMQP (no broker simulation).
- ``RepositoryContract`` shared suite run against both mongomock and a real Mongo
  testcontainer in CI so the fake cannot silently drift from production.
- ``testing`` Poetry extra (``pymongo-async-mock``, ``fakeredis``, ``moto[server]``)
  and a ``pytest11`` plugin that registers the fixtures.
- Container-only boundary documented: Mongo transactions / multi-doc atomicity and
  all AMQP broker semantics (routing, confirms, DLX/TTL retry).

### Deprecated

- ``AbstractRepositoryInMemory`` — prefer ``build_mongomock_database`` /
  ``mongomock_database`` so Beanie and ``AbstractRepository`` execute for real.
  Emits ``DeprecationWarning``; removal planned after one release cycle.

### Removed

- Unused ``pytest-mongo`` test dependency.
- ``find_spec("pytest")`` gating on ODM / aiohttp mocker exports (always exported).

## [5.22.0] - 2026-08-08

### Added

- ``RedisPlugin`` — general-purpose async Redis client (``redis.asyncio``) with
  ``build_key`` namespacing, Depends accessors for HTTP/Taskiq, startup ``ping``,
  shutdown ``aclose``, and ``StatusService`` registration as ``CACHE``. Separate
  pool from ``TaskiqPlugin``; no TTL/serialization/fail-open policy in the plugin.
- Direct ``redis`` dependency (``^8.0``).
- ``AbstractRepository.count()`` and public ``collection_name`` accessor for
  global match counts without reaching into ``_document_type``.

## [5.21.2] - 2026-08-08

### Fixed

- Aiopika ``AbstractListener`` rejects decode/validation poison with
  ``requeue=False`` (invalid bodies never become valid by redelivery).
- ``AbstractManagedListener.POISON_MESSAGE_REQUEUE`` default is now ``False``.

## [5.21.1] - 2026-08-04

### Fixed

- ``reconcile_update_request`` replaces union-typed updateable fields wholesale:
  ``_flatten_dict`` stops descending at known updateable leaves so a
  discriminated-union value is not key-patched into ignored child paths.

## [5.21.0] - 2026-08-01

### Added

- ``S3BucketResource`` bucket-scoped async helpers: ``get_bytes``, ``put_bytes``,
  ``put_file``, ``download_to_file``, ``head_or_none``, ``list_keys``, ``delete``,
  ``object_url``, ``key_from_url``, and ``presigned_get_url``.
- Canonical object-URL codec (``parse_bucket_and_key``) with a strict percent-encoded
  path-style writer and a tolerant reader that accepts path-style and virtual-host
  legacy URLs regardless of endpoint host.
- ``S3Config.presign_endpoint_url`` / ``presign_expiry_seconds`` and a second
  signing-only aioboto3 client (host-only SigV4 + public path-prefix re-injection).
- OpenTelemetry ``AiobotocoreInstrumentor`` (``opentelemetry-instrumentation-botocore``)
  wired into the OpenTelemetry plugin instrument list.

## [5.20.0] - 2026-08-01

### Added

- OpenTelemetry auto-instrumentation for ``httpx`` and ``redis`` (opt-in via
  package presence, same ``find_spec`` pattern as other instruments).

### Changed

- ``OpenTelemetryPluginBuilder.build_resource`` uses ``Resource.create`` so
  ``OTEL_RESOURCE_ATTRIBUTES`` (e.g. ``environment=stg``) merges with
  application ``service.*`` / ``deployment.environment`` attributes.
- Trace context propagator is now a composite of W3C ``tracecontext``,
  ``baggage``, and B3 multi (was B3-only).

## [5.19.1] - 2026-07-29

### Fixed

- S3 plugin pre-commit / CI: import ``aioboto3.session.Session`` for mypy,
  rename ``S3PluginBaseException`` → ``S3PluginBaseError`` (N818), and clear
  pylint findings in startup / fixtures / unit tests.

## [5.19.0] - 2026-07-29

### Added

- **S3Plugin** — async MinIO / S3 integration via aioboto3: shared long-lived
  client, named buckets in YAML (`s3.buckets`), `S3BucketDepends` DI, and
  STORAGE health / readiness. Declared buckets must already exist at startup.

### Changed

- Agent skill docs no longer live under `docs/skill/`; canonical skill is
  [DeerHide/agent_skills](https://github.com/DeerHide/agent_skills/tree/main/skills/fastapi-factory-utilities)
  (`docs/SKILL.md` pointer).

## [5.18.5] - 2026-07-25

### Fixed

- Release CI posts the poetry.lock dependency snapshot via the Dependency
  Submission API with ``ref: refs/heads/main``. Runners ignore ``GITHUB_*``
  env overrides, so the v5.18.4 ``GITHUB_REF`` workaround never retargeted
  ``anchore/sbom-action`` away from ``refs/tags/*``.

## [5.18.4] - 2026-07-25

### Fixed

- Release CI submits the Syft dependency snapshot against ``refs/heads/main``
  so Dependabot can refresh the default-branch graph and auto-close alerts.
  Tag-ref snapshots never reached that graph, leaving the November 2025
  manifest frozen and generating false-positive alerts.

## [5.18.3] - 2026-07-25

### Fixed

- Drop ``[tool.poetry.requires-plugins]`` so Homebrew Poetry can
  ``poetry install`` when nmap's ``ndiff==7.99`` is visible on
  ``sys.path``. Wire dynamic versioning through the PEP 517
  ``poetry_dynamic_versioning.backend`` instead.

## [5.18.2] - 2026-07-25

### Fixed

- Pylint C1803 / C0123 in the v5.18.1 consolidating tests (empty-container
  comparisons and ``type(None)`` checks) so tag CI passes.

## [5.18.1] - 2026-07-25

### Fixed

- ``nested_basemodel_for_annotation`` sequence descent is opt-in via
  ``descend_sequences=True``. Unconditional descent in 5.18.0 collapsed
  ``list[Model]`` response/update annotations to a scalar nested model, broke
  ``get_exposed_fields`` / ``get_updateable_fields`` for list containers, and
  caused ``reconcile_update_request`` to silently ignore PUT updates to
  list-of-model fields. Filter builders (``SearchableEntity``, dotted path
  helpers) pass ``descend_sequences=True``; response/update builders keep the
  default.
- ``build_query_filter_kwargs`` resolves query-name segments against
  ``validation_alias`` values (longest-prefix match), so dotted alias escape
  hatches such as ``object1.field1`` re-nest onto the Python field instead of
  being dropped.

## [5.18.0] - 2026-07-25

### Added

- ``nested_basemodel_for_annotation`` descends into homogeneous sequence
  containers (``list`` / ``set`` / ``tuple`` / ``Sequence``) whose item type is
  a ``BaseModel``, so ``SearchableEntity.build_query_filter_model`` builds
  nested filter segments for ``list[Model]`` fields (e.g. ``features.enabled``).
  Scalar sequences (``list[str]``, ``list[UUID]``, …) remain leaf
  ``QueryField``s for MongoDB array-membership equality.
- ``build_query_filter_kwargs`` re-nests dotted :class:`QueryResolver` fields
  into kwargs for ``model.model_construct``, so generic search endpoints no
  longer silently drop nested filters.
- ``SearchableEntity.build_query_filter_model`` prefers Pydantic-resolved
  ``FieldInfo.annotation`` over ``typing.get_type_hints`` so generic TypeVars
  on concrete subclasses (e.g. ``config: MyConfig | None``) produce nested
  filter segments instead of unbound ``TypeVar`` leaves.

## [5.17.0] - 2026-07-25

### Added

- ``setup_log`` injects ``trace_id`` / ``span_id`` (lowercase hex) from the
  active OpenTelemetry span into every structlog and stdlib log record so
  Loki lines can be correlated with Tempo traces.

## [5.16.5] - 2026-07-25

### Fixed

- Ruff/pre-commit: extend ``# noqa`` for ``PLR0917`` (too many positional
  args) and put ``None`` last in ODM ``sort`` unions (``RUF036``) so tag
  CI passes on current Ruff.

## [5.16.4] - 2026-07-21

### Fixed

- Taskiq scheduler startup no longer passes Starlette ``State`` into
  ``taskiq_fastapi.populate_dependency_context``. That library
  ``copy.copy``s the ASGI state mapping; copying ``State`` recurses via
  ``__getattr__`` and floods workers with ``RecursionError``. Depends already
  resolve from ``request.app.state`` via ``scope["app"]``.

## [5.16.3] - 2026-07-20

### Fixed

- ``DependsRootConfig`` uses ``request: Request = TaskiqDepends()`` so Taskiq
  workers can resolve ``depends_root_config`` (and nested ``Depends`` chains)
  without ``TypeError: missing 1 required positional argument: 'request'``.

### Changed

- Bump `anchore/sbom-action` to v0.24.0 and `anchore/scan-action` to v7.4.0 (Node.js 24) to clear GitHub Actions Node 20 deprecation warnings.

## [5.16.2] - 2026-07-18

### Fixed

- JWT decoder: unknown `kid` (`KeyError` from JWKS lookup) maps to
  `InvalidJWTError` so callers get a clean auth failure instead of an
  unhandled 500.
- ``QueryResolver`` treats empty or whitespace-only filter query values as
  absent (``?field=`` no longer fails coercion for UUID/enum filters).

### Changed

- Bump `softprops/action-gh-release` from v2.5.0 to v3.0.2 (Node.js 24 runtime) to clear the GitHub Actions Node 20 deprecation warning.

## [5.16.1] - 2026-07-14

### Changed

- Dependency constraints bumped: uvicorn (>=0.51.0), pyaml (^26.7.0), certifi
  (^2026.6.17), psutil (^7), pyupgrade (^3.21.2), locust (^2.45.0).
- ``fastapi`` upper bound raised to ``<0.140.0`` now that
  ``opentelemetry-instrumentation-fastapi`` 0.64b0 fixes FastAPI 0.137+ included-router
  tracing.

## [5.16.0] - 2026-07-14

### Changed

- OpenTelemetry SDK, OTLP exporters, and B3 propagator bumped to 1.43; aio-pika
  instrumentation aligned to 0.64b0 so semantic-conventions resolve with the SDK.
- structlog constraint raised to 26.x.
- pymongo constraint raised to 4.17.x.
- Dev-only type stubs refreshed (types-deprecated, types-pygments, types-colorama).

## [5.15.1] - 2026-07-11

### Fixed

- ODM plugin: ``ODMPluginBaseException`` now subclasses ``Exception`` instead of
  ``BaseException``, so duplicate-key and other ODM errors participate in normal
  exception handling and can be mapped to HTTP responses instead of escaping as
  unhandled ASGI failures.

## [5.15.0] - 2026-07-08

### Changed

- **BREAKING** Taskiq: Redis stream, result-backend, and schedule-source keys are
  now prefixed with ``<name_suffix>:taskiq:…`` (e.g.
  ``youtube-integration:taskiq:stream``) so they fall under per-service Valkey ACL
  grants ``~<svc>:*``. Services must set ``TaskiqPlugin(name_suffix=…)`` to the
  pulumi service name (matching ``redis-<svc>``). Existing ``taskiq_*_<suffix>``
  keys are orphaned on upgrade; cron schedules re-register on the next tick.

## [5.14.0] - 2026-07-05

### Added

- Taskiq: ``SchedulerComponent.prune_unregistered_schedules()`` removes persisted
  schedules for tasks no longer registered, self-healing the legacy ``heartbeat``
  cron leftover.

## [5.13.3] - 2026-06-30

### Changed

- Aiopika: publisher and listener setup no longer acquire unused AMQP channels;
  queue and nested exchange share one channel via ``ensure_shared_channel_with``
  and ``reset_channel``.
- Aiopika: removed broken ``depends_robust_connection`` helper (use
  ``depends_aiopika_robust_connection``).

## [5.13.2] - 2026-06-29

### Removed

- Taskiq: ``SchedulerComponent`` no longer auto-schedules a registered ``heartbeat``
  task on startup; consumers must schedule cron tasks explicitly.

## [5.13.1] - 2026-06-25

### Fixed

- Aiopika: ``AbstractPublisher.set_robust_connection`` now propagates the robust
  connection to its owned exchange, fixing ``AiopikaPluginConnectionNotProvidedError``
  when ``setup()`` declares the exchange after ``set_robust_connection``.

## [5.13.0] - 2026-06-25

### Added

- API: ``build_response_model`` now projects ``list`` and ``dict`` containers of nested
  ``ApiResponseModelAbstract`` types recursively, dropping unexposed leaves instead of
  reusing raw nested domain classes (fixes generic-model JSON serialization failures).

## [5.12.1] - 2026-06-25

### Fixed

- Logging: disable ``show_locals`` in JSON traceback rendering (``dict_tracebacks``) so exceptions whose frame locals hold non-JSON-serializable objects (e.g. ``bson.Binary``) no longer crash the ``JSONRenderer`` with ``TypeError: Object of type ... is not JSON serializable``.

## [5.12.0] - 2026-06-24

### Added

- Aiopika: ``AbstractManagedListener`` with precheck gate, ``MessageDeliveryOutcome`` settlement (ack / requeue / delayed requeue), and ``process_message`` pipeline.
- Aiopika: swappable ``ConcurrencyGate`` interface with ``LocalConcurrencyGate`` (process-local asyncio semaphores), registry helpers, and optional OpenTelemetry consumer telemetry.
- Aiopika: delay retry queue topology helpers for ``REQUEUE_DELAYED`` dead-letter / TTL patterns.

## [5.11.0] - 2026-06-24

### Changed

- Taskiq: auto-schedule the ``heartbeat`` cron only when a task named ``heartbeat`` is registered; services without that task no longer fail startup or receive a default every-minute schedule.

## [5.10.1] - 2026-06-24

### Fixed

- Aiopika: include the offending value and length in ``PartStr`` validation errors so queue-name segment overflows are easier to diagnose at startup.

## [5.10.0] - 2026-06-23

### Added

- Logging: suppress ASGI access log lines for successful (HTTP 200) ``/sys/health`` and ``/sys/readiness`` probe requests (uvicorn, hypercorn, granian).

## [5.9.0] - 2026-06-21

### Added

- JWT: optional Hydra introspection cache keyed by verified ``jti`` claim, using ``cacheout`` with per-entry TTL capped by token expiration; configurable via ``JWTBearerAuthenticationConfig`` (``cache_enabled``, ``cache_ttl_seconds``, ``cache_max_entries``). Signature verification still runs on every request.

## [5.8.3] - 2026-06-20

### Fixed

- ODM plugin: omit ``maxIdleTimeMS`` and ``heartbeatFrequencyMS`` from ``AsyncMongoClient`` when configured as ``0``; PyMongo requires values greater than zero, and zero is intended to mean no limit (driver default).

## [5.8.2] - 2026-06-20

### Fixed

- ODM plugin: source MongoDB warm-up timeout from the built config instead of optional plugin-injected config (which is ``None`` for default ``ODMPlugin()`` usage), use a single ``wait_for`` ping, and propagate startup failures instead of swallowing them.
- Granian server: enable ``log_enabled`` on the embed server so startup errors remain visible.

## [5.8.1] - 2026-06-20

### Fixed

- Config loading: surface Pydantic field-level validation errors in `ValueErrorConfigError` and propagate the underlying cause through `ConfigBuilderError`, so startup failures name the offending field and reason instead of a generic message.

## [5.8.0] - 2026-06-20

### Added

- API utilities: `fields` sparse-fieldset query param for search/list endpoints (`parse_fields_param`, `project`, `fields_query_param`) to prune response payloads by dotted paths (including `tasks[].name` list notation); always keeps `id` per result item.

## [5.7.0] - 2026-06-20

### Added

- Server: optional Granian ASGI support alongside Uvicorn and Hypercorn (`core.utils.granian`, app builder wiring), using Granian's embed server for in-process apps, with integration coverage for ASGI servers.

## [5.6.0] - 2026-06-20

### Added

- ODM plugin: warm the MongoDB connection pool on startup with ``min_pool_size``
  concurrent ``ping`` commands so the first request avoids cold-connect latency.

## [5.5.0] - 2026-06-19

### Added

- ODM plugin: configurable MongoDB connection pool tuning via ``ODMConfig``
  (``min_pool_size``, ``max_pool_size``, ``max_idle_time_ms``,
  ``heartbeat_frequency_ms``), forwarded to ``AsyncMongoClient`` at startup.

## [5.4.0] - 2026-06-19

### Added

- OpenTelemetry PyMongo plugin: optional ``pymongo_capture_statement`` config flag
  registers a sanitized ``request_hook`` that records truncated MongoDB command
  summaries (filter/sort/limit; large ``$in`` arrays capped) on CLIENT spans.

## [5.3.3] - 2026-06-19

### Fixed

- Dependencies: removed the explicit Starlette version pin; FastAPI remains capped at `<0.137.0` for OpenTelemetry compatibility.

## [5.3.2] - 2026-06-19

### Fixed

- Dependencies: pinned FastAPI to `<0.137.0` and added Starlette `>=1.2.1,<1.3.0` until `opentelemetry-instrumentation-fastapi` supports newer releases.

## [5.3.1] - 2026-06-15

### Fixed

- JWT telemetry tests: replaced an incorrect `@pytest.skip(...)` decorator with `@pytest.mark.skip(reason=...)` so the `tests/units/fastapi_factory_utilities/core/security/jwt/test_telemetry.py` module is collected by pytest again. The previous form invoked `pytest.skip()` at import time and aborted the whole module.
- JWT module lint/format compliance: rewrapped an over-long explanation comment in `extract_token_from_request` (E501), waived `PLR0911` on `JWTAuthenticationServiceAbstract.authenticate` where one return per error outcome is intentional, applied ruff-format reflow to multi-arg `_record_failure` and `raise_exception` call sites in `decoders.py`/`services.py`, and added file-level `# ruff: noqa: E402` plus pylint disables for the deliberate post-OTel-provider-install imports in the telemetry test module.

## [5.3.0] - 2026-06-15

### Added

- JWT OpenTelemetry instrumentation: new `core.security.jwt.telemetry` module exposing a shared tracer, meter and histogram instruments (`jwt.authentication.duration`, `jwt.extract.duration`, `jwt.decode.duration`, `jwt.verify.duration`, `jwt.jwks.get.duration`, `jwt.jwks.bootstrap.duration`), attribute keys (`jwt.identifier`, `jwt.outcome`, `jwt.location`, `jwt.kid`, `jwt.iss`), outcome constants and a `ContextVar`-based identifier propagator so the active auth-service identifier flows to all child JWT layers without constructor changes.
- JWT layers wired to telemetry: services, decoders, verifiers, stores and extraction strategies now emit spans (`jwt.authenticate`, `jwt.extract`, `jwt.decode`, `jwt.verify`, `jwt.jwks.get_jwk`, `jwt.jwks.bootstrap`), record durations, and tag operations with the resolved outcome (success / missing_credentials / invalid_jwt / expired / invalid_payload / not_verified / internal_error).
- Tests: unit tests covering JWT span emission, parent/child relationships, outcome attribution, histogram data points and `JWT_IDENTIFIER_CTX` propagation and reset.

### Changed

- `.cursorignore`: removed the redundant `.venv/` entry (already covered by the workspace defaults).

## [5.2.0] - 2026-06-14

### Added

- OpenTelemetry plugin: PyMongo / Beanie auto-instrumentation via `PymongoInstrumentor` (with `capture_statement=False` to keep raw query payloads out of span attributes), exposing CLIENT spans for both synchronous and asynchronous Mongo operations.
- OpenTelemetry plugin: HTTP client auto-instrumentation for `requests` and `urllib3` covering Google OAuth token refresh and other non-aiohttp outbound traffic.
- OpenTelemetry plugin: `asyncio` task instrumentation so scheduled coroutines and tasks produce spans on the configured tracer provider.
- OpenTelemetry plugin: process / runtime system metrics via `SystemMetricsInstrumentor` (CPU, memory, GC, ...) on the configured meter provider.
- Dependencies: `opentelemetry-instrumentation-requests`, `opentelemetry-instrumentation-urllib3`, `opentelemetry-instrumentation-asyncio`, `opentelemetry-instrumentation-system-metrics`, and `psutil` (runtime requirement of the system-metrics instrumentor).
- Tests: new unit tests covering the `INSTRUMENTS` registry order and each new instrumentor's `find_spec` guard and provider wiring.

## [5.1.0] - 2026-05-08

### Added

- Kratos admin service: added `delete_session(session_id)` helper to revoke a single session via the admin API with structured error mapping and logging.

## [5.0.2] - 2026-05-08

### Fixed

- Hydra introspection DTOs now accept nested/non-string `ext` claim values, preventing validation errors on richer token metadata.
- Hydra introspection service now reuses a single parsed JSON payload before model validation to keep response handling deterministic.

## [5.0.1] - 2026-05-07

### Fixed

- JWT authentication: verifier-raised invalid token errors are now translated into expected `403` authentication outcomes instead of bubbling as generic server failures.
- HTTP validation handling: request validation errors now return HTTP `422` with FastAPI-compatible structured `detail` payloads.

### Changed

- Logging: request validation logs now emit concise method/path/error-count metadata instead of full request objects.
- Logging: JWT authentication error classes now default to debug-level logging to reduce noise from expected invalid-credential flows.

## [5.0.0] - 2026-05-07

### Changed

- **Breaking:** API entities no longer inherit `QueryAbstract` through `ApiEntityAbstract`; query pagination/sort fields (`page`, `page_size`, `sorts`, computed `offset`) are no longer part of entity instances, while `SearchableEntity.build_query_filter_model()` still returns `QueryAbstract` filter models.

## [4.5.0] - 2026-05-01

### Added

- API: added `ApiEntityAbstract` as a convenience base combining searchable/query filter and response model behaviors for entity DTOs.

### Changed

- API markers: standardized marker usage around `ApiField(...)` flags across core services, ODM persisted entities, and API utility tests while preserving response/update/search semantics.

## [4.4.4] - 2026-05-01

### Changed

- API/query utilities: consolidated pagination, query abstractions/resolvers/types, and API response/searchable model helpers under `core.utils.api`; updated ODM plugin imports and coverage to match the new module layout.

## [4.4.3] - 2026-04-18

### Fixed

- API: `get_updateable_fields` now descends into nested `ApiResponseModelAbstract` fields that are marked only with `ApiResponseField`, so dotted updateable paths match `reconcile_update_request` for PUT payloads under API-only containers.

### Added

- Tests: coverage for updateable path collection and reconciliation (optional nested containers, deep API-only chains, combined `ApiResponseField` / `UpdateableField` markers, `added` / `removed` change kinds).

## [4.4.2] - 2026-04-17

### Changed

- CI: merged SBOM generation and Grype vulnerability scan into a single `dependency-scan` job and updated release dependencies accordingly, simplifying the pipeline while preserving artifacts used by release.

## [4.4.1] - 2026-04-17

### Fixed

- CI: workflow now uses runner-embedded Poetry/uv binaries from `/home/runner/.local/bin` instead of reinstalling toolchain dependencies in jobs, reducing setup overhead while keeping release publishing intact.

## [4.4.0] - 2026-04-17

### Added

- API response models: add `UpdateableField`, PUT request model generation, and update reconciliation helpers that merge payloads by policy, track changed/ignored paths, and support strict rejection of non-updateable fields.

## [4.3.2] - 2026-04-16

### Fixed

- Aiopika: `AbstractListener` passes the bound queue’s exclusivity (and an optional `exclusive` constructor override, including explicit `False`) to `consume` instead of always using an exclusive consumer; `Queue` exposes an `exclusive` read-only property.

## [4.3.1] - 2026-04-14

### Fixed

- CI release job: extract GitHub release notes when the `CHANGELOG.md` version line uses Keep a Changelog’s dated form (`## [x.y.z] - YYYY-MM-DD`), not only a bare `## [x.y.z]` line.

## [4.3.0] - 2026-04-14

### Added

- Application builder: `build_as_uvicorn_utils`, `build_as_hypercorn_utils`, and `build_and_serve` forward `**kwargs` to `build()` for callers that need late FastAPI wiring.

### Changed

- Queries: narrow mypy noise on dynamic `create_model` when building nested `SearchableEntity` query filter models.

## [4.2.1] - 2026-04-14

### Fixed

- Release: GitHub release notes extraction now matches the `CHANGELOG.md` version header exactly and fails the workflow when notes for the tag are missing/empty, preventing silent blank release descriptions.

## [4.2.0] - 2026-04-14

### Added

- Server: optional Hypercorn ASGI support alongside Uvicorn (`core.utils.hypercorn`, app builder wiring, config), with integration coverage for ASGI servers.

## [4.1.1] - 2026-04-14

### Added

- Audit: `AuditEventObject.pre_publish_hook(entity)` now provides a default hook for redacting or transforming audited entities before publish.

### Fixed

- Audit: `AbstractAuditPublisherService.publish` now delegates to `AbstractPublisher.publish` and wraps broker failures as `AuditServiceError` without recursive self-calls.
- Audit: default routing-key prefix now uses a valid topic segment (`all`) so the publisher service can be imported and instantiated safely.

## [4.1.0] - 2026-04-12

### Changed

- Audit: `AuditableEntity` uses a permissive Pydantic `model_config` (`extra="allow"`, `arbitrary_types_allowed=True`) so auditable actors can carry extended or non-JSON-native fields when needed.

## [4.0.1] - 2026-04-12

### Changed

- Audit: `AuditableEntity` is a standalone model again; `PersistedAuditableEntity` subclasses it with `revision_id` and optional auto-generated `id` aligned to `PersistedEntity` without multiple `BaseModel` inheritance.

## [4.0.0] - 2026-04-12

### Added

- Audit: `UseCaseName`, optional `AuditEventObject.use_case` (default `unknown`) and `metadata`, and `PersistedAuditableEntity` for ODM-backed documents.

### Changed

- **Breaking:** `AuditableEntity` now subclasses `PersistedEntity` with a required `id`, adds `published` / `published_at`, and drops embedded `entity_name`, `domain_name`, `service_name` fields and their getters (domain/service remain on `AuditEventObject`).

## [3.4.0] - 2026-04-11

### Added

- Queries: `QueryResolver` coerces query strings to `enum.Flag` / `enum.IntFlag`, `enum.Enum` (including `StrEnum` and `IntEnum`), and other leaf types via a `TypeAdapter` fallback (for example `datetime`).

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

[Unreleased]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.5.3...HEAD
[6.5.3]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.5.2...v6.5.3
[6.5.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.5.1...v6.5.2
[6.5.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.5.0...v6.5.1
[6.5.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.4.0...v6.5.0
[6.4.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.3.0...v6.4.0
[6.3.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.2.0...v6.3.0
[6.2.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.1.0...v6.2.0
[6.1.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.0.1...v6.1.0
[6.0.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v6.0.0...v6.0.1
[6.0.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.25.0...v6.0.0
[5.25.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.24.0...v5.25.0
[5.24.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.23.0...v5.24.0
[5.23.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.22.0...v5.23.0
[5.22.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.21.2...v5.22.0
[5.21.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.21.1...v5.21.2
[5.21.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.21.0...v5.21.1
[5.21.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.20.0...v5.21.0
[5.20.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.19.1...v5.20.0
[5.19.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.19.0...v5.19.1
[5.19.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.18.5...v5.19.0
[5.18.5]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.18.4...v5.18.5
[5.18.4]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.18.3...v5.18.4
[5.18.3]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.18.2...v5.18.3
[5.18.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.18.1...v5.18.2
[5.18.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.18.0...v5.18.1
[5.18.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.17.0...v5.18.0
[5.17.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.16.5...v5.17.0
[5.16.5]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.16.4...v5.16.5
[5.16.4]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.16.3...v5.16.4
[5.16.3]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.16.2...v5.16.3
[5.16.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.16.1...v5.16.2
[5.16.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.16.0...v5.16.1
[5.16.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.15.1...v5.16.0
[5.15.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.15.0...v5.15.1
[5.15.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.14.0...v5.15.0
[5.14.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.13.3...v5.14.0
[5.13.3]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.13.2...v5.13.3
[5.13.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.13.1...v5.13.2
[5.13.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.13.0...v5.13.1
[5.13.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.12.1...v5.13.0
[5.12.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.12.0...v5.12.1
[5.12.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.11.0...v5.12.0
[5.11.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.10.1...v5.11.0
[5.10.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.10.0...v5.10.1
[5.10.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.9.0...v5.10.0
[5.9.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.8.3...v5.9.0
[5.8.3]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.8.2...v5.8.3
[5.8.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.8.1...v5.8.2
[5.8.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.8.0...v5.8.1
[5.8.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.7.0...v5.8.0
[5.7.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.6.0...v5.7.0
[5.6.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.5.0...v5.6.0
[5.5.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.4.0...v5.5.0
[5.4.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.3.3...v5.4.0
[5.3.3]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.3.2...v5.3.3
[5.3.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.3.1...v5.3.2
[5.3.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.3.0...v5.3.1
[5.3.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.2.0...v5.3.0
[5.2.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.1.0...v5.2.0
[5.1.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.0.2...v5.1.0
[5.0.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.0.1...v5.0.2
[5.0.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v5.0.0...v5.0.1
[5.0.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.5.0...v5.0.0
[4.5.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.4.4...v4.5.0
[4.4.4]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.4.3...v4.4.4
[4.4.3]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.4.2...v4.4.3
[4.4.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.4.1...v4.4.2
[4.4.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.4.0...v4.4.1
[4.4.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.3.2...v4.4.0
[4.3.2]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.3.1...v4.3.2
[4.3.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.3.0...v4.3.1
[4.3.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.2.1...v4.3.0
[4.2.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.2.0...v4.2.1
[4.2.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.1.1...v4.2.0
[4.1.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.1.0...v4.1.1
[4.1.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.0.1...v4.1.0
[4.0.1]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v4.0.0...v4.0.1
[4.0.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v3.4.0...v4.0.0
[3.4.0]: https://github.com/DeerHide/fastapi_factory_utilities/compare/v3.3.0...v3.4.0
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
