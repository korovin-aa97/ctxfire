# Report and CLI contract

Report schema: `1.1`. Configuration schema: `1`.

The canonical schema is
[`../schemas/report-v1.1.schema.json`](../schemas/report-v1.1.schema.json).
Schema 1.0 remains published for existing snapshots, and `ctxfire diff` accepts
both 1.0 and 1.1 inputs.

## Scan JSON

Top-level fields:

- `schema_version`: report contract, independent of package version;
- `tool`: package name and version;
- `project`: user-selected name and privacy-safe `root: "."`;
- `discovery`: eligible-file method and boundary policies;
- `assumptions`: every factor used to produce estimates;
- `agents`: context edges and per-agent aggregation;
- `totals`: daily aggregate estimates;
- `warnings`: deterministic, sorted uncertainty and skipped-path messages.

`exact_candidate_bytes_per_fire` is the sum of all selected candidate files,
including conditional candidates. `estimated_tokens_per_fire` weights each
candidate's estimated token count by its activation rate and rounds up. Daily
tokens multiply that figure by `fires_per_day` and round up.

Each edge has `exact_bytes` from the current file and `counted_bytes` after an
adapter loading cap or component expansion. These differ, for example, when the
declared Codex combined instruction limit truncates the final file or when one
Claude skill contributes both a catalog entry and a full body.

Schema 1.1 requires a non-empty `components` array on every file edge. A
component has its own `kind`, `counted_bytes`, `estimated_tokens`, `activation`,
`activation_rate`, and `reason`. A file is `mixed` when its components do not
share one activation/rate. File `counted_bytes` and `estimated_tokens` are sums
of the components; its activation rate is their token-weighted average. Daily
aggregation weights components directly, so the machine report preserves the
always-on/conditional split instead of collapsing it into one opaque file
assumption.

`discovery.content_access` is `metadata-only` when neither the adapter nor the
tokenizer needs file content. It is `matched-file-content-local` for the
content-aware `claude-code@2` adapter and for an opt-in tokenizer. Assumptions
record tokenizer identity/version; adapter reasons disclose the metadata parse.

USD is `null` unless `usd_per_million_input_tokens` is explicitly configured.
When configured, it represents API-equivalent input pricing under the recorded
model/date/cache assumptions—not a subscription bill or measured charge.

## SARIF

`scan --format sarif` emits informational context-surface notes. `check --format
sarif` emits only failed budgets as error-level SARIF 2.1.0 results. GitHub
supports a subset of SARIF 2.1.0; see
https://docs.github.com/en/code-security/concepts/code-scanning/sarif-files.
Each result points at the requested config path when it is repository-relative;
an absolute config path is reduced to its filename to avoid leaking workstation
layout.

## Diff

`diff` accepts two valid full schema-1.0 or schema-1.1 scan snapshots, including
a cross-version pair. It reports per-agent daily token delta and path
additions/removals. A size-only or activation change appears in the token delta
even when the path sets are unchanged. Because snapshots can record different
assumptions, the text output states that each side uses its own assumptions.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | successful command or passing budget |
| `1` | invalid input, unsupported schema, or operational error |
| `2` | valid scan whose `check` budget was exceeded |

Adding an optional field is backward-compatible. Removing a field, changing a
field's meaning/type, or changing aggregation requires a new report schema.
Schema 1.1 changed aggregation by adding component-level activation; consumers
that only understand 1.0 must reject it rather than silently flattening it.
