# FAQ

## Does ctxfire show my actual AI bill?

No. It creates an explainable static planning model. Runtime prompt construction,
conversation history, tool output, cache hits, output tokens, subscriptions, and
negotiated prices are outside scope.

## Does it upload my repository?

No. There is no telemetry or network code. The default estimator reads file
metadata only. The optional tiktoken backend reads matched bytes locally in
memory and does not print, store, or upload content.

## Why does the same file appear for several agents?

The graph deduplicates a file within one agent but preserves it across agents.
If five agents load the same root instructions, that repeated context is the
point of the analysis.

## Why are Claude rules counted as always-on?

Claude distinguishes unconditional rules from rules with path frontmatter.
v0.1 is metadata-only by default and does not parse that frontmatter, so the
adapter uses a conservative upper bound. Projects can explicitly choose a
conditional aggregate assumption.

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
