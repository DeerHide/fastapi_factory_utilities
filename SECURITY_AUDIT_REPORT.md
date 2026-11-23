# Security audit report — fastapi_factory_utilities

**Date:** 2026-09-11  
**Scope:** Application security review of DeerHide/fastapi_factory_utilities (library defaults, JWT/Hydra auth helpers, CI/CD, supply chain).  
**Method:** Static review of `src/`, `.github/workflows/`, `pyproject.toml`, `SECURITY.md`, and Starlette CORS behavior. No production exploit against third parties.

Findings were filed as GitHub issues (no `security` label exists in the repo; severity is in the title).

## Inventory

| Issue | Severity | Summary |
|------:|----------|---------|
| [#41](https://github.com/DeerHide/fastapi_factory_utilities/issues/41) | High | Default CORS `allow_origins=["*"]` + `allow_credentials=True` reflects arbitrary `Origin` |
| [#42](https://github.com/DeerHide/fastapi_factory_utilities/issues/42) | Medium | JWT `aud` not verified by default; unused `audience` config field |
| [#43](https://github.com/DeerHide/fastapi_factory_utilities/issues/43) | Medium | Process-global Hydra introspection cache keyed only by `jti` |
| [#44](https://github.com/DeerHide/fastapi_factory_utilities/issues/44) | Medium | GitHub Actions pinned to tags, not commit SHAs (release/publish path) |
| [#45](https://github.com/DeerHide/fastapi_factory_utilities/issues/45) | Medium | CI `packages:write` / `contents:write` on `pull_request` (self-hosted runners) |
| [#46](https://github.com/DeerHide/fastapi_factory_utilities/issues/46) | Low | `JWTNoneVerifier` skips introspection/revocation; publicly exported |
| [#47](https://github.com/DeerHide/fastapi_factory_utilities/issues/47) | Low | `FastAPIBuilder` always enables OpenAPI/Swagger/ReDoc; no kill-switch |
| [#48](https://github.com/DeerHide/fastapi_factory_utilities/issues/48) | Info | `SECURITY.md` uses public issues; marks all 0.x unsupported |
| [#49](https://github.com/DeerHide/fastapi_factory_utilities/issues/49) | Low | Optional `taskiq-dependencies` from private velmios index |

## Residual risk / out of scope

- No Critical issues confirmed in this pass.
- Consumer apps remain responsible for wiring authz, Redis/Mongo/AMQP network controls, and production TLS.
- Example `docker-compose.yml` `:latest` tags and binding `0.0.0.0` are typical for local demos and were not filed separately.
- ODM query helpers enforce allowlists for filters/sorts; regex values are escaped — no separate injection issue filed.
- CSFLE Vault unwrap uses unverified JWT decode for **logging-only** namespace extraction (documented); not treated as an authz bypass.

## Suggested priority

1. Fix CORS defaults (#41) before the next release.  
2. Require JWT audiences (#42) and fix introspection cache keying (#43).  
3. Harden CI pin + permissions (#44, #45).  
4. Address Low/Info items in documentation and API surface cleanup.
