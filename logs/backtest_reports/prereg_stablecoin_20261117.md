# Pre-registration — stablecoin supply flows as a new input (2026-11-17)

Written BEFORE `stablecoin_data.py` / `stablecoin_study.py` exist and before any feature of this data was computed. Week 3b of the weekly new-input cadence (`research/new_inputs_ledger.md`); user 2026-11-17: "go" to "start the skew recorder now and test stablecoin flows meanwhile". The engine has never read stablecoin supply. Same protocol, periods, bars, trade population (the 3,531 trades, 29 symbols) and trade shape as `prereg_dvol_20261117.md`, so the inputs are judged alike.

## Idea
New stablecoins are minted when money comes into crypto to be spent on coins; supply shrinks when money leaves. Reading (fixed before the data): **stablecoin supply growing faster than usual favours a LONG (fresh buying power); shrinking or slowing favours a SHORT.** The opposite reading is the `against` bucket in Test A and the `flipped` control in Test B, never selected.

## Data (`stablecoin_data.py` → `logs/backtest_cache/stablecoins/`, gitignored)
- DefiLlama public API (no key): `stablecoincharts/all` (all stablecoins, `totalCirculatingUSD.peggedUSD`, daily) and `stablecoincharts/all?stablecoin=1` (USDT only). Rows are dated 00:00 UTC; the current day's row is updated during the day.
- **Timing rule (no look-ahead):** the row dated D is used only from D + 1 day 00:00 UTC (a feature at T reads rows dated ≤ floor_day(T) − 1 day). Known remaining risk, stated: DefiLlama may have revised older rows after the fact; a free archive of first-published values does not exist.
- **Market-wide input:** one value per day for every coin.

## Features (at a signal close T, on daily rows)
- `stable_7d`: 7-day % change of total USD stablecoin supply, z-scored against the trailing 90 daily values of the same 7-day change (needs ≥ 60 present, sd > 0).
- `stable_30d`: 30-day % change of total USD stablecoin supply, z-scored against the trailing 180 daily values of the same 30-day change (needs ≥ 120, sd > 0).
- `usdt_7d`: as `stable_7d` for USDT only (Tether mints are the most-quoted "money coming in" signal).
No data → `no_data`; the trade is excluded from that variant's denominator.

## Readings
All three: positive favours a LONG. Aligned for a LONG = feature > +thr; for a SHORT = feature < −thr; `against` = the opposite beyond thr; `neutral` between.

## Test A — filter on the six live rules
Population: the 3,531 recorded trades (`unified_20261021_365d_trades.json`, six live rules, filled, the 29 symbols, signals 2025-11-15 → 2026-10-14). Variants: each feature × thr {0.5, 1.0} = 6. Selection on the fit half (OLDER + TRAIN): largest (aligned − all) gap with aligned n ≥ 60. Grading on the unseen half (TEST + H), all required: aligned n ≥ 30; gap ≥ +0.05R; aligned net > 0; aligned net PF ≥ 1.3; gap ≥ 0 in TEST and in H; against not better than aligned. Composition check (mandatory, reported): unseen gap by direction and by rule; a gap carried by one direction only is named in the verdict line.

## Test B — a signal of its own
At every closed 4h bar of the 29 symbols with a harness cache (2025-11-15 → 2026-10-14): feature > +1.0 → LONG, < −1.0 → SHORT. Variants: the three features at thr 1.0 = 3. Trade shape `orderbook_study.sim_book_trade` (limit at the first scored 15m open, stop 1 ATR(4h), T1 0.75R, T2 2R, trail, 2-day window), one open trade per symbol per variant. Controls: random side at the same closes (3 draws, seed 7) and the flipped sign. Selection on the fit half (largest net with n ≥ 100). Grading on the unseen half, all required: n ≥ 100; net > 0; PF ≥ 1.3; ≥ 55 % weeks green; net ≥ random + 0.05R; net > 0 in TEST and in H.

**Trials:** 9. Nothing is varied after the run; anything found afterwards is a post-hoc lead needing its own pre-registration on untouched data.

## Follow-up rules
PASS → confirmation on an untouched window (stablecoin history reaches 2017; klines for 2023-03 → 2024-10 to be fetched), then a shadow lane with its own forward clock; changes no pick. NO → closed, written up in `progress.md` and the ledger.

## Honest priors
A daily, market-wide number changes slowly: within a year there are only a handful of supply regimes (mint waves), so the effective sample is tiny and a pass must survive the per-period and direction checks. Supply also follows price (rallies attract mints), so the feature is partly a lagging trend signal — the direction-composition check exists for that. The DVOL study the same day showed how a two-regime fit-half lift reverses. Expected: NO on both.
