"""Thin client for the (unofficial, undocumented) FPL API.

Every method returns the parsed JSON exactly as the API sends it. Turning that
into tables happens elsewhere, so this is the only file that has to change if
the API changes.
"""

import time

import requests

BASE_URL = "https://fantasy.premierleague.com/api"

# 503 is what the API returns while "the game is being updated" after matches.
RETRYABLE = {429, 500, 502, 503, 504}


class FPLClient:
    def __init__(self, min_interval: float = 0.5, timeout: float = 30, retries: int = 3):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "fpl-assistant (personal project)"
        self.min_interval = min_interval
        self.timeout = timeout
        self.retries = retries
        self._last_request = 0.0

    def get(self, path: str) -> dict | list:
        for attempt in range(self.retries):
            # The API is free and unofficial, so space requests out rather than hammer it.
            wait = self.min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            resp = self.session.get(f"{BASE_URL}/{path}", timeout=self.timeout)
            self._last_request = time.monotonic()
            if resp.status_code in RETRYABLE and attempt < self.retries - 1:
                time.sleep(5 * 2**attempt)  # back off: 5s, 10s, ...
                continue
            resp.raise_for_status()
            return resp.json()
        raise RuntimeError("unreachable")

    # Game-wide data
    def bootstrap(self) -> dict:
        """Players, teams, gameweeks, chips and game settings: the main endpoint."""
        return self.get("bootstrap-static/")

    def fixtures(self) -> list:
        return self.get("fixtures/")

    def element_summary(self, element_id: int) -> dict:
        """One player's per-gameweek history this season, upcoming fixtures and past seasons."""
        return self.get(f"element-summary/{element_id}/")

    # One manager's team (all public, no login needed)
    def entry(self, team_id: int) -> dict:
        return self.get(f"entry/{team_id}/")

    def entry_history(self, team_id: int) -> dict:
        """Per-gameweek points, bank, team value, transfers made and chips played."""
        return self.get(f"entry/{team_id}/history/")

    def entry_transfers(self, team_id: int) -> list:
        """Every transfer, including the price paid: needed to work out selling prices."""
        return self.get(f"entry/{team_id}/transfers/")

    def entry_picks(self, team_id: int, gameweek: int) -> dict:
        """The 15 players picked in a gameweek, with captaincy and bench order."""
        return self.get(f"entry/{team_id}/event/{gameweek}/picks/")
