"""Turn OpenDota's raw `objectives` log into readable match events.

The raw entries look like:

    {"time": 140, "type": "CHAT_MESSAGE_FIRSTBLOOD", "player_slot": 0}
    {"time": 721, "type": "building_kill", "key": "npc_dota_badguys_tower1_top",
     "unit": "npc_dota_hero_lycan", "player_slot": 4}

Mapping happens on read rather than at ingest, so improving the wording doesn't
require re-fetching every match.
"""

import re
from typing import Any

# OpenDota team codes inside objectives.
RADIANT, DIRE = 2, 3

BUILDING_RE = re.compile(
    r"npc_dota_(?P<side>goodguys|badguys)_(?P<kind>tower\d|melee_rax|range_rax|fort|healers)"
    r"(?:_(?P<lane>top|mid|bot))?"
)

KIND_LABELS = {
    "melee_rax": "melee barracks",
    "range_rax": "ranged barracks",
    "fort": "ancient",
    "healers": "shrine",
}


def _side_of(side: str) -> str:
    """`goodguys` buildings belong to Radiant, `badguys` to Dire."""
    return "radiant" if side == "goodguys" else "dire"


def _other(team: str) -> str:
    return "dire" if team == "radiant" else "radiant"


def _building_label(key: str) -> tuple[str, str] | None:
    """(label, owning team) for a destroyed building, or None if unrecognised."""
    match = BUILDING_RE.match(key or "")
    if not match:
        return None
    owner = _side_of(match["side"])
    kind = match["kind"]
    label = KIND_LABELS.get(kind, kind.replace("tower", "tier ") + " tower")
    if match["lane"]:
        label = f"{label} ({match['lane']})"
    return label, owner


def build_events(
    objectives: list[dict[str, Any]] | None,
    hero_by_slot: dict[int, str],
) -> list[dict[str, Any]]:
    """Readable, time-ordered events. Unknown objective types are dropped."""
    events: list[dict[str, Any]] = []

    for raw in objectives or []:
        kind = raw.get("type")
        time = raw.get("time")
        if time is None:
            continue
        slot = raw.get("player_slot")
        hero = hero_by_slot.get(slot) if slot is not None else None
        team = None if slot is None else ("radiant" if slot < 128 else "dire")

        if kind == "CHAT_MESSAGE_FIRSTBLOOD":
            events.append(
                {
                    "time": time,
                    "kind": "first_blood",
                    "team": team,
                    "label": f"First blood{f' — {hero}' if hero else ''}",
                }
            )
        elif kind == "building_kill":
            parsed = _building_label(raw.get("key", ""))
            if parsed is None:
                continue
            label, owner = parsed
            events.append(
                {
                    "time": time,
                    # The ancient falling is the game ending, not a routine push.
                    "kind": "throne" if "ancient" in label else "building",
                    # Credit the team that destroyed it, not the one that lost it.
                    "team": _other(owner),
                    "label": f"{owner.title()} {label} destroyed",
                }
            )
        elif kind == "CHAT_MESSAGE_ROSHAN_KILL":
            killer = raw.get("team")
            side = "radiant" if killer == RADIANT else "dire" if killer == DIRE else None
            events.append(
                {
                    "time": time,
                    "kind": "roshan",
                    "team": side,
                    "label": f"Roshan killed{f' by {side.title()}' if side else ''}",
                }
            )
        elif kind == "CHAT_MESSAGE_AEGIS":
            events.append(
                {
                    "time": time,
                    "kind": "aegis",
                    "team": team,
                    "label": f"Aegis picked up{f' by {hero}' if hero else ''}",
                }
            )
        elif kind in ("CHAT_MESSAGE_AEGIS_STOLEN", "CHAT_MESSAGE_DENIED_AEGIS"):
            events.append(
                {
                    "time": time,
                    "kind": "aegis",
                    "team": team,
                    "label": (
                        f"Aegis {'stolen' if 'STOLEN' in kind else 'denied'}"
                        f"{f' by {hero}' if hero else ''}"
                    ),
                }
            )

    events.sort(key=lambda e: e["time"])
    return events
