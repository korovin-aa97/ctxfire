"""Context graph construction and cost estimation."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from . import __version__
from .adapters import Inclusion, exact_probe_paths, excluded, inclusions, matches
from .config import AgentConfig, Config
from .discovery import inventory, path_kind
from .frontmatter import Frontmatter, first_markdown_paragraph, read_frontmatter, yaml_boolean
from .model import (
    REPORT_SCHEMA_VERSION,
    AgentReport,
    ContextComponent,
    ContextFile,
    ScanReport,
)


@lru_cache(maxsize=16)
def _tiktoken_encoding(name: str) -> Any:
    import tiktoken

    try:
        return tiktoken.get_encoding(name)
    except ValueError as error:
        raise ValueError(f"unknown tiktoken encoding: {name}") from error


def _tokenize_bytes(content: bytes, tokenizer: str) -> int:
    encoding_name = tokenizer.partition(":")[2]
    text = content.decode("utf-8", errors="replace")
    return len(_tiktoken_encoding(encoding_name).encode(text, disallowed_special=()))


@dataclass(frozen=True)
class _ClaudeV2Metadata:
    frontmatter: dict[str, Frontmatter]
    active_agent_paths: frozenset[str]
    selected_agent_path: str | None
    preloaded_skill_paths: frozenset[str]
    warnings: tuple[str, ...]


def _scope_depth(path: str, marker: str) -> int:
    prefix = path.partition(marker)[0].rstrip("/")
    return 0 if not prefix else len(prefix.split("/"))


def _paths_for_reason(
    paths: set[str], rules: tuple[Inclusion, ...], reason_fragment: str
) -> set[str]:
    patterns = [rule.pattern for rule in rules if reason_fragment in rule.reason]
    return {path for path in paths if any(matches(path, pattern) for pattern in patterns)}


def _choose_named_paths(
    candidates: set[str],
    frontmatter: dict[str, Frontmatter],
    *,
    marker: str,
    default_name: bool,
) -> tuple[dict[str, str], list[str]]:
    grouped: dict[str, list[str]] = {}
    warnings: list[str] = []
    for path in sorted(candidates):
        document = frontmatter[path]
        name = document.scalar("name")
        if not name and default_name:
            name = Path(path).parent.name
        if not name:
            warnings.append(f"{path}: missing required frontmatter name; skipped")
            continue
        grouped.setdefault(name, []).append(path)

    chosen: dict[str, str] = {}
    for name, paths in sorted(grouped.items()):
        ranked = sorted(paths, key=lambda item: (_scope_depth(item, marker), item), reverse=True)
        chosen[name] = ranked[0]
        top_depth = _scope_depth(ranked[0], marker)
        same_scope = [item for item in ranked if _scope_depth(item, marker) == top_depth]
        if len(same_scope) > 1:
            warnings.append(
                f"duplicate {name!r} definitions at one Claude project scope; "
                f"selected {ranked[0]} deterministically but Claude filesystem order is unspecified"
            )
    return chosen, warnings


def _claude_v2_metadata(
    root: Path,
    agent: AgentConfig,
    agent_paths: set[str],
    rules: tuple[Inclusion, ...],
) -> _ClaudeV2Metadata:
    agent_candidates = _paths_for_reason(agent_paths, rules, "project subagent")
    project_skill_candidates = _paths_for_reason(agent_paths, rules, "project skill")
    skill_candidates = set(project_skill_candidates)
    skill_candidates.update(_paths_for_reason(agent_paths, rules, "descendant skill"))
    rule_candidates = _paths_for_reason(agent_paths, rules, "project rule")
    parsed_paths = agent_candidates | skill_candidates | rule_candidates
    documents = {path: read_frontmatter(root / path) for path in sorted(parsed_paths)}
    warnings = [
        f"{path}: {document.warning}"
        for path, document in documents.items()
        if document.warning is not None
    ]

    agents_by_name, name_warnings = _choose_named_paths(
        agent_candidates,
        documents,
        marker=".claude/agents/",
        default_name=False,
    )
    warnings.extend(name_warnings)
    skills_by_name, skill_warnings = _choose_named_paths(
        project_skill_candidates,
        documents,
        marker=".claude/skills/",
        default_name=True,
    )
    warnings.extend(skill_warnings)

    selected_agent_path = None
    preloaded: set[str] = set()
    if agent.claude_subagent is not None:
        selected_agent_path = agents_by_name.get(agent.claude_subagent)
        if selected_agent_path is None:
            warnings.append(
                f"{agent.name}: Claude subagent {agent.claude_subagent!r} was not found"
            )
        else:
            for skill_name in documents[selected_agent_path].items("skills") or ():
                skill_path = skills_by_name.get(skill_name)
                if skill_path is None:
                    warnings.append(
                        f"{agent.name}: preloaded Claude skill {skill_name!r} was not found"
                    )
                    continue
                if yaml_boolean(
                    documents[skill_path].scalar("disable-model-invocation"), default=False
                ):
                    warnings.append(
                        f"{agent.name}: Claude skill {skill_name!r} disables model invocation "
                        "and cannot be preloaded"
                    )
                    continue
                preloaded.add(skill_path)

    return _ClaudeV2Metadata(
        frontmatter=documents,
        active_agent_paths=frozenset(agents_by_name.values()),
        selected_agent_path=selected_agent_path,
        preloaded_skill_paths=frozenset(preloaded),
        warnings=tuple(warnings),
    )


def _estimated_tokens(content: bytes, counted_bytes: int, config: Config) -> int:
    if config.assumptions.tokenizer == "byte-estimate":
        return math.ceil(counted_bytes / config.assumptions.bytes_per_token)
    return _tokenize_bytes(content[:counted_bytes], config.assumptions.tokenizer)


def _component(
    *,
    kind: str,
    content: bytes,
    activation: str,
    activation_rate: float,
    reason: str,
    config: Config,
    counted_bytes: int | None = None,
) -> ContextComponent:
    size = len(content) if counted_bytes is None else counted_bytes
    return ContextComponent(
        kind=kind,
        counted_bytes=size,
        estimated_tokens=_estimated_tokens(content, size, config),
        activation=activation,
        activation_rate=activation_rate,
        reason=reason,
    )


def _catalog_content(document: Frontmatter, default_name: str) -> bytes:
    name = document.scalar("name") or default_name
    description = document.scalar("description") or (
        "" if document.warning is not None else first_markdown_paragraph(document.body)
    )
    when_to_use = document.scalar("when_to_use") or ""
    combined = " ".join(part for part in (description, when_to_use) if part).strip()[:1536]
    return f"{name}: {combined}".encode() if combined else name.encode()


def _context_file(
    *,
    path: str,
    exact_bytes: int,
    pattern: str,
    components: tuple[ContextComponent, ...],
    reason: str,
) -> ContextFile:
    estimated_tokens = sum(component.estimated_tokens for component in components)
    weighted_tokens = sum(
        component.estimated_tokens * component.activation_rate for component in components
    )
    activation_rate = (
        max((component.activation_rate for component in components), default=0.0)
        if estimated_tokens == 0
        else weighted_tokens / estimated_tokens
    )
    activations = {(component.activation, component.activation_rate) for component in components}
    activation = next(iter(activations))[0] if len(activations) == 1 else "mixed"
    return ContextFile(
        path=path,
        exact_bytes=exact_bytes,
        counted_bytes=sum(component.counted_bytes for component in components),
        estimated_tokens=estimated_tokens,
        activation=activation,
        activation_rate=activation_rate,
        reason=reason,
        pattern=pattern,
        components=components,
    )


def _claude_v2_components(
    *,
    path: str,
    content: bytes,
    rule: Inclusion,
    agent: AgentConfig,
    metadata: _ClaudeV2Metadata,
    config: Config,
) -> tuple[ContextComponent, ...] | None:
    document = metadata.frontmatter.get(path)
    conditional_rate = config.assumptions.conditional_activation_rate
    if "project rule" in rule.reason:
        path_patterns = None if document is None else document.items("paths")
        conditional = path_patterns is not None
        activation = "conditional" if conditional else "always"
        rate = conditional_rate if conditional else 1.0
        detail = (
            "paths frontmatter present; loads only for matching files"
            if conditional
            else "no paths frontmatter; loads at session start"
        )
        return (
            _component(
                kind="rule-body",
                content=content,
                activation=activation,
                activation_rate=rate,
                reason=f"claude-code@2 project rule: {detail}",
                config=config,
            ),
        )

    if "skill" in rule.reason:
        if document is None:
            return None
        if path in metadata.preloaded_skill_paths:
            return (
                _component(
                    kind="preloaded-skill",
                    content=content,
                    activation="always",
                    activation_rate=1.0,
                    reason="claude-code@2 skill preloaded by selected subagent skills frontmatter",
                    config=config,
                ),
            )
        components: list[ContextComponent] = []
        if not yaml_boolean(document.scalar("disable-model-invocation"), default=False):
            catalog = _catalog_content(document, Path(path).parent.name)
            catalog_is_conditional = "descendant skill" in rule.reason
            components.append(
                _component(
                    kind="skill-catalog",
                    content=catalog,
                    activation="conditional" if catalog_is_conditional else "always",
                    activation_rate=conditional_rate if catalog_is_conditional else 1.0,
                    reason=(
                        "claude-code@2 skill name/description catalog; "
                        + (
                            "available after descendant subtree discovery"
                            if catalog_is_conditional
                            else "model-visible at session start"
                        )
                        + "; runtime wrapper bytes excluded"
                    ),
                    config=config,
                )
            )
        components.append(
            _component(
                kind="skill-body",
                content=content,
                activation="conditional",
                activation_rate=conditional_rate,
                reason="claude-code@2 full skill content; loaded when invoked",
                config=config,
            )
        )
        return tuple(components)

    if "project subagent" in rule.reason:
        if path not in metadata.active_agent_paths or document is None:
            return None
        if agent.claude_subagent is not None:
            if path != metadata.selected_agent_path:
                return None
            return (
                _component(
                    kind="subagent-definition",
                    content=content,
                    activation="always",
                    activation_rate=1.0,
                    reason="claude-code@2 selected subagent definition and system prompt",
                    config=config,
                ),
            )
        catalog = _catalog_content(document, Path(path).stem)
        return (
            _component(
                kind="subagent-catalog",
                content=catalog,
                activation="always",
                activation_rate=1.0,
                reason=(
                    "claude-code@2 model-visible project subagent name/description catalog; "
                    "definition body stays in isolated subagent context"
                ),
                config=config,
            ),
        )
    return None


def scan(config: Config) -> ScanReport:
    """Build a deterministic report under the configured adapter/privacy contract."""

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
    for agent in config.agents:
        selected: dict[str, ContextFile] = {}
        agent_paths = set(found.paths)
        for path in exact_probe_paths(agent):
            kind = path_kind(config.root, path)
            if kind == "symlink":
                warnings.append(f"skipped symlink: {path}")
            elif kind == "file":
                if path not in agent_paths:
                    out_of_git_probes.add(path)
                    warnings.append(
                        f"included exact engine/config path outside Git discovery: {path}"
                    )
                agent_paths.add(path)
        available = {path: (config.root / path).stat().st_size for path in agent_paths}
        rules = inclusions(agent, available)
        claude_metadata = (
            _claude_v2_metadata(config.root, agent, agent_paths, rules)
            if agent.adapter == "claude-code@2"
            else None
        )
        if claude_metadata is not None:
            warnings.extend(claude_metadata.warnings)
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
                needs_content = config.assumptions.tokenizer != "byte-estimate" or (
                    claude_metadata is not None
                    and any(
                        fragment in rule.reason
                        for fragment in ("project rule", "skill", "project subagent")
                    )
                )
                content = (config.root / path).read_bytes() if needs_content else b""
                special_components = (
                    _claude_v2_components(
                        path=path,
                        content=content,
                        rule=rule,
                        agent=agent,
                        metadata=claude_metadata,
                        config=config,
                    )
                    if claude_metadata is not None
                    else None
                )
                if claude_metadata is not None and any(
                    fragment in rule.reason
                    for fragment in ("project rule", "skill", "project subagent")
                ):
                    if special_components is None:
                        continue
                    components = special_components
                    fact_reason = (
                        "claude-code@2 mixed catalog/body activation"
                        if len(special_components) > 1
                        else special_components[0].reason
                    )
                else:
                    components = (
                        _component(
                            kind="whole-file",
                            content=content,
                            counted_bytes=counted_bytes,
                            activation=rule.activation,
                            activation_rate=activation_rate,
                            reason=rule.reason,
                            config=config,
                        ),
                    )
                    fact_reason = rule.reason
                fact = _context_file(
                    path=path,
                    exact_bytes=exact_bytes,
                    pattern=rule.pattern,
                    components=components,
                    reason=fact_reason,
                )
                previous = selected.get(path)
                if previous is None or (
                    fact.activation_rate,
                    fact.counted_bytes,
                    fact.reason == "explicit include",
                ) > (
                    previous.activation_rate,
                    previous.counted_bytes,
                    previous.reason == "explicit include",
                ):
                    selected[path] = fact
        files = tuple(selected[path] for path in sorted(selected))
        tokens_fire = math.ceil(
            sum(
                component.estimated_tokens * component.activation_rate
                for item in files
                for component in item.components
            )
        )
        daily_estimate = tokens_fire * agent.fires_per_day
        if not math.isfinite(daily_estimate):
            raise ValueError(f"computed daily token estimate is not finite for {agent.name}")
        tokens_day = math.ceil(daily_estimate)
        price = config.assumptions.usd_per_million_input_tokens
        cost_estimate = None if price is None else tokens_day * price / 1_000_000
        if cost_estimate is not None and not math.isfinite(cost_estimate):
            raise ValueError(f"computed daily cost estimate is not finite for {agent.name}")
        usd_day = None if cost_estimate is None else round(cost_estimate, 6)
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
    total_usd = None if not total_usd_values else sum(total_usd_values)
    if total_usd is not None and not math.isfinite(total_usd):
        raise ValueError("computed total daily cost estimate is not finite")
    totals: dict[str, int | float | None] = {
        "exact_candidate_bytes_across_agents_per_fire": sum(
            item.exact_candidate_bytes_per_fire for item in reports
        ),
        "estimated_tokens_per_day": sum(item.estimated_tokens_per_day for item in reports),
        "estimated_usd_per_day": None if total_usd is None else round(total_usd, 6),
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
                and all(agent.adapter != "claude-code@2" for agent in config.agents)
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
