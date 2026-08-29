"""Estimate the daily context surface of a multi-agent repository."""

from __future__ import annotations

import argparse
import json
import math
import tomllib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FileFact:
    path: str
    bytes: int


@dataclass(frozen=True)
class AgentReport:
    name: str
    engine: str
    fires_per_day: float
    files: tuple[FileFact, ...]
    exact_bytes_per_fire: int
    estimated_tokens_per_fire: int
    estimated_tokens_per_day: int


def _files_for_pattern(root: Path, pattern: str) -> set[Path]:
    if not any(character in pattern for character in "*?["):
        candidate = root / pattern
        return {candidate} if candidate.is_file() else set()
    return {candidate for candidate in root.glob(pattern) if candidate.is_file()}


def scan_agent(
    root: Path, raw: dict[str, Any], bytes_per_token: float
) -> AgentReport:
    discovered: set[Path] = set()
    for pattern in raw.get("include", []):
        discovered.update(_files_for_pattern(root, str(pattern)))
    facts = tuple(
        FileFact(path=path.relative_to(root).as_posix(), bytes=path.stat().st_size)
        for path in sorted(discovered)
    )
    total_bytes = sum(item.bytes for item in facts)
    tokens_per_fire = math.ceil(total_bytes / bytes_per_token)
    fires_per_day = float(raw.get("fires_per_day", 1))
    return AgentReport(
        name=str(raw["name"]),
        engine=str(raw.get("engine", "unknown")),
        fires_per_day=fires_per_day,
        files=facts,
        exact_bytes_per_fire=total_bytes,
        estimated_tokens_per_fire=tokens_per_fire,
        estimated_tokens_per_day=math.ceil(tokens_per_fire * fires_per_day),
    )


def load_config(path: Path) -> tuple[Path, float, list[dict[str, Any]]]:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    root_value = Path(str(project.get("root", ".")))
    root = root_value if root_value.is_absolute() else path.resolve().parent / root_value
    bytes_per_token = float(project.get("bytes_per_token", 4.0))
    if bytes_per_token <= 0:
        raise ValueError("bytes_per_token must be greater than zero")
    return root.resolve(), bytes_per_token, list(data.get("agents", []))


def render_text(reports: list[AgentReport], bytes_per_token: float) -> str:
    lines = [
        "ctxcost draft report",
        f"Assumption: 1 token ~= {bytes_per_token:g} bytes; estimates are not bills.",
        "",
    ]
    for report in reports:
        lines.extend(
            [
                f"{report.name} ({report.engine})",
                f"  files: {len(report.files)}",
                f"  exact bytes/fire: {report.exact_bytes_per_fire}",
                f"  estimated tokens/fire: {report.estimated_tokens_per_fire}",
                f"  estimated tokens/day: {report.estimated_tokens_per_day}",
            ]
        )
    lines.append("")
    lines.append(
        "TOTAL estimated tokens/day: "
        f"{sum(report.estimated_tokens_per_day for report in reports)}"
    )
    return "\n".join(lines)


def command_scan(args: argparse.Namespace) -> int:
    root, bytes_per_token, raw_agents = load_config(args.config)
    reports = [scan_agent(root, raw, bytes_per_token) for raw in raw_agents]
    if args.json:
        payload = {
            "root": str(root),
            "assumptions": {"bytes_per_token": bytes_per_token},
            "agents": [asdict(report) for report in reports],
            "estimated_tokens_per_day": sum(
                report.estimated_tokens_per_day for report in reports
            ),
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_text(reports, bytes_per_token))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ctxcost")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan = subparsers.add_parser("scan")
    scan.add_argument("--config", type=Path, default=Path("ctxcost.toml"))
    scan.add_argument("--json", action="store_true")
    scan.set_defaults(handler=command_scan)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))
