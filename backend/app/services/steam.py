"""Steam sign-in via OpenID 2.0.

Steam is an OpenID *provider*, so there is no app registration and no API key —
you redirect the user to Steam, they come back with signed parameters, and you
ask Steam to confirm the signature.

    build_login_url()      -> where to send the browser
    verify_callback(params) -> the verified SteamID64, or None

The only thing Steam tells us is the SteamID64. `account_id` (what OpenDota and
the Dota client call your account) is its low 32 bits.
"""

import re
from collections.abc import Mapping

import httpx

STEAM_OPENID_ENDPOINT = "https://steamcommunity.com/openid/login"
OPENID_NS = "http://specs.openid.net/auth/2.0"
IDENTIFIER_SELECT = "http://specs.openid.net/auth/2.0/identifier_select"

# Steam returns the identity as https://steamcommunity.com/openid/id/<steamid64>.
CLAIMED_ID_RE = re.compile(r"^https?://steamcommunity\.com/openid/id/(\d{17})$")

# SteamID64 = STEAM_ID64_BASE + account_id, for individual accounts.
STEAM_ID64_BASE = 76561197960265728


def steamid64_to_account_id(steamid64: int) -> int:
    """The 32-bit account id OpenDota and Dotabuff use."""
    return steamid64 - STEAM_ID64_BASE


def account_id_to_steamid64(account_id: int) -> int:
    return account_id + STEAM_ID64_BASE


def build_login_url(return_to: str, realm: str) -> str:
    """The URL to redirect the browser to in order to start sign-in.

    `realm` must be a prefix of `return_to` or Steam rejects the request.
    """
    params = {
        "openid.ns": OPENID_NS,
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": realm,
        # We don't know who they are yet — let Steam pick the identity.
        "openid.identity": IDENTIFIER_SELECT,
        "openid.claimed_id": IDENTIFIER_SELECT,
    }
    return f"{STEAM_OPENID_ENDPOINT}?{httpx.QueryParams(params)}"


def parse_claimed_id(claimed_id: str) -> int | None:
    match = CLAIMED_ID_RE.match(claimed_id or "")
    return int(match.group(1)) if match else None


def _signature_covers_identity(params: Mapping[str, str]) -> bool:
    """Reject a response whose claimed_id wasn't part of what Steam signed.

    Without this check an attacker could keep a valid signature over some other
    subset of fields and swap in any SteamID they liked.
    """
    signed = (params.get("openid.signed") or "").split(",")
    return "claimed_id" in signed and "identity" in signed


async def verify_callback(
    params: Mapping[str, str], client: httpx.AsyncClient | None = None
) -> int | None:
    """Ask Steam to confirm the parameters it just sent us. Returns SteamID64.

    Returns None for anything that doesn't check out — never trust `claimed_id`
    before this call succeeds.
    """
    if params.get("openid.mode") != "id_res":
        return None
    if not _signature_covers_identity(params):
        return None

    steamid64 = parse_claimed_id(params.get("openid.claimed_id", ""))
    if steamid64 is None:
        return None

    # Echo every openid.* field back, with mode swapped to check_authentication.
    payload = {k: v for k, v in params.items() if k.startswith("openid.")}
    payload["openid.mode"] = "check_authentication"

    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=15.0)
    try:
        response = await client.post(STEAM_OPENID_ENDPOINT, data=payload)
        response.raise_for_status()
        verified = any(
            line.strip() == "is_valid:true" for line in response.text.splitlines()
        )
    finally:
        if owns_client:
            await client.aclose()

    return steamid64 if verified else None
