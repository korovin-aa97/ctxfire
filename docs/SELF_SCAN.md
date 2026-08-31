# Dated self-scan

This is a small real-repository smoke test, not a measured savings case study.
It scans the `ctxfire` repository at commit `30c16729f233` with the checked-in
[`examples/ctxfire-self.toml`](../examples/ctxfire-self.toml) configuration.

Run date: 2026-08-31. Tool version: 0.1.3.

This pinned pre-v0.2 scan remains a historical launch baseline. It does not
exercise the content-aware Claude adapter; use the synthetic
[`examples/claude-v2`](../examples/claude-v2) fixture for that contract.

```bash
uvx --from 'ctxfire==0.1.3' ctxfire scan \
  --config examples/ctxfire-self.toml
uvx --from 'ctxfire==0.1.3' ctxfire explain \
  --config examples/ctxfire-self.toml
```

The scan attributes the same root `AGENTS.md` file to two configured agents
under two explicit loading models:

```text
implementer [codex@1]
  context candidates: 1 files, 4444 exact bytes/fire
  estimate: 1111 tokens/fire x 8/day = 8888 tokens/day
reviewer [agents-md@1]
  context candidates: 1 files, 4444 exact bytes/fire
  estimate: 1111 tokens/fire x 8/day = 8888 tokens/day

TOTAL estimated tokens/day: 17776
```

The 4,444-byte file sizes are facts at the pinned commit. The token figures use
the declared four-bytes-per-token approximation, and eight fires per day is an
illustrative schedule. The result is not observed prompt construction, usage,
cache behavior, savings, subscription cost, or a vendor bill. See the broader
[18-repository validation report](VALIDATION.md) for discovery and adapter
coverage beyond this intentionally minimal self-scan.
