"""Versioned loading-semantics adapters."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from functools import lru_cache
from pathlib import PurePosixPath

from .config import AgentConfig


@dataclass(frozen=True)
class Inclusion:
    pattern: str
    activation: str
    reason: str


@lru_cache(maxsize=512)
def _glob_regex(pattern: str) -> re.Pattern[str]:
    normalized = pattern.removeprefix("./")
    index = 0
    translated = ""
    while index < len(normalized):
        character = normalized[index]
        if character == "*":
            if index + 1 < len(normalized) and normalized[index + 1] == "*":
                index += 2
                if index < len(normalized) and normalized[index] == "/":
                    translated += "(?:.*/)?"
                    index += 1
                else:
                    translated += ".*"
                continue
            translated += "[^/]*"
        elif character == "?":
            translated += "[^/]"
        elif character == "[":
            closing = normalized.find("]", index + 1)
            if closing == -1:
                translated += r"\["
            else:
                content = normalized[index + 1 : closing]
                if content.startswith("!"):
                    content = "^" + content[1:]
                translated += "[" + content.replace("\\", r"\\") + "]"
                index = closing
        else:
            translated += re.escape(character)
        index += 1
    return re.compile(f"^{translated}$")


def matches(path: str, pattern: str) -> bool:
    """Match a root-relative POSIX path with ``*`` and recursive ``**`` globs."""

    return _glob_regex(pattern).fullmatch(path) is not None


def _chain_directories(working_directory: str) -> tuple[PurePosixPath, ...]:
    current = PurePosixPath() if working_directory == "." else PurePosixPath(working_directory)
    return tuple(PurePosixPath(*current.parts[:depth]) for depth in range(len(current.parts) + 1))


def _under(directory: PurePosixPath, relative: str) -> str:
    return (directory / relative).as_posix()


def inclusions(
    agent: AgentConfig, available: Mapping[str, int] | None = None
) -> tuple[Inclusion, ...]:
    """Expand an adapter to ordered, explainable include rules."""

    available = available or {}
    result: list[Inclusion] = []
    directories = _chain_directories(agent.working_directory)
    if agent.adapter == "agents-md@1":
        result.extend(
            Inclusion(_under(directory, "AGENTS.md"), "always", "agents-md@1 chain")
            for directory in directories
        )
    if agent.adapter == "codex@1":
        for directory in directories:
            candidates = (
                "AGENTS.override.md",
                "AGENTS.md",
                *agent.instruction_fallback_filenames,
            )
            for filename in candidates:
                path = _under(directory, filename)
                if available.get(path, 0) > 0:
                    result.append(Inclusion(path, "always", "codex@1 instruction chain precedence"))
                    break
            result.append(
                Inclusion(
                    _under(directory, ".agents/skills/*/SKILL.md"),
                    "conditional",
                    "codex@1 skill body; loaded only when selected",
                )
            )
    if agent.adapter == "claude-code@1":
        for directory in directories:
            for filename in ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md"):
                result.append(
                    Inclusion(
                        _under(directory, filename),
                        "always",
                        "claude-code@1 project memory ancestor chain",
                    )
                )
            result.append(
                Inclusion(
                    _under(directory, ".claude/rules/**/*.md"),
                    agent.claude_rules_activation,
                    "claude-code@1 project rule; metadata-only mode cannot parse paths frontmatter",
                )
            )
            result.append(
                Inclusion(
                    _under(directory, ".claude/skills/*/SKILL.md"),
                    "conditional",
                    "claude-code@1 skill body; loaded only when selected",
                )
            )
        working_prefix = "" if agent.working_directory == "." else f"{agent.working_directory}/"
        result.extend(
            [
                Inclusion(
                    f"{working_prefix}**/CLAUDE.md",
                    "conditional",
                    "claude-code@1 descendant memory; loaded when that subtree is read",
                ),
                Inclusion(
                    f"{working_prefix}**/CLAUDE.local.md",
                    "conditional",
                    "claude-code@1 descendant local memory; loaded when that subtree is read",
                ),
                Inclusion(
                    f"{working_prefix}**/.claude/skills/*/SKILL.md",
                    "conditional",
                    "claude-code@1 descendant skill body; available when that subtree is read",
                ),
            ]
        )
    result.extend(Inclusion(pattern, "always", "explicit include") for pattern in agent.include)
    result.extend(
        Inclusion(pattern, "conditional", "explicit conditional include")
        for pattern in agent.conditional
    )
    return tuple(result)


def exact_probe_paths(agent: AgentConfig) -> tuple[str, ...]:
    """Return known exact paths that engines load even when Git ignores them."""

    result: list[str] = []
    directories = _chain_directories(agent.working_directory)
    if agent.adapter == "agents-md@1":
        result.extend(_under(directory, "AGENTS.md") for directory in directories)
    elif agent.adapter == "codex@1":
        for directory in directories:
            result.extend(
                _under(directory, filename)
                for filename in (
                    "AGENTS.override.md",
                    "AGENTS.md",
                    *agent.instruction_fallback_filenames,
                )
            )
    elif agent.adapter == "claude-code@1":
        for directory in directories:
            result.extend(
                _under(directory, filename)
                for filename in ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md")
            )
    for pattern in (*agent.include, *agent.conditional):
        if not any(character in pattern for character in "*?["):
            result.append(pattern)
    return tuple(dict.fromkeys(result))


def excluded(path: str, patterns: tuple[str, ...]) -> bool:
    return any(matches(path, pattern) for pattern in patterns)
