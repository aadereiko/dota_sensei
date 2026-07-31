"""HTTP surface. Everything the React app talks to lives here."""

from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import OptionalAccount
from app.config import Settings, get_settings
from app.db import get_session
from app.models import Hero, Insight, Item, Match, MatchPlayer, Player
from app.schemas import (
    HeroOut,
    ItemOut,
    ItemRefOut,
    MatchDetailOut,
    MatchFullOut,
    MatchImportRequest,
    MatchImportResult,
    MatchSummaryOut,
    PlayerOut,
    ScoreboardPlayerOut,
    SyncRequest,
    SyncResult,
)
from app.services.cdn import cdn_image_url
from app.services.heroes import ensure_heroes, hero_image_url
from app.services.ingest import SlotTakenError, import_match, sync_player
from app.services.items import ensure_items

router = APIRouter(prefix="/api")

SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings)]

SEVERITY_ORDER = {"info": 0, "warn": 1, "critical": 2}


@router.get("/health")
async def health(session: SessionDep) -> dict[str, str]:
    await session.execute(select(1))
    return {"status": "ok", "database": "ok"}


@router.get("/config")
async def client_config(settings: SettingsDep) -> dict[str, int | None]:
    """Lets the UI preload the owner's account without hardcoding it."""
    return {"default_account_id": settings.default_account_id}


@router.get("/heroes", response_model=list[HeroOut])
async def list_heroes(session: SessionDep) -> list[HeroOut]:
    """Every hero. Populates the cache on first call."""
    await ensure_heroes(session)
    heroes = (
        (await session.execute(select(Hero).order_by(Hero.localized_name))).scalars().all()
    )
    return [
        HeroOut(
            id=h.id,
            name=h.name,
            localized_name=h.localized_name,
            primary_attr=h.primary_attr,
            attack_type=h.attack_type,
            roles=h.roles or [],
            image_url=cdn_image_url(h.img),
            icon_url=cdn_image_url(h.icon),
        )
        for h in heroes
    ]


@router.get("/items", response_model=list[ItemOut])
async def list_items(session: SessionDep) -> list[ItemOut]:
    """Every item. Populates the cache on first call."""
    await ensure_items(session)
    items = (
        (await session.execute(select(Item).order_by(Item.localized_name))).scalars().all()
    )
    return [
        ItemOut(
            id=i.id,
            name=i.name,
            localized_name=i.localized_name,
            cost=i.cost,
            quality=i.quality,
            tier=i.tier,
            created=i.created,
            components=i.components,
            notes=i.notes,
            image_url=cdn_image_url(i.img),
        )
        for i in items
    ]


@router.post("/sync", response_model=SyncResult)
async def sync(
    payload: SyncRequest, session: SessionDep, signed_in: OptionalAccount
) -> SyncResult:
    """Pull recent matches from OpenDota and re-run the analysis over them.

    Defaults to the signed-in account, so the UI doesn't have to know the id.
    """
    if payload.limit < 1 or payload.limit > 100:
        raise HTTPException(422, "limit must be between 1 and 100")
    account_id = payload.account_id or signed_in
    if account_id is None:
        raise HTTPException(400, "sign in with Steam or pass an account_id")
    return await sync_player(session, account_id, payload.limit)


