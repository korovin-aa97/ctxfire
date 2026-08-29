# Report and CLI contract

Report schema: `1.0`. Configuration schema: `1`.

The canonical schema is [`../schemas/report-v1.0.schema.json`](../schemas/report-v1.0.schema.json).

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
adapter loading cap. These differ, for example, when the declared Codex combined
instruction limit truncates the final file. Token estimates use `counted_bytes`.

`discovery.content_access` is `metadata-only` for the dependency-free byte
estimator and `matched-file-content-local` for an opt-in tokenizer. Assumptions
record both tokenizer identity and installed version.

USD is `null` unless `usd_per_million_input_tokens` is explicitly configured.
When configured, it represents API-equivalent input pricing under the recorded
model/date/cache assumptions—not a subscription bill or measured charge.

## SARIF

`scan --format sarif` emits informational context-surface notes. `check --format
sarif` emits only failed budgets as error-level SARIF 2.1.0 results. GitHub
supports a subset of SARIF 2.1.0; see
https://docs.github.com/en/code-security/concepts/code-scanning/sarif-files.

## Diff

`diff` accepts two full schema-1.0 scan snapshots. It reports per-agent daily
token delta and path additions/removals. A size-only change appears in the token
delta even when the path sets are unchanged. Because snapshots can record
different assumptions, the text output states that each side uses its own
assumptions.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | successful command or passing budget |
| `1` | invalid input, unsupported schema, or operational error |
| `2` | valid scan whose `check` budget was exceeded |

Adding an optional field is backward-compatible. Removing a field, changing a
field's meaning/type, or changing aggregation requires a new report schema.
