# Pre-registration — does the live pre-filter pick the coins where `failed_breakout_short` works? (2026-11-02)

Written before any data for this test was fetched or computed. Research only: no rule, gate or pick changes.

## Hypothesis (from `fbs_check_20261102.md`, Q4 — found after looking, so it needs fresh data)

On the live coins and weeks (2026-09-21 → 10-31), engine fires the live scan also took made +0.333R (n 69);
fires it did not take made +0.026R (n 204). Hypothesis: **`failed_breakout_short` 4h works on the coins the
live pre-filter selects** (top 30 by `_ticker_interest_score` + watchlist + momentum hot list), and not
elsewhere. Fixed-universe backtests never applied that filter.

## Test period

**2025-10-01 → 2026-09-20** (signal bars). It ends before the live data that produced the hypothesis.
Validation of the reconstruction only: 2026-09-21 → 2026-10-22 (the edge cache ends 10-23).

## Reconstruction of the live selection at every 4h close t (fixed now)

- Coins: every crypto USDT perp that was in the daily top 100 by turnover with ≥ $10M on any day of the period
  (edge cache, non-crypto already excluded). Non-crypto perps that took top-100 slots live are ignored (stated).
- Per coin at t: 24h turnover = sum of the last six closed 4h bars; 24h change = close(t) / close(t − 24h) − 1;
  funding = latest settled rate ≤ t (×100, %); open interest = latest daily value ≤ t, **in coins** (the live
  ticker field, compared to $ thresholds exactly as the live code does).
- Pool = top 100 by 24h turnover. Score = the live `BybitFetcher._ticker_interest_score` (called, not copied).
- Hot list at t: coins flagged at any 4h close in (t − 48h, t] among the top 50 by turnover — big move
  (|24h| > 8% and turnover > $200M), funding squeeze (|funding| > 0.05% and |24h| > 3%), volume acceleration
  (24h turnover ÷ the value 4h earlier > 3; the live pulse compares 2h apart — approximation). Bonus from the
  latest flag's acceleration, as live.
- Selected = the live procedure: watchlist (BTC, ETH, SOL) + hot coins in the scored list first, fill to 30 by
  score, then the rest of watchlist + hot.

## Trades

`failed_breakout_short` 4h via `signal_rules.detect_at` on closed 4h bars. Population = fires on coins whose
24h turnover ≥ $10M at the fire (could have been in the pool). 2-day dedup per coin within each group.
Entry at the live time: window starts at the first 15m candle at or after close + 2 min (the keeper's lag);
limit at that open, `trade_sim` management, T1 0.75R / T2 2R from the fill, costs. **Selected** = coin in the
reconstructed selection at t; **not selected** = the rest. Random baseline: shorts on the same coin at every
other 4h close within ±3.5 days, same stop in ATR, same timing and management.

## Bar (all must hold on the TEST period for PASS)

1. **Quality yardstick on the selected book:** net R/trade > 0, net PF ≥ 1.3, ≥ 55% of ISO weeks green.
2. **Beats random:** selected mean − matched random mean ≥ +0.05R per trade, and the bootstrap 95% CI of the
   per-bet difference (same 4h bar = one bet) has its lower bound > 0.
3. **Selection is the mechanism:** selected − not selected ≥ +0.10R per trade, bootstrap CI lower bound > 0
   (bets resampled within each group).
4. **Stable:** selected net > 0 in both chronological halves.

**Validity gate (checked first):** the reconstruction must mark as selected ≥ 80% of the live record's trades
in 2026-09-21 → 10-22. Below that the test is **VOID** (the reconstruction is wrong), not FAIL.

## Outcomes

- **PASS** → pre-register a forward clock on the live lane (bar fixed before any further data).
- **FAIL** → the `failed_breakout_short` lead is closed; the six-week forward record is treated as luck/regime;
  R-2026-10-16-1 graded refuted. No live change either way without the user.
