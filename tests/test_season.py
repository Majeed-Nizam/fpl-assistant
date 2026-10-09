"""Tests use small hand-built inputs, not the live API, so they're fast and never
break because of the network or because the real season moved on."""

from fpl.season import chips_for_gameweek, gameweek_status, rules


def make_bootstrap(current=None, next_=None, finished=True):
    events = [
        {
            "id": gw,
            "deadline_time": f"2026-08-{10 + gw:02d}T10:00:00Z",
            "is_current": gw == current,
            "is_next": gw == next_,
            "finished": finished if gw == current else gw < (current or 0),
        }
        for gw in range(1, 39)
    ]
    chips = [
        {"name": "wildcard", "start_event": 2, "stop_event": 19},
        {"name": "wildcard", "start_event": 20, "stop_event": 38},
        {"name": "bboost", "start_event": 1, "stop_event": 19},
        {"name": "bboost", "start_event": 20, "stop_event": 38},
    ]
    settings = {
        "squad_squadsize": 15,
        "squad_team_limit": 3,
        "squad_total_spend": 1000,
        "max_extra_free_transfers": 4,
        "transfers_sell_on_fee": 0.5,
    }
    return {"events": events, "chips": chips, "game_settings": settings}


def test_mid_season():
    gw = gameweek_status(make_bootstrap(current=5, next_=6))
    assert (gw.current, gw.next, gw.current_finished) == (5, 6, True)
    assert gw.next_deadline.tzinfo is not None


def test_gameweek_still_being_played():
    assert gameweek_status(make_bootstrap(current=5, next_=6, finished=False)).current_finished is False


def test_preseason_has_no_current_gameweek():
    gw = gameweek_status(make_bootstrap(current=None, next_=1))
    assert gw.current is None and gw.next == 1


def test_end_of_season_has_no_next_gameweek():
    gw = gameweek_status(make_bootstrap(current=38, next_=None))
    assert gw.next is None and gw.next_deadline is None


def test_chip_windows_switch_at_halfway():
    bootstrap = make_bootstrap()
    assert {(c.name, c.stop_event) for c in chips_for_gameweek(bootstrap, 19)} == {("Wildcard", 19), ("Bench Boost", 19)}
    assert {(c.name, c.stop_event) for c in chips_for_gameweek(bootstrap, 20)} == {("Wildcard", 38), ("Bench Boost", 38)}


def test_first_wildcard_not_available_in_gw1():
    names = [c.name for c in chips_for_gameweek(make_bootstrap(), 1)]
    assert "Wildcard" not in names and "Bench Boost" in names


def test_rules():
    r = rules(make_bootstrap())
    assert r.budget == 100.0 and r.max_banked_free_transfers == 5
