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
