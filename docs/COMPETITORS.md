# Category and name check

Checked directly on 2026-08-29. This is positioning research, not a claim that
the list is exhaustive.

## Name

- GitHub's API returned two unrelated exact-name repositories. Most importantly,
  `saksham10arora-dotcom/ctxcost` was created and pushed on 2026-08-25 with the
  description “How much of your agent's context window does this repo eat? Token
  cost analyzer.” It is active, MIT-licensed, and directly overlaps the short
  name/category: https://github.com/saksham10arora-dotcom/ctxcost.
- `Pilotless-Labs/ctxcost` was created 2026-06-25 but has no default branch or
  description: https://github.com/Pilotless-Labs/ctxcost.
- PyPI's exact `ctxcost` project endpoint returned 404 before release:
  https://pypi.org/project/ctxcost/
- npm's exact package endpoint returned 404 before release:
  https://www.npmjs.com/package/ctxcost

The very similar **ContextCost** package (`contextcost`) launched in August 2026
and audits the token size/waste of a flat repository, then verifies proposed
ignore changes: https://pypi.org/project/contextcost/. This creates discoverability
confusion in addition to the direct GitHub collision.

Conclusion: `ctxcost` was not an acceptable public brand despite the free
package-registry slot. The project was renamed to **ctxfire** before publication.
Final direct checks on 2026-08-29 found zero exact-name GitHub repositories and
404 responses for `ctxfire` from both PyPI and npm. Hacker News title search had
no exact or relevant `ctxfire` product result. The name describes the project's
specific planning unit—context per agent fire and per day—without claiming
runtime measurement.

## Adjacent tools

| Project | Primary job | Difference from `ctxfire` |
|---|---|---|
| ContextCost | measure/reduce repository files | flat repository walk; no per-agent loading graph/schedule |
| Context Analyzer | runtime context-window forensics | observes sessions/hooks; `ctxfire` is a local static loading model |
| Repomix | pack repositories for LLM input | creates context bundles; `ctxfire` does not package content |
| Trazum | local prompt/usage-log cost analysis | runtime prompts/logs rather than declared context-loading graph |

Primary project pages checked:

- https://github.com/CAOShurong/contextcost
- https://github.com/manavgup/context-analyzer
- https://github.com/yamadashy/repomix
- https://github.com/Davmunrey/Trazum

## Wedge retained

The defensible product unit is:

```text
agent → versioned adapter rule → context edge → activation assumption → fires/day
```

No claim is made that `ctxfire` measures actual prompt construction, cache hits,
subscription charges, or the value/waste of repository files.
