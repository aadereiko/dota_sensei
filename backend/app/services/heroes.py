"""Hero metadata cache.

OpenDota's /constants/heroes is static within a patch, so it's fetched once and
stored rather than pulled per request. Beyond showing names instead of ids, the
`roles` field is what lets the analysis rules tell a support from a core on an
*unparsed* match, where `lane_role` is null.
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Hero
from app.services.opendota import OpenDotaClient

# OpenDota returns CDN-relative paths like /apps/dota2/images/.../rubick.png?
HERO_IMAGE_BASE = "https://cdn.cloudflare.steamstatic.com"


def hero_image_url(path: str | None) -> str | None:
    if not path:
        return None
    return f"{HERO_IMAGE_BASE}{path.rstrip('?')}"


async def sync_heroes(session: AsyncSession, client: OpenDotaClient | None = None) -> int:
    """Fetch and upsert every hero. Returns how many were written."""
    async with client or OpenDotaClient() as api:
        constants: dict[str, Any] = await api.hero_constants()

    written = 0
    for raw in constants.values():
        hero_id = raw.get("id")
        if hero_id is None:
            continue
        values = {
            "id": hero_id,
            "name": raw.get("name") or "",
            "localized_name": raw.get("localized_name") or f"Hero {hero_id}",
            "primary_attr": raw.get("primary_attr"),
            "attack_type": raw.get("attack_type"),
            "roles": raw.get("roles") or [],
            "img": raw.get("img"),
            "icon": raw.get("icon"),
        }
        await session.execute(
            pg_insert(Hero)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[Hero.id],
                set_={k: v for k, v in values.items() if k != "id"},
            )
        )
        written += 1
    await session.flush()
    return written


async def ensure_heroes(session: AsyncSession, client: OpenDotaClient | None = None) -> None:
    """Populate the cache if it's empty. Cheap no-op once filled."""
    count = (await session.execute(select(func.count()).select_from(Hero))).scalar_one()
    if count == 0:
        await sync_heroes(session, client)


async def hero_map(session: AsyncSession) -> dict[int, Hero]:
    heroes = (await session.execute(select(Hero))).scalars().all()
    return {hero.id: hero for hero in heroes}
