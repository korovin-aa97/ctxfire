# ctxfire v0.1.1

This patch release hardens project-boundary enforcement, invalid-input handling,
SARIF attribution, packaging, and the public install experience.

## Highlights

- Never follow an exact instruction/config path through a symlinked parent
  directory outside the configured project root.
- Reject non-finite estimates, cross-platform escape paths, malformed globs,
  invalid CLI values, and malformed diff snapshots with the documented error
  exit instead of a traceback or ambiguous result.
- Honor a full explicit include when the same file was first selected under a
  smaller Codex instruction-chain cap.
- Point SARIF results at the selected config without leaking an absolute path.
- Pin CI actions, verify release tag/version/ancestry, add Bandit and formatting
  gates, and smoke-test the zero-runtime-dependency wheel.
- Repair PyPI README assets, links, and the copy-paste quickstart.

## Validation

The release passes 28 unit/integration tests plus four parameterized numeric
cases on Python 3.11–3.13 across Linux, macOS, and Windows, strict typing, Ruff,
Bandit, Actionlint, JSON Schema validation, wheel/sdist checks, clean installs,
and deterministic scans of the 18-repository public corpus.

## Install

```bash
pipx install 'ctxfire==0.1.1'
ctxfire --version
```

Byte sizes are exact. Tokens, activation, schedules, caching, and
API-equivalent prices remain explicit planning estimates—not measured usage or
vendor bills.
