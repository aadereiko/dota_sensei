"""Rule framework.

A rule looks at one `MatchPlayer` and either stays quiet or returns a `Finding`.
Rules are pure: no DB, no network. That keeps them trivially unit-testable —
build a MatchPlayer, assert on the finding.

Add a rule by writing a function decorated with @rule and importing it in
`app.analysis.rules`.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal

from app.models import MatchPlayer

Severity = Literal["info", "warn", "critical"]


@dataclass(slots=True)
class Finding:
    rule_key: str
    severity: Severity
    title: str
    detail: str
    metrics: dict[str, Any] = field(default_factory=dict)


RuleFn = Callable[[MatchPlayer], Finding | None]

REGISTRY: dict[str, RuleFn] = {}


def rule(key: str) -> Callable[[RuleFn], RuleFn]:
    """Register a rule under a stable key (the key is persisted on Insight rows)."""

    def decorator(fn: RuleFn) -> RuleFn:
        if key in REGISTRY:
            raise ValueError(f"duplicate rule key: {key}")
        REGISTRY[key] = fn
        return fn

    return decorator


def evaluate_all(performance: MatchPlayer) -> list[Finding]:
    """Run every registered rule. A rule that raises is skipped, not fatal."""
    findings: list[Finding] = []
    for fn in REGISTRY.values():
        try:
            finding = fn(performance)
        except Exception:  # noqa: BLE001 - one bad rule must not kill the report
            continue
        if finding is not None:
            findings.append(finding)
    return findings


# --- Helpers shared by rules ---

CORE_ROLES = {1, 2}  # OpenDota lane_role: 1 safe, 2 mid, 3 off, 4 jungle
SUPPORT_ROLES = {3, 4}


def benchmark_pct(performance: MatchPlayer, metric: str) -> float | None:
    """OpenDota benchmark percentile for a metric, 0.0-1.0, if available."""
    raw = (performance.benchmarks or {}).get(metric)
    if isinstance(raw, dict):
        value = raw.get("pct")
        if isinstance(value, int | float):
            return float(value)
    return None


def minutes(performance: MatchPlayer) -> float:
    return max((performance.match.duration_seconds or 0) / 60.0, 1.0)
