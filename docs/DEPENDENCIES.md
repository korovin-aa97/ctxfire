# Dependency and license review

Reviewed from the locked release environment on 2026-08-30.

The default `ctxfire` installation has **zero runtime dependencies**.

The optional `tokenizers` extra installs tiktoken and its transitive runtime
dependencies. The versions resolved for the v0.1.1 release rehearsal were:

| Package | Version | Declared license |
|---|---:|---|
| tiktoken | 0.14.0 | MIT |
| regex | 2026.7.19 | Apache-2.0 AND CNRI-Python |
| requests | 2.34.2 | Apache-2.0 |
| charset-normalizer | 3.5.1 | MIT |
| idna | 3.19 | BSD-3-Clause |
| urllib3 | 2.7.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |

These are optional, dynamically installed libraries; none is copied or vendored
into ctxfire's MIT-licensed source or wheel. Their licenses permit the intended
use and distribution model. The lockfile also contains development-only tools,
which are not installed with the default package or tokenizer extra.

Re-run the metadata/license review whenever the optional dependency range or
lockfile changes.

The v0.1.1 rehearsal also audited the fully pinned default, tokenizer, and
development environments with `pip-audit`; no known vulnerabilities were
reported. GitHub Dependabot likewise reported no open dependency alerts.
