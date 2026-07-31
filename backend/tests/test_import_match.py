"""Slot resolution for `POST /api/matches/import`.

The tricky part isn't fetching the match, it's deciding which of the ten players
is the user — precisely because the case this feature exists for is the one where
OpenDota anonymised them.
"""

from app.services.ingest import resolve_slot

ME = 1202629804
SOMEONE_ELSE = 70388657


def players(*slots: tuple[int, int | None]) -> list[dict[str, object]]:
    """(player_slot, account_id) pairs -> the shape OpenDota returns."""
    return [
        {"player_slot": slot, "account_id": account, "hero_id": 10 + i}
        for i, (slot, account) in enumerate(slots)
    ]


def test_identified_account_is_found_automatically() -> None:
    chosen = resolve_slot(players((0, SOMEONE_ELSE), (1, ME), (128, None)), ME, None)
    assert chosen is not None
    assert chosen["player_slot"] == 1


def test_anonymous_account_cannot_be_guessed() -> None:
    """The whole reason the endpoint takes a player_slot."""
    assert resolve_slot(players((0, SOMEONE_ELSE), (1, None), (128, None)), ME, None) is None


def test_explicit_slot_wins() -> None:
    chosen = resolve_slot(players((0, SOMEONE_ELSE), (1, None)), ME, player_slot=1)
    assert chosen is not None
    assert chosen["account_id"] is None


def test_explicit_slot_that_does_not_exist() -> None:
    assert resolve_slot(players((0, None), (1, None)), ME, player_slot=99) is None


def test_no_match_for_account() -> None:
    assert resolve_slot(players((0, SOMEONE_ELSE), (128, None)), ME, None) is None


def test_slot_zero_is_not_treated_as_absent() -> None:
    """player_slot 0 is a real slot; a falsy check here would break radiant safelane."""
    chosen = resolve_slot(players((0, None), (1, None)), ME, player_slot=0)
    assert chosen is not None
    assert chosen["player_slot"] == 0
