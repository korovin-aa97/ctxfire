"""Exercise ctxfire invariants against already-cloned public repositories."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from ctxfire.config import load_config
from ctxfire.scanner import scan


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def validate(repo: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as temporary:
        config = Path(temporary) / "ctxfire.toml"
        root = repo.resolve().as_posix()
        config.write_text(
            f'''schema_version = "1"
[project]
name = "{repo.name}"
root = "{root}"
bytes_per_token = 4.0
tokenizer = "byte-estimate"
model = "unspecified"
price_date = "unspecified"
cache_assumption = "no-cache-credit"
conditional_activation_rate = 0.25

[[agents]]
name = "agents-md"
adapter = "agents-md@1"
fires_per_day = 1
include = ["README*", "LICENSE*", "COPYING*"]

[[agents]]
name = "codex"
adapter = "codex@1"
fires_per_day = 2
include = ["README*"]

[[agents]]
name = "claude"
adapter = "claude-code@1"
fires_per_day = 2
include = ["README*"]
''',
            encoding="utf-8",
        )
        loaded = load_config(config)
        first = scan(loaded)
        second = scan(loaded)
    payload = first.as_dict()
    serialized = json.dumps(payload, sort_keys=True)
    all_paths = [item["path"] for agent in payload["agents"] for item in agent["files"]]
    checks = {
        "deterministic": payload == second.as_dict(),
        "git_discovery": payload["discovery"]["method"] == "git-index+untracked-nonignored",
        "relative_paths": all(not Path(path).is_absolute() for path in all_paths),
        "no_root_leak": str(repo.resolve()) not in serialized,
        "all_edges_explained": all(
            item["reason"] and item["pattern"]
            for agent in payload["agents"]
            for item in agent["files"]
        ),
        "nonempty": bool(all_paths),
    }
    if not all(checks.values()):
        raise RuntimeError(f"validation failed for {repo}: {checks}")
    return {
        "repository": git(repo, "config", "--get", "remote.origin.url"),
        "commit": git(repo, "rev-parse", "--short=12", "HEAD"),
        "eligible_files": payload["discovery"]["eligible_regular_files"],
        "context_edges": len(all_paths),
        "warnings": len(payload["warnings"]),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repositories", nargs="+", type=Path)
    args = parser.parse_args()
    results = [validate(repo) for repo in args.repositories]
    print(json.dumps({"schema_version": "1", "results": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
