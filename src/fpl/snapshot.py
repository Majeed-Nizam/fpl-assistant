"""Archive the parts of the API that get overwritten.

bootstrap-static only ever shows the *current* prices, injury flags, news and
ownership. Once they change the old values are gone for good, so every run
saves a timestamped, gzipped copy. A few weeks of these is what the minutes
and news models will learn from later.
"""

import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

from fpl.api import FPLClient


def save_snapshot(client: FPLClient, out_dir: Path) -> list[Path]:
    now = datetime.now(timezone.utc)
    folder = out_dir / now.strftime("%Y-%m-%d")
    folder.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%H%M%S")

    saved = []
    for name, payload in (("bootstrap", client.bootstrap()), ("fixtures", client.fixtures())):
        path = folder / f"{name}_{stamp}.json.gz"
        with gzip.open(path, "wt", encoding="utf-8") as f:
            json.dump(payload, f)
        saved.append(path)
    return saved


def load_snapshot(path: Path) -> dict | list:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)
