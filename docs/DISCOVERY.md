# Discovery behavior

`ctxfire` needs a deterministic candidate universe before adapter patterns are
applied.

## Git repositories

The configured root must equal Git's top-level directory to use Git discovery.
The scanner asks Git for tracked files plus non-ignored untracked files. This
honors nested `.gitignore`, `.git/info/exclude`, and the user's configured global
ignore for untracked files. Tracked files remain eligible even when a later
ignore rule matches them, which is standard Git behavior.

Paths are NUL-delimited and decoded with surrogate escape, so whitespace and
unusual byte sequences do not become command injection or record separators.
No shell is involved.

After the Git universe is built, the active adapter probes known exact ancestor
instruction paths and exact (non-glob) configured paths. An ignored local
instruction can therefore be counted without admitting all ignored files. The
report's `exact_probe_files_outside_git_discovery` count and warning make this
exception visible.

## Non-Git fallback

The fallback walks regular files and reports a warning. It skips version-control
metadata and common generated trees: `.git`, `.hg`, `.svn`, `node_modules`,
virtual environments, `dist`, `build`, and `__pycache__`. It does not promise
full `.gitignore` emulation. For reproducible CI results, use a Git top-level.

## Boundaries

- Symlinks: skipped and warned; targets are never opened.
- Submodules/gitlinks: skipped and warned; scan them as separate roots.
- Nested repositories/worktrees: not recursively crossed by the outer root.
- Missing tracked path: skipped and warned.
- Generated/vendored tracked files: eligible unless an agent `exclude` removes
  them; `ctxfire` does not guess whether tracked content is valuable.
- Ignored rule/skill trees: not globbed. Track shared engine configuration or
  add exact entry points; known exact instruction-chain files are probed.
- Explicit patterns: must be relative and cannot contain `..`.

These boundaries favor explainability and local safety over maximal discovery.