@router.post("/matches/import", response_model=MatchImportResult)
async def import_match_by_id(
    payload: MatchImportRequest, session: SessionDep, signed_in: OptionalAccount
) -> MatchImportResult:
    """Analyse one match by id — the path for accounts without public history.

    Returns `resolved: false` plus the ten slots when we can't tell which player
    is you; post again with `player_slot` to claim one.
    """
    account_id = payload.account_id or signed_in
    if account_id is None:
        raise HTTPException(400, "sign in with Steam or pass an account_id")
    try:
        return await import_match(
            session, payload.match_id, account_id, payload.player_slot
        )
    except SlotTakenError as exc:
        raise HTTPException(409, str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise HTTPException(404, f"OpenDota has no match {payload.match_id}") from exc
        raise HTTPException(502, f"OpenDota error: {exc.response.status_code}") from exc


@router.get("/matches/{match_id}", response_model=MatchFullOut)
async def get_full_match(match_id: int, session: SessionDep) -> MatchFullOut:
    """The whole match: both teams, inventories, and the advantage series.

    Reads only what's already ingested — import the match first.
    """
    match = await session.get(Match, match_id)
    if match is None:
        raise HTTPException(404, "match not ingested — POST /api/matches/import first")

    rows = (
        (
            await session.execute(
                select(MatchPlayer)
                .where(MatchPlayer.match_id == match_id)
                .options(selectinload(MatchPlayer.hero))
                .order_by(MatchPlayer.player_slot)
            )
        )
        .scalars()
        .all()
    )

    # One lookup for every item id in the match rather than a query per slot.
    wanted: set[int] = set()
    for row in rows:
        wanted.update(i for i in (row.items or []) if i)
        wanted.update(i for i in (row.backpack or []) if i)
        if row.item_neutral:
            wanted.add(row.item_neutral)
    items: dict[int, Item] = {}
    if wanted:
        found = (
            (await session.execute(select(Item).where(Item.id.in_(wanted)))).scalars().all()
        )
        items = {i.id: i for i in found}

    def ref(item_id: int | None) -> ItemRefOut | None:
        item = items.get(item_id or 0)
        if item is None:
            return None
        return ItemRefOut(
            id=item.id, name=item.localized_name, image_url=cdn_image_url(item.img)
        )

    def refs(ids: list[int] | None) -> list[ItemRefOut]:
        return [r for r in (ref(i) for i in (ids or []) if i) if r is not None]

    players = [
        ScoreboardPlayerOut(
            player_slot=row.player_slot,
            is_radiant=row.is_radiant,
            account_id=row.account_id,
            hero_id=row.hero_id,
            hero_name=row.hero.localized_name if row.hero else None,
            hero_icon_url=cdn_image_url(row.hero.icon) if row.hero else None,
            level=row.level,
            kills=row.kills,
            deaths=row.deaths,
            assists=row.assists,
            last_hits=row.last_hits,
            denies=row.denies,
            gold_per_min=row.gold_per_min,
            xp_per_min=row.xp_per_min,
            net_worth=row.net_worth,
            hero_damage=row.hero_damage,
            tower_damage=row.tower_damage,
            hero_healing=row.hero_healing,
            obs_placed=row.obs_placed,
            sen_placed=row.sen_placed,
            items=refs(row.items),
            backpack=refs(row.backpack),
            neutral_item=ref(row.item_neutral),
        )
        for row in rows
    ]

    return MatchFullOut(
        match_id=match.match_id,
        start_time=match.start_time,
        duration_seconds=match.duration_seconds,
        radiant_win=match.radiant_win,
        is_parsed=match.is_parsed,
        radiant_score=sum(p.kills or 0 for p in players if p.is_radiant),
        dire_score=sum(p.kills or 0 for p in players if not p.is_radiant),
        players=players,
        radiant_gold_adv=match.radiant_gold_adv or [],
        radiant_xp_adv=match.radiant_xp_adv or [],
    )


@router.get("/players/{account_id}", response_model=PlayerOut)
async def get_player(account_id: int, session: SessionDep) -> Player:
    player = await session.get(Player, account_id)
    if player is None:
        raise HTTPException(404, "player not synced yet — POST /api/sync first")
    return player


@router.get("/players/{account_id}/matches", response_model=list[MatchSummaryOut])
async def list_matches(
    account_id: int,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[MatchSummaryOut]:
    rows = (
        (
            await session.execute(
                select(MatchPlayer)
                .join(Match)
                .where(MatchPlayer.account_id == account_id)
                .options(
                    selectinload(MatchPlayer.match),
                    selectinload(MatchPlayer.insights),
                    selectinload(MatchPlayer.hero),
                )
                .order_by(Match.start_time.desc())
                .limit(limit)
            )
        )
        .scalars()
        .all()
    )
    return [_summary(row) for row in rows]


@router.get("/players/{account_id}/matches/{match_id}", response_model=MatchDetailOut)
async def get_match(account_id: int, match_id: int, session: SessionDep) -> MatchDetailOut:
    row = (
        await session.execute(
            select(MatchPlayer)
            .where(MatchPlayer.account_id == account_id, MatchPlayer.match_id == match_id)
            .options(
                    selectinload(MatchPlayer.match),
                    selectinload(MatchPlayer.insights),
                    selectinload(MatchPlayer.hero),
                )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(404, "no such match for this player")

    summary = _summary(row)
    return MatchDetailOut(
        **summary.model_dump(),
        last_hits=row.last_hits,
        denies=row.denies,
        net_worth=row.net_worth,
        hero_damage=row.hero_damage,
        tower_damage=row.tower_damage,
        hero_healing=row.hero_healing,
        obs_placed=row.obs_placed,
        sen_placed=row.sen_placed,
        lane_role=row.lane_role,
        benchmarks=row.benchmarks,
        item_timings=row.item_timings,
        insights=[i for i in sorted(row.insights, key=_severity_key)],
    )


@router.get("/players/{account_id}/insights/recurring")
async def recurring_mistakes(
    account_id: int,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[dict[str, object]]:
    """The point of the whole app: which mistakes keep repeating."""
    # severity is a string column, so rank it numerically before aggregating —
    # a plain MAX() would order it alphabetically (critical < info < warn).
    severity_rank = case(
        (Insight.severity == "critical", 2),
        (Insight.severity == "warn", 1),
        else_=0,
    )
    rows = await session.execute(
        select(
            Insight.rule_key,
            Insight.title,
            func.count().label("occurrences"),
            func.max(severity_rank).label("severity_rank"),
        )
        .join(MatchPlayer, MatchPlayer.id == Insight.match_player_id)
        .where(MatchPlayer.account_id == account_id)
        .group_by(Insight.rule_key, Insight.title)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rank_to_severity = {2: "critical", 1: "warn", 0: "info"}
    return [
        {
            "rule_key": row.rule_key,
            "title": row.title,
            "occurrences": row.occurrences,
            "severity": rank_to_severity[row.severity_rank],
        }
        for row in rows
    ]


def _severity_key(insight: Insight) -> int:
    return -SEVERITY_ORDER.get(insight.severity, 0)


def _summary(row: MatchPlayer) -> MatchSummaryOut:
    worst = max(
        (i.severity for i in row.insights),
        key=lambda s: SEVERITY_ORDER.get(s, 0),
        default=None,
    )
    hero = row.__dict__.get("hero")
    return MatchSummaryOut(
        match_id=row.match_id,
        start_time=row.match.start_time,
        duration_seconds=row.match.duration_seconds,
        hero_id=row.hero_id,
        hero_name=hero.localized_name if hero else None,
        hero_icon_url=hero_image_url(hero.icon) if hero else None,
        won=row.won,
        kills=row.kills,
        deaths=row.deaths,
        assists=row.assists,
        gold_per_min=row.gold_per_min,
        xp_per_min=row.xp_per_min,
        is_parsed=row.match.is_parsed,
        insight_count=len(row.insights),
        worst_severity=worst,
    )
