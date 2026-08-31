# FAQ

## Does ctxfire show my actual AI bill?

No. It creates an explainable static planning model. Runtime prompt construction,
conversation history, tool output, cache hits, output tokens, subscriptions, and
negotiated prices are outside scope.

## Does it upload my repository?

No. There is no telemetry or network code. Metadata-only adapters read file
sizes. `claude-code@2` reads matched rule/skill/subagent Markdown locally to
parse frontmatter and catalog fields, and the optional tiktoken backend reads
matched bytes locally for tokenization. Neither prints, stores, or uploads file
content; the report declares local content access.

## Why does the same file appear for several agents?

The graph deduplicates a file within one agent but preserves it across agents.
If five agents load the same root instructions, that repeated context is the
point of the analysis.

## Why is a Claude rule always-on or conditional?

`claude-code@2` parses each rule: no top-level `paths` means always-on; `paths`
means conditional under the configured activation rate. The legacy
metadata-only `claude-code@1` adapter retains its conservative project-wide
behavior for reproducibility.

## Why can counted bytes exceed the file size?

One source file can feed more than one runtime surface. A Claude skill, for
example, contributes its name/description catalog at startup and its full body
when invoked. Schema 1.1 exposes both components instead of pretending the file
has one activation class.

## Why was a symlink skipped?

Coding agents may follow some symlinked instruction/skill paths. ctxfire does
not, because following a repository symlink could cross the configured privacy
boundary. The report warns instead of silently undercounting.

## Why no built-in model price table?

Vendor prices and aliases age quickly, caching is runtime-specific, and API
prices are not subscription bills. Configure an exact price and date you have
verified; every report preserves those assumptions.

## Is ctxfire related to ContextCost or the older ctxcost repositories?

No. The private draft was renamed before publication after launch-day research
found an active overlapping `ctxcost`. ctxfire's unit is the per-agent loading
graph multiplied by a declared schedule, not a flat repository-waste score.
