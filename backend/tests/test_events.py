"""Objective log -> readable events.

The subtle part is attribution: `npc_dota_goodguys_tower1_top` is a *Radiant*
building, so its destruction is a *Dire* achievement. Getting that backwards
would invert every push in the timeline.
"""

from app.services.events import build_events

HEROES = {0: "Lycan", 4: "Clinkz", 129: "Undying"}


def test_building_ownership_is_not_the_credited_team() -> None:
    events = build_events(
        [{"time": 721, "type": "building_kill", "key": "npc_dota_badguys_tower1_top"}],
        HEROES,
    )
    assert len(events) == 1
    assert events[0]["label"] == "Dire tier 1 tower (top) destroyed"
    # Dire lost it, so Radiant did it.
    assert events[0]["team"] == "radiant"


def test_radiant_building_credits_dire() -> None:
    events = build_events(
        [{"time": 768, "type": "building_kill", "key": "npc_dota_goodguys_tower1_top"}],
        HEROES,
    )
    assert events[0]["label"] == "Radiant tier 1 tower (top) destroyed"
    assert events[0]["team"] == "dire"


def test_barracks_and_ancient_get_their_own_wording() -> None:
    events = build_events(
        [
            {"time": 1800, "type": "building_kill", "key": "npc_dota_badguys_melee_rax_mid"},
            {"time": 2400, "type": "building_kill", "key": "npc_dota_goodguys_fort"},
        ],
        HEROES,
    )
    assert "melee barracks (mid)" in events[0]["label"]
    assert events[1]["kind"] == "throne"
    assert "ancient" in events[1]["label"]


def test_first_blood_names_the_hero() -> None:
    events = build_events(
        [{"time": 140, "type": "CHAT_MESSAGE_FIRSTBLOOD", "player_slot": 4}], HEROES
    )
    assert events[0]["kind"] == "first_blood"
    assert events[0]["label"] == "First blood — Clinkz"
    assert events[0]["team"] == "radiant"


def test_dire_player_slot_maps_to_dire() -> None:
    events = build_events(
        [{"time": 140, "type": "CHAT_MESSAGE_FIRSTBLOOD", "player_slot": 129}], HEROES
    )
    assert events[0]["team"] == "dire"


def test_roshan_uses_the_team_code_not_a_slot() -> None:
    events = build_events(
        [
            {"time": 900, "type": "CHAT_MESSAGE_ROSHAN_KILL", "team": 2},
            {"time": 1900, "type": "CHAT_MESSAGE_ROSHAN_KILL", "team": 3},
        ],
        HEROES,
    )
    assert events[0]["team"] == "radiant"
    assert events[1]["team"] == "dire"


def test_events_are_time_ordered_and_unknowns_dropped() -> None:
    events = build_events(
        [
            {"time": 900, "type": "CHAT_MESSAGE_ROSHAN_KILL", "team": 2},
            {"time": 140, "type": "CHAT_MESSAGE_FIRSTBLOOD", "player_slot": 0},
            {"time": 300, "type": "CHAT_MESSAGE_SOMETHING_NEW"},
            {"time": 400, "type": "building_kill", "key": "npc_dota_unrecognised"},
        ],
        HEROES,
    )
    assert [e["time"] for e in events] == [140, 900]


def test_empty_input_is_fine() -> None:
    assert build_events(None, {}) == []
    assert build_events([], {}) == []
