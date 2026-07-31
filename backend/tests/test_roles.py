"""Role inference — the thing that lets rules say something useful about an
unparsed match, where `lane_role` is null.

Priority: a parsed replay's lane_role wins; otherwise fall back to the hero's
static role tags; otherwise admit we don't know.
"""

from app.analysis.base import guess_role, role_is_certain
from app.analysis.rules import farm_below_benchmark, last_hit_efficiency, vision_deficit
from app.models import Hero, Match, MatchPlayer

RUBICK = Hero(id=86, name="npc_dota_hero_rubick", localized_name="Rubick",
              roles=["Support", "Disabler", "Nuker"])
ANTIMAGE = Hero(id=1, name="npc_dota_hero_antimage", localized_name="Anti-Mage",
                roles=["Carry", "Escape", "Nuker"])
# Tagged both Carry and Support — genuinely ambiguous.
WINDRANGER = Hero(id=21, name="npc_dota_hero_windrunner", localized_name="Windranger",
                  roles=["Carry", "Support", "Disabler", "Escape", "Nuker"])


def perf(hero: Hero | None = None, lane_role: int | None = None, **kw: object) -> MatchPlayer:
    defaults: dict[str, object] = {
        "match_id": 1, "account_id": 1, "player_slot": 0, "is_radiant": True,
        "won": False, "hero_id": hero.id if hero else 0, "lane_role": lane_role,
        "kills": 2, "deaths": 4, "assists": 8, "last_hits": 300,
        "gold_per_min": 400, "obs_placed": 0, "sen_placed": 0,
        "benchmarks": {"gold_per_min": {"pct": 0.5}},
    }
    defaults.update(kw)
    p = MatchPlayer(**defaults)
    p.match = Match(match_id=1, duration_seconds=2400)  # 40 minutes
    p.hero = hero
    return p


def test_lane_role_wins_over_hero_tags() -> None:
    """A support hero played mid is a core, and a parsed replay knows it."""
    assert guess_role(perf(RUBICK, lane_role=2)) == "core"
    assert guess_role(perf(ANTIMAGE, lane_role=3)) == "support"


def test_hero_tags_used_when_lane_role_missing() -> None:
    assert guess_role(perf(RUBICK)) == "support"
    assert guess_role(perf(ANTIMAGE)) == "core"


def test_ambiguous_hero_is_not_guessed() -> None:
    assert guess_role(perf(WINDRANGER)) is None


def test_unknown_without_hero_data() -> None:
    assert guess_role(perf(None)) is None


def test_role_certainty_reports_the_source() -> None:
    assert role_is_certain(perf(RUBICK, lane_role=4)) is True
    assert role_is_certain(perf(RUBICK)) is False


def test_farm_advice_is_role_specific() -> None:
    """The original bug: core advice handed to a support."""
    poor = {"gold_per_min": 243, "benchmarks": {"gold_per_min": {"pct": 0.038}}}

    support = farm_below_benchmark(perf(RUBICK, **poor))
    assert support is not None
    assert "jungle route" not in support.detail
    assert support.metrics["role"] == "support"

    core = farm_below_benchmark(perf(ANTIMAGE, **poor))
    assert core is not None
    assert "jungle route" in core.detail
    assert core.metrics["role"] == "core"


def test_percentile_is_rounded_for_display() -> None:
    finding = farm_below_benchmark(
        perf(ANTIMAGE, gold_per_min=243, benchmarks={"gold_per_min": {"pct": 0.0380794701986755}})
    )
    assert finding is not None
    assert finding.metrics["bottom_percent"] == 4
    assert "bottom 4%" in finding.detail
    # The metric must be the same number the sentence quotes.
    assert "0.0380794701986755" not in str(finding.metrics)


def test_tiny_percentile_never_reads_as_zero_percent() -> None:
    """round(0.5) is 0 under banker's rounding — "the bottom 0%" is nonsense."""
    finding = farm_below_benchmark(
        perf(RUBICK, gold_per_min=170, benchmarks={"gold_per_min": {"pct": 0.005}})
    )
    assert finding is not None
    assert finding.metrics["bottom_percent"] == 1
    assert "bottom 1%" in finding.detail


def test_vision_rule_now_runs_on_unparsed_support_games() -> None:
    """Previously impossible: no lane_role meant the rule never fired."""
    finding = vision_deficit(perf(RUBICK, obs_placed=1))
    assert finding is not None
    assert finding.metrics["obs_placed"] == 1


def test_vision_rule_still_ignores_cores() -> None:
    assert vision_deficit(perf(ANTIMAGE, obs_placed=0)) is None


def test_last_hit_rule_now_runs_on_unparsed_core_games() -> None:
    finding = last_hit_efficiency(perf(ANTIMAGE, last_hits=100))
    assert finding is not None


def test_last_hit_rule_still_ignores_supports() -> None:
    assert last_hit_efficiency(perf(RUBICK, last_hits=100)) is None
