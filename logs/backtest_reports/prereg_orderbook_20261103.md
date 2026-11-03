# PRE-REGISTRATION — resting order-book depth as a new input (2026-11-03)

_Written after the raw depth files started downloading and before any feature was computed or any result seen. User 2026-11-03: "ok sure lets try that" to the plan "every week one new idea with a NEW input, graded train/test within the week; a pass goes to the shadow lane with its own clock, a fail is written up and closed." The bar below may not be changed after the run._

## Why

Every per-trade input the engine has (price, volume, RSI/EMA/ATR/ADX, funding, OI, liquidations, taker flow, the checklist) has been graded and came back flat after costs. The resting order book — how much is bid and offered within 1–5 % of the price — is the one public data set the engine has never read. The trading-desk reading is: a bid-heavy book is a cushion below (support), an ask-heavy book a lid above; a book that tilts over the last hour shows where liquidity is being pulled or added before the move. This study grades that reading on our trades and as a signal of its own.

## Data (proxy, frozen)

Binance USDT-M perps, `data.binance.vision` `bookDepth` daily files: one snapshot per minute, cumulative resting notional within ±0.2 / 1 / 2 / 3 / 4 / 5 % of mid, bids and asks (`orderbook_data.py`; reduced to the snapshot AT each 15m boundary and the mean over the 15 minutes before it). Window 2025-10-20 → 2026-11-02. Symbols = the 365-day harness universe that exists on Binance (PUMPFUNUSDT = PUMPUSDT; CASHCATUSDT and the tokenized-stock perps have no Binance book and are skipped). **Bybit does not publish historical depth, so Binance is a proxy** (same status as the CVD study): a PASS here is a candidate for an on-venue confirmation on Bybit's own `orderbook` feed, never directly a live input.

Look-ahead rule: a feature at close time T reads only snapshots with timestamp ≤ T (the boundary snapshot is stamped at T + 1 s by Binance; it is the standing book at T). Nothing after T.

## Features (fixed)

- `imb_b(T)` = (bid − ask) / (bid + ask) of the cumulative notional within ±b % at the boundary snapshot, b ∈ {1, 2}. Range (−1, +1); **positive = bid-heavy**.
- `tilt_b(T)` = mean of `imb_b` over the 4 boundaries ending at T (the last hour) − mean over the 4 before (the hour before that). Positive = the book turned bid-heavy over the last hour.
- A missing snapshot at T (none within 5 min) → the trade/close is `no_data` and excluded from both buckets (counted and reported).

Sign convention, fixed by the desk reading above: **aligned** with a LONG = bid-heavy (feature > +thr), with a SHORT = ask-heavy (feature < −thr); **against** = the opposite beyond thr; **neutral** otherwise. thr ∈ {0.10, 0.20}.

## Test A — the book as a filter on the live rules

Population: `logs/backtest_reports/unified_20261021_365d_trades.json`, the six live rule/timeframes (`mtf_entry_study.LIVE`), filled, signals 2025-11-15 → 2026-10-13, symbols with depth data. Outcome = the recorded `net_blended_rr` (the managed trade, maker entry). Periods as in every study since 2026-10-21: OLDER 2025-11-15 → 2026-03-26 · TRAIN → 07-19 · TEST → 09-23 · H → 10-13. **Fit half = OLDER + TRAIN; unseen half = TEST + H.**

Variants: 2 features (`imb`, `tilt`) × 2 bands × 2 thresholds = **8**, each pooled over the six rules. Selection: the variant with the largest (aligned − all) net gap on the fit half, with aligned n ≥ 60 there. Per-rule and per-direction tables are reported for every variant, never selected on.

**PASS** if, for the selected variant on the unseen half: aligned n ≥ 30, aligned net − all net ≥ +0.05R, aligned net > 0, aligned PF ≥ 1.3, and aligned − all ≥ 0 in both TEST and H. **Also required:** the against bucket is not better than aligned on the unseen half (a sign flip = no edge, whatever the gap). Otherwise **NO**.

## Test B — the book as a signal of its own

At every closed 4h bar T of every symbol with depth data (same window, same four periods): if `imb_2(T)` > +thr → LONG, < −thr → SHORT, thr ∈ {0.20, 0.30}; a second pair uses `tilt_2(T)` with thr ∈ {0.10, 0.20}. **4 variants.** One trade model, the live one: post-only limit at the first 15m open ≥ T + 2 min (`config.UB_SCAN_LAG_MIN`), filled only if traded through within 2 bars; stop = **1.0 × ATR14(4h)** from the limit price; T1 = 0.75R (50 % off), breakeven after T1, +0.3R lock after 1R; T2 = 2.0R; window 192 × 15m (2 days); maker fees on entry/targets, taker + slippage on stops/expiry, funding (`trade_sim.simulate_limit`). One trade per symbol at a time (no re-entry while a trade is open). Selection on the fit half (largest net); grade on the unseen half.

Control: the same closes, the same geometry, the side drawn at random (seed 7, 3 draws per trade) — what luck alone produces with these costs.

**PASS** if, for the selected variant on the unseen half: n ≥ 100, net > 0, PF ≥ 1.3, ≥ 55 % of weeks green, net ≥ random + 0.05R, and net > 0 in both TEST and H. Otherwise **NO**. The flipped sign (fade the book) is reported as a control only; it is not a candidate whatever it shows.

## Multiple testing

12 selected trials (8 + 4) → about 0.6 false PASS expected at 5 % with no edge; the unseen-half grade and the two-sub-period requirement are the guard. Per-rule, per-direction, per-band tables are descriptive.

## What follows

- **Any PASS** → an on-venue confirmation plan: a Bybit `orderbook.200` collector (data only, as the CVD/liquidation collectors) and the same variant re-graded on ≥ 8 weeks of Bybit snapshots before it may enter the shadow lane with its own clock. Nothing live changes from this study alone.
- **All NO** → resting depth at 1–5 % is closed as an input; write-up in `progress.md`; next week's input is a different data set.

No feature definition, threshold, band, period boundary, stop multiple, target or window is varied after the run.
