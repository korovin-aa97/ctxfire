# ctxcost

Private draft of a static cost analyzer for multi-agent context graphs.

`ctxcost` answers a practical question: which instructions, skills, and memory
files are loaded by each agent, how often is that agent started, and what is the
estimated context volume per day?

It is intentionally not a live usage tracker and not an exact billing tool.
File sizes are exact; token and price figures are estimates whose assumptions
must be shown in every report.

## Draft scope

- explicit, versioned adapters described in TOML;
- git-aware file discovery is planned but not implemented in this first draft;
- per-agent bytes, estimated tokens per fire, and estimated tokens per day;
- human and JSON output.

```bash
ctxcost scan --config ctxcost.toml
```

Before a public release this must be validated against 10–20 unrelated
repositories and the loading semantics of each supported agent engine.

No public license has been selected while this repository is private.
