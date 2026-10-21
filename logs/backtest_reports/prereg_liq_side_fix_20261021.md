# Pre-registration — liquidation-cluster test with the side corrected (2026-10-21)

Written BEFORE any corrected number was computed. The only result seen before writing
this file is an exact reproduction of the 2026-10-08 run with the OLD code (1h: ALL
TEST −0.101 n=192, NEAR-aligned TEST −0.114 n=126 — identical to
`liq_cluster_20261008_1h.txt`), which confirms the data store and kline cache are
unchanged.

## Why a re-run

Fork A was closed on 2026-10-08. On 2026-10-19 we found that Bybit's `allLiquidation`
`S` field is the POSITION side: `"Buy"` = a LONG was liquidated (forced market sell),
`"Sell"` = a short was liquidated (forced market buy) — 96% of liquidated notional in BTC
hours that fell > 1% was "Buy". `liq_cluster_backtest.py` assumed the opposite, so every
"direction-aligned" cluster was the wrong side's cluster: long trades were paired with
short-liquidation clusters below them, short trades with long-liquidation clusters above.
The hypothesis itself was never tested.

## Hypothesis (unchanged from 2026-08-09, side now read correctly)

- LONG entry near a cluster of LONG liquidations at/below entry (longs just flushed) → better.
- SHORT entry near a cluster of SHORT liquidations at/above entry (shorts just squeezed) → better.

## Part A — like-for-like corrected re-run (legacy harness)

`liq_cluster_backtest.py` + `liq_cluster_deep_dive.py`, identical parameters to 10-08:
1h and 4h, trailing window 48 h, bin 0.5 ATR, cluster ≥ 5% of window notional, target
1.5R, 48-bar horizon, fixed cost 0.072R, `trend_pullback_long/short`, chrono split 0.60,
same store (`logs/liquidations/ci/`, 214 files, 88,774 events) and same kline cache.
**Only change: the side mapping.**

Bar (the 2026-08-09 rule, "clearly" quantified now): on 1h, NEAR-aligned (≤ 1.5 ATR,
the harness's split cut) **TEST net ≥ 0 AND ≥ ALL TEST net + 0.05R**. 4h is expected to
be untestable again (liq data covers only the last ~60 of 166 days); it is reported,
not judged.

## Part B — the promotion path (unified engine, operating discipline #7)

Tag the trades in `logs/backtest_reports/unified_20261016_cvd_trades.json` (unified
engine: closed-bar signals, limit-open entry, managed trade net of cost; same 19 symbols
as the liquidation store; 2026-08-04 → 10-16) restricted to the **six live rules at
their live timeframes** (trend_pullback_short 4h, failed_breakout_short 4h,
liquidity_sweep_long 1h, rsi_bounce_long 4h, range_reversion_short 4h,
range_reversion_long 4h) whose signal close AND full 48 h trailing window lie inside the
symbol's liquidation coverage. Same cluster definition as Part A; entry = signal close,
ATR = the trade's ATR at signal. Metric: mean `net_blended_rr` (the managed trade) and
`profitable` %. Split: global chronological by signal time, first 60% TRAIN / last 40%
TEST.

Bar: NEAR-aligned (≤ 1.5 ATR) **TEST mean net ≥ 0 AND ≥ ALL TEST + 0.05R AND
NEAR TEST n ≥ 30, AND NEAR > ALL on TRAIN too** (same sign on both halves).

## Decision

- Both parts PASS → candidate shadow-lane filter with its own forward clock (needs the
  liquidation collector's raw prints kept again; NOT a live change).
- Part B fails (or n TEST < 30 → INCONCLUSIVE, reported as such) → fork A closed for
  good; no further extension.
- Part A passes but Part B fails → closed (Part A's trade model is not comparable to
  live; it cannot promote anything on its own).

Descriptive only, never judged: per-bucket table (at / near / far / none), the
0.5–1.5 ATR ring alone, per direction, per rule, coverage sensitivity, the opposite
(old, wrong-side) alignment as a control. Multiple-testing note: two harnesses, one
primary cut each.
