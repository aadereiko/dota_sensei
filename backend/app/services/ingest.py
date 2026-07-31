"""Ingest pipeline: OpenDota -> Postgres -> analysis rules -> Insight rows.

    sync_player(session, account_id, limit)
      1. upsert the Player profile
      2. list recent match ids
      3. for each match we don't already have detail for: fetch, upsert Match +
         all 10 MatchPlayer rows
      4. run the rule registry over *our* performance and persist Findings

Idempotent: re-running skips matches already marked `detail_fetched` and replaces
insights for the performances it re-evaluates.
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis import evaluate_all
from app.models import Hero, Insight, Match, MatchPlayer, Player
from app.schemas import MatchImportResult, MatchSlotOut, SyncResult
from app.services.heroes import ensure_heroes, hero_image_url, hero_map
from app.services.opendota import OpenDotaClient


def _to_datetime(unix_seconds: int | None) -> datetime:
    return datetime.fromtimestamp(unix_seconds or 0, tz=UTC)


def _won(player_slot: int, radiant_win: bool | None) -> bool:
    is_radiant = player_slot < 128
    return bool(radiant_win) is is_radiant


async def upsert_player(
    session: AsyncSession, account_id: int, profile: dict[str, Any]
) -> Player:
    values = {
        "account_id": account_id,
        "persona_name": (profile.get("profile") or {}).get("personaname"),
        "avatar_url": (profile.get("profile") or {}).get("avatarfull"),
        "rank_tier": profile.get("rank_tier"),
        "estimate_mmr": (profile.get("mmr_estimate") or {}).get("estimate"),
        "last_synced_at": datetime.now(UTC),
    }
    stmt = (
        pg_insert(Player)
        .values(**values)
        .on_conflict_do_update(
            index_elements=[Player.account_id],
            set_={k: v for k, v in values.items() if k != "account_id"},
        )
        .returning(Player)
    )
    return (await session.execute(stmt)).scalar_one()


def _match_player_values(raw: dict[str, Any], match: dict[str, Any]) -> dict[str, Any]:
    slot = raw.get("player_slot", 0)
    return {
        "match_id": match["match_id"],
        "account_id": raw.get("account_id"),
        "player_slot": slot,
        "is_radiant": slot < 128,
        "won": _won(slot, match.get("radiant_win")),
        "hero_id": raw.get("hero_id") or 0,
        "lane_role": raw.get("lane_role"),
        "is_roaming": raw.get("is_roaming"),
        "kills": raw.get("kills"),
        "deaths": raw.get("deaths"),
        "assists": raw.get("assists"),
        "last_hits": raw.get("last_hits"),
        "denies": raw.get("denies"),
        "gold_per_min": raw.get("gold_per_min"),
        "xp_per_min": raw.get("xp_per_min"),
        "net_worth": raw.get("net_worth") or raw.get("total_gold"),
        "hero_damage": raw.get("hero_damage"),
        "tower_damage": raw.get("tower_damage"),
        "hero_healing": raw.get("hero_healing"),
        "obs_placed": raw.get("obs_placed"),
        "sen_placed": raw.get("sen_placed"),
        "camps_stacked": raw.get("camps_stacked"),
        "stuns_seconds": raw.get("stuns"),
        "timeline": {
            "gold_t": raw.get("gold_t"),
            "xp_t": raw.get("xp_t"),
            "lh_t": raw.get("lh_t"),
            "kills_log": raw.get("kills_log"),
            "purchase_log": raw.get("purchase_log"),
        },
        "benchmarks": raw.get("benchmarks"),
        "item_timings": raw.get("first_purchase_time") or raw.get("purchase_time"),
    }


async def ingest_match(session: AsyncSession, match: dict[str, Any]) -> list[MatchPlayer]:
    """Upsert one full match and all of its player rows. Returns the player rows."""
    match_values = {
        "match_id": match["match_id"],
        "start_time": _to_datetime(match.get("start_time")),
        "duration_seconds": match.get("duration") or 0,
        "game_mode": match.get("game_mode"),
        "lobby_type": match.get("lobby_type"),
        "radiant_win": match.get("radiant_win"),
        "patch": match.get("patch"),
        "average_rank": match.get("average_rank"),
        "detail_fetched": True,
        # OpenDota sets `version` only on parsed replays.
        "is_parsed": match.get("version") is not None,
    }
    await session.execute(
        pg_insert(Match)
        .values(**match_values)
        .on_conflict_do_update(
            index_elements=[Match.match_id],
            set_={k: v for k, v in match_values.items() if k != "match_id"},
        )
    )

    performances: list[MatchPlayer] = []
    for raw in match.get("players") or []:
        values = _match_player_values(raw, match)
        stmt = (
            pg_insert(MatchPlayer)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_match_players_slot",
                set_={
                    k: v for k, v in values.items() if k not in ("match_id", "player_slot")
                },
            )
            .returning(MatchPlayer)
        )
        performances.append((await session.execute(stmt)).scalar_one())
    return performances


async def analyse_performance(session: AsyncSession, performance: MatchPlayer) -> int:
    """Run the rules and persist findings. Replaces prior insights for this row."""
    findings = evaluate_all(performance)
    for finding in findings:
        values = {
            "match_player_id": performance.id,
            "rule_key": finding.rule_key,
            "severity": finding.severity,
            "title": finding.title,
            "detail": finding.detail,
            "metrics": finding.metrics,
        }
        await session.execute(
            pg_insert(Insight)
            .values(**values)
            .on_conflict_do_update(
                constraint="uq_insights_rule",
                set_={
                    k: v
                    for k, v in values.items()
                    if k not in ("match_player_id", "rule_key")
                },
            )
        )
    return len(findings)


def _hero_name(heroes: dict[int, Hero], hero_id: int | None) -> str | None:
    hero = heroes.get(hero_id or 0)
    return hero.localized_name if hero else None


def _hero_icon(heroes: dict[int, Hero], hero_id: int | None) -> str | None:
    hero = heroes.get(hero_id or 0)
    return hero_image_url(hero.icon) if hero else None


def resolve_slot(
    players: list[dict[str, Any]], account_id: int, player_slot: int | None
) -> dict[str, Any] | None:
    """Work out which of the ten players is the user.

    An explicit slot wins. Otherwise we can only tell if their account is visible
    in the match — which it won't be when the whole point is that OpenDota
    anonymised them. Returns None to mean "ask the user".
    """
    if player_slot is not None:
        return next((p for p in players if p.get("player_slot") == player_slot), None)
    mine = [p for p in players if p.get("account_id") == account_id]
    return mine[0] if len(mine) == 1 else None


class SlotTakenError(Exception):
    """The requested slot already belongs to a different, identified account."""


async def import_match(
    session: AsyncSession,
    match_id: int,
    account_id: int,
    player_slot: int | None = None,
    client: OpenDotaClient | None = None,
) -> MatchImportResult:
    """Ingest a single match by id and analyse the user's slot in it.

    This is the escape hatch for accounts without public match history: the match
    itself is public even when the player in it is anonymous, so pasting a match
    id from the Dota client still gets you a breakdown.
    """
    await ensure_heroes(session, client)
    async with client or OpenDotaClient() as api:
        detail = await api.match(match_id)

    raw_players: list[dict[str, Any]] = detail.get("players") or []
    performances = await ingest_match(session, detail)
    is_parsed = detail.get("version") is not None
    heroes = await hero_map(session)

    chosen = resolve_slot(raw_players, account_id, player_slot)
    if chosen is None:
        # Store the match anyway — it's useful — but let the caller pick a slot.
        return MatchImportResult(
            match_id=match_id,
            resolved=False,
            is_parsed=is_parsed,
            candidates=[
                MatchSlotOut(
                    player_slot=p.get("player_slot", 0),
                    is_radiant=p.get("player_slot", 0) < 128,
                    hero_id=p.get("hero_id") or 0,
                    hero_name=_hero_name(heroes, p.get("hero_id")),
                    hero_icon_url=_hero_icon(heroes, p.get("hero_id")),
                    account_id=p.get("account_id"),
                    won=_won(p.get("player_slot", 0), detail.get("radiant_win")),
                    kills=p.get("kills"),
                    deaths=p.get("deaths"),
                    assists=p.get("assists"),
                    gold_per_min=p.get("gold_per_min"),
                    net_worth=p.get("net_worth") or p.get("total_gold"),
                )
                for p in raw_players
            ],
        )

    slot = chosen.get("player_slot", 0)
    performance = next((p for p in performances if p.player_slot == slot), None)
    if performance is None:
        raise SlotTakenError(f"slot {slot} is not in match {match_id}")

    # Claiming an anonymous slot is the whole point. Claiming someone else's
    # identified slot is not.
    if performance.account_id is not None and performance.account_id != account_id:
        raise SlotTakenError(
            f"slot {slot} belongs to account {performance.account_id}"
        )
    if performance.account_id is None:
        performance.account_id = account_id
        await session.flush()

    # `hero` must be eagerly loaded: the rules read hero.roles to tell a support
    # from a core, and a lazy load inside sync rule code would blow up.
    await session.refresh(performance, ["match", "hero"])
    created = await analyse_performance(session, performance)
    await session.flush()
    return MatchImportResult(
        match_id=match_id,
        resolved=True,
        is_parsed=is_parsed,
        insights_created=created,
    )


async def sync_player(
    session: AsyncSession,
    account_id: int,
    limit: int = 20,
    client: OpenDotaClient | None = None,
) -> SyncResult:
    await ensure_heroes(session, client)
    async with client or OpenDotaClient() as api:
        await upsert_player(session, account_id, await api.player(account_id))
        recent = await api.recent_matches(account_id, limit=limit)

        known = set(
            (
                await session.execute(
                    select(Match.match_id).where(
                        Match.match_id.in_([m["match_id"] for m in recent] or [0]),
                        Match.detail_fetched.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )

        ingested = 0
        insights = 0
        for summary in recent:
            match_id = summary["match_id"]
            if match_id in known:
                continue
            detail = await api.match(match_id)
            performances = await ingest_match(session, detail)
            ingested += 1
            for performance in performances:
                if performance.account_id == account_id:
                    # `match` for duration; `hero` because the rules read
                    # hero.roles, and a lazy load in sync rule code would blow up.
                    await session.refresh(performance, ["match", "hero"])
                    insights += await analyse_performance(session, performance)

        await session.flush()
        return SyncResult(
            account_id=account_id,
            matches_seen=len(recent),
            matches_ingested=ingested,
            insights_created=insights,
        )
