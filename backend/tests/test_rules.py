"""Rules are pure functions over a MatchPlayer, so they test without a database."""

from app.analysis import evaluate_all
from app.analysis.rules import death_count_high, vision_deficit
from app.models import Match, MatchPlayer


def make_performance(**overrides: object) -> MatchPlayer:
    defaults: dict[str, object] = {
        "match_id": 1,
        "account_id": 1,
        "player_slot": 0,
        "is_radiant": True,
        "won": False,
        "hero_id": 74,
        "lane_role": 1,
        "kills": 5,
        "deaths": 3,
        "assists": 7,
        "last_hits": 400,
        "gold_per_min": 600,
        "obs_placed": 0,
        "sen_placed": 0,
        "benchmarks": {"gold_per_min": {"pct": 0.8}},
    }
    defaults.update(overrides)
    performance = MatchPlayer(**defaults)
    performance.match = Match(match_id=1, duration_seconds=2400)  # 40 minutes
    return performance


def test_clean_game_produces_no_findings() -> None:
    assert evaluate_all(make_performance()) == []


def test_high_deaths_flagged_as_critical() -> None:
    finding = death_count_high(make_performance(deaths=18))
    assert finding is not None
    assert finding.severity == "critical"
    assert finding.metrics["deaths"] == 18


def test_deaths_scaled_by_game_length() -> None:
    """8 deaths in 40 minutes is fine; the same 8 in 15 minutes is not."""
    long_game = make_performance(deaths=8)
    assert death_count_high(long_game) is None

    short_game = make_performance(deaths=8)
    short_game.match.duration_seconds = 900
    assert death_count_high(short_game) is not None


def test_vision_rule_only_applies_to_supports() -> None:
    assert vision_deficit(make_performance(lane_role=1)) is None

    support = make_performance(lane_role=4, obs_placed=1)
    finding = vision_deficit(support)
    assert finding is not None
    assert finding.metrics["obs_placed"] == 1


def test_low_farm_on_core_is_flagged() -> None:
    poor = make_performance(
        gold_per_min=280,
        benchmarks={"gold_per_min": {"pct": 0.12}},
    )
    keys = {f.rule_key for f in evaluate_all(poor)}
    assert "farm_below_benchmark" in keys
