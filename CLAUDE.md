# FPL Assistant: notes for Claude

## Working agreement
Claude writes the code; the owner steers. Explain the *why* behind structure and Python
patterns as you go, using math analogies (filters, estimation, detection) where they help.
Keep each step small enough to read in one sitting.

## Architecture
Four components, kept separate:
1. **State engine**: gameweek, squad, bank, selling prices, free transfers, chips. Pure bookkeeping.
2. **xP model**: decomposed by scoring component (minutes, team-strength-driven goals/clean
   sheets, attacking shares, defcon, saves, bonus), never a single regressor on total points.
3. **News layer**: turns text into minutes adjustments. Manual overrides first, LLM later.
4. **Optimizer**: multi-gameweek MILP over xP and state.

## Conventions
- `api.py` returns raw JSON only; parsing lives in the module that uses it.
- Read game rules (chip windows, FT cap, budget) from bootstrap-static; don't hard-code them.
- Join players across seasons on `code` (stable), not `id` (changes every season).
- Money: the API uses tenths of £m (`now_cost` 156 = £15.6m). Convert at the edges.
- Tests use hand-built inputs, never the live API.
- Anything that uses data must only see what was known before that gameweek's deadline (no leakage).
