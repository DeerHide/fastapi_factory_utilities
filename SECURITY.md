# Security Policy

## Supported Versions

Security fixes are applied on a **best-effort** basis to the latest published
`0.x` / current major line on `main`. Older `0.*` releases are not
backported unless a maintainer explicitly says otherwise.

| Version | Supported |
| ------- | --------- |
| Latest release on `main` | :white_check_mark: best-effort |
| Older `0.*` tags | :x: no regular backports |

## Reporting a Vulnerability

**Prefer a private channel** so details are not public before a fix exists:

1. **GitHub Security Advisories / Private vulnerability reporting** for this
   repository (Security tab → Report a vulnerability), when enabled.
2. If private reporting is unavailable, email the maintainer listed in
   `pyproject.toml` (`maintainers`) with a clear subject like
   `[SECURITY] fastapi_factory_utilities …`.

Please include impact, affected versions, and a minimal reproduction when
possible. Do **not** open a public issue for unfixed vulnerabilities.

We aim to acknowledge reports and discuss next steps as capacity allows
(best-effort; no SLA).
