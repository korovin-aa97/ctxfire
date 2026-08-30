# ctxfire v0.1.2

This distribution-only patch republishes the 0.1.1 runtime under GitHub's
immutable-releases policy. It does not change scanner behavior, adapter
semantics, report schemas, dependencies, privacy boundaries, or telemetry.

> **Superseded by v0.1.3:** the v0.1.2 PyPI workflow rebuilt the distributions
> independently, so their bytes did not match the immutable GitHub Release
> assets. Both sets came from the same source SHA and the runtime is unchanged;
> v0.1.3 publishes one exact verified set to both registries.

## Distribution changes

- Version package and installation metadata as 0.1.2.
- Publish checksummed wheel and source distribution assets through a draft
  release before making the release immutable.
- Publish the same distributions to PyPI through the OIDC trusted publisher,
  with attestations enabled.

## Validation

The release passes the full cross-platform CI matrix on Python 3.11–3.13,
strict typing, Ruff, Bandit, JSON Schema validation, wheel/sdist checks, clean
installs, and reproducible-build comparison.

## Install

```bash
pipx install 'ctxfire==0.1.2'
ctxfire --version
```

Byte sizes are exact. Tokens, activation, schedules, caching, and
API-equivalent prices remain explicit planning estimates—not measured usage or
vendor bills.
