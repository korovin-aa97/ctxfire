# Changelog

All notable changes follow [Keep a Changelog](https://keepachangelog.com/) and
this project uses [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-08-31

### Added

- Add the content-aware `claude-code@2` adapter while preserving
  `claude-code@1` unchanged for metadata-only compatibility.
- Classify each Claude rule from its top-level `paths:` frontmatter instead of
  forcing one activation class across a mixed rule set.
- Account separately for always-visible skill and subagent catalogs,
  conditional full skill bodies, selected subagent definitions, and native
  `skills:` preloads.
- Warn when a selected subagent, declared preload, or same-scope definition is
  missing, disabled, or ambiguous.
- Add report schema 1.1 with independently activated per-file `components` and
  a synthetic Claude v2 example.

### Changed

- `diff` accepts both schema 1.0 and 1.1 scan snapshots.
- Reports explicitly disclose local matched-file reads required for Claude v2
  frontmatter/catalog parsing.

### Fixed

- Remove the material overcount caused by treating path-scoped and unscoped
  Claude rules as one project-wide activation class.

## [0.1.3] - 2026-08-30

### Fixed

- Publish the exact checksummed immutable GitHub Release wheel and source
  archive to PyPI instead of rebuilding them in a second environment.
- Verify release immutability, tag/version/SHA ancestry, PyPI digests, OIDC
  provenance, and clean wheel/source installs in the release workflow.

There are no runtime or report-schema changes from 0.1.2.

## [0.1.2] - 2026-08-30

### Changed

- Publish distribution artifacts under GitHub's immutable-releases policy.
- Refresh installation examples and release metadata for version 0.1.2.

There are no runtime or report-schema changes from 0.1.1. This release is
superseded by 0.1.3 because its independently rebuilt PyPI files did not
byte-match the immutable GitHub Release files.

## [0.1.1] - 2026-08-30

### Fixed

- Prevent exact-path probes from following a symlinked parent directory outside
  the configured project root.
- Reject non-finite numeric assumptions, Windows-style escape paths, malformed
  globs, malformed diff snapshots, and invalid CLI values with exit code 1.
- Let an authoritative explicit include restore full counting when a Codex
  instruction-chain cap selected the same file first.
- Point SARIF findings at the requested config file without exposing absolute
  workstation paths.

### Changed

- Pin CI actions, validate release tag ancestry/version, add Bandit and format
  checks, and smoke-test the dependency-free wheel.
- Make the PyPI quickstart and rendered README links work outside a source clone.

## [0.1.0] - 2026-08-29

### Added

- Versioned `explicit@1`, `agents-md@1`, `codex@1`, and `claude-code@1` adapters.
- Git-index discovery with standard ignores and safe symlink/submodule handling.
- `scan`, `explain`, `diff`, and `check` commands.
- Human, JSON schema 1.0, and SARIF 2.1.0 output.
- Explicit token, schedule, conditional-activation, cache, price, and model assumptions.
- Reproducible fixtures, external-repository validation, packaging, and CI.

[0.2.0]: https://github.com/korovin-aa97/ctxfire/releases/tag/v0.2.0
[0.1.3]: https://github.com/korovin-aa97/ctxfire/releases/tag/v0.1.3
[0.1.2]: https://github.com/korovin-aa97/ctxfire/releases/tag/v0.1.2
[0.1.1]: https://github.com/korovin-aa97/ctxfire/releases/tag/v0.1.1
[0.1.0]: https://github.com/korovin-aa97/ctxfire/releases/tag/v0.1.0
