# FPL Assistant

A Fantasy Premier League assistant for weekly squad selection: it tracks your team's
state, predicts expected points (xP) per player per gameweek, and solves for the best
transfers, captain, bench and chip timing.

## Setup

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Commands

```bash
.venv/bin/fpl status     # current gameweek, next deadline, chip windows, rules
.venv/bin/fpl team       # your squad, bank, selling prices, free transfers, chips
.venv/bin/fpl snapshot   # archive today's prices/flags/news (run daily)
.venv/bin/pytest         # run the tests
```

## Layout

```
src/fpl/
  api.py       thin client for the FPL API (raw JSON in, raw JSON out)
  season.py    what gameweek it is, chip windows, game rules
  snapshot.py  daily archive of data the API overwrites
  state.py     your team: squad, selling prices, free transfers, chips
  cli.py       the `fpl` command
tests/         fast tests on hand-built data, no network
data/          downloaded data (not in git)
fpl.toml       your settings (team ID)
```

## Roadmap

1. **Foundation**: API client, snapshots, season status ✅
2. **State engine**: your squad, bank, selling prices, free transfers, chips used ✅
3. **Baseline xP + optimizer**: usable for real decisions
4. **Models**: team strength → clean sheets, minutes, attacking rates, defcon/saves/bonus
5. **Backtest**: walk-forward on last season vs baselines
6. **Interface**: lock/ban/minutes overrides, chip what-ifs, Streamlit
