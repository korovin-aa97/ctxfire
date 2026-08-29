"""Public, versioned report models for ctxfire."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

REPORT_SCHEMA_VERSION = "1.0"
CONFIG_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class Assumptions:
    """Inputs used to turn exact byte counts into estimates."""

    tokenizer: str
    tokenizer_version: str
    bytes_per_token: float
    model: str
    price_date: str
    usd_per_million_input_tokens: float | None
    cache_assumption: str
    conditional_activation_rate: float


@dataclass(frozen=True)
class ContextFile:
    """One privacy-safe context graph edge and its filesystem fact."""

    path: str
    exact_bytes: int
    counted_bytes: int
    estimated_tokens: int
    activation: str
    activation_rate: float
    reason: str
    pattern: str


@dataclass(frozen=True)
class AgentReport:
    """Context surface attributed to one configured agent."""

    name: str
    adapter: str
    engine: str
    working_directory: str
    fires_per_day: float
    files: tuple[ContextFile, ...]
    exact_candidate_bytes_per_fire: int
    estimated_tokens_per_fire: int
    estimated_tokens_per_day: int
    estimated_usd_per_day: float | None


@dataclass(frozen=True)
class ScanReport:
    """Stable machine-readable scan result."""

    schema_version: str
    tool: dict[str, str]
    project: dict[str, str]
    discovery: dict[str, Any]
    assumptions: Assumptions
    agents: tuple[AgentReport, ...]
    totals: dict[str, int | float | None]
    warnings: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return only JSON-compatible primitives."""

        return asdict(self)
