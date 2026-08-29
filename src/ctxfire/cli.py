"""Command-line interface for ctxfire."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, cast

from . import __version__
from .config import load_config
from .render import explain_text, json_text, sarif, scan_text
from .scanner import scan

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_BUDGET_EXCEEDED = 2


def _write(text: str, output: Path | None) -> None:
    if output is None:
        print(text, end="")
    else:
        output.write_text(text, encoding="utf-8")


def _report(args: argparse.Namespace):  # type: ignore[no-untyped-def]
    return scan(load_config(args.config))


def command_scan(args: argparse.Namespace) -> int:
    report = _report(args)
    if args.format == "json":
        rendered = json_text(report.as_dict())
    elif args.format == "sarif":
        findings = [
            {
                "rule_id": "ctxfire/context-surface",
                "title": "Agent context surface",
                "help": (
                    "Review the versioned adapter assumptions and use ctxfire explain "
                    "for attribution."
                ),
                "level": "note",
                "message": (
                    f"{agent.name}: estimated {agent.estimated_tokens_per_day} input tokens/day."
                ),
            }
            for agent in report.agents
        ]
        rendered = json_text(
            sarif(findings, report.tool["version"], report.as_dict()["assumptions"])
        )
    else:
        rendered = scan_text(report)
    _write(rendered, args.output)
    return EXIT_OK


def command_explain(args: argparse.Namespace) -> int:
    report = _report(args)
    if args.format == "json":
        agents = []
        for agent in report.as_dict()["agents"]:
            if args.agent and agent["name"] != args.agent:
                continue
            agent["files"] = [
                item for item in agent["files"] if not args.file or item["path"] == args.file
            ]
            agents.append(agent)
        rendered = json_text(
            {
                "schema_version": report.schema_version,
                "tool": report.tool,
                "assumptions": report.as_dict()["assumptions"],
                "agents": agents,
            }
        )
    else:
        rendered = explain_text(report, args.agent, args.file)
    _write(rendered, args.output)
    return EXIT_OK


def _load_snapshot(path: Path) -> dict[str, Any]:
    payload = cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))
    if payload.get("schema_version") != "1.0" or not isinstance(payload.get("agents"), list):
        raise ValueError(f"not a ctxfire report schema 1.0: {path}")
    return payload


def command_diff(args: argparse.Namespace) -> int:
    before = _load_snapshot(args.before)
    after = _load_snapshot(args.after)
    old = {agent["name"]: agent for agent in before["agents"]}
    new = {agent["name"]: agent for agent in after["agents"]}
    changes = []
    for name in sorted(old.keys() | new.keys()):
        old_tokens = int(old.get(name, {}).get("estimated_tokens_per_day", 0))
        new_tokens = int(new.get(name, {}).get("estimated_tokens_per_day", 0))
        old_paths = {item["path"] for item in old.get(name, {}).get("files", [])}
        new_paths = {item["path"] for item in new.get(name, {}).get("files", [])}
        old_files = {item["path"]: item for item in old.get(name, {}).get("files", [])}
        new_files = {item["path"]: item for item in new.get(name, {}).get("files", [])}
        changed_files = []
        for path in sorted(old_paths & new_paths):
            old_file = old_files[path]
            new_file = new_files[path]
            compared = ("exact_bytes", "counted_bytes", "estimated_tokens", "activation_rate")
            if any(old_file.get(field) != new_file.get(field) for field in compared):
                changed_files.append(
                    {
                        "path": path,
                        "before": {field: old_file.get(field) for field in compared},
                        "after": {field: new_file.get(field) for field in compared},
                    }
                )
        changes.append(
            {
                "agent": name,
                "fires_per_day_before": old.get(name, {}).get("fires_per_day", 0),
                "fires_per_day_after": new.get(name, {}).get("fires_per_day", 0),
                "estimated_tokens_per_day_before": old_tokens,
                "estimated_tokens_per_day_after": new_tokens,
                "estimated_tokens_per_day_delta": new_tokens - old_tokens,
                "added_files": sorted(new_paths - old_paths),
                "removed_files": sorted(old_paths - new_paths),
                "changed_files": changed_files,
            }
        )
    payload = {
        "schema_version": "1.0",
        "kind": "ctxfire-diff",
        "assumptions_before": before.get("assumptions"),
        "assumptions_after": after.get("assumptions"),
        "assumptions_changed": before.get("assumptions") != after.get("assumptions"),
        "changes": changes,
    }
    if args.format == "json":
        rendered = json_text(payload)
    else:
        lines = [
            "ctxfire diff",
            "Estimated token deltas use each snapshot's recorded assumptions.",
            "",
        ]
        if payload["assumptions_changed"]:
            lines.append("WARNING: estimation assumptions changed between snapshots.")
        for item in changes:
            lines.append(
                f"{item['agent']}: {item['estimated_tokens_per_day_delta']:+d} estimated tokens/day"
            )
            lines.extend(f"  + {path}" for path in item["added_files"])
            lines.extend(f"  - {path}" for path in item["removed_files"])
            for changed in item["changed_files"]:
                lines.append(
                    f"  ~ {changed['path']}: {changed['before']['exact_bytes']} -> "
                    f"{changed['after']['exact_bytes']} exact bytes; "
                    f"~{changed['before']['estimated_tokens']} -> "
                    f"~{changed['after']['estimated_tokens']} tokens"
                )
            if item["fires_per_day_before"] != item["fires_per_day_after"]:
                lines.append(
                    f"  schedule: {item['fires_per_day_before']:g} -> "
                    f"{item['fires_per_day_after']:g} fires/day"
                )
        rendered = "\n".join(lines) + "\n"
    _write(rendered, args.output)
    return EXIT_OK


def command_check(args: argparse.Namespace) -> int:
    report = _report(args)
    for option, value in (
        ("--max-tokens-per-fire", args.max_tokens_per_fire),
        ("--max-tokens-per-day", args.max_tokens_per_day),
        ("--max-usd-per-day", args.max_usd_per_day),
    ):
        if value is not None and value < 0:
            raise ValueError(f"{option} cannot be negative")
    findings: list[dict[str, str]] = []
    checks = [
        (
            "tokens-per-fire",
            args.max_tokens_per_fire,
            max((item.estimated_tokens_per_fire for item in report.agents), default=0),
        ),
        ("tokens-per-day", args.max_tokens_per_day, int(report.totals["estimated_tokens_per_day"])),
    ]
    for name, limit, actual in checks:
        if limit is not None and actual > limit:
            findings.append(
                {
                    "rule_id": f"ctxfire/{name}",
                    "title": f"Context budget exceeded: {name}",
                    "help": (
                        "Run ctxfire explain to attribute context files, then adjust "
                        "context or the explicit budget."
                    ),
                    "level": "error",
                    "message": f"Estimated {name} is {actual}, above configured CLI limit {limit}.",
                }
            )
    if args.max_usd_per_day is not None:
        cost = report.totals["estimated_usd_per_day"]
        if cost is None:
            raise ValueError("--max-usd-per-day requires usd_per_million_input_tokens in config")
        if float(cost) > args.max_usd_per_day:
            findings.append(
                {
                    "rule_id": "ctxfire/usd-per-day",
                    "title": "API-equivalent cost budget exceeded",
                    "help": (
                        "Review the dated price and cache assumptions before changing the budget."
                    ),
                    "level": "error",
                    "message": (
                        "Estimated API-equivalent input cost/day is "
                        f"${float(cost):.6f}, above ${args.max_usd_per_day:.6f}."
                    ),
                }
            )
    if args.format == "sarif":
        rendered = json_text(
            sarif(findings, report.tool["version"], report.as_dict()["assumptions"])
        )
    elif args.format == "json":
        rendered = json_text(
            {
                "schema_version": "1.0",
                "passed": not findings,
                "findings": findings,
                "report": report.as_dict(),
            }
        )
    else:
        assumptions = report.assumptions
        rendered = (
            ("ctxfire check: PASS\n" if not findings else "ctxfire check: FAIL\n")
            + (
                f"Estimates: {assumptions.tokenizer} ({assumptions.tokenizer_version}), "
                f"{assumptions.bytes_per_token:g} bytes/token, model {assumptions.model}, "
                f"price date {assumptions.price_date}, cache {assumptions.cache_assumption}.\n"
            )
            + "\n".join(f"  - {item['message']}" for item in findings)
            + ("\n" if findings else "")
        )
    _write(rendered, args.output)
    return EXIT_OK if not findings else EXIT_BUDGET_EXCEEDED


def _common(parser: argparse.ArgumentParser, formats: tuple[str, ...]) -> None:
    parser.add_argument("--config", type=Path, default=Path("ctxfire.toml"))
    parser.add_argument("--format", choices=formats, default=formats[0])
    parser.add_argument("--output", type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ctxfire",
        description="Explain and budget the static context graph of coding agents.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)
    scan_parser = subparsers.add_parser(
        "scan", help="build a context graph and estimate its daily cost"
    )
    _common(scan_parser, ("text", "json", "sarif"))
    scan_parser.set_defaults(handler=command_scan)
    explain_parser = subparsers.add_parser("explain", help="show why each file is included")
    _common(explain_parser, ("text", "json"))
    explain_parser.add_argument("--agent")
    explain_parser.add_argument("--file")
    explain_parser.set_defaults(handler=command_explain)
    diff_parser = subparsers.add_parser("diff", help="compare two JSON scan snapshots")
    diff_parser.add_argument("before", type=Path)
    diff_parser.add_argument("after", type=Path)
    diff_parser.add_argument("--format", choices=("text", "json"), default="text")
    diff_parser.add_argument("--output", type=Path)
    diff_parser.set_defaults(handler=command_diff)
    check_parser = subparsers.add_parser("check", help="enforce stable CI budgets")
    _common(check_parser, ("text", "json", "sarif"))
    check_parser.add_argument("--max-tokens-per-fire", type=int)
    check_parser.add_argument("--max-tokens-per-day", type=int)
    check_parser.add_argument("--max-usd-per-day", type=float)
    check_parser.set_defaults(handler=command_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
        return int(args.handler(args))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"ctxfire: error: {error}", file=sys.stderr)
        return EXIT_ERROR
