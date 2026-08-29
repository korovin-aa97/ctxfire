"""Context graph construction and cost estimation."""

from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import exact_probe_paths, excluded, inclusions, matches
from .config import Config
from .discovery import inventory
from .model import REPORT_SCHEMA_VERSION, AgentReport, ContextFile, ScanReport


@lru_cache(maxsize=16)
def _tiktoken_encoding(name: str) -> Any:
    import tiktoken

    try:
        return tiktoken.get_encoding(name)
    except ValueError as error:
        raise ValueError(f"unknown tiktoken encoding: {name}") from error


def _tokenize_file(path: Path, counted_bytes: int, tokenizer: str) -> int:
    encoding_name = tokenizer.partition(":")[2]
    with path.open("rb") as handle:
        content = handle.read(counted_bytes).decode("utf-8", errors="replace")
    return len(_tiktoken_encoding(encoding_name).encode(content, disallowed_special=()))


def scan(config: Config) -> ScanReport:
    """Scan only file metadata and return a deterministic report."""

    found = inventory(config.root)
    warnings = [f"skipped symlink: {path}" for path in found.skipped_symlinks]
    warnings.extend(
        f"skipped non-regular path (submodule or missing): {path}"
        for path in found.skipped_non_files
    )
    if found.method == "filesystem-fallback":
        warnings.append(
            "project root is not a Git top-level; used conservative filesystem fallback ignores"
        )

    reports: list[AgentReport] = []
    out_of_git_probes: set[str] = set()
    token_cache: dict[tuple[str, int], int] = {}
    for agent in config.agents:
        selected: dict[str, ContextFile] = {}
        agent_paths = set(found.paths)
        for path in exact_probe_paths(agent):
            candidate = config.root / path
            if candidate.is_symlink():
                warnings.append(f"skipped symlink: {path}")
            elif candidate.is_file():
                if path not in agent_paths:
                    out_of_git_probes.add(path)
                    warnings.append(
                        f"included exact engine/config path outside Git discovery: {path}"
                    )
                agent_paths.add(path)
        available = {path: (config.root / path).stat().st_size for path in agent_paths}
        rules = inclusions(agent, available)
        instruction_bytes_used = 0
        for rule in rules:
            matches_for_rule = [
                path
                for path in sorted(agent_paths)
                if matches(path, rule.pattern) and not excluded(path, agent.exclude)
            ]
            if (
                rule.reason == "explicit include"
                and not matches_for_rule
                and not any(character in rule.pattern for character in "*?[")
            ):
                warnings.append(f"{agent.name}: configured context file not found: {rule.pattern}")
            for path in matches_for_rule:
                exact_bytes = available[path]
                counted_bytes = exact_bytes
                if (
                    agent.instruction_max_bytes is not None
                    and rule.reason == "codex@1 instruction chain precedence"
                ):
                    remaining = max(agent.instruction_max_bytes - instruction_bytes_used, 0)
                    counted_bytes = min(exact_bytes, remaining)
                    instruction_bytes_used += counted_bytes
                    if counted_bytes < exact_bytes:
                        warnings.append(
                            f"{agent.name}: {path} truncated by declared "
                            f"instruction_max_bytes={agent.instruction_max_bytes}"
                        )
                activation_rate = (
                    1.0
                    if rule.activation == "always"
                    else config.assumptions.conditional_activation_rate
                )
                cache_key = (path, counted_bytes)
                if cache_key not in token_cache:
                    if config.assumptions.tokenizer == "byte-estimate":
                        token_cache[cache_key] = math.ceil(
                            counted_bytes / config.assumptions.bytes_per_token
                        )
                    else:
                        token_cache[cache_key] = _tokenize_file(
                            config.root / path,
                            counted_bytes,
                            config.assumptions.tokenizer,
                        )
                fact = ContextFile(
                    path=path,
                    exact_bytes=exact_bytes,
                    counted_bytes=counted_bytes,
                    estimated_tokens=token_cache[cache_key],
                    activation=rule.activation,
                    activation_rate=activation_rate,
                    reason=rule.reason,
                    pattern=rule.pattern,
                )
                previous = selected.get(path)
                if previous is None or fact.activation_rate > previous.activation_rate:
                    selected[path] = fact
        files = tuple(selected[path] for path in sorted(selected))
        tokens_fire = math.ceil(sum(item.estimated_tokens * item.activation_rate for item in files))
        tokens_day = math.ceil(tokens_fire * agent.fires_per_day)
        price = config.assumptions.usd_per_million_input_tokens
        usd_day = None if price is None else round(tokens_day * price / 1_000_000, 6)
        reports.append(
            AgentReport(
                name=agent.name,
                adapter=agent.adapter,
                engine=agent.engine,
                working_directory=agent.working_directory,
                fires_per_day=agent.fires_per_day,
                files=files,
                exact_candidate_bytes_per_fire=sum(item.exact_bytes for item in files),
                estimated_tokens_per_fire=tokens_fire,
                estimated_tokens_per_day=tokens_day,
                estimated_usd_per_day=usd_day,
            )
        )
    total_usd_values = [
        item.estimated_usd_per_day for item in reports if item.estimated_usd_per_day is not None
    ]
    totals: dict[str, int | float | None] = {
        "exact_candidate_bytes_across_agents_per_fire": sum(
            item.exact_candidate_bytes_per_fire for item in reports
        ),
        "estimated_tokens_per_day": sum(item.estimated_tokens_per_day for item in reports),
        "estimated_usd_per_day": None if not total_usd_values else round(sum(total_usd_values), 6),
    }
    return ScanReport(
        schema_version=REPORT_SCHEMA_VERSION,
        tool={"name": "ctxfire", "version": __version__},
        project={"name": config.project_name, "root": "."},
        discovery={
            "method": found.method,
            "eligible_regular_files": len(found.paths),
            "exact_probe_files_outside_git_discovery": len(out_of_git_probes),
            "content_access": (
                "metadata-only"
                if config.assumptions.tokenizer == "byte-estimate"
                else "matched-file-content-local"
            ),
            "symlink_policy": "skip-with-warning",
            "submodule_policy": "skip-gitlink-with-warning",
        },
        assumptions=config.assumptions,
        agents=tuple(reports),
        totals=totals,
        warnings=tuple(sorted(set(warnings))),
    )
