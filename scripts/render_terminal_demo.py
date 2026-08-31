#!/usr/bin/env python3
"""Generate the deterministic ctxfire launch cast and GIF."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess  # nosec B404
import tempfile
from pathlib import Path

WIDTH = 128
HEIGHT = 24
CAST_DURATION_SECONDS = 16.0
EXPECTED_DELTA = "implementer: -1104 estimated tokens/day"
SECRET_PATTERNS = (
    re.compile(r"\bgh[opsu]_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/assets"),
        help="directory for ctxfire-demo.cast and ctxfire-demo.gif",
    )
    parser.add_argument(
        "--ctxfire",
        help="ctxfire executable; defaults to the first executable on PATH",
    )
    parser.add_argument("--skip-gif", action="store_true", help="only write the asciicast")
    return parser


def _resolve_executable(value: str | None, name: str) -> str:
    candidate = value or shutil.which(name)
    if candidate is None:
        raise RuntimeError(f"{name} is required but was not found on PATH")
    resolved = Path(candidate).expanduser().resolve()
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise RuntimeError(f"not an executable file: {resolved}")
    return str(resolved)


def _run(command: list[str], root: Path) -> str:
    result = subprocess.run(  # nosec B603
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed with exit {result.returncode}: {command[0]}\n{result.stderr}"
        )
    return result.stdout


def _color(code: str, text: str) -> str:
    return f"\x1b[{code}m{text}\x1b[0m"


def _cast_events(explain: str, difference: str) -> list[list[float | str]]:
    clear = "\x1b[2J\x1b[H"
    return [
        [
            0.0,
            "o",
            clear + _color("1;38;5;208", "ctxfire: explain the static context graph") + "\r\n\r\n",
        ],
        [
            1.0,
            "o",
            _color(
                "1;37",
                "$ ctxfire explain --config examples/ctxfire-self.toml "
                "--agent implementer --file AGENTS.md",
            )
            + "\r\n",
        ],
        [1.8, "o", explain.replace("\n", "\r\n")],
        [5.2, "o", clear],
        [5.4, "o", _color("1;38;5;208", "ctxfire: compare two graph snapshots") + "\r\n\r\n"],
        [
            6.2,
            "o",
            _color(
                "1;37",
                "$ ctxfire scan --config examples/demo/before.toml "
                "--format json --output before.json",
            )
            + "\r\n",
        ],
        [7.2, "o", _color("1;32", "[ok] baseline graph captured") + "\r\n"],
        [
            8.0,
            "o",
            _color(
                "1;37",
                "$ ctxfire scan --config examples/demo/after.toml "
                "--format json --output after.json",
            )
            + "\r\n",
        ],
        [9.0, "o", _color("1;32", "[ok] changed graph captured") + "\r\n\r\n"],
        [9.8, "o", _color("1;37", "$ ctxfire diff before.json after.json") + "\r\n"],
        [10.6, "o", difference.replace("\n", "\r\n")],
        [
            14.0,
            "o",
            "\r\n" + _color("38;5;110", "Exact bytes. Explicit assumptions. Local only.") + "\r\n",
        ],
        [16.0, "o", _color("2", "github.com/korovin-aa97/ctxfire") + "\r\n"],
    ]


def _write_cast(path: Path, events: list[list[float | str]]) -> None:
    header = {
        "version": 2,
        "width": WIDTH,
        "height": HEIGHT,
        "env": {"TERM": "xterm-256color"},
        "idle_time_limit": 2.0,
        "title": "ctxfire deterministic context-graph demo",
    }
    lines = [json.dumps(header, ensure_ascii=False, separators=(",", ":"))]
    lines.extend(json.dumps(event, ensure_ascii=False, separators=(",", ":")) for event in events)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _assert_private_data_absent(payload: str, root: Path) -> None:
    forbidden = {str(root), str(Path.home())}
    for value in forbidden:
        if value and value in payload:
            raise RuntimeError(f"cast contains a forbidden host path: {value}")
    for pattern in SECRET_PATTERNS:
        if pattern.search(payload):
            raise RuntimeError(f"cast matches forbidden secret pattern: {pattern.pattern}")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    output_dir = args.output_dir
    if not output_dir.is_absolute():
        output_dir = root / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    ctxfire = _resolve_executable(args.ctxfire, "ctxfire")

    with tempfile.TemporaryDirectory(prefix="ctxfire-recording-") as temporary:
        temp = Path(temporary)
        explain = _run(
            [
                ctxfire,
                "explain",
                "--config",
                "examples/ctxfire-self.toml",
                "--agent",
                "implementer",
                "--file",
                "AGENTS.md",
            ],
            root,
        )
        _run(
            [
                ctxfire,
                "scan",
                "--config",
                "examples/demo/before.toml",
                "--format",
                "json",
                "--output",
                str(temp / "before.json"),
            ],
            root,
        )
        _run(
            [
                ctxfire,
                "scan",
                "--config",
                "examples/demo/after.toml",
                "--format",
                "json",
                "--output",
                str(temp / "after.json"),
            ],
            root,
        )
        difference = _run(
            [ctxfire, "diff", str(temp / "before.json"), str(temp / "after.json")], root
        )

    if EXPECTED_DELTA not in difference:
        raise RuntimeError(f"demo output no longer contains expected delta: {EXPECTED_DELTA}")
    events = _cast_events(explain, difference)
    cast_path = output_dir / "ctxfire-demo.cast"
    _write_cast(cast_path, events)
    cast_payload = cast_path.read_text(encoding="utf-8")
    _assert_private_data_absent(cast_payload, root)

    gif_path = output_dir / "ctxfire-demo.gif"
    if not args.skip_gif:
        agg = _resolve_executable(None, "agg")
        subprocess.run(  # nosec B603
            [
                agg,
                "--quiet",
                "--theme",
                "github-dark",
                "--font-size",
                "16",
                "--idle-time-limit",
                "2",
                "--fps-cap",
                "20",
                "--last-frame-duration",
                "3",
                "--cols",
                str(WIDTH),
                "--rows",
                str(HEIGHT),
                str(cast_path),
                str(gif_path),
            ],
            cwd=root,
            check=True,
        )

    print(
        f"wrote {cast_path.relative_to(root)} ({CAST_DURATION_SECONDS:.1f}s, "
        f"{WIDTH}x{HEIGHT} cells)"
    )
    if not args.skip_gif:
        print(f"wrote {gif_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
