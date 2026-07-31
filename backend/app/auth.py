"""Steam sign-in routes and the current-user dependency.

Flow:

    GET  /api/auth/steam/login     302 -> steamcommunity.com
    GET  /api/auth/steam/callback  Steam redirects back here; we verify the
                                   signature with Steam, store account_id in the
                                   session cookie, then 302 to the app
    GET  /api/auth/me              who am I (401 if signed out)
    POST /api/auth/logout          clear the session

The session is a signed (not encrypted) cookie holding only `account_id`, which
is public information anyway — it's in every Dotabuff URL.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_session
from app.models import Player
from app.schemas import CurrentUser
from app.services.ingest import upsert_player
from app.services.opendota import OpenDotaClient
from app.services.steam import (
    account_id_to_steamid64,
    build_login_url,
    steamid64_to_account_id,
    verify_callback,
)

router = APIRouter(prefix="/auth")

SESSION_KEY = "account_id"


def current_account_id(request: Request) -> int | None:
    """The signed-in account, or None. Use for endpoints that work either way."""
    value = request.session.get(SESSION_KEY)
    return int(value) if isinstance(value, int | str) and str(value).isdigit() else None


def require_account_id(request: Request) -> int:
    account_id = current_account_id(request)
    if account_id is None:
        raise HTTPException(401, "not signed in")
    return account_id


CurrentAccount = Annotated[int, Depends(require_account_id)]
OptionalAccount = Annotated[int | None, Depends(current_account_id)]


@router.get("/steam/login")
async def steam_login(settings: Annotated[Settings, Depends(get_settings)]) -> RedirectResponse:
    return RedirectResponse(
        build_login_url(settings.steam_return_to, settings.steam_realm),
        status_code=302,
    )


@router.get("/steam/callback")
async def steam_callback(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RedirectResponse:
    steamid64 = await verify_callback(dict(request.query_params))
    if steamid64 is None:
        return RedirectResponse(f"{settings.public_base_url}/?login=failed", status_code=302)

    account_id = steamid64_to_account_id(steamid64)
    request.session[SESSION_KEY] = account_id

    # Pull the profile straight away so the UI has a name and avatar to show.
    # A failure here must not break sign-in — they're logged in either way.
    try:
        async with OpenDotaClient() as api:
            await upsert_player(session, account_id, await api.player(account_id))
    except Exception:  # noqa: BLE001 - profile is cosmetic, the session is not
        pass

    return RedirectResponse(f"{settings.public_base_url}/?login=ok", status_code=302)


@router.get("/me", response_model=CurrentUser)
async def me(
    account_id: CurrentAccount,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CurrentUser:
    player = await session.get(Player, account_id)
    return CurrentUser(
        account_id=account_id,
        steam_id64=str(account_id_to_steamid64(account_id)),
        persona_name=player.persona_name if player else None,
        avatar_url=player.avatar_url if player else None,
        last_synced_at=player.last_synced_at if player else None,
    )


@router.post("/logout")
async def logout(request: Request) -> dict[str, bool]:
    request.session.clear()
    return {"ok": True}
