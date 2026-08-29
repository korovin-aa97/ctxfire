# Deterministic before/after demo

The synthetic [`../examples/demo`](../examples/demo) project has one always-on
instruction, one conditional release skill, and—in the baseline—one legacy
handbook explicitly loaded on every fire.

```bash
ctxfire scan --config examples/demo/before.toml --format json --output before.json
ctxfire scan --config examples/demo/after.toml --format json --output after.json
ctxfire diff before.json after.json
```

Expected v0.1 result:

```text
ctxfire diff
Estimated token deltas use each snapshot's recorded assumptions.

implementer: -1104 estimated tokens/day
  - docs/legacy-handbook.md
```

The number is not a measured saving. It is the reproducible difference between
two static graphs under the same recorded byte/token, activation, and schedule
assumptions. The example root is a subdirectory of this Git repository, so the
scanner deliberately reports its conservative filesystem fallback.
