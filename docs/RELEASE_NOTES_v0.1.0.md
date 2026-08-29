# ctxfire v0.1.0

The first public release of **ctxfire**, a local static analyzer for multi-agent
context graphs.

## Highlights

- See the instruction, rule, and skill files attributed to each configured agent.
- Explain every edge with versioned `codex@1`, `claude-code@1`, `agents-md@1`,
  and `explicit@1` loading semantics.
- Multiply context estimates by a declared schedule without pretending to be a
  runtime meter or invoice.
- Compare snapshots with `diff` and enforce stable budgets with `check`.
- Export stable JSON schema 1.0 and SARIF 2.1.0.
- Keep the default scan metadata-only, local, dependency-free, and telemetry-free.
- Opt into a local, version-recorded tiktoken backend when byte approximation is
  not enough.

## Validation

The release passed 16 unit/integration tests, strict typing, Ruff, Bandit (no
medium/high findings), Actionlint, JSON Schema validation, wheel/sdist checks,
clean Python 3.11 and 3.12 installs, and a reproducible scan across 18 unrelated
public repositories. See [`docs/VALIDATION.md`](VALIDATION.md).

## Install

```bash
pipx install 'ctxfire==0.1.0'
ctxfire --version
```

## Important boundary

Byte sizes are exact. Tokens, conditional activation, schedules, cache behavior,
and API-equivalent prices are explicit estimates. They are not measured prompt
usage, cache hits, subscription charges, or vendor bills.
