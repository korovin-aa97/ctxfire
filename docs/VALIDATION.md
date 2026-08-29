# v0.1 validation report

Run date: 2026-08-30. Tool version: 0.1.1. Repositories: 18 unrelated public
GitHub repositories at pinned commits.

## Method

Each shallow clone was scanned twice with all three built-in engine families
(`agents-md@1`, `codex@1`, and `claude-code@1`) plus explicit root documentation
patterns. [`../scripts/validate_public_repos.py`](../scripts/validate_public_repos.py)
failed the run unless all of these held:

- both reports were byte-for-byte equal as Python data;
- discovery used the Git index plus non-ignored untracked files;
- every emitted path was relative;
- the absolute clone root did not appear anywhere in serialized JSON;
- every context edge had a non-empty reason and originating pattern;
- at least one real edge was found.

The corpus includes ordinary Python projects, Rust CLIs, multiple README
languages, tracked symlinks, root `AGENTS.md`/`CLAUDE.md`, Claude skills, and a
Codex skill. The 28 fixture tests plus four parameterized numeric cases
separately cover nested instruction chains, conditional weighting, excludes,
missing config, direct and ancestor symlink escape, malformed globs/snapshots,
schema errors, SARIF, diff, and budget/error exit codes.

## Results

| Repository | Commit | Eligible files | Edges | Warnings | Result |
|---|---:|---:|---:|---:|---|
| affaan-m/ECC | `656d4b574641` | 3,505 | 62 | 0 | pass |
| python-attrs/attrs | `764bf92a1c96` | 140 | 4 | 0 | pass |
| pypa/build | `8ec7ae2441c4` | 104 | 4 | 0 | pass |
| pallets/click | `36baa15ff831` | 166 | 4 | 0 | pass |
| sharkdp/fd | `cdea7f56331e` | 60 | 5 | 0 | pass |
| PyCQA/flake8 | `efe6750405be` | 215 | 4 | 0 | pass |
| encode/httpx | `b5addb64f016` | 125 | 4 | 0 | pass |
| python-jsonschema/jsonschema | `2d7d41ebd3b7` | 628 | 4 | 1 | pass |
| pypa/pipx | `3ca5d731cd4e` | 217 | 1 | 0 | pass |
| pytest-dev/pytest | `fdba12e17083` | 688 | 4 | 0 | pass |
| psf/requests | `5460f467b02e` | 128 | 4 | 2 | pass |
| Textualize/rich | `9d8f9a372cc5` | 553 | 55 | 0 | pass |
| BurntSushi/ripgrep | `3fce3b5bb023` | 236 | 5 | 1 | pass |
| encode/starlette | `d9ed5b0f98fd` | 148 | 4 | 0 | pass |
| tox-dev/tox | `c8c010ac68d4` | 317 | 4 | 0 | pass |
| fastapi/typer | `99eb220df7c6` | 774 | 4 | 0 | pass |
| vinta/awesome-python | `15b057c832a5` | 43 | 10 | 0 | pass |
| jaywcjlove/awesome-mac | `7186663920d1` | 45 | 13 | 0 | pass |

The four warnings were expected tracked symlinks, not unexplained files:
`json/tests/latest`, two Requests test-certificate links, and Ripgrep's
`HomebrewFormula`. Manual inspection confirmed that each was skipped and its
target was not read.

`awesome-python` exercised root `AGENTS.md`, root `CLAUDE.md`, and three Claude
skill entry points. `ECC` exercised the official repository `.agents/skills`
Codex layout across dozens of real skill entry points.
Rich's 55 edges are explainable: its many root-level translated `README*` files
were intentionally selected independently for three configured agents, plus its
license. This also caught and fixed an early glob bug where `*` crossed directory
boundaries; a regression test now pins root-relative glob behavior.

## Reproduce

Clone the repositories at the commits above, install the project, then run:

```bash
python scripts/validate_public_repos.py /path/to/clone1 /path/to/clone2
```

The validation script makes no network calls and does not retain generated
configuration. Repository contents are not included in this report.
