# Adapter specification

Adapter contract version: 2. Updated: 2026-08-31.

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
estimated tokens, activation class/rate, reason, and originating pattern.
Report schema 1.1 can split an edge into independently activated components—for
example, an always-visible skill catalog entry plus a conditional full body.
`counted_bytes` is the sum of modeled components and can exceed `exact_bytes`
when the same source contributes to more than one runtime surface. When
multiple rules select the same path, the strongest activation rate wins; the
largest counted surface breaks a tie, and an explicit include is authoritative
when both are otherwise equal. This deduplicates a file within one agent while
intentionally retaining the cost when the same file is loaded by different
agents.

Cycles cannot occur in the current adapters because the graph does not parse Markdown
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
when selected. The always-visible name/description catalog is not estimated by
`codex@1`. Supporting files referenced by a skill are not inferred;
list them under `conditional` if they affect budgeting.

Primary semantics reference: OpenAI Codex documentation, “Custom instructions
with AGENTS.md” and “Agent Skills,” checked 2026-08-30:

- https://learn.chatgpt.com/docs/agent-configuration/agents-md
- https://learn.chatgpt.com/docs/build-skills

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
Claude's memory” and “Extend Claude with skills,” checked 2026-08-30:

- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/slash-commands

Uncertainty: imported memory files, stripped HTML comments, auto memory,
user/enterprise policy, setting-source exclusions, additional directories, and
content-derived rule activation are not inferred. Claude can follow symlinked
memory/skill paths in some environments; `ctxfire` skips them and warns.

## `claude-code@2`

`claude-code@2` preserves the v1 project-memory chain and adds narrowly scoped,
local parsing for repository-authored Claude metadata:

- each `.claude/rules/**/*.md` file without top-level `paths` is always-on;
  one with `paths` is conditional and uses
  `project.conditional_activation_rate`;
- a project skill contributes an always-on catalog component containing its
  effective name plus `description`/`when_to_use` text, capped at 1,536
  characters, and a conditional full-file component;
- `disable-model-invocation: true` removes the catalog component but leaves the
  manually invocable body conditional;
- a main session includes the effective project subagent name/description
  catalog, not each definition body;
- setting `claude_subagent = "<name>"` selects a project subagent invocation or
  `--agent` session. Its definition and every resolvable `skills:` preload are
  always-on; missing or disabled preloads produce warnings instead of silently
  retaining stale config;
- skills below the starting working directory remain conditional until Claude
  discovers that subtree.

The selected subagent still receives the normal project memory/rules surface;
the adapter omits only the other subagent catalog entries from its isolated
context. Unlisted project skills remain available on demand.

The parser is intentionally dependency-free. It accepts the top-level scalar,
inline-list, indented-list, literal, and folded frontmatter shapes needed by
these fields. Malformed frontmatter is warned and treated conservatively; no
repository file is executed. The byte estimator reads only matched rule,
skill, and subagent Markdown locally for this adapter and records
`matched-file-content-local` in the report.

Primary semantics references: Anthropic Claude Code documentation, checked
2026-08-31:

- https://code.claude.com/docs/en/memory
- https://code.claude.com/docs/en/slash-commands
- https://code.claude.com/docs/en/sub-agents
- https://code.claude.com/docs/en/features-overview

Uncertainty: the configured activation rate summarizes a workload; ctxfire does
not observe which files a session opens or evaluate the rule globs against a
future task. Claude's global skill-listing budget, usage-based description
truncation, `skillOverrides`, settings-source exclusions, dynamic skill
commands/arguments, supporting files, Markdown imports, auto-memory, agent
memory, hooks, additional directories, user/enterprise configuration, runtime
wrappers, conversation/tool output, and prompt caching remain outside the
static repository model. Full skill/definition components use source-file bytes
as a reproducible upper bound because the runtime's exact rendered wrapper and
frontmatter stripping are not a public byte contract.

## Discovery contract

At a Git top-level, the eligible universe comes from:

```text
git ls-files -z --cached --others --exclude-standard --deduplicate
```

This combines tracked files with untracked files that standard Git ignore
sources do not exclude. The behavior is documented by Git's `git-ls-files`
manual: https://git-scm.com/docs/git-ls-files.html (checked 2026-08-30).

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
