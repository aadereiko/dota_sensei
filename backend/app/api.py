"""HTTP surface. Everything the React app talks to lives here."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import OptionalAccount
from app.config import Settings, get_settings
from app.db import get_session
from app.models import Insight, Match, MatchPlayer, Player
from app.schemas import (
    MatchDetailOut,
    MatchSummaryOut,
    PlayerOut,
    SyncRequest,
    SyncResult,
)
from app.services.ingest import sync_player

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
                .options(selectinload(MatchPlayer.match), selectinload(MatchPlayer.insights))
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
            .options(selectinload(MatchPlayer.match), selectinload(MatchPlayer.insights))
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
    return MatchSummaryOut(
        match_id=row.match_id,
        start_time=row.match.start_time,
        duration_seconds=row.match.duration_seconds,
        hero_id=row.hero_id,
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
