"""Pydantic DTOs — the wire format the React app consumes."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["info", "warn", "critical"]


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PlayerOut(ORMModel):
    account_id: int
    persona_name: str | None
    avatar_url: str | None
    rank_tier: int | None
    estimate_mmr: int | None
    last_synced_at: datetime | None


class InsightOut(ORMModel):
    rule_key: str
    severity: Severity
    title: str
    detail: str
    metrics: dict[str, Any] | None


class MatchSummaryOut(ORMModel):
    match_id: int
    start_time: datetime
    duration_seconds: int
    hero_id: int
    won: bool
    kills: int | None
    deaths: int | None
    assists: int | None
    gold_per_min: int | None
    xp_per_min: int | None
    # Unparsed matches have no lane_role / timeline, so fewer rules can run.
    is_parsed: bool = False
    insight_count: int = 0
    worst_severity: Severity | None = None


class MatchDetailOut(MatchSummaryOut):
    last_hits: int | None
    denies: int | None
    net_worth: int | None
    hero_damage: int | None
    tower_damage: int | None
    hero_healing: int | None
    obs_placed: int | None
    sen_placed: int | None
    lane_role: int | None
    benchmarks: dict[str, Any] | None
    item_timings: dict[str, Any] | None
    insights: list[InsightOut] = []


class SyncRequest(BaseModel):
    account_id: int
    # How many recent matches to pull detail for. Detail is one API call each,
    # so keep it small while iterating.
    limit: int = 20


class SyncResult(BaseModel):
    account_id: int
    matches_seen: int
    matches_ingested: int
    insights_created: int
