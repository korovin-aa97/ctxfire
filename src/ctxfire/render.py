"""Human, JSON, and SARIF rendering."""

from __future__ import annotations

import json
from typing import Any

from .model import ScanReport


def json_text(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"


def scan_text(report: ScanReport) -> str:
    assumptions = report.assumptions
    lines = [
        f"ctxfire {report.tool['version']} — {report.project['name']}",
        (
            "Exact: filesystem byte sizes. Estimated: tokens, activation weighting, "
            "and API-equivalent cost."
        ),
        (
            f"Assumptions: {assumptions.tokenizer} ({assumptions.tokenizer_version}); "
            f"1 token ~= {assumptions.bytes_per_token:g} bytes; "
            f"conditional activation {assumptions.conditional_activation_rate:.0%}; "
            f"model {assumptions.model}; price date {assumptions.price_date}; "
            f"cache {assumptions.cache_assumption}."
        ),
        f"Content access: {report.discovery['content_access']}.",
        "",
    ]
    for agent in report.agents:
        cost = (
            "not configured"
            if agent.estimated_usd_per_day is None
            else f"${agent.estimated_usd_per_day:.6f}/day"
        )
        lines.extend(
            [
                f"{agent.name} [{agent.adapter}]",
                (
                    f"  context candidates: {len(agent.files)} files, "
                    f"{agent.exact_candidate_bytes_per_fire} exact bytes/fire"
                ),
                (
                    f"  estimate: {agent.estimated_tokens_per_fire} tokens/fire x "
                    f"{agent.fires_per_day:g}/day = "
                    f"{agent.estimated_tokens_per_day} tokens/day"
                ),
                f"  API-equivalent input cost: {cost}",
            ]
        )
    lines.extend(["", f"TOTAL estimated tokens/day: {report.totals['estimated_tokens_per_day']}"])
    if report.totals["estimated_usd_per_day"] is not None:
        lines.append(
            f"TOTAL API-equivalent input cost/day: ${report.totals['estimated_usd_per_day']:.6f}"
        )
    if report.warnings:
        lines.extend(["", "Warnings:"] + [f"  - {warning}" for warning in report.warnings])
    lines.append(
        "Estimates are planning aids, not measured usage, cache hits, subscription "
        "charges, or vendor bills."
    )
    return "\n".join(lines) + "\n"


def explain_text(report: ScanReport, agent_name: str | None, file_path: str | None) -> str:
    assumptions = report.assumptions
    lines = [
        "ctxfire explain",
        (
            "No file contents were read or printed."
            if report.discovery["content_access"] == "metadata-only"
            else (
                "Matched file content was read locally for adapter metadata and/or tokenization; "
                "it was not printed or uploaded."
            )
        ),
        "Byte sizes are exact; token figures are estimates.",
        (
            f"Assumptions: {assumptions.tokenizer} ({assumptions.tokenizer_version}), "
            f"{assumptions.bytes_per_token:g} bytes/token, "
            f"model {assumptions.model}, price date {assumptions.price_date}, "
            f"cache {assumptions.cache_assumption}."
        ),
        "",
    ]
    matched = 0
    for agent in report.agents:
        if agent_name and agent.name != agent_name:
            continue
        lines.append(f"{agent.name} [{agent.adapter}]")
        for item in agent.files:
            if file_path and item.path != file_path:
                continue
            matched += 1
            size = f"{item.exact_bytes} exact bytes"
            if item.counted_bytes != item.exact_bytes:
                detail = (
                    "after adapter cap"
                    if len(item.components) == 1 and item.components[0].kind == "whole-file"
                    else "across adapter components"
                )
                size += f", {item.counted_bytes} counted {detail}"
            lines.append(
                f"  {item.path}: {size}, ~{item.estimated_tokens} tokens, "
                f"{item.activation} at {item.activation_rate:.0%} — {item.reason} "
                f"({item.pattern})"
            )
            if len(item.components) > 1 or item.components[0].kind != "whole-file":
                lines.extend(
                    (
                        f"    [{component.kind}] {component.counted_bytes} counted bytes, "
                        f"~{component.estimated_tokens} tokens, {component.activation} at "
                        f"{component.activation_rate:.0%} — {component.reason}"
                    )
                    for component in item.components
                )
    if not matched:
        lines.append("No matching context edge.")
    return "\n".join(lines) + "\n"


def sarif(
    findings: list[dict[str, str]],
    tool_version: str,
    assumptions: dict[str, Any],
    config_uri: str = "ctxfire.toml",
) -> dict[str, Any]:
    rules: dict[str, dict[str, Any]] = {}
    results: list[dict[str, Any]] = []
    for finding in findings:
        rule_id = finding["rule_id"]
        rules[rule_id] = {
            "id": rule_id,
            "shortDescription": {"text": finding["title"]},
            "help": {"text": finding["help"]},
        }
        results.append(
            {
                "ruleId": rule_id,
                "level": finding["level"],
                "message": {"text": finding["message"]},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": config_uri, "uriBaseId": "%SRCROOT%"}
                        }
                    }
                ],
            }
        )
    return {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ctxfire",
                        "version": tool_version,
                        "informationUri": "https://github.com/korovin-aa97/ctxfire",
                        "rules": [rules[key] for key in sorted(rules)],
                    }
                },
                "properties": {"ctxfireAssumptions": assumptions},
                "results": results,
            }
        ],
    }
