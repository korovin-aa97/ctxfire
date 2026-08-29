# ctxcost — Public Release Plan

Status: private draft. Target: a validated `v0.1.0` CLI release.

## Release thesis

Agent teams repeatedly load definitions, rules, skills, and memory. Individual
files may look small while the transitive graph multiplied by schedules becomes
expensive. `ctxcost` makes that graph visible and explains the estimate.

Canonical public line:

> Static cost analyzer for multi-agent context graphs: see what every agent
> loads and estimate tokens per fire and per day.

Portfolio signature:

> Built from operating a mixed Claude/Codex production fleet.

Never describe estimates as actual invoices or measured cache performance.

## Phase 0 — Revalidate category and name

- [ ] Directly search GitHub, PyPI, npm, HN, and current product sites for
      context cost, agent context graph, skill tax, usage, and package tools.
- [ ] Recheck adjacent categories: agent package managers, per-file linters,
      runtime usage meters, skill analytics, and context recommenders.
- [ ] Record dated facts and evidence URLs in `docs/COMPETITORS.md`.
- [ ] Recheck `ctxcost` on GitHub/PyPI/npm and decide whether a clearer public
      name is needed. Do not appropriate an active project name.
- [ ] Confirm the narrow wedge: transitive multi-agent context graph multiplied
      by schedule, with explainable cost assumptions.
- [ ] Select a license. MIT is the current compatibility-first recommendation.

## Phase 1 — Adapter specification

- [ ] Write `docs/ADAPTER_SPEC.md` defining when AGENTS.md, Claude Code rules,
      Codex configuration, skills, memory, and nested instructions are loaded.
- [ ] Give every adapter an engine name, supported version range, source links,
      precedence rules, roots, ignores, and uncertainty notes.
- [ ] Separate explicit context from conditional/on-demand content.
- [ ] Specify graph nodes, edges, shared-file deduplication, cycles, schedules,
      and per-fire versus per-day aggregation.
- [ ] Specify exact facts versus estimates in every report schema.
- [ ] Define tokenizer, model-price date, prompt caching, and subscription/API
      equivalence assumptions. Prices must be configurable and dated.

Exit gate: a user can explain why every counted file appears and reproduce the
same graph under the pinned adapter version.

## Phase 2 — Build the trustworthy scanner

- [ ] Discover tracked files from the git index with `.gitignore`, explicit root,
      nested-worktree, submodule, generated-file, symlink, and vendored handling.
- [ ] Implement `scan`, `explain`, `diff`, and `check`.
- [ ] Add human, JSON, and SARIF/GitHub annotation outputs with versioned schema.
- [ ] Add a dependency-free byte estimate plus optional accurate tokenizers.
- [ ] Support schedule inputs without becoming a scheduler.
- [ ] Make default output metadata-only; never print repository content unless
      explicitly requested.
- [ ] Add fixture repositories for every loading and discovery rule.
- [ ] Validate results manually on 10–20 unrelated public repositories and keep
      a dated, reproducible validation report.

Exit gate: adapters agree with documented engine behaviour on fixtures and real
repositories; unexplained files and silent duplicates are release blockers.

## Phase 3 — Repository and package readiness

- [ ] Finalize name, license, version, CLI commands, and report schema.
- [ ] README: problem, visual graph/demo, quickstart, exact-vs-estimated legend,
      supported adapters, `explain` example, CI budget example, limitations,
      comparison table, privacy, roadmap, and portfolio signature.
- [ ] Add `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`,
      `CODE_OF_CONDUCT.md`, templates, and real `good first issue`s.
- [ ] Add adapter reference, report schema, pricing assumptions, privacy notes,
      and an extension guide.
- [ ] Add CI for lint, types, unit/integration fixtures, packaging, and schema
      stability.
- [ ] Add PyPI OIDC trusted publishing and provenance.
- [ ] Add `llms.txt` and an optional agent skill for "explain and reduce context"
      only after the CLI contract is stable.
- [ ] Generate a 1280x640 social preview and a deterministic before/after demo.
- [ ] Add accurate GitHub topics such as `ai-agents`, `context-window`,
      `token-cost`, `claude-code`, `codex`, `static-analysis`, and `python`.

## Phase 4 — Pre-public rehearsal

- [ ] Build wheel and source distribution and install each in a clean environment.
- [ ] Run the README quickstart against two fixture repos and one external repo.
- [ ] Confirm JSON/SARIF schemas and exit codes are stable.
- [ ] Check that every report shows assumptions and no default output leaks file
      contents or secrets.
- [ ] Review dependency licenses and scan repository/history for private paths,
      internal agent names, schedules, costs, topology, and credentials.
- [ ] Re-run direct competitor/name checks on launch day.
- [ ] Prepare release notes, demo media, FAQ, Show HN maker comment, distinct
      community drafts, dev.to deep dive, and Habr version before the flip.

## Phase 5 — Owner-authorized public flip

Do not execute without an explicit owner instruction.

1. [ ] Configure pending PyPI trusted publisher for the release workflow.
2. [ ] Change GitHub visibility to public.
3. [ ] Confirm README, license, demo, description, topics, and clean history.
4. [ ] Enable secret scanning, push protection, vulnerability reporting, and
       code scanning.
5. [ ] Upload social preview and pin the repository.
6. [ ] Tag `v0.1.0`, publish through OIDC, and create human GitHub release notes.
7. [ ] Verify package provenance and clean `uvx ctxcost --help`/quickstart.
8. [ ] Submit to relevant Python, developer-tool, agent-tool, and static-analysis
       awesome lists. Add a Homebrew recipe only if real demand justifies it.

## Phase 6 — Launch content, days 2–14

- [ ] Show HN after at least one quiet day: link GitHub, show a real repository
      graph, disclose assumptions and limitations in the maker comment.
- [ ] Publish different posts on different days for r/ClaudeCode, r/codex,
      r/opensource, and cost/LLM engineering communities.
- [ ] Story article: the hidden daily cost of repeated agent instructions.
- [ ] Technical article: reconstructing a versioned multi-agent context graph.
- [ ] Case study: measurable reduction from one public repository, with explicit
      methodology rather than anonymous unsupported percentages.
- [ ] Habr adaptation and Console.dev submission where appropriate.
- [ ] Do not cross-post identical text, buy stars, or request votes.

## Phase 7 — Post-launch operation

- [ ] Respond to issues within 24 hours during the first two weeks.
- [ ] Track installs, stars, forks, external CI references, and voluntary adopter
      notes without telemetry.
- [ ] Keep adapter versions current and publish loading-semantics changes clearly.
- [ ] Add new engines only with fixtures and maintainable semantics.
- [ ] After 30 days, continue active investment only if at least three external
      users repeatedly run it or keep it in CI; otherwise maintain the core.

## Actions reserved for the owner

Visibility change, PyPI account/trusted-publisher confirmation, public release
authorization, profile pinning/social preview if manual, and all posts or
submissions from personal external accounts.
