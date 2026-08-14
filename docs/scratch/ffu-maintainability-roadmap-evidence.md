# ffu-maintainability-roadmap — group 1 evidence

Scratch for tasks 1.1–1.5. Codemod input: `deep-import-inventory.csv` (same directory).

## 1.1 Deep-import inventory

Counted as `ast.ImportFrom` of `fastapi_factory_utilities…` across 12 consumer repos (cloudflare_review_backend has none).

| Class | Count |
| --- | --- |
| Migrate (deep submodule; parent package should re-export) | 168 symbol occurrences / 141 import lines in the original audit |
| Keep as documented module path | `core.exceptions`, `core.utils.exceptions`, `core.app.enums`, `core.protocols` |
| Already package-level | the rest of the 889 import lines |

`core.utils` has no `__init__.py`, so `RedisCredentialsConfig` / `RabbitMQCredentialsConfig` re-export from `redis_plugin` and `aiopika` (their owning plugins), not a new utils barrel.

Symbols that still need an `__all__` addition (group 2):

| Package | Symbols |
| --- | --- |
| `core.plugins.odm_plugin` | `ODMConfig` |
| `core.security` | `OAuth2Scope`, `OAuth2Issuer`, `OAuth2Audience`, `OAuth2Subject`, `KratosSessionAuthenticationService` |
| `core.security.jwt` | `JWTLocation`, `HydraJWKSStoreError` |
| `core.app` | `DependsCsrfProtect` |
| `core.plugins.redis_plugin` | `RedisCredentialsConfig` (today on `utils.redis_configs`) |
| `core.plugins.aiopika` | `RabbitMQCredentialsConfig` (today on `utils.rabbitmq_configs`) |

Everything else in the migrate set is already in the parent `__all__` — consumer-only.

## 1.2 ASGI server

**uvicorn.** One server.

- `ApplicationGenericBuilder._server_implementation` defaults to `ServerImplementationEnum.UVICORN`.
- Every service entrypoint is `velmios-main` → `app_builder.build_and_serve()` with no `set_server_implementation`.
- CNB process in `velmios-services-gitops` overlays is `velmios-main`.
- `backend-base/deployment.yml` comment: "every backend boots a uvicorn".
- No consumer imports `GranianUtils` / `HypercornUtils` / `UvicornUtils`. Two commented `build_as_uvicorn_utils` leftovers in `audit_backend` and `customer_backend`.

Group 4.4 can delete `granian.py` and `hypercorn.py`. Do not stop group 5.

## 1.3 `dependencies.http.*` placeholders

Non-empty. Every consumer `application.yaml` uses `${ENV:default}` under `dependencies.http`.

| Service | Keys |
| --- | --- |
| customer_backend | kratos_public, kratos_admin, hydra_internal_{public,admin}, hydra_customer_{public,admin}, notifications_backend |
| youtube_integration_backend | hydra_internal_{public,admin}, hydra_customer_{public,admin}, customers |
| mcp_backend | hydra_internal_{public,admin}, hydra_customer_{public,admin} |
| information-provider-gateway-backend | hydra_internal_{public,admin}, hydra_customer_{public,admin}, vies, recherche_entreprises, eurovalidate, enigma |
| notification_backend | hydra_internal_{public,admin}, hydra_customer_{public,admin} |
| audit_backend | hydra_internal_{public,admin}, hydra_customer_{public,admin} |
| qonto-gateway-backend | hydra_internal_{public,admin}, hydra_customer_{public,admin}, qonto |
| review-backend | hydra_internal_{public,admin}, hydra_customer_{public,admin}, notification_backend |
| subscription-backend | hydra_internal_{public,admin}, hydra_customer_{public,admin}, customers, qonto_gateway, payment, information_provider_gateway |
| payment_backend | hydra_internal_{public,admin}, hydra_customer_{public,admin} |
| velmios-backend-service-template | hydra_internal_{public,admin}, hydra_customer_{public,admin} |

`YamlFileReader.use_environment_injection` already defaults to `True`, and `aiohttp/factories.py` omits the kwarg, so these already resolve today. The design's "will begin resolving" CHANGELOG note is stale. Still verify on stg in 5.5 because the shared loader in group 6 is the explicit path.

## 1.4 Dead-code importer counts

| Symbol / module | FFU `src/` importers | Consumer importers | Stay in group 11? |
| --- | --- | --- | --- |
| `ExceptionMapper`, `exception_mapper` | definitions + docs in `core/utils/exceptions.py` only | 0 | yes |
| `MonitoredAbstract` | definition in `core/utils/status.py` only | 0 | yes |
| `core.utils.granian` | `app/builder.py` + FFU tests | 0 | delete in 4.4 |
| `core.utils.hypercorn` | `app/builder.py` + FFU tests | 0 | delete in 4.4 |
| `core.utils.uvicorn` | `app/builder.py` + FFU tests | 0 | keep |

FFU tests for `ExceptionMapper` exist (`tests/units/…/test_exceptions.py`). No consumer imports. Group 11 still holds.

## 1.5 Plugin config helper

**Extend `build_config_from_file_in_package`. No sibling.**

It already takes `yaml_base_key` and always sets `use_environment_injection=True`. Plugin builders duplicate the YamlFileReader + validate block only to wrap errors in a plugin type. Group 6 adds an optional error-type argument (or a four-line `try/except` at each call site). Do not invent a second loader.

## 2.5 Plugin injection-seam audit

| Plugin | Opens a connection | Existing injection | Consumer private-path patch? | Action |
| --- | --- | --- | --- | --- |
| Aiopika | `connect_robust` | config only | yes (notification_backend, payment_backend) | add `connection_factory` (2.4) |
| ODM | Mongo client | `ODMBuilder(odm_client=…)` / `ODMPlugin(odm_config=…)` | no | none |
| Redis | `Redis.from_url` | `redis_credentials_config` | no (FFU unit tests patch `from_url`) | none |
| S3 | aioboto3 Session | `s3_config` | no | none |
| Taskiq | Redis broker via `SchedulerComponent` | `redis_credentials_config` | no | none |
