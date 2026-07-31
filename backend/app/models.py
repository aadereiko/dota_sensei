"""ORM models.

Shape of the domain:

    Player  1---*  MatchPlayer  *---1  Match
                        |
                        *
                     Insight

`MatchPlayer` is the interesting table: one row per (match, player) and the grain
at which every analysis rule operates. `Insight` is a materialised finding — one
concrete mistake attached to one performance.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Hero(Base):
    """Hero metadata from OpenDota's /constants/heroes.

    Changes per patch, not per request, so it's cached here rather than fetched
    with each match. `roles` is what lets the analysis rules say something
    sensible about a support without needing a parsed replay.
    """

    __tablename__ = "heroes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64))  # npc_dota_hero_rubick
    localized_name: Mapped[str] = mapped_column(String(64))  # Rubick
    primary_attr: Mapped[str | None] = mapped_column(String(8))
    attack_type: Mapped[str | None] = mapped_column(String(16))
    roles: Mapped[list[str]] = mapped_column(JSONB, default=list)
    # Paths relative to Steam's CDN; see HERO_IMAGE_BASE.
    img: Mapped[str | None] = mapped_column(String(256))
    icon: Mapped[str | None] = mapped_column(String(256))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Item(Base):
    """Item metadata from OpenDota's /constants/items.

    Cached for the same reasons as `Hero`: static within a patch, and needed to
    turn the numeric item ids in a purchase log into something readable.
    """

    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True)  # blink
    localized_name: Mapped[str] = mapped_column(String(128))  # Blink Dagger
    cost: Mapped[int | None] = mapped_column(Integer)
    # component | common | rare | epic | artifact | consumable | secret_shop.
    # Null for recipes and neutrals.
    quality: Mapped[str | None] = mapped_column(String(32), index=True)
    # 1-5 for neutral items, null otherwise.
    tier: Mapped[int | None] = mapped_column(Integer, index=True)
    # True when the item is built from a recipe rather than bought outright.
    created: Mapped[bool] = mapped_column(Boolean, default=False)
    # Internal names of the parts, e.g. ["mithril_hammer", "ogre_axe"].
    components: Mapped[list[str] | None] = mapped_column(JSONB)
    notes: Mapped[str | None] = mapped_column(Text)
    img: Mapped[str | None] = mapped_column(String(256))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class Player(Base):
    __tablename__ = "players"

    account_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    persona_name: Mapped[str | None] = mapped_column(String(128))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    rank_tier: Mapped[int | None] = mapped_column(Integer)
    estimate_mmr: Mapped[int | None] = mapped_column(Integer)

    # Ingest bookkeeping — lets us fetch only what's new.
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_synced_match_id: Mapped[int | None] = mapped_column(BigInteger)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Not a real FK relationship — see MatchPlayer.account_id for why.
    performances: Mapped[list["MatchPlayer"]] = relationship(
        back_populates="player",
        primaryjoin="foreign(MatchPlayer.account_id) == Player.account_id",
        viewonly=True,
    )


class Match(Base):
    __tablename__ = "matches"

    match_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer)
    game_mode: Mapped[int | None] = mapped_column(Integer)
    lobby_type: Mapped[int | None] = mapped_column(Integer)
    radiant_win: Mapped[bool | None] = mapped_column(Boolean)
    patch: Mapped[int | None] = mapped_column(Integer)
    average_rank: Mapped[int | None] = mapped_column(Integer)

    # True once we've pulled the full match, not just the summary row from
    # /players/{id}/matches.
    detail_fetched: Mapped[bool] = mapped_column(Boolean, default=False)
    # True when OpenDota has parsed the replay. Only parsed matches carry
    # lane_role, per-minute series and the purchase log — so the role-gated
    # rules can only run on these. Use OpenDotaClient.request_parse to fill gaps.
    is_parsed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Per-minute net advantage, radiant minus dire. Positive = radiant ahead.
    # Parsed matches only; empty otherwise.
    radiant_gold_adv: Mapped[list[int] | None] = mapped_column(JSONB)
    radiant_xp_adv: Mapped[list[int] | None] = mapped_column(JSONB)

    # --- Parsed-replay extras ---
    # Raw objective log (towers, roshan, first blood, aegis). Turned into
    # readable events on read rather than at ingest, so the mapping can change
    # without a re-ingest.
    objectives: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    teamfight_count: Mapped[int | None] = mapped_column(Integer)
    first_blood_time: Mapped[int | None] = mapped_column(Integer)
    # Gold amounts, NOT booleans: `stomp` is the winner's peak lead and
    # `comeback` the largest deficit they came back from. Nearly every match has
    # non-zero values, so treating them as flags labels everything a stomp.
    comeback: Mapped[int | None] = mapped_column(Integer)
    stomp: Mapped[int | None] = mapped_column(Integer)

    # Set when we've asked OpenDota to parse the replay, so the UI can poll.
    parse_job_id: Mapped[int | None] = mapped_column(BigInteger)
    raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    players: Mapped[list["MatchPlayer"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class MatchPlayer(Base):
    """One player's performance in one match."""

    __tablename__ = "match_players"
    __table_args__ = (
        UniqueConstraint("match_id", "player_slot", name="uq_match_players_slot"),
        Index("ix_match_players_account_hero", "account_id", "hero_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.match_id", ondelete="CASCADE"), index=True
    )
    # Deliberately NOT a foreign key to players. Ingesting one match writes all
    # ten rows, and we only hold Player profiles for accounts we've explicitly
    # synced — an FK here would reject the other nine. Null when the account is
    # private/anonymous.
    account_id: Mapped[int | None] = mapped_column(BigInteger, index=True)

    player_slot: Mapped[int] = mapped_column(Integer)
    is_radiant: Mapped[bool] = mapped_column(Boolean)
    won: Mapped[bool] = mapped_column(Boolean)
    hero_id: Mapped[int] = mapped_column(Integer, index=True)
    lane_role: Mapped[int | None] = mapped_column(Integer)
    is_roaming: Mapped[bool | None] = mapped_column(Boolean)

    # --- Core stat line ---
    kills: Mapped[int | None] = mapped_column(Integer)
    deaths: Mapped[int | None] = mapped_column(Integer)
    assists: Mapped[int | None] = mapped_column(Integer)
    last_hits: Mapped[int | None] = mapped_column(Integer)
    denies: Mapped[int | None] = mapped_column(Integer)
    gold_per_min: Mapped[int | None] = mapped_column(Integer)
    xp_per_min: Mapped[int | None] = mapped_column(Integer)
    net_worth: Mapped[int | None] = mapped_column(Integer)
    hero_damage: Mapped[int | None] = mapped_column(Integer)
    tower_damage: Mapped[int | None] = mapped_column(Integer)
    hero_healing: Mapped[int | None] = mapped_column(Integer)
    obs_placed: Mapped[int | None] = mapped_column(Integer)
    sen_placed: Mapped[int | None] = mapped_column(Integer)
    camps_stacked: Mapped[int | None] = mapped_column(Integer)
    stuns_seconds: Mapped[float | None] = mapped_column(Float)
    level: Mapped[int | None] = mapped_column(Integer)

    # --- Inventory (present even on unparsed matches) ---
    # Six main slots as item ids; 0 means empty.
    items: Mapped[list[int] | None] = mapped_column(JSONB)
    backpack: Mapped[list[int] | None] = mapped_column(JSONB)
    item_neutral: Mapped[int | None] = mapped_column(Integer)

    # --- Parsed-replay extras ---
    # How much of the lane's available gold+xp you actually took, 0-100.
    lane_efficiency_pct: Mapped[int | None] = mapped_column(Integer)
    teamfight_participation: Mapped[float | None] = mapped_column(Float)
    actions_per_min: Mapped[int | None] = mapped_column(Integer)
    neutral_kills: Mapped[int | None] = mapped_column(Integer)
    tower_kills: Mapped[int | None] = mapped_column(Integer)
    roshan_kills: Mapped[int | None] = mapped_column(Integer)
    buyback_count: Mapped[int | None] = mapped_column(Integer)
    pings: Mapped[int | None] = mapped_column(Integer)

    # --- Series & derived blobs (only present once detail is fetched) ---
    # gold_t / xp_t / lh_t per-minute arrays, purchase_log, kills_log, etc.
    timeline: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # OpenDota's own percentile benchmarks for this hero (gpm, xpm, kda, ...).
    benchmarks: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # {"blink": 812, "black_king_bar": 1455, ...} seconds into the match.
    item_timings: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    match: Mapped["Match"] = relationship(back_populates="players")
    # No FK: heroes are a cache that may not be populated yet, and a missing
    # hero row must not block ingesting a match.
    hero: Mapped["Hero | None"] = relationship(
        primaryjoin="foreign(MatchPlayer.hero_id) == Hero.id",
        viewonly=True,
    )
    player: Mapped["Player | None"] = relationship(
        back_populates="performances",
        primaryjoin="foreign(MatchPlayer.account_id) == Player.account_id",
        viewonly=True,
    )
    insights: Mapped[list["Insight"]] = relationship(
        back_populates="performance", cascade="all, delete-orphan"
    )


class Insight(Base):
    """A single mistake (or notable pattern) found by one analysis rule."""

    __tablename__ = "insights"
    __table_args__ = (
        UniqueConstraint("match_player_id", "rule_key", name="uq_insights_rule"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("match_players.id", ondelete="CASCADE"), index=True
    )

    rule_key: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(16))  # info | warn | critical
    title: Mapped[str] = mapped_column(String(200))
    detail: Mapped[str] = mapped_column(Text)
    # Numbers behind the verdict, so the UI can render a chart or a "yours vs
    # benchmark" comparison without re-running the rule.
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    performance: Mapped["MatchPlayer"] = relationship(back_populates="insights")
