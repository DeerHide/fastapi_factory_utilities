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

## Supply-chain trust boundaries

- **Default / PyPI installs** resolve from the public Python Package Index.
- When resolving with **Poetry**, the optional extra **`taskiq`** installs
  `taskiq-dependencies` from the private index
  `https://pypi.velmios.io/simple` (`[[tool.poetry.source]]` name `velmios`,
  `priority = "explicit"`). That Poetry source configuration is an intentional
  trust boundary: consumers who enable `[taskiq]` via Poetry trust that host
  and its publishing pipeline. Compromise or spoofing of the index could
  deliver malicious code into apps that install FFU with `[taskiq]` through
  Poetry.
- **pip** does not read `[[tool.poetry.source]]`; it only contacts Velmios if
  you explicitly configure an index/extra-index URL. Prefer hash pinning /
  provenance checks in CI when using the Velmios index.
