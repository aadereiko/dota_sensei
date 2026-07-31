"""Item metadata cache.

Same deal as heroes: /constants/items is static within a patch, so it's stored
rather than refetched. Beyond the browse page, this is what will turn the numeric
ids in a purchase log into "Black King Bar at 14:32".
"""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Item
from app.services.opendota import OpenDotaClient


def _clean_notes(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


async def sync_items(session: AsyncSession, client: OpenDotaClient | None = None) -> int:
    """Fetch and upsert every item. Returns how many were written."""
    async with client or OpenDotaClient() as api:
        constants: dict[str, Any] = await api.item_constants()

    written = 0
    for key, raw in constants.items():
        item_id = raw.get("id")
        if item_id is None:
            continue
        values = {
            "id": item_id,
            "name": key,
            "localized_name": raw.get("dname") or key.replace("_", " ").title(),
            "cost": raw.get("cost"),
            "quality": raw.get("qual"),
            "tier": raw.get("tier"),
            # `created` means "built from a recipe", not "exists".
            "created": bool(raw.get("created")),
            "components": raw.get("components"),
            "notes": _clean_notes(raw.get("notes")),
            "img": raw.get("img"),
        }
        await session.execute(
            pg_insert(Item)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[Item.id],
                set_={k: v for k, v in values.items() if k != "id"},
            )
        )
        written += 1
    await session.flush()
    return written


async def ensure_items(session: AsyncSession, client: OpenDotaClient | None = None) -> None:
    """Populate the cache if it's empty. Cheap no-op once filled."""
    count = (await session.execute(select(func.count()).select_from(Item))).scalar_one()
    if count == 0:
        await sync_items(session, client)
