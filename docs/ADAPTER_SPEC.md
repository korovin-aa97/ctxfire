# Adapter specification

Adapter contract version: 1. Updated: 2026-08-29.

An adapter maps public engine loading rules to context graph edges. The adapter
name is versioned because engine behavior changes independently of `ctxfire`.
The report records the exact adapter string used.

## Common graph model

Each configured agent has:

- a unique `name`;
- an adapter and display `engine`;
- a repository-relative `working_directory`;
- a non-negative `fires_per_day` planning assumption;
- optional always-on `include`, conditional `conditional`, and `exclude` globs.

Each edge has one repository-relative file path, exact current byte size,
estimated tokens, activation class/rate, reason, and originating pattern. When
multiple rules select the same path, the strongest activation rate wins. This
deduplicates a file within one agent while intentionally retaining the cost
when the same file is loaded by different agents.

Cycles cannot occur in adapter v1 because the graph does not parse Markdown
imports. Referenced files must be configured explicitly. This conservative
boundary prevents accidental content parsing and false transitive claims.

## `explicit@1`

Only configuration is authoritative:

- `include`: always-on at activation rate `1.0`;
- `conditional`: weighted by `project.conditional_activation_rate`;
- `exclude`: removes matching paths after discovery.

Use this adapter for custom engines and as the reproducible escape hatch.

## `agents-md@1`

Adds `AGENTS.md` at each directory from project root through
`working_directory`, if present. Explicit rules still apply.

This models the repository-scoped instruction-chain convention without naming
a specific runtime. It does not scan instructions above project root.

## `codex@1`

For each directory from project root through `working_directory`, chooses the
first non-empty file in this precedence order:

1. `AGENTS.override.md`;
2. `AGENTS.md`;
3. configured `instruction_fallback_filenames`.

The default combined `instruction_max_bytes` is 32 KiB, matching the documented
Codex default. Reports retain each file's full `exact_bytes`, expose the portion
used for estimation as `counted_bytes`, and warn when the declared cap truncates
the chain. Configure the field if your Codex profile changes the default.

Codex scans `.agents/skills` in every ancestor directory from the working
directory to repository root. The adapter records each direct
`.agents/skills/*/SKILL.md` body as conditional because the full body loads only
when selected. The always-visible name/description catalog is not estimated in
metadata-only v0.1. Supporting files referenced by a skill are not inferred;
list them under `conditional` if they affect budgeting.

Primary semantics reference: OpenAI Codex documentation, “Custom instructions
with AGENTS.md” and “Agent Skills,” checked 2026-08-29:

- https://developers.openai.com/codex/guides/agents-md
- https://developers.openai.com/codex/skills

Uncertainty: user/global instructions, custom fallback names/max bytes not
declared in the agent table, platform policy, the skill description catalog,
runtime tool output, and dynamic skill references are outside the default
repository model. Codex can follow symlinked skill folders; `ctxfire` instead
skips symlinks as an explicit local-safety boundary and warns.

## `claude-code@1`

Adds `CLAUDE.md`, `CLAUDE.local.md`, and `.claude/CLAUDE.md` candidates from
project root through `working_directory` as always-on when present. Descendant
memory files below the working directory are conditional because Claude loads
them when it reads that subtree.

Project `.claude/rules/**/*.md` files are counted always-on by default. Official
Claude behavior distinguishes rules with `paths` frontmatter (conditional) from
rules without it (always-on), but v0.1 deliberately does not read content. The
conservative default avoids undercounting. Set `claude_rules_activation =
"conditional"` only when a single project-wide activation estimate is more
appropriate.

Project `.claude/skills/*/SKILL.md` bodies are conditional. Ancestor skill
directories are available at launch; descendant skill directories become
available when their subtree is read. In both cases, the full body loads only
when selected.

Primary semantics references: Anthropic Claude Code documentation, “Manage
Claude's memory” and “Extend Claude with skills,” checked 2026-08-29:

- https://docs.anthropic.com/en/docs/claude-code/memory
- https://docs.anthropic.com/en/docs/claude-code/skills

Uncertainty: imported memory files, stripped HTML comments, auto memory,
user/enterprise policy, setting-source exclusions, additional directories, and
content-derived rule activation are not inferred. Claude can follow symlinked
memory/skill paths in some environments; `ctxfire` skips them and warns.

## Discovery contract

At a Git top-level, the eligible universe comes from:

```text
git ls-files -z --cached --others --exclude-standard --deduplicate
```

This combines tracked files with untracked files that standard Git ignore
sources do not exclude. The behavior is documented by Git's `git-ls-files`
manual: https://git-scm.com/docs/git-ls-files.html (checked 2026-08-29).

The scanner never follows symlinks. Gitlinks/submodules and missing or other
non-regular paths are skipped with warnings. Nested repositories are not
recursed unless they are ordinary files in the selected root's index.

Known exact instruction-chain paths and non-glob explicit includes are probed
with file metadata even when Git ignores them. This matches engines that load an
ignored `CLAUDE.local.md` or `AGENTS.override.md` while avoiding a broad scan of
ignored build/cache trees. Such additions are counted and warned in discovery.
Ignored skill/rule trees selected only by a glob are not traversed in v1; keep
shared engine configuration tracked or add its exact entry points explicitly.

## Compatibility rule

Corrections that only improve warnings or documentation can retain an adapter
version. Any change that can add/remove context edges or change activation
semantics requires a new adapter version or an explicitly documented compatible
bug fix with regression fixtures.
