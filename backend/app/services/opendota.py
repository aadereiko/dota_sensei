"""Thin async client for the OpenDota public API.

Docs: https://docs.opendota.com/
Rate limit without a key: 60 calls/min, 2000/day.
"""

from typing import Any

import httpx

from app.config import get_settings


class OpenDotaClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        settings = get_settings()
        self._base_url = settings.opendota_base_url
        self._api_key = settings.opendota_api_key
        self._owns_client = client is None
        self._client = client or httpx.AsyncClient(
            base_url=self._base_url,
            timeout=settings.opendota_timeout_seconds,
        )

    async def __aenter__(self) -> "OpenDotaClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get(self, path: str, **params: Any) -> Any:
        if self._api_key:
            params["api_key"] = self._api_key
        response = await self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    # --- Endpoints we actually use ---

    async def player(self, account_id: int) -> dict[str, Any]:
        """Profile, rank_tier, mmr_estimate."""
        return await self._get(f"/players/{account_id}")

    async def recent_matches(self, account_id: int, limit: int = 20) -> list[dict[str, Any]]:
        """Summary rows — cheap, one call for many matches."""
        return await self._get(f"/players/{account_id}/matches", limit=limit)

    async def match(self, match_id: int) -> dict[str, Any]:
        """Full match: all 10 players, per-minute series, purchase log, benchmarks."""
        return await self._get(f"/matches/{match_id}")

    async def hero_stats(self) -> list[dict[str, Any]]:
        """Hero metadata + per-bracket win rates. Cache this; it changes per patch."""
        return await self._get("/heroStats")

    async def hero_constants(self) -> dict[str, Any]:
        """Hero id -> name, roles, images. Static within a patch."""
        return await self._get("/constants/heroes")

    async def request_parse(self, match_id: int) -> dict[str, Any]:
        """Ask OpenDota to parse a replay. Needed for timeline-level detail."""
        response = await self._client.post(f"/request/{match_id}")
        response.raise_for_status()
        return response.json()
