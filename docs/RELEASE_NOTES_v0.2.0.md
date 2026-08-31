# ctxfire v0.2.0

This release turns the first external evaluation into a narrower, more useful
Claude Code model. It fixes the three static-context gaps that materially
affected that evaluation while keeping runtime consumption outside scope.

## What changed

- New `claude-code@2` adapter parses each rule's top-level `paths:` frontmatter,
  so mixed scoped and unscoped rule sets no longer require one inaccurate
  project-wide override.
- Claude skills now expose separate always-visible catalog and conditional body
  components. `disable-model-invocation: true` hides the catalog as Claude does.
- Project subagents are discovered from `.claude/agents/**/*.md`.
  `claude_subagent = "<name>"` models the selected definition and automatically
  resolves full `skills:` preloads, warning on missing or disabled entries.
- Report schema 1.1 records independently activated components; `diff` still
  accepts existing schema 1.0 snapshots.
- Reports disclose that Claude v2 frontmatter/catalog parsing reads only matched
  Markdown locally. Nothing is printed, stored, uploaded, or executed.

`claude-code@1` is unchanged and remains available for reproducible
metadata-only scans.

## Deliberate boundaries

This remains a static analyzer for repository-authored context, not a runtime
meter. Conversation history, tool output, prompt caching, actual invocation
frequency, model-specific Claude tokenization, user/enterprise configuration,
auto-memory, settings overrides, hooks, dynamic skill rendering, Markdown
imports, and runtime MCP loading stay outside the estimate.

Path-scoped rules use the configured aggregate conditional activation rate;
ctxfire does not predict which files a future task will open. Skill catalog
components model source descriptions before Claude's global, usage-dependent
listing budget is applied.

## Validation

The release candidate includes a dependency-free parser and synthetic Claude v2
fixture covering mixed rules, catalogs, selected subagents, preloaded skills,
disabled skills, drift warnings, descendant discovery, schema validation, and
schema-1.0 diff compatibility. The full Python 3.11–3.13 CI matrix, lint, strict
typing, security checks, package checks, and clean wheel/sdist installs remain
release gates.

## Install

```bash
pipx install 'ctxfire==0.2.0'
ctxfire --version
```

For an existing config, opt in explicitly by changing the adapter to
`claude-code@2`. Remove the legacy project-wide `claude_rules_activation`
override; v2 derives rule activation per file. Add `claude_subagent` only for a
selected custom subagent run.

Byte sizes are exact filesystem facts. Catalog/body composition, tokens,
activation, schedules, caching, and API-equivalent prices remain explicit
planning estimates—not measured usage or vendor bills.
