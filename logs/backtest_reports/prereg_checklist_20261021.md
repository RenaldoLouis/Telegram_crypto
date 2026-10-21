# PRE-REGISTRATION — the trader's checklist (2026-10-21)

_Written before any code for this study existed and before any result was seen. User 2026-10-21: "usually how people play is they look at the 4h, 1h trendline and then enter on the 15m timeframe, and of course look at supply and demand and the price movement based on MA200, and I want to automate this … adding [the Orion-style] information would be nice but it should be used by our system, I don't want to filter it manually." Then: "go ahead, test it first." The bar below may not be changed after the run._

## Question

Does a discretionary trader's checklist — 4h and 1h trend, supply/demand zones, trendlines, MA200, plus the Orion-style market numbers (BTC, funding, open interest, volume) — computed mechanically, (A) pick the winners among our candidates, or (B) make money on its own with a 15m entry?

## Prior (stated before the run)

Parts of it were tested alone and failed: 4h + 1h agreement (2026-10-20: better, still negative), the 15m trigger (halves disagree), MA200 daily (TRAIN +0.09R, TEST −0.10R), OI change (2026-08-09, reversed out of sample), funding/OI divergence (2026-09-23 filter study, no edge). Supply/demand zones and trendlines were never coded. Expected: no pass — but the combination is what a trader actually uses, so it gets its own test.

## The checklist (9 points, signs fixed by trading logic, nothing fitted)

All read at the signal close T from bars CLOSED at or before T. 4h/1h frames = `signal_rules.compute_indicators` on the harness's kline caches; "ATR" = the 4h ATR(14) of the last closed 4h bar j unless stated. Long = mirror of short throughout.

1. **trend_4h** — 4h EMA20 vs EMA50 agrees with the trade (EMA20 > EMA50 for a long).
2. **trend_1h** — same on 1h.
3. **ma200_d** — the signal close is above the daily SMA200 (closed daily bars) for a long, below for a short.
4. **sd_zone** — price is at a fresh, unbroken 4h demand zone (long) / supply zone (short):
   - impulse bar k (k ≤ j − 2, k ≥ j − 120): body ≥ 1.5 × ATR(14) of bar k − 1, in the trade's direction, closing beyond bar k − 1's extreme (long: close > high[k−1]);
   - zone = bar k − 1's [low, high] (the base before the move);
   - unbroken: no 4h close beyond the far side between k + 1 and j (long: no close < zone low);
   - at the zone: signal close within [zone low − 0.25 ATR, zone high + 0.5 ATR] (long; short mirrored: [zone low − 0.5 ATR, zone high + 0.25 ATR]);
   - fresh: the current visit = the run of bars ending at j whose low (long) / high (short) is inside that band; no bar between k + 1 and the start of the visit touched the zone (long: low ≤ zone high).
5. **trendline** — price is at a rising 4h support line (long) / falling resistance line (short): the two most recent confirmed swing lows (long; a bar whose low is the minimum of the 3 bars each side, confirmed by bar j) within the last 120 bars, ≥ 5 bars apart, the later one higher; line through them extended to bar j; signal close − line ∈ [−0.25, +0.75] ATR; no close below line − 0.25 ATR between the second swing and bar j − 1. Short: swing highs, the later one lower, close − line ∈ [−0.75, +0.25] ATR, no close above line + 0.25 ATR.
6. **btc_4h** — BTC's 4h EMA20/EMA50 trend agrees with the trade.
7. **funding** — the last settled funding rate is ≥ 0.005% in size and the trade is against the side paying it (short when longs pay, long when shorts pay).
8. **oi_trapped** — open interest rose > 0.5% over 24 h while price moved > 0.5% against the trade over the same 24 h (short after a rise, long after a drop): fresh positions on the other side.
9. **volume** — the signal bar's volume ≥ 1.5 × its 20-bar average.

Missing input → that point is 0 (coverage reported per item). Score = sum, 0–9.

