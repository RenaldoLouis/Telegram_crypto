# Pre-registration — crowd & top-trader positioning as a new input (2026-11-03)

Written BEFORE `positioning_study.py` exists and before any feature of this data was computed. The input is new to the engine: it has only ever read Bybit funding and open interest (`derivs_data.py`, 2026-09-23: no edge). Same protocol, periods and bars as `prereg_orderbook_20261103.md` so the two inputs are judged alike.

## Data
Binance USDT-M `metrics` archive (`positioning_data.py` → `logs/backtest_cache/positioning/`), one row per 5 minutes since 2023, reduced to 15-minute boundaries. Two series are used:
- **`glob_acc`** = `count_long_short_ratio`: long / short ratio of ALL accounts with a position — the crowd.
- **`top_pos`** = `sum_toptrader_long_short_ratio`: long / short ratio of the top 20 % of accounts by margin balance, by POSITION size — the "smart money" of the exchange's own definition.
Both are read as `ln(ratio)` (symmetric around 0). Open interest (correlated with Bybit OI, already tested) and the taker buy/sell ratio (fork #4's family, closed 2026-10-16) are stored but NOT used.

Binance is the source of this input, not a proxy for Bybit: a live implementation would read the same numbers from Binance's public `futures/data/globalLongShortAccountRatio` and `topLongShortPositionRatio` endpoints at scan time and tag Bybit trades.

## Features (at a signal close T; all from boundaries ≤ T)
- `glob_z` / `top_z`: z-score of ln(ratio) at T against its own trailing 7 days of 15-minute boundaries (672; needs ≥ 400 present, sd > 0).
- `glob_tilt` / `top_tilt`: ln(ratio at T) − ln(ratio 4 h earlier), divided by the sd of the same 4-hour changes over the trailing 7 days (needs ≥ 100 changes).
No data → `no_data`; the trade is excluded from that variant's denominator.

## Readings (signs fixed by trading logic, before the data)
- **Crowd (`glob_*`) is faded:** aligned for a LONG = the crowd is short / getting shorter (feature < −thr); aligned for a SHORT = feature > +thr.
- **Top traders (`top_*`) are followed:** aligned for a LONG = feature > +thr; aligned for a SHORT = feature < −thr.
- `against` = the opposite beyond thr; `neutral` between.

## Test A — the input as a filter on the six live rules
Population: the 3,531 recorded trades of the first study (`unified_20261021_365d_trades.json`, six live rules, filled, 29 symbols, signals 2025-11-15 → 2026-10-14). Variants: {`glob_z`, `top_z`, `glob_tilt`, `top_tilt`} × thr {0.5, 1.0} = 8. Selection on the fit half (OLDER + TRAIN): largest (aligned − all) gap with aligned n ≥ 60. Grading on the unseen half (TEST + H), all required: aligned n ≥ 30; gap ≥ +0.05R; aligned net > 0; aligned net PF ≥ 1.3; gap ≥ 0 in TEST and in H; against not better than aligned. → PASS / NO.

## Test B — the input as a signal of its own
At every closed 4h bar of the 29 symbols (2025-11-15 → 2026-10-14): side from the feature — fade the crowd (`glob_*` > +thr → short, < −thr → long), follow the top traders (`top_*` > +thr → long). Variants: `glob_z` 1.0, `top_z` 1.0, `glob_tilt` 1.0, `top_tilt` 1.0 = 4. Trade shape `orderbook_study.sim_book_trade` (limit at the first scored 15m open, stop 1 ATR(4h), T1 0.75R, T2 2R, trail, 2-day window), one open trade per symbol per variant. Controls: random side at the same closes (3 draws, seed 7) and the flipped sign. Selection on the fit half (largest net with n ≥ 100). Grading on the unseen half, all required: n ≥ 100; net > 0; PF ≥ 1.3; ≥ 55 % weeks green; net ≥ random + 0.05R; net > 0 in TEST and in H. → PASS / NO.

**Trials:** 12 (≈ 0.6 false PASS expected at 5 % with no edge). Nothing is varied after the run; anything found afterwards is a post-hoc lead and would need its own pre-registration on untouched data (the 2024-10 → 2025-10 year is available for that).

## Follow-up rules
PASS on A → the filter goes to the shadow lane with its own forward clock, fed by Binance's public endpoint at scan time; changes no pick. PASS on B → a shadow rule of its own, same clock. NO → closed, written up in `progress.md`.

## Honest priors
Positioning ratios are widely watched; the crowd-fade reading is folklore with mixed academic support, and the first study showed how a fit-half gap of +0.24R reversed out of sample. Expected: NO on both.
