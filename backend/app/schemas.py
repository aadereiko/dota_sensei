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


class HeroOut(BaseModel):
    id: int
    name: str
    localized_name: str
    primary_attr: str | None
    attack_type: str | None
    roles: list[str]
    image_url: str | None
    icon_url: str | None


class ItemOut(BaseModel):
    id: int
    name: str
    localized_name: str
    cost: int | None
    quality: str | None
    tier: int | None
    created: bool
    components: list[str] | None
    notes: str | None
    image_url: str | None


class CurrentUser(BaseModel):
    account_id: int
    # A JS number can't hold a 17-digit SteamID64 exactly, so send it as a string.
    steam_id64: str
    persona_name: str | None
    avatar_url: str | None
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
    hero_name: str | None = None
    hero_icon_url: str | None = None
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
    # Optional: defaults to the signed-in account.
    account_id: int | None = None
    # How many recent matches to pull detail for. Detail is one API call each,
    # so keep it small while iterating.
    limit: int = 20


class ItemRefOut(BaseModel):
    """An item in an inventory slot, already resolved for display."""

    id: int
    name: str
    image_url: str | None


class PurchaseOut(BaseModel):
    """When an item was bought, in seconds from horn (negative = pre-game)."""

    time: int
    name: str
    image_url: str | None


class MatchEventOut(BaseModel):
    time: int
    kind: str  # first_blood | building | throne | roshan | aegis
    team: str | None  # radiant | dire
    label: str


class ScoreboardPlayerOut(BaseModel):
    """One player's full line in the match scoreboard."""

    player_slot: int
    is_radiant: bool
    account_id: int | None
    hero_id: int
    hero_name: str | None
    hero_icon_url: str | None
    level: int | None
    kills: int | None
    deaths: int | None
    assists: int | None
    last_hits: int | None
    denies: int | None
    gold_per_min: int | None
    xp_per_min: int | None
    net_worth: int | None
    hero_damage: int | None
    tower_damage: int | None
    hero_healing: int | None
    obs_placed: int | None
    sen_placed: int | None
    items: list[ItemRefOut] = []
    backpack: list[ItemRefOut] = []
    neutral_item: ItemRefOut | None = None

    # Parsed replays only — null on unparsed matches.
    lane_efficiency_pct: int | None = None
    teamfight_participation: float | None = None
    actions_per_min: int | None = None
    neutral_kills: int | None = None
    tower_kills: int | None = None
    buyback_count: int | None = None
    purchases: list[PurchaseOut] = []


class MatchFullOut(BaseModel):
    """Everything about one match: both teams, inventories, and the graphs."""

    match_id: int
    start_time: datetime
    duration_seconds: int
    radiant_win: bool | None
    is_parsed: bool
    radiant_score: int
    dire_score: int
    players: list[ScoreboardPlayerOut]
    # Per-minute radiant-minus-dire. Empty on unparsed matches.
    radiant_gold_adv: list[int] = []
    radiant_xp_adv: list[int] = []

    # Parsed replays only.
    events: list[MatchEventOut] = []
    first_blood_time: int | None = None
    teamfight_count: int | None = None
    comeback: int | None = None
    stomp: int | None = None
    # Set while a parse we requested is still queued.
    parse_job_id: int | None = None


class ParseStatusOut(BaseModel):
    match_id: int
    job_id: int | None
    # queued while OpenDota works; done once the match came back parsed.
    status: str
    is_parsed: bool


class MatchImportRequest(BaseModel):
    """Analyse one match by id, for people whose history isn't public.

    `account_id` defaults to the signed-in user. `player_slot` says which of the
    ten players is you — needed only when we can't work it out ourselves.
    """

    match_id: int
    account_id: int | None = None
    player_slot: int | None = None


class MatchSlotOut(BaseModel):
    """One slot in a match, enough for a human to recognise themselves."""

    player_slot: int
    is_radiant: bool
    hero_id: int
    # Without a name here, "which of these ten was you" is unanswerable.
    hero_name: str | None = None
    hero_icon_url: str | None = None
    account_id: int | None
    won: bool
    kills: int | None
    deaths: int | None
    assists: int | None
    gold_per_min: int | None
    net_worth: int | None


class MatchImportResult(BaseModel):
    match_id: int
    # False when the match was stored but we couldn't tell which player is you;
    # pick from `candidates` and post again with player_slot.
    resolved: bool
    is_parsed: bool = False
    insights_created: int = 0
    candidates: list[MatchSlotOut] = []


class SyncResult(BaseModel):
    account_id: int
    matches_seen: int
    matches_ingested: int
    insights_created: int
