"""Command-line entry point: `fpl status`, `fpl snapshot`, ..."""

import argparse
import tomllib
from datetime import datetime, timezone
from pathlib import Path

from fpl.api import FPLClient
from fpl.season import chips_for_gameweek, gameweek_status, rules
from fpl.snapshot import save_snapshot
from fpl.state import load_team_state

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
CONFIG_PATH = PROJECT_ROOT / "fpl.toml"


def load_config() -> dict:
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def money(tenths: int) -> str:
    return f"£{tenths / 10:.1f}m"


def cmd_status(args: argparse.Namespace) -> None:
    bootstrap = FPLClient().bootstrap()
    gw = gameweek_status(bootstrap)
    r = rules(bootstrap)

    if gw.current:
        state = "finished" if gw.current_finished else "in progress"
        print(f"Gameweek {gw.current}: {state}")
    if gw.next:
        local = gw.next_deadline.astimezone()  # convert UTC to this machine's timezone
        left = gw.next_deadline - datetime.now(timezone.utc)
        hours, rem = divmod(int(left.total_seconds()), 3600)
        print(f"Next: Gameweek {gw.next}, deadline {local:%a %d %b %H:%M %Z} (in {hours}h {rem // 60}m)")
        chips = chips_for_gameweek(bootstrap, gw.next)
        print(f"Chip windows open for GW{gw.next}: " + ", ".join(
            f"{c.name} (until GW{c.stop_event})" for c in chips
        ))
    print(
        f"Rules: {r.squad_size}-man squad, max {r.max_per_club} per club, "
        f"£{r.budget:.1f}m budget, bank up to {r.max_banked_free_transfers} free transfers"
    )


def cmd_team(args: argparse.Namespace) -> None:
    team_id = args.id or load_config()["team_id"]
    s = load_team_state(FPLClient(), team_id)

    print(f"{s.team_name}: going into GW{s.gameweek}")
    print(f"Bank {money(s.bank)} · Free transfers {s.free_transfers} · Budget if you sold everything {money(s.budget)}")
    print("Chips available: " + (", ".join(s.chips_available) or "none"))
    if s.chips_used:
        print("Chips used: " + ", ".join(f"{chip} (GW{gw})" for chip, gw in s.chips_used))
    print()
    print(f"{'Pos':<4} {'Player':<16} {'Club':<5} {'Paid':>7} {'Now':>7} {'Sell':>7}  Flag")
    for i, p in enumerate(s.squad):
        if i == 11:
            print("---- bench")
        flag = f"{p.chance_of_playing}% · {p.news}" if p.news and p.chance_of_playing is not None else p.news
        print(
            f"{p.position:<4} {p.name:<16} {p.club:<5} {money(p.purchase_price):>7} "
            f"{money(p.current_price):>7} {money(p.selling_price):>7}  {flag}"
        )


def cmd_snapshot(args: argparse.Namespace) -> None:
    for path in save_snapshot(FPLClient(), DATA_DIR / "snapshots"):
        print(f"saved {path.relative_to(PROJECT_ROOT)} ({path.stat().st_size / 1e3:.0f} kB)")


def main() -> None:
    parser = argparse.ArgumentParser(prog="fpl", description="FPL prediction assistant")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="current gameweek, next deadline, chip windows, rules").set_defaults(func=cmd_status)
    team = sub.add_parser("team", help="your squad, bank, selling prices, free transfers and chips")
    team.add_argument("--id", type=int, help="FPL team ID (default: team_id in fpl.toml)")
    team.set_defaults(func=cmd_team)
    sub.add_parser("snapshot", help="archive today's bootstrap and fixtures").set_defaults(func=cmd_snapshot)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