**Reproduction check:** items 1, 2, 7, 8, 9 must match the fields recorded by `unified_backtest.py` on the primary trades (`h4_trend`, `h1_trend`, `funding_side`, `oi_divergence`, `vol_spike`) on ≥ 95% of trades, or the run is invalid.

## Data (frozen)

- **Primary:** the 1,884 trades of the six live rule/timeframes in `unified_20260923_trades.json` (29 symbols, 2026-03-29 → 09-23), outcomes as recorded (managed trade, limit entry, net of costs); kline caches `*_20260327_20260923`, funding/OI caches `*_20260327_20260923`.
- **Holdout H (untouched by every filter study):** the six live rules' signals 2026-09-24 → 10-19 from `scalp_study_20261019_trades.json` set B, outcome = `B0` (today's trade; unfilled excluded); kline caches `*_20260422_20261019`; funding/OI fetched fresh from Bybit's public API (cached).
- Daily candles for MA200: fetched fresh from Bybit (cached under `logs/backtest_cache/checklist/`).
- Split: TRAIN < 2026-07-20 ≤ TEST < 2026-09-24 ≤ H.

## Arm A — the checklist as the selector of our candidates (judged)

Threshold **N = the 75th percentile of the score over TRAIN trades, rounded up** (computed from the features alone, before outcomes are joined; reported). "Pick" = score ≥ N.

**PASS** if all of: (a) TEST pick n ≥ 30, TEST pick net > 0 and ≥ ALL TEST net + 0.05R; (b) TRAIN pick net > ALL TRAIN net; (c) Spearman ρ(score, net R) > 0 on TRAIN and on TEST; (d) H pick net > ALL H net — if H pick n < 15 the holdout is "thin" and a pass reads "PASS (holdout pending)".
**BETTER-BUT-NEGATIVE** if (b), (c) hold and TEST pick net > ALL TEST net but ≤ 0. **NO** otherwise.

## Arm B — the trader's method on its own (judged)

At every 4h close, for each of the holdout's 30 symbols (kline caches `*_20260422_20261019`, funding/OI fetched fresh) and each direction, a **setup** = trend_4h AND trend_1h AND ma200_d AND (sd_zone OR trendline) AND score ≥ 6. One setup per symbol and direction per 24 h. Setups start once 120 4h bars of history exist.

- **Entry: the 15m trigger** exactly as `mtf_entry_study.py` V3 (wait ≤ 16 bars; a 15m close beyond the prior 4 bars' extreme; invalidated if the original stop trades first; post-only limit at the next 15m open; stop = 15m swing of the trigger bar and 7 before it, capped at the original stop, floor 0.25 × 4h ATR). Original stop = 1.5 × 4h ATR from the signal close. T1 0.75R / T2 2.0R, the harness's `sim_trade_limit`, 2-day window (4h).
- **Control:** 3 random twins per setup — same symbol and period (TRAIN / TEST / H), a random 4h close, a random side, the same original stop distance in %, the same trigger entry and targets.
- **PASS** if TEST n ≥ 30, TEST net > 0, TRAIN net > 0, TEST net ≥ control TEST net + 0.05R, and H net > 0 (if H n < 15 → "PASS (holdout pending)"). **NO** otherwise.
- Diagnostic only: the same setups entered at the next 15m open (no trigger).

## Decision

- A PASS in either arm → candidate for the live system (Arm A: the daily book picks by checklist score; Arm B: a new setup source), built into the one trade model (`signal_rules` / `trade_sim` / `unified_backtest.py`) with its own forward clock; the user decides. Nothing goes live from this file.
- NO / BETTER-BUT-NEGATIVE → no live change. The checklist may still be printed per pick as information only if the user asks.

Two judged trials (Arm A, Arm B). Reported but not judged: each item alone (TRAIN/TEST/H), score buckets, by direction. Nothing is varied after the run.
