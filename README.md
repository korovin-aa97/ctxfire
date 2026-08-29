# ctxfire

**See what every coding agent loads, why it loads, and what that repeated
context could cost.**

![ctxfire context graph preview](https://raw.githubusercontent.com/korovin-aa97/ctxfire/main/docs/assets/social-preview.png)

`ctxfire` is a local, telemetry-free static analyzer for multi-agent context
graphs. It connects agent definitions to repository instructions, rules, and
skills; multiplies the estimated input by each agent's schedule; and keeps every
assumption visible.

```text
implementer [codex@1]
  context candidates: 3 files, 18120 exact bytes/fire
  estimate: 3810 tokens/fire × 8/day = 30480 tokens/day
reviewer [claude-code@1]
  context candidates: 4 files, 22644 exact bytes/fire
  estimate: 4725 tokens/fire × 8/day = 37800 tokens/day

TOTAL estimated tokens/day: 68280
```

This is not a runtime meter or an invoice calculator. File sizes are exact;
tokens, conditional activation, cache behavior, schedules, and API-equivalent
prices are estimates recorded in every report.

## Why another context-cost tool?

Most repository analyzers ask, “How large is this codebase?” Runtime meters ask,
“What did this one session consume?” `ctxfire` asks a different question:

> What is the transitive instruction surface of each agent, and what happens
> when the team loads it repeatedly every day?

The unit of analysis is `agent → loading rule → context file → schedule`, not a
flat repository walk.

## Quickstart

The runtime requires Python 3.11+ and Git. Install the published package with
`pipx` (recommended) or another Python package manager:

```bash
pipx install 'ctxfire==0.1.2'
ctxfire --version
curl -fsSLo ctxfire.toml \
  https://raw.githubusercontent.com/korovin-aa97/ctxfire/v0.1.2/ctxfire.example.toml
ctxfire scan
```

Or run without a persistent install:

```bash
uvx --from 'ctxfire==0.1.2' ctxfire scan --config ctxfire.toml
```

Start from [`ctxfire.example.toml`](https://github.com/korovin-aa97/ctxfire/blob/main/ctxfire.example.toml):

```toml
schema_version = "1"

[project]
name = "my-agent-team"
root = "."
bytes_per_token = 4.0
tokenizer = "byte-estimate"
model = "unspecified"
price_date = "unspecified"
cache_assumption = "no-cache-credit"
conditional_activation_rate = 0.25

[[agents]]
name = "implementer"
adapter = "codex@1"
working_directory = "."
fires_per_day = 8
include = ["docs/product-rules.md"]
conditional = ["docs/playbooks/**/*.md"]
```

`usd_per_million_input_tokens` is optional. Add it only with a model and a
dated price you have verified. `ctxfire` deliberately ships no silently aging
vendor price table.

## Commands

```bash
# Human report
ctxfire scan --config ctxfire.toml

# Stable schema 1.0 snapshot
ctxfire scan --format json --output before.json

# Why is each edge present?
ctxfire explain --agent implementer
ctxfire explain --file AGENTS.md

# Attribute change between snapshots
ctxfire diff before.json after.json

# CI: exit 2 only when a budget is exceeded
ctxfire check --max-tokens-per-day 75000

# GitHub-compatible SARIF
ctxfire check --max-tokens-per-day 75000 --format sarif --output ctxfire.sarif
```

Exit codes are stable: `0` success/pass, `1` invalid input or operational error,
and `2` a valid scan that exceeded a `check` budget.

## Exact versus estimated

| Field | Kind | Meaning |
|---|---|---|
| relative path, file presence, byte size | Exact | Facts from the local working tree |
| adapter and inclusion reason | Declared model | Versioned loading semantics used for the graph |
| tokens | Estimated | `ceil(bytes / bytes_per_token)` by default, or an opt-in local tokenizer count |
| conditional activation | Estimated | User-provided rate from 0 to 1 |
| fires/day | Assumption | Planning input; `ctxfire` is not a scheduler |
| USD/day | Estimated equivalence | Dated input-token price × estimated tokens; not a bill |
| cache | Assumption | Stated in the report; v0.1 does not observe cache hits |

The default estimator never reads file contents. This makes it reproducible and
privacy-safe, but less accurate than a model-specific tokenizer—especially for
non-English text and code-heavy files.

For an opt-in local tokenizer:

```bash
pipx install 'ctxfire[tokenizers]'
```

Then set `tokenizer = "tiktoken:cl100k_base"` (or another explicit tiktoken
encoding). The report records the installed tokenizer version and changes
`discovery.content_access` to `matched-file-content-local`. Matched bytes are
read only in memory; they are never printed, stored, or uploaded.

## Supported adapters

| Adapter | Always-on context | Conditional candidates |
|---|---|---|
| `explicit@1` | `include` patterns | `conditional` patterns |
| `agents-md@1` | ancestor `AGENTS.md` chain for `working_directory` | configured patterns |
| `codex@1` | precedence-selected ancestor instruction chain, under a declared byte cap | ancestor `.agents/skills/*/SKILL.md` bodies |
| `claude-code@1` | ancestor project memory and conservative project rules | descendant memory and project skill bodies |

Adapters are conservative static models, not claims that every candidate is
loaded on every invocation. Details, source links, and known uncertainty are in
[`docs/ADAPTER_SPEC.md`](https://github.com/korovin-aa97/ctxfire/blob/main/docs/ADAPTER_SPEC.md).

## Git-aware and private by default

- Uses `git ls-files --cached --others --exclude-standard` at a Git top-level.
- Includes tracked files and non-ignored untracked files; ignored build output
  does not silently inflate the graph.
- Probes only known exact engine instruction paths and exact configured paths
  outside that universe, so an ignored `CLAUDE.local.md` is still counted and
  clearly warned without opening arbitrary ignored trees.
- Skips symlinks rather than following them outside the repository.
- Skips submodule gitlinks and missing/non-regular paths with a warning.
- Emits repository-relative paths, never an absolute workstation path.
- Default byte mode reads file metadata only. The optional tokenizer reads only
  matched files locally; neither mode makes network calls, emits telemetry,
  uploads content, or invokes a model.

For non-Git directories, a clearly reported conservative filesystem fallback is
used. See [`docs/PRIVACY.md`](https://github.com/korovin-aa97/ctxfire/blob/main/docs/PRIVACY.md)
and [`docs/DISCOVERY.md`](https://github.com/korovin-aa97/ctxfire/blob/main/docs/DISCOVERY.md).

## CI example

```yaml
- name: Enforce agent context budget
  run: |
    pipx install 'ctxfire==0.1.2'
    ctxfire check --max-tokens-per-day 75000 \
      --format sarif --output ctxfire.sarif
```

Pin a package version in CI. `ctxfire diff` also lets reviewers see
whether a context-cost increase came from a new file, a removed file, or a size
change.

## Current limitations

- The default byte-ratio estimator is intentionally approximate. The optional
  tiktoken backend is more repeatable for a named encoding but still does not
  prove which tokenizer a hosted agent runtime used.
- Claude rule frontmatter is not parsed by the v0.1 adapter. Rules are counted
  as always-on by default; set `claude_rules_activation =
  "conditional"` only when that is a justified project-wide approximation.
- User-level/global engine instructions are outside the project root and are
  intentionally not scanned.
- Imports referenced inside Markdown are not inferred. Add them explicitly.
- Submodule contents and symlink targets are not traversed.
- Subscription quotas, tool output, conversation history, cached-token billing,
  output tokens, and runtime prompt construction are outside scope.

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
mypy src
pytest
python -m build
```

The report contract is public API. Schema changes require a new schema version,
fixture updates, and a changelog entry.

See the [deterministic before/after demo](https://github.com/korovin-aa97/ctxfire/blob/main/docs/DEMO.md)
for a small, inspectable
`diff` walkthrough.

Questions about bills, privacy, shared files, rules, symlinks, or prices are
answered in the [FAQ](https://github.com/korovin-aa97/ctxfire/blob/main/docs/FAQ.md).

The default package has no runtime dependencies; the optional tokenizer stack
and its licenses are recorded in the
[dependency review](https://github.com/korovin-aa97/ctxfire/blob/main/docs/DEPENDENCIES.md).

## Project status

`v0.1.2` is a distribution-only patch over the intentionally small first
release. The analyzer was exercised against 18 unrelated public repositories;
the dated methodology and results live in
[`docs/VALIDATION.md`](https://github.com/korovin-aa97/ctxfire/blob/main/docs/VALIDATION.md).
Contributions are welcome—see
[`CONTRIBUTING.md`](https://github.com/korovin-aa97/ctxfire/blob/main/CONTRIBUTING.md)
and the extension guide.

Built from operating a mixed Claude/Codex production fleet. The analyzer is a
clean, generic extraction: no private fleet configuration or telemetry is
included.

MIT © 2026 Alexander Korovin.
