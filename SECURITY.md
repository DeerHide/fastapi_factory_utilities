# Security Policy

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 0.*.*   | :x:                |

## Reporting a Vulnerability

You can use Issue on the repository to report any vulnerabilities.
https://github.com/DeerHide/fastapi_factory_utilities/issues

Fixes will be done as best effort.

## Supply-chain trust boundaries

- **Default / PyPI installs** resolve from the public Python Package Index.
- The optional Poetry extra **`taskiq`** installs `taskiq-dependencies` from
  the private index `https://pypi.velmios.io/simple` (`[[tool.poetry.source]]`
  name `velmios`, `priority = "explicit"`). Consumers who enable that extra
  trust that host and its publishing pipeline. Compromise or spoofing of the
  index could deliver malicious code into apps that install FFU with
  `[taskiq]`. Prefer hash pinning / provenance checks in CI when using it.
