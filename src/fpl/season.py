"""Where are we in the season, and what are the rules?

Everything here is read from bootstrap-static rather than hard-coded, so when
FPL changes a rule (chip windows, how many free transfers you can bank) the
code picks it up without edits.
"""

from dataclasses import dataclass
from datetime import datetime

CHIP_NAMES = {
    "wildcard": "Wildcard",
    "freehit": "Free Hit",
    "bboost": "Bench Boost",
    "3xc": "Triple Captain",
}


@dataclass
class GameweekStatus:
    current: int | None  # latest GW whose deadline has passed (None before GW1)
    current_finished: bool  # all of its matches played and points confirmed
    next: int | None  # next GW you can still make moves for (None after GW38)
    next_deadline: datetime | None  # timezone-aware, UTC


@dataclass
class ChipWindow:
    key: str  # the API's name: "wildcard", "freehit", "bboost", "3xc"
    start_event: int
    stop_event: int

    @property
    def name(self) -> str:
        return CHIP_NAMES.get(self.key, self.key)


@dataclass
class Rules:
    squad_size: int
    max_per_club: int
    budget: float  # in £m
    max_banked_free_transfers: int
    sell_on_fee: float  # share of a price rise FPL keeps when you sell


def gameweek_status(bootstrap: dict) -> GameweekStatus:
    events = bootstrap["events"]
    current = next((e for e in events if e["is_current"]), None)
    upcoming = next((e for e in events if e["is_next"]), None)
    return GameweekStatus(
        current=current["id"] if current else None,
        current_finished=bool(current and current["finished"]),
        next=upcoming["id"] if upcoming else None,
        next_deadline=datetime.fromisoformat(upcoming["deadline_time"]) if upcoming else None,
    )


def chip_windows(bootstrap: dict) -> list[ChipWindow]:
    return [ChipWindow(c["name"], c["start_event"], c["stop_event"]) for c in bootstrap["chips"]]


def chips_for_gameweek(bootstrap: dict, gameweek: int) -> list[ChipWindow]:
    """Chip windows that are open in a given gameweek (ignores whether you've used them)."""
    return [w for w in chip_windows(bootstrap) if w.start_event <= gameweek <= w.stop_event]


def rules(bootstrap: dict) -> Rules:
    s = bootstrap["game_settings"]
    return Rules(
        squad_size=s["squad_squadsize"],
        max_per_club=s["squad_team_limit"],
        budget=s["squad_total_spend"] / 10,  # the API stores money in tenths of a million
        # "extra" free transfers on top of the 1 you get each week
        max_banked_free_transfers=1 + s["max_extra_free_transfers"],
        sell_on_fee=s["transfers_sell_on_fee"],
    )
