# PRE-REGISTRATION — top-down entry: 4h + 1h direction, 15m trigger (2026-10-20)

_Written before any code for this study existed and before any result was seen. User idea 2026-10-20: "get the 4h timeframe, the 1h timeframe, and then put the trade in on the 15m, so we have more view on where this is going." User: "run it." The bar below may not be changed after the run._

## Question

Does requiring the 4h and 1h trends to agree with a signal, and then entering on a 15m confirmation instead of the next 15m open, turn our signals into a profitable book — and if the 15m trigger helps, is that information or just stop/target geometry?

## Prior (stated before the run)

A quick in-sample look on 2026-10-20 (no split): trades whose 4h and 1h trends both agree with the direction were 57.2% / −0.046R vs 53.4% / −0.100R when neither agrees — better, still negative. Our signal entries are indistinguishable from random entries at every target size (`win_rate_geometry.py`), and a 15m entry only changes timing and stop size; tighter stops raise cost in R (the 15m scalp study failed on costs). Prior: a small improvement, net still ≤ 0.

## Data (frozen)

- Signals: the 1,884 trades of the six live rule/timeframes in `logs/backtest_reports/unified_20260923_trades.json` (29 symbols, 2026-03-29 → 09-23), with their recorded entry, stop, `target_r`, `atr`, `h4_trend`, `h1_trend`.
- 15m candles: `logs/backtest_cache/unified/<SYMBOL>_15_20260327_20260923.json` (the same cache the harness used). No download.
- Split: chronological 60/40 over all signals by signal time (TEST starts at the 60th-percentile signal, ≈ 2026-07-20).

## Variants (one trade model: `trade_sim.simulate_limit`, post-only limit at the next 15m open, 2-bar wait, T1 0.75R with 50% off, breakeven after T1, +0.3R lock after 1R, T2 at the rule's `target_r`, maker entry/targets, taker + slippage on stops/expiry, funding; hold window 2 days for 4h signals, 1 day for 1h signals, counted from the fill)

- **V1 — today's entry** (baseline): re-simulated with the harness's own `sim_trade_limit` logic; must reproduce the recorded results.
- **V2 — agreement (judged):** V1, only when `h4_trend` and `h1_trend` both equal the trade's side (bearish for shorts, bullish for longs).
- **V3 — agreement + 15m trigger (judged):** the V2 signals, but:
  - *Wait:* up to 16 15m bars (4 hours) after the signal close.
  - *Trigger:* a 15m bar that closes beyond the previous 4 bars' extreme in the trade's direction (short: close < lowest low of the 4 prior bars; long: close > highest high).
  - *Invalidation:* if price touches the original stop before or on the trigger bar, no trade.
  - *Entry:* post-only limit at the next 15m bar's open, 2-bar wait.
  - *Stop:* the 15m swing — highest high (short) / lowest low (long) of the trigger bar and the 7 bars before it; never further from the entry than the original stop level (if it is, use the original stop); never closer than 0.25 × the signal timeframe's ATR (then set to that distance).
  - *Targets:* T1 0.75R, T2 at the rule's `target_r`, from the new entry and stop.
  - No trigger within 4 hours → no trade (counted as skipped; trigger rate reported).
- **V3b — 15m trigger without the agreement filter (context, used for the control):** V3's entry on all signals.
- **Control — random entries:** 3 twins per signal (same symbol, same timeframe and `target_r`, stop distance = the signal's risk %, a random 4h close from the same cache, random side): R1 = next-open entry like V1, R3 = 15m trigger like V3b. Δ_signal = net(V3b) − net(V1); Δ_random = net(R3) − net(R1).

## Decision (per judged variant; net = managed trade net of costs, the system's one expectancy)

- **ADOPT-CANDIDATE:** TEST n ≥ 30, TEST net > 0, TEST net > V1's TEST net, and TRAIN net > V1's TRAIN net; for V3 also Δ_signal > Δ_random on TEST (the trigger must help our signals more than it helps random entries). → It becomes a candidate for the live entry/filter, built into `unified_backtest.py` / `trade_sim.py` (one trade model) and given its own forward clock; the user decides.
- **BETTER-BUT-NEGATIVE:** TEST net and TRAIN net both above V1's, but TEST net ≤ 0 → recorded; no live change.
- **NO:** otherwise.

Hit rate (profitable %) is reported for every variant; the verdict uses net. Two judged trials (V2, V3); V3b and the control are diagnostics. No parameter (lookback 4, swing 8, wait 16, floor 0.25 ATR) is varied after the run.
