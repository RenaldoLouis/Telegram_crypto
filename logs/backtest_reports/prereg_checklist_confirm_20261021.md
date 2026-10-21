# PRE-REGISTRATION — confirm "checklist score ≥ 5" on older, untouched data (2026-10-21)

_Written before the confirmation backtest was run and before any trade in its window was scored. Origin: the post-hoc lead in `checklist_20261021.md` (score ≥ 5 positive on TRAIN / TEST / holdout; the threshold was picked after seeing the table). User 2026-10-21: "yes go for both" (this test + forward logging of the score on live candidates). The bar below may not be changed after the run._

## Hypothesis

Among the six live rules' candidates, those with checklist score ≥ 5 (the 9 points exactly as defined in `prereg_checklist_20261021.md` and implemented in `checklist_study.py` today — no definition, threshold or parameter changes) make money net of costs, and do better than all candidates.

## Data (frozen before the run)

- `unified_backtest.py --days 365 --symbols <the 34 symbols of the primary + holdout sets>` run on 2026-10-21 (unified engine: closed-bar signals, limit-open entry, managed trade net of costs; derivs on). Outputs renamed to `unified_20261021_365d*` so the monthly fade check does not read them.
- **Window scored: signals 2025-11-15 → 2026-03-26** (from 25 days after the run's first bar, so the 120-bar zone/swing lookback is full; up to the day before the first study's data). No trade in this window has been used by any unified-engine filter study.
- Population: the six live rule/timeframes, filled trades.
- Caveat stated in advance: the symbols are today's survivors (survivorship), and coins listed after the window contribute nothing.

## Validity

The run is **INVALID** (neither pass nor fail; reported as such) if funding or open-interest data is missing for > 10% of the window's trades, or if the reproduction check (my trend_4h / trend_1h / funding / oi_trapped / volume vs the harness's recorded fields) matches < 95% of trades.

## Bar

- **Primary (judged):** score ≥ 5 → n ≥ 30, net R per trade > 0, AND ≥ all candidates' net + 0.05R.
- **Secondary (judged):** `liquidity_sweep_long` 1h with score ≥ 5 → n ≥ 30, net > 0, AND > all `liquidity_sweep_long` net. If n < 30 → "thin", not judged.
- Reported, not judged: score buckets, by direction, by rule, by month.

## Decision

- Primary PASS → "score ≥ 5" becomes the candidate selector for the daily book, **gated on the forward log**: the live score has been logged on every candidate since 2026-10-21; once ≥ 30 forward candidates with score ≥ 5 are scored, they must show net > 0 and beat all candidates; then the user decides whether `select_daily_picks` ranks by score.
- Primary FAIL → the lead is closed; the forward log may keep running only as information.
- Secondary is reported with the primary; it cannot pass on its own if the primary fails (one more look at the data, not a rescue).
