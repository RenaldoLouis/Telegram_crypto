# Pre-registration — "fade the book" confirmation on untouched data (2026-11-03)

Written BEFORE any kline or depth data of the confirmation window was downloaded or looked at. Nothing below changes after the run; the report quotes this file.

## Where the lead came from
`orderbook_20261103.md` Test A (closed NO). One cell of its 8 × 3 table was positive in both halves: trades of the six live rules taken **against** the resting Binance book at band 2 %, threshold 0.10 (`imb_2_0.1`, bucket "against") — fit +0.038R (n 476) vs all −0.065R; unseen +0.056R (n 167) vs all −0.107R. That is the opposite of the reading that study pre-registered, found after the fact, one of 16 against/aligned cells → a lead, not a result. This file turns it into one pre-specified test on data neither study touched.

## Data (untouched)
- **Window:** signals closing in **[2024-10-20, 2025-10-19) UTC**. The depth store (`logs/backtest_cache/orderbook/`) starts 2025-10-20 and every earlier study of the live rules started at 2025-10-21 (`unified_20261021_365d_trades.json`), so no trade of this window has been seen with or without a book. Klines are fetched from 2024-07-01 for indicator warm-up only; signals before 2024-10-20 are discarded.
- **Universe:** the same 29 symbols as the first study (the depth store's symbols). A symbol with < `UB_MIN_HISTORY_DAYS` (60) of 4h history or < 500 15m bars inside the fetch window is dropped and listed; a day missing on the Binance archive (not yet listed there) is `no_data` for its trades.
- **Trades:** `unified_backtest.build_trades` + `sim_trade` at the current parity-fixed code (commit 57ad2fa), limit-open entry, the six live rules (`mtf_entry_study.LIVE`), filled trades only, no funding/OI features (`deriv=None` — the live rules' own gates do not read them). Same population construction as the first study's `C_TRADES`.
- **Feature:** `orderbook_study.feature(idx, sym, signal_ms, "imb", 2.0)` — the Binance bookDepth snapshot at the last 15m boundary ≤ the signal bar's close, no more than 5 minutes old, `(bid − ask) / (bid + ask)` of resting notional within ±2 % of mid; `orderbook_study.bucket(x, direction, 0.10)`. Identical code path to the first study.

## The one test
Bucket **against** (for a long: the book is ask-heavy beyond 0.10; for a short: bid-heavy beyond 0.10) vs **all trades with data** of the window. Cells: n, profitable %, net R per trade (the managed trade), net PF, % of weeks green — `quality_study.quality`.

**PASS (all of):**
1. against n ≥ 100;
2. against net R > 0;
3. against − all ≥ +0.05R;
4. against net PF ≥ 1.3;
5. against % weeks green ≥ 55;
6. against − all ≥ 0 in BOTH halves of the window (H1 = 2024-10-20 → 2025-04-20, H2 = 2025-04-20 → 2025-10-19).

**REPLICATED, BELOW BAR:** 1, 2, 3 and 6 hold but 4 or 5 fails — the book carries the information the lead suggested, but the filtered book is not tradeable under the quality yardstick. Recorded; not a candidate; no further tuning (no new thresholds/bands on this window).

**NO:** anything else, including a sign flip in either half.

**Trials:** 1. Nothing else is selected. Reported descriptively, never graded: the aligned bucket (should be the mirror), by rule, by direction, and `tilt_2_0.1` against.

## What a PASS would mean
The feature is defined on the **Binance** book, so a live implementation would read Binance's public futures depth endpoint (no key) at scan time and tag Bybit trades — Binance is the signal source here, not a proxy for Bybit (unlike the CVD fork). PASS → a shadow-lane filter with its own forward clock before it touches a pick; it changes no pick by itself. Bybit's public book (≤ 1000 levels) does not reach ±2 % on the majors, which is why the live source would be Binance.

## Honest priors
A −0.07R → +0.04R lift is a filter that removes losers, not a stand-alone edge; the yardstick's PF ≥ 1.3 is a high bar for it. Expected: REPLICATED-BELOW-BAR or NO. A post-hoc cell found in 16 has a fair chance of being noise; this window has ~12 months, roughly the size of the fit half.
