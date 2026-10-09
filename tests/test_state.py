from fpl.season import ChipWindow
from fpl.state import chips_available, free_transfers, purchase_prices, selling_price


def gw(event, transfers=0):
    return {"event": event, "event_transfers": transfers}


# Selling prices (all in tenths of £m)

def test_price_drop_passed_on_in_full():
    assert selling_price(purchase=80, current=77) == 77


def test_half_of_profit_kept_rounded_down():
    assert selling_price(purchase=80, current=83) == 81  # +0.3 rise -> you get +0.1
    assert selling_price(purchase=80, current=84) == 82


def test_single_rise_gives_no_profit():
    assert selling_price(purchase=80, current=81) == 80


# Free transfers

def test_rollover_from_gw1():
    # Matches the real team: 0,0 then 3 transfers in GW4, 0 in GW5 -> 2 FTs for GW6
    history = [gw(1), gw(2), gw(3), gw(4, transfers=3), gw(5)]
    assert free_transfers(history, {}, started_event=1, max_ft=5) == 2


def test_capped_at_max():
    history = [gw(e) for e in range(1, 10)]
    assert free_transfers(history, {}, started_event=1, max_ft=5) == 5


def test_hit_leaves_one_for_next_week():
    history = [gw(1), gw(2, transfers=3)]  # 1 FT, made 3 (a -8 hit)
    assert free_transfers(history, {}, started_event=1, max_ft=5) == 1


def test_wildcard_keeps_saved_transfers_without_the_weekly_one():
    history = [gw(1), gw(2), gw(3, transfers=11)]  # 2 FTs saved, wildcard in GW3
    assert free_transfers(history, {3: "wildcard"}, started_event=1, max_ft=5) == 2


def test_late_joiner_starts_from_their_first_gameweek():
    history = [gw(7, transfers=0), gw(8)]
    assert free_transfers(history, {}, started_event=7, max_ft=5) == 2


# Purchase prices

def test_latest_transfer_in_is_the_purchase_price():
    transfers = [
        {"element_in": 10, "element_in_cost": 60, "event": 2, "time": "2026-08-20T10:00:00Z"},
        {"element_in": 10, "element_in_cost": 65, "event": 5, "time": "2026-09-18T10:00:00Z"},
    ]
    assert purchase_prices([10], transfers, set(), {10: 55}) == {10: 65}


def test_original_squad_bought_at_start_price():
    assert purchase_prices([10], [], set(), {10: 55}) == {10: 55}


def test_free_hit_transfers_ignored():
    transfers = [{"element_in": 10, "element_in_cost": 70, "event": 4, "time": "2026-09-12T10:00:00Z"}]
    assert purchase_prices([10], transfers, {4}, {10: 55}) == {10: 55}


# Chips

def test_used_chip_only_closes_its_own_half():
    windows = [ChipWindow("wildcard", 2, 19), ChipWindow("bboost", 1, 19)]
    used = [{"name": "wildcard", "event": 4}]
    assert chips_available(used, windows) == ["Bench Boost"]
    second_half = [ChipWindow("wildcard", 20, 38)]
    assert chips_available(used, second_half) == ["Wildcard"]
