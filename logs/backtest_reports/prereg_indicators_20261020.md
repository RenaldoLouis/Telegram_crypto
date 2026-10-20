# PRE-REGISTRATION — MA200, Bollinger Bands, Accumulation/Distribution (2026-10-20)

_Written before any code for this study existed and before any result was seen. User question 2026-10-20: "is it possible to use indicators on this scan, like MA200, Bollinger, distribution/accumulation?" User: "run the indicator test now." The bar below may not be changed after the run._

## Question

Do classic indicators the scan does not use yet — MA200, Bollinger Bands, Accumulation/Distribution — (A) separate winning from losing signals of our six live rules out of sample, or (B) make a profitable rule on their own?

## Prior (stated before the run)

These belong to the family already tested: Bollinger extremes resemble the 20-candle range rules; A/D and OBV are candle-based approximations of taker flow (the on-venue CVD test failed); MA200 is a trend filter like the 4h/1h agreement just tested (better on both halves, still negative). The technical-analysis literature finds such rules rarely survive costs and multiple testing. Prior: small effects, nothing profitable.

## Data (frozen; no download)

- Signals for part A: the 1,884 trades of the six live rule/timeframes in `logs/backtest_reports/unified_20260923_trades.json` (29 symbols, 2026-03-29 → 09-23) with their recorded results (`net_blended_rr`, `profitable`).
- Candles: `logs/backtest_cache/unified/<SYMBOL>_{240,60,15}_20260327_20260923.json` (the harness cache); daily history for MA200 from `logs/backtest_cache/xs_<SYMBOL>_D.json` (2025-04-12 → 2026-10-03).
- Split: TEST = signals from **2026-07-20** on (the same date as the 2026-10-20 entry study, the 60th-percentile signal); TRAIN = before.
- Every indicator is read on CLOSED bars at the signal's close (no look-ahead): the signal-timeframe bar that closed at the signal time; for the daily MA200, the last daily bar closed at or before it.

## Indicator definitions (frozen)

- **MA200 daily** — simple 200-day average of daily closes. **MA200 4h** — 200-bar average of 4h closes (4h bars closed at or before the signal; needs 200 bars, so signals before ≈ 2026-04-29 have none and are left out of that filter).
- **Bollinger** (signal timeframe, 20 bars, 2 standard deviations): %B = (close − lower) / (upper − lower); **stretch** = %B for shorts, 1 − %B for longs (high = price pushed in the direction being faded). **Width** = (upper − lower) / middle, ranked as a percentile of its own last 120 bars.
- **Chaikin A/D line** (signal timeframe): cumulative Σ volume × ((close − low) − (high − close)) / (high − low). **OBV**: cumulative Σ ± volume by close-to-close direction. For each, the 10-bar change, read against the trade: **confirming** = falling for shorts (distribution), rising for longs (accumulation).

## Part A — filters on the live signals (6 judged trials)

| filter | buckets (fixed) |
|---|---|
| `ma200_d` | with the trend (short below / long above) · against it |
| `ma200_4h` | with · against |
| `bb_stretch` | < 0.5 · 0.5–1.0 · > 1.0 (outside the band) |
| `bb_width` | squeeze (bottom 20%) · normal · wide (top 20%) |
| `ad_slope` | confirming · not |
| `obv_slope` | confirming · not |

For each filter, the bucket with the best TRAIN net (n ≥ 50 on TRAIN) is selected on TRAIN only, then read on TEST. Baseline = all signals in the same period.

- **KEEP-CANDIDATE:** selected bucket's TEST n ≥ 30, TEST net > 0, and TEST net > the TEST baseline → candidate gate, to be built into `signal_rules.py` and re-validated in `unified_backtest.py` (one trade model) with its own forward clock; the user decides.
- **HELPS-BUT-NEGATIVE:** TEST n ≥ 30 and TEST net above the TEST baseline, but ≤ 0 → recorded; no live change.
- **NO:** otherwise.

## Part B — stand-alone indicator rules (2 judged trials)

4h bars of the 29 symbols, every closed bar from index 130 on (warm-up for the 120-bar width rank), the system's trade model (`unified_backtest.sim_trade_limit`: limit at the next 15m open, 2-bar wait, T1 0.75R with 50% off, breakeven, +0.3R lock after 1R, costs, 2-day hold), 2-day dedup per symbol and side, stop = entry ∓ 1.5 × ATR(14, 4h).

- **`bb_fade`**: close above the upper band → short; close below the lower band → long; T2 = 1.5R.
- **`bb_squeeze_break`**: band width in the bottom 20% of its last 120 bars on the previous bar, and this bar closes outside the band → trade in the breakout direction; T2 = 2.0R.

Verdict per rule on the same date split: **CANDIDATE** if TEST n ≥ 30, TEST profitable ≥ 60%, TEST net > 0 and TRAIN net > 0 (≥ 70% on TEST would meet the system's SHIP bar); else **NO**. Reported next to a random-entry reference (same trade model).

## Multiple testing

8 judged trials (6 filters with a TRAIN-selected bucket among 2–3, 2 stand-alone rules); at 5% each, about one false "winner" is expected by chance. Per-rule and per-direction splits are context only. Nothing (periods, bands, lookbacks, cut points, stops, targets) is varied after the run.
