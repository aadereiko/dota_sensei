"""Steam OpenID: id conversion, claimed_id parsing, and callback verification.

The verification tests matter most — everything downstream trusts the account id
that comes out of `verify_callback`.
"""

import httpx
import pytest

from app.services.steam import (
    account_id_to_steamid64,
    build_login_url,
    parse_claimed_id,
    steamid64_to_account_id,
    verify_callback,
)

# Dendi's public profile: steamid64 76561198030654385 -> account 70388657.
STEAMID64 = 76561198030654385
ACCOUNT_ID = 70388657


def signed_params(**overrides: str) -> dict[str, str]:
    params = {
        "openid.mode": "id_res",
        "openid.signed": (
            "signed,op_endpoint,claimed_id,identity,return_to,response_nonce,assoc_handle"
        ),
        "openid.claimed_id": f"https://steamcommunity.com/openid/id/{STEAMID64}",
        "openid.identity": f"https://steamcommunity.com/openid/id/{STEAMID64}",
        "openid.sig": "fake-signature",
    }
    params.update(overrides)
    return params


def client_returning(body: str) -> httpx.AsyncClient:
    transport = httpx.MockTransport(lambda _request: httpx.Response(200, text=body))
    return httpx.AsyncClient(transport=transport)


def test_steamid_round_trip() -> None:
    assert steamid64_to_account_id(STEAMID64) == ACCOUNT_ID
    assert account_id_to_steamid64(ACCOUNT_ID) == STEAMID64


def test_parse_claimed_id() -> None:
    assert parse_claimed_id(f"https://steamcommunity.com/openid/id/{STEAMID64}") == STEAMID64
    assert parse_claimed_id("https://evil.example.com/openid/id/76561198030654385") is None
    assert parse_claimed_id("https://steamcommunity.com/openid/id/nope") is None
    assert parse_claimed_id("") is None


def test_login_url_carries_return_to_and_realm() -> None:
    url = build_login_url("http://localhost:5273/api/auth/steam/callback", "http://localhost:5273")
    assert url.startswith("https://steamcommunity.com/openid/login?")
    assert "openid.mode=checkid_setup" in url
    assert "openid.return_to=http%3A%2F%2Flocalhost%3A5273%2Fapi%2Fauth%2Fsteam%2Fcallback" in url


async def test_verified_response_yields_steamid() -> None:
    async with client_returning("ns:http://specs.openid.net/auth/2.0\nis_valid:true\n") as client:
        assert await verify_callback(signed_params(), client) == STEAMID64


async def test_steam_saying_invalid_is_rejected() -> None:
    async with client_returning("is_valid:false\n") as client:
        assert await verify_callback(signed_params(), client) is None


async def test_claimed_id_must_be_covered_by_the_signature() -> None:
    """The core attack: a valid signature over fields that exclude the identity."""
    params = signed_params(**{"openid.signed": "return_to,response_nonce,assoc_handle"})
    async with client_returning("is_valid:true\n") as client:
        assert await verify_callback(params, client) is None


async def test_non_steam_claimed_id_is_rejected() -> None:
    params = signed_params(
        **{"openid.claimed_id": f"https://evil.example.com/openid/id/{STEAMID64}"}
    )
    async with client_returning("is_valid:true\n") as client:
        assert await verify_callback(params, client) is None


async def test_wrong_mode_is_rejected() -> None:
    params = signed_params(**{"openid.mode": "cancel"})
    async with client_returning("is_valid:true\n") as client:
        assert await verify_callback(params, client) is None


@pytest.mark.parametrize("body", ["", "is_valid:true-ish", "nonsense"])
async def test_garbage_verification_body_is_rejected(body: str) -> None:
    async with client_returning(body) as client:
        assert await verify_callback(signed_params(), client) is None
