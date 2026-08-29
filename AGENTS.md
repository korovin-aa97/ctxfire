# ctxfire — Agent Bootstrap

Last updated: 2026-08-29. Repository status: **v0.1.0 initial public release**.

Read this file first, followed by `README.md`, `ctxfire.example.toml`, the
source, and `docs/PUBLIC_RELEASE_PLAN.md`.

## Product in one sentence

`ctxfire` maps the context each versioned adapter attributes to a coding agent,
how often that agent fires, and the estimated token and API-equivalent cost per
fire and per day.

## Positioning

This is a static cost analyzer for multi-agent context graphs. It is not a live
token meter, agent package manager, skill recommender, generic context manager,
or exact subscription bill calculator.

The product's useful graph is:

`agent -> definition -> rules/skills/memory -> schedule -> estimated daily cost`

File paths and byte counts can be exact. Token counts, cache behaviour, prices,
and daily cost are estimates and must always expose their assumptions.

## Current state

- Version `0.1.0`; renamed from the colliding private draft name before launch.
- Versioned explicit, AGENTS.md, Codex, and Claude Code adapters.
- Git-index discovery plus narrow exact probes for ignored engine instructions.
- `scan`, `explain`, `diff`, and `check`; human, JSON 1.0, and SARIF 2.1.0.
- Dependency-free byte estimates and an opt-in local tiktoken backend.
- MIT license, community/security docs, CI, release workflow, fixtures, schema,
  demo, and a dated 18-repository validation report.

## Non-negotiable boundaries

- Never present estimates as actual vendor bills or measured prompt-cache hits.
- Reports must separate exact facts from estimates and include model,
  tokenizer, price date, cache assumption, and adapter version.
- Do not collect or upload repository contents. The OSS scanner is local-only
  and telemetry-free by default.
- Do not absorb package management or runtime orchestration into this tool.
- Keep adapters explicit and versioned because engine loading semantics change.
- Use git-index and ignore semantics so worktrees, caches, generated copies, and
  vendored trees do not silently inflate results.
- Keep the extraction clean-room: no internal hosts, agent names, schedules,
  budgets, customer data, or private fleet topology.

## Next work, in order

1. Keep adapter semantics aligned with their dated official sources.
2. Preserve report schema 1.0 compatibility through the 0.1 line.
3. Triage real user reports before expanding engine or tokenizer scope.
4. Treat runtime measurement, package management, and scheduling as out of scope.

## v0.1 definition of done

- Loading rules are documented and pinned per adapter version.
- Discovery agrees with each supported engine on representative fixtures.
- Exact bytes, estimated tokens, schedules, cache assumptions, and prices are
  distinguishable in both human and machine-readable reports.
- `explain` shows why every file is included; `diff` attributes cost changes;
  `check` provides stable CI thresholds.
- The scanner handles ignored files, nested worktrees, symlinks, missing files,
  cycles, shared dependencies, and generated content deterministically.
- Results are manually checked on 10–20 third-party repositories before launch.
- Clean installs, documentation, community files, security policy, changelog,
  packaging, release workflow, and public demo are ready.

## Working rules for future agents

- Use Python 3.11+ and type all public interfaces.
- Treat adapter semantics and report schemas as public APIs.
- Add a regression fixture for every loading rule or parser quirk.
- Avoid reading file contents when metadata is enough; never print sensitive
  contents in default reports.
- No hidden network calls or telemetry.
- Date and source every price or competitor claim.
- Before each release, repeat direct checks of GitHub, PyPI/npm, and competitor sites;
  young tools and bot-blocked sites are easy to miss in search indexes.

## Success criterion

Before announcement: correct scans on 10–20 external repositories. Within 30
days after launch: at least three external users run it repeatedly or keep its
CI integration. Use voluntary adopter notes or interviews, not embedded
telemetry.

## Release authority

Agents may prepare and rehearse everything. Repository visibility changes,
package publication, public releases, directory submissions, and public launch
posts require explicit owner authorization in the active session.
