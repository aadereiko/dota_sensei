"""The actual mistake detectors.

These four are starters that prove the framework end to end. The interesting
work is adding more — feeding off `timeline` (deaths by minute, gold curves)
rather than just the summary stat line.
"""

from app.analysis.base import (
    CORE_ROLES,
    SUPPORT_ROLES,
    Finding,
    benchmark_pct,
    minutes,
    rule,
)
from app.models import MatchPlayer


@rule("farm_below_benchmark")
def farm_below_benchmark(p: MatchPlayer) -> Finding | None:
    """GPM in the bottom third for this hero.

    No role gate: OpenDota's benchmarks are per-hero, so the percentile is already
    normalised for what the hero is meant to be doing. That also means this rule
    still works on unparsed matches, where `lane_role` is null.
    """
    pct = benchmark_pct(p, "gold_per_min")
    if pct is None or pct >= 0.35:
        return None
    return Finding(
        rule_key="farm_below_benchmark",
        severity="critical" if pct < 0.2 else "warn",
        title="Farm well below par for this hero",
        detail=(
            f"{p.gold_per_min} GPM puts you in the bottom {round(pct * 100)}% of this hero's "
            "games. That usually means idle time between fights — check your jungle "
            "route after a lane win and whether you're stacking camps."
        ),
        metrics={"gpm": p.gold_per_min, "gpm_percentile": pct},
    )


@rule("last_hit_efficiency")
def last_hit_efficiency(p: MatchPlayer) -> Finding | None:
    """Core averaging under ~5 last hits/minute over a full-length game."""
    if p.lane_role not in CORE_ROLES or p.last_hits is None:
        return None
    mins = minutes(p)
    if mins < 20:
        return None
    per_min = p.last_hits / mins
    if per_min >= 5.0:
        return None
    return Finding(
        rule_key="last_hit_efficiency",
        severity="warn",
        title="Last hits per minute are low",
        detail=(
            f"{p.last_hits} last hits in {round(mins)} minutes is {per_min:.1f}/min. "
            "A core should clear 5/min in a game this long; below that, creep waves are "
            "dying without you."
        ),
        metrics={"last_hits": p.last_hits, "per_minute": round(per_min, 2)},
    )


@rule("death_count_high")
def death_count_high(p: MatchPlayer) -> Finding | None:
    """Dying more than roughly once every four minutes."""
    if p.deaths is None:
        return None
    mins = minutes(p)
    deaths_per_10 = p.deaths / mins * 10
    if deaths_per_10 < 2.5:
        return None
    return Finding(
        rule_key="death_count_high",
        severity="critical" if deaths_per_10 >= 4 else "warn",
        title=f"{p.deaths} deaths is too many for a {round(mins)} minute game",
        detail=(
            f"That's {deaths_per_10:.1f} deaths per 10 minutes. Each one is roughly a "
            "creep wave plus map control handed over. Look at where they happened — "
            "repeated deaths in the same lane usually mean a missing ward, not a "
            "mechanical mistake."
        ),
        metrics={"deaths": p.deaths, "deaths_per_10_min": round(deaths_per_10, 2)},
    )


@rule("vision_deficit")
def vision_deficit(p: MatchPlayer) -> Finding | None:
    """Support who barely warded."""
    if p.lane_role not in SUPPORT_ROLES:
        return None
    obs = p.obs_placed or 0
    sen = p.sen_placed or 0
    mins = minutes(p)
    expected = mins / 5  # loosely: one observer per ward cooldown pair
    if obs >= expected:
        return None
    return Finding(
        rule_key="vision_deficit",
        severity="warn",
        title="Not enough vision for a support game",
        detail=(
            f"{obs} observers and {sen} sentries in {round(mins)} minutes. Roughly "
            f"{round(expected)} observers were buyable in that time. Unspent ward "
            "charges are the cheapest thing you left on the table."
        ),
        metrics={
            "obs_placed": obs,
            "sen_placed": sen,
            "obs_expected": round(expected, 1),
        },
    )
