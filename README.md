# ctxfire

**See what each configured coding agent can load, why it is included, and what
that repeated context could cost.**

![ctxfire context graph preview](https://raw.githubusercontent.com/korovin-aa97/ctxfire/main/docs/assets/social-preview.png)

`ctxfire` is a local, telemetry-free static analyzer for multi-agent context
graphs. It connects agent definitions to repository instructions, rules, and
skills; multiplies the estimated input by each agent's schedule; and keeps every
assumption visible.

Illustrative output (exact byte sizes plus estimates under declared
assumptions):

```text
implementer [codex@1]
  context candidates: 3 files, 18120 exact bytes/fire
  estimate: 3810 tokens/fire × 8/day = 30480 tokens/day
reviewer [claude-code@2]
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
pipx install 'ctxfire==0.2.0'
ctxfire --version
curl -fsSLo ctxfire.toml \
  https://raw.githubusercontent.com/korovin-aa97/ctxfire/v0.2.0/ctxfire.example.toml
ctxfire scan
```

The downloaded file is a template: edit the agent names, schedules, working
directories, and context paths before treating its estimates as meaningful.
Missing example paths are reported as warnings rather than silently ignored.

Or run without a persistent install:

```bash
uvx --from 'ctxfire==0.2.0' ctxfire scan --config ctxfire.toml
```

For a no-edit smoke test from a source checkout, scan `ctxfire` itself:

```bash
uvx --from 'ctxfire==0.2.0' ctxfire scan \
  --config examples/ctxfire-self.toml
```

The [dated self-scan](https://github.com/korovin-aa97/ctxfire/blob/main/docs/SELF_SCAN.md)
records the config, output, commit, and limitations.

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

# Stable schema 1.1 snapshot
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
| cache | Assumption | Stated in the report; ctxfire does not observe cache hits |

The default byte estimator is dependency-free and reads only file sizes for the
metadata-only adapters. `claude-code@2` locally reads matched rule, skill, and
subagent Markdown to derive frontmatter and catalog components; it never prints,
retains, or uploads that content. The byte ratio remains less accurate than a
model-specific tokenizer—especially for non-English text and code-heavy files.

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
| `claude-code@2` | ancestor project memory, unscoped rules, skill/subagent catalogs; selected subagent definition and preloaded skills | `paths:`-scoped rules, descendant memory, full skill bodies |

`claude-code@1` remains available as the metadata-only compatibility model. Use
`claude-code@2` for content-aware Claude projects. Omit `claude_subagent` for a
main session; set `claude_subagent = "reviewer"` to model an invocation or a
session started with that project subagent, including its declared `skills:`
preloads. A complete synthetic fixture lives in
[`examples/claude-v2`](https://github.com/korovin-aa97/ctxfire/tree/main/examples/claude-v2).

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
- Default byte mode reads file metadata only unless an adapter explicitly
  declares local metadata parsing. `claude-code@2` and the optional tokenizer
  read only matched files locally; no mode makes network calls, emits telemetry,
  uploads content, or invokes a model.

For non-Git directories, a clearly reported conservative filesystem fallback is
used. See [`docs/PRIVACY.md`](https://github.com/korovin-aa97/ctxfire/blob/main/docs/PRIVACY.md)
and [`docs/DISCOVERY.md`](https://github.com/korovin-aa97/ctxfire/blob/main/docs/DISCOVERY.md).

## CI example

```yaml
- name: Enforce agent context budget
  run: |
    pipx install 'ctxfire==0.2.0'
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
- `claude-code@2` classifies each rule from top-level `paths:` frontmatter, but
  weights all path-scoped rules with the configured aggregate activation rate;
  it does not observe which project files a real session opens.
- Skill support files, Markdown `@imports`, settings overrides, MCP servers,
  hooks, and auto-memory are not inferred. Add repository-authored support
  files explicitly when they matter to the budget.
- User-level/global engine instructions are outside the project root and are
  intentionally not scanned.
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

If a supported adapter includes or misses a file you did not expect, please
[open an adapter report](https://github.com/korovin-aa97/ctxfire/issues/new?template=adapter.yml).
The config and `ctxfire explain` output are useful; repository contents are not
needed and should not be attached.

The default package has no runtime dependencies; the optional tokenizer stack
and its licenses are recorded in the
[dependency review](https://github.com/korovin-aa97/ctxfire/blob/main/docs/DEPENDENCIES.md).

## Project status

`v0.2.0` adds the first content-aware Claude Code adapter in response to an
external evaluation while keeping `claude-code@1` unchanged. The analyzer was
also exercised against 18 unrelated public repositories;
the dated methodology and results live in
[`docs/VALIDATION.md`](https://github.com/korovin-aa97/ctxfire/blob/main/docs/VALIDATION.md).
Contributions are welcome—see
[`CONTRIBUTING.md`](https://github.com/korovin-aa97/ctxfire/blob/main/CONTRIBUTING.md)
and the extension guide.

Built from operating a mixed Claude/Codex production fleet. The analyzer is a
clean, generic extraction: no private fleet configuration or telemetry is
included.

MIT © 2026 Alexander Korovin.
