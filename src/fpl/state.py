"""Your team's state going into the next deadline, rebuilt from public data.

The rules live in small pure functions (selling_price, free_transfers, ...)
that take plain data and return answers, so they can be tested without the
network. load_team_state is the only part that talks to the API.

Public endpoints only show what was locked in at the last deadline: transfers
you've already made for the upcoming gameweek won't appear until it passes.

Money is kept in tenths of £m as integers, like the API (now_cost 156 = £15.6m).
Floats can't store 0.1 exactly, and selling prices round down to the nearest
£0.1m, so integers keep that arithmetic exact.
"""

import math
from dataclasses import dataclass

from fpl.api import FPLClient
from fpl.season import chips_for_gameweek, gameweek_status, rules

CHIPS_THAT_KEEP_FREE_TRANSFERS = {"wildcard", "freehit"}


@dataclass
class SquadPlayer:
    element: int  # this season's player id
    name: str
    position: str  # GKP, DEF, MID or FWD
    club: str
    purchase_price: int  # tenths of £m
    current_price: int
    selling_price: int
    chance_of_playing: int | None  # None means no flag
    news: str


@dataclass
class TeamState:
    team_id: int
    team_name: str
    gameweek: int  # the deadline this state is for
    squad: list[SquadPlayer]  # last lineup's order: XI first, then bench
    bank: int  # tenths of £m
    free_transfers: int
    chips_available: list[str]
    chips_used: list[tuple[str, int]]  # (chip, gameweek played)

    @property
    def budget(self) -> int:
        """What you could actually spend on a full rebuild: bank plus selling prices."""
        return self.bank + sum(p.selling_price for p in self.squad)


def selling_price(purchase: int, current: int, sell_on_fee: float = 0.5) -> int:
    """Losses are passed on in full; FPL keeps a share of any profit, rounded down."""
    if current <= purchase:
        return current
    return purchase + math.floor((current - purchase) * (1 - sell_on_fee))


def free_transfers(history: list[dict], chip_events: dict[int, str], started_event: int, max_ft: int) -> int:
    """Free transfers for the gameweek after the last one in `history`.

    Replays the rules week by week:
      - the squad you start with is free, then you get 1 FT
      - unused FTs roll over, +1 each gameweek, capped at max_ft
      - taking a hit uses up everything, so you roll over 0
      - Wildcard / Free Hit transfers are free: you keep your saved FTs,
        but don't get the usual +1 that week
    """
    ft = 0
    for row in sorted(history, key=lambda r: r["event"]):
        gw = row["event"]
        if gw == started_event:
            ft = 1
        elif chip_events.get(gw) in CHIPS_THAT_KEEP_FREE_TRANSFERS:
            continue
        else:
            ft = min(max(ft - row["event_transfers"], 0) + 1, max_ft)
    return ft


def purchase_prices(
    squad: list[int], transfers: list[dict], freehit_events: set[int], start_prices: dict[int, int]
) -> dict[int, int]:
    """What you paid for each player you own.

    Your latest transfer in of a player is the price you paid. Free Hit
    transfers are skipped because the squad reverts afterwards. A player you
    never transferred in was in your original squad, bought at the start price.
    """
    paid = {}
    for t in sorted(transfers, key=lambda t: t["time"]):
        if t["event"] not in freehit_events:
            paid[t["element_in"]] = t["element_in_cost"]
    return {el: paid.get(el, start_prices[el]) for el in squad}


def chips_available(chips_used: list[dict], open_windows: list) -> list[str]:
    """Chip windows open this gameweek that you haven't already used a chip from."""
    return [
        w.name
        for w in open_windows
        if not any(c["name"] == w.key and w.start_event <= c["event"] <= w.stop_event for c in chips_used)
    ]


def load_team_state(client: FPLClient, team_id: int) -> TeamState:
    bootstrap = client.bootstrap()
    entry = client.entry(team_id)
    history = client.entry_history(team_id)
    transfers = client.entry_transfers(team_id)

    r = rules(bootstrap)
    next_gw = gameweek_status(bootstrap).next
    chip_events = {c["event"]: c["name"] for c in history["chips"]}

    # The last deadline that has passed. After a Free Hit, the squad and bank
    # revert to the week before, so that's the squad you actually own.
    last_gw = history["current"][-1]["event"]
    squad_gw = last_gw - 1 if chip_events.get(last_gw) == "freehit" else last_gw
    # Keep the last lineup's order: starting XI in positions 1-11, then the bench.
    picks = sorted(client.entry_picks(team_id, squad_gw)["picks"], key=lambda p: p["position"])
    bank = next(row["bank"] for row in history["current"] if row["event"] == squad_gw)

    players = {p["id"]: p for p in bootstrap["elements"]}
    clubs = {t["id"]: t["short_name"] for t in bootstrap["teams"]}
    positions = {t["id"]: t["singular_name_short"] for t in bootstrap["element_types"]}

    squad_ids = [p["element"] for p in picks]
    # Prices only start moving after the GW1 deadline, so today's price minus
    # the change since the start is what you paid pre-season. (Managers who
    # joined later would need the price at their first deadline instead.)
    start_prices = {el: players[el]["now_cost"] - players[el]["cost_change_start"] for el in squad_ids}
    freehit_events = {gw for gw, chip in chip_events.items() if chip == "freehit"}
    paid = purchase_prices(squad_ids, transfers, freehit_events, start_prices)

    squad = []
    for el in squad_ids:
        p = players[el]
        squad.append(SquadPlayer(
            element=el,
            name=p["web_name"],
            position=positions[p["element_type"]],
            club=clubs[p["team"]],
            purchase_price=paid[el],
            current_price=p["now_cost"],
            selling_price=selling_price(paid[el], p["now_cost"], r.sell_on_fee),
            chance_of_playing=p["chance_of_playing_next_round"],
            news=p["news"],
        ))

    return TeamState(
        team_id=team_id,
        team_name=entry["name"],
        gameweek=next_gw,
        squad=squad,
        bank=bank,
        free_transfers=free_transfers(history["current"], chip_events, entry["started_event"], r.max_banked_free_transfers),
        chips_available=chips_available(history["chips"], chips_for_gameweek(bootstrap, next_gw)),
        chips_used=[(c["name"], c["event"]) for c in history["chips"]],
    )
