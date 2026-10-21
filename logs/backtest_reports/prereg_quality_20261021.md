# PRE-REGISTRATION — quality trades, winners allowed to run (2026-10-21)

_Written before any code for this study existed and before any result was seen. User 2026-10-21: "are you sure we are not checking all of the strategy in the wrong way? … quality is more important than quantity … we don't need a 70% win rate, even 60/50 is fine, but the quality of the trade has to be great." Then: "yeah let's try that" — (1) switch the yardstick, (2) this test. The bar below may not be changed after the run._

## Why

Every per-trade test since 2026-09-23 used one trade shape built for the ≥ 70% hit-rate bar: 50% off at 0.75R, stop to breakeven, +0.3R lock after 1R, target ≤ 2R, closed after 1–2 days. The management sweep only tried T1 0.5–1.0R and T2 1.5–2R and picked by hit rate. Winners were capped at ~2R while every trade paid ~0.1R in costs. A strategy whose money comes from a few large winners was never tested. This is the one assumption never varied.

## The new yardstick (user decision 2026-10-21; replaces the ≥ 70% hit-rate bar for new work)

On ≥ 30 trades (here: pooled over the four periods, n ≥ 100): **net R per trade > 0** after costs (the managed trade), **net profit factor ≥ 1.3**, **≥ 55% of weeks green** (weekly sum of net R by signal week), and — for a backtest — **net ≥ random entries with the same management + 0.05R**. Max drawdown (sequential, in R) and win rate are reported, not gated. Pre-registered tests already running keep their own rules.

## Population (frozen)

- Trades: `logs/backtest_reports/unified_20261021_365d_trades.json`, the six live rule/timeframes, filled under today's entry (post-only limit at the next 15m open), symbols with a complete 15m cache in `*_20251021_20261021` (XPLUSDT excluded), signals **2025-11-15 → 2026-10-13** (so every trade has a full 7-day forward window).
- **Checklist score ≥ 5** (`checklist.py`, the same scoring as `checklist_confirm_20261021.md`).
- Periods: OLDER 2025-11-15 → 2026-03-26 · TRAIN → 07-19 · TEST → 09-23 · H → 10-13.

## Variants (one trade model: `trade_sim.simulate_limit`, maker entry/targets, taker + slippage on stops/expiry, funding)

- **M0 — today's trade (reference):** T1 0.75R 50%, breakeven, +0.3R lock after 1R, T2 = the rule's target, 2-day (4h) / 1-day (1h) window. Must reproduce the recorded results.
- **Q1 — ATR trailing stop (judged):** same entry and initial stop; no partial, no breakeven, no lock, no target; the stop trails **2 × ATR14(4h at the signal)** behind the best price of PRIOR 15m candles and never loosens; max hold **7 days** (672 × 15m), then marked at the close.
- **Q2 — 3R bracket (judged):** same entry and initial stop; one target at **3R**; no partial, no breakeven, no lock; max hold 7 days.

## Control

3 random twins per trade: same symbol and period, a random 4h close, a random side, the same initial stop distance in % of price, the same 4h ATR in % (for Q1's trail), the same entry and management.

## Decision (per judged variant)

**PASS** if, pooled over the four periods: n ≥ 100, net > 0, PF ≥ 1.3, ≥ 55% of weeks green, net ≥ random twins + 0.05R, and net > M0's net on the same trades; AND net > 0 in at least 3 of the 4 periods. Otherwise **NO**.

- A PASS → candidate shape for the daily book: score ≥ 5 candidates traded with that management, on its own forward clock (live scoring would use the same `trade_sim` option); the user decides.
- Both NO → letting winners run is not the missing piece on these candidates; score ≥ 5 stays on today's trade shape.

Reported, not judged: Q1/Q2 on ALL candidates (any score), by direction, by rule, average win / average loss, hold time, max drawdown. Two judged trials. No parameter (2 × ATR, 3R, 7 days, score ≥ 5) is varied after the run.
