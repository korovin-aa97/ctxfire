"""Configuration parsing and validation."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from math import isfinite
from pathlib import Path, PurePosixPath
from typing import Any

from .model import CONFIG_SCHEMA_VERSION, Assumptions


@dataclass(frozen=True)
class AgentConfig:
    name: str
    adapter: str
    engine: str
    working_directory: str
    fires_per_day: float
    include: tuple[str, ...]
    conditional: tuple[str, ...]
    exclude: tuple[str, ...]
    instruction_fallback_filenames: tuple[str, ...]
    instruction_max_bytes: int | None
    claude_rules_activation: str


@dataclass(frozen=True)
class Config:
    path: Path
    root: Path
    project_name: str
    assumptions: Assumptions
    agents: tuple[AgentConfig, ...]


def _patterns(raw: dict[str, Any], key: str) -> tuple[str, ...]:
    value = raw.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be an array of strings")
    for pattern in value:
        if not pattern or "\\" in pattern:
            raise ValueError(f"{key} patterns must be non-empty POSIX paths: {pattern!r}")
        pure = PurePosixPath(pattern)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"{key} pattern must stay inside project root: {pattern}")
    return tuple(value)


def load_config(path: Path) -> Config:
    """Load a ctxfire v1 TOML file without reading repository content."""

    resolved = path.resolve()
    data = tomllib.loads(resolved.read_text(encoding="utf-8"))
    if str(data.get("schema_version", "")) != CONFIG_SCHEMA_VERSION:
        raise ValueError(f'schema_version must be "{CONFIG_SCHEMA_VERSION}"')
    project = data.get("project", {})
    if not isinstance(project, dict):
        raise ValueError("[project] must be a table")
    root_value = Path(str(project.get("root", ".")))
    root = root_value if root_value.is_absolute() else resolved.parent / root_value
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"project root is not a directory: {root}")

    bytes_per_token = float(project.get("bytes_per_token", 4.0))
    conditional_rate = float(project.get("conditional_activation_rate", 0.0))
    if not isfinite(bytes_per_token) or bytes_per_token <= 0:
        raise ValueError("bytes_per_token must be finite and greater than zero")
    if not isfinite(conditional_rate) or not 0 <= conditional_rate <= 1:
        raise ValueError("conditional_activation_rate must be finite and between 0 and 1")
    price_raw = project.get("usd_per_million_input_tokens")
    price = None if price_raw is None else float(price_raw)
    if price is not None and (not isfinite(price) or price < 0):
        raise ValueError("usd_per_million_input_tokens must be finite and non-negative")
    tokenizer = str(project.get("tokenizer", "byte-estimate"))
    if tokenizer == "byte-estimate":
        tokenizer_version = "approximation-v1"
    elif tokenizer.startswith("tiktoken:") and tokenizer.partition(":")[2]:
        try:
            tokenizer_version = version("tiktoken")
        except PackageNotFoundError as error:
            raise ValueError("tiktoken tokenizer requested; install ctxfire[tokenizers]") from error
    else:
        raise ValueError("tokenizer must be byte-estimate or tiktoken:<encoding>")
    assumptions = Assumptions(
        tokenizer=tokenizer,
        tokenizer_version=tokenizer_version,
        bytes_per_token=bytes_per_token,
        model=str(project.get("model", "unspecified")),
        price_date=str(project.get("price_date", "unspecified")),
        usd_per_million_input_tokens=price,
        cache_assumption=str(project.get("cache_assumption", "no-cache-credit")),
        conditional_activation_rate=conditional_rate,
    )

    raw_agents = data.get("agents", [])
    if not isinstance(raw_agents, list) or not raw_agents:
        raise ValueError("configure at least one [[agents]] table")
    agents: list[AgentConfig] = []
    names: set[str] = set()
    for raw in raw_agents:
        if not isinstance(raw, dict) or not str(raw.get("name", "")).strip():
            raise ValueError("every [[agents]] table needs a non-empty name")
        name = str(raw["name"])
        if name in names:
            raise ValueError(f"duplicate agent name: {name}")
        names.add(name)
        fires = float(raw.get("fires_per_day", 1.0))
        if not isfinite(fires) or fires < 0:
            raise ValueError(f"fires_per_day must be finite and non-negative for {name}")
        working_directory = str(raw.get("working_directory", ".")).strip("/") or "."
        if "\\" in working_directory:
            raise ValueError(f"working_directory must use POSIX separators for {name}")
        work_path = PurePosixPath(working_directory)
        if work_path.is_absolute() or ".." in work_path.parts:
            raise ValueError(f"working_directory must stay inside project root: {name}")
        adapter = str(raw.get("adapter", "explicit@1"))
        if adapter not in {"explicit@1", "agents-md@1", "codex@1", "claude-code@1"}:
            raise ValueError(f"unsupported adapter {adapter!r} for {name}")
        fallback_names = _patterns(raw, "instruction_fallback_filenames")
        if any("/" in item or "\\" in item for item in fallback_names):
            raise ValueError(f"instruction fallback names must be filenames for {name}")
        max_bytes_raw = raw.get("instruction_max_bytes", 32768 if adapter == "codex@1" else None)
        if max_bytes_raw is not None and (
            not isinstance(max_bytes_raw, int) or isinstance(max_bytes_raw, bool)
        ):
            raise ValueError(f"instruction_max_bytes must be an integer for {name}")
        instruction_max_bytes = max_bytes_raw
        if instruction_max_bytes is not None and instruction_max_bytes <= 0:
            raise ValueError(f"instruction_max_bytes must be positive for {name}")
        claude_rules_activation = str(raw.get("claude_rules_activation", "always"))
        if claude_rules_activation not in {"always", "conditional"}:
            raise ValueError(f"claude_rules_activation must be always or conditional for {name}")
        agents.append(
            AgentConfig(
                name=name,
                adapter=adapter,
                engine=str(raw.get("engine", adapter.partition("@")[0])),
                working_directory=working_directory,
                fires_per_day=fires,
                include=_patterns(raw, "include"),
                conditional=_patterns(raw, "conditional"),
                exclude=_patterns(raw, "exclude"),
                instruction_fallback_filenames=fallback_names,
                instruction_max_bytes=instruction_max_bytes,
                claude_rules_activation=claude_rules_activation,
            )
        )
    return Config(
        path=resolved,
        root=root,
        project_name=str(project.get("name", root.name)),
        assumptions=assumptions,
        agents=tuple(agents),
    )
