# ctxfire v0.1.3

This corrective distribution-only patch publishes one exact checksummed wheel
and source archive to both the immutable GitHub Release and PyPI. It supersedes
v0.1.2, whose PyPI workflow independently rebuilt equivalent—but not
byte-identical—files.

There are no scanner behavior, adapter, report-schema, dependency, privacy, or
telemetry changes from v0.1.2.

## Distribution fixes

- Require the GitHub Release to be published and immutable before PyPI upload.
- Verify the release tag, package version, target SHA, and ancestry against
  `main`.
- Download and verify the release's exact wheel, source archive, and
  `SHA256SUMS` instead of rebuilding.
- Publish those verified files through the PyPI OIDC trusted publisher with
  attestations enabled.
- Compare PyPI SHA-256 digests and attested subjects with the GitHub assets,
  then perform clean wheel and forced-source installs from PyPI.

## Validation

The release passes the full cross-platform CI matrix on Python 3.11–3.13,
strict typing, Ruff, Bandit, Actionlint, JSON Schema validation, wheel/sdist
checks, clean installs, and reproducible-build comparison.

## Install

```bash
pipx install 'ctxfire==0.1.3'
ctxfire --version
```

Byte sizes are exact. Tokens, activation, schedules, caching, and
API-equivalent prices remain explicit planning estimates—not measured usage or
vendor bills.
