# Pre-registration — scalp / hold-time study (2026-10-19)

Written 2026-10-19 ~09:50 Asia/Jakarta, BEFORE any result of this study existed. Nothing below
may change after the run; a change = a new study with a new date.

**Question (user, 2026-10-19):** would 1:1 (max 1:1.5) targets on 15m — shorter holds, less
news exposure — work better than today's 4h trade? And does the news worry justify capping how
long today's trades stay open?

**Code:** `scalp_study.py` (reuses `unified_backtest` data loading + `sim_trade_limit`,
`signal_rules.detect_at`, `trade_sim` — the one trade model). Report →
`logs/backtest_reports/scalp_study_<date>.md`.

**Data:** harness default universe (`auto_universe(30)`, same as the `backtest` alias), 180 days
ending at run time, fresh Bybit klines, no funding/OI. TRAIN = first 60% by signal time,
TEST = last 40%.

**Entry + costs (both studies):** today's live model — post-only limit at the next 15m open,
filled only if price trades through it within 2 bars (30 min), maker fee on entry and
take-profits, taker + slippage on stops and expiry, funding over the hold, wick stops,
stop checked before target inside a candle.

## Study A — 15m scalp

- Rules: the 7 price-pattern rules in `signal_rules.py` (trend_pullback_short,
  failed_breakout_short, liquidity_sweep_long, rsi_bounce_long, range_reversion_short,
  range_reversion_long, rsi_rejection_short), detected on CLOSED 15m bars. Rule logic and
  parameters unchanged; only the timeframe changes. Stops = the rule's own stop on 15m ATR.
- Exit: whole position at the target — **A1 = 1.0R**, **A2 = 1.5R** — no partial, no
  breakeven, no trail. Max hold 16 × 15m = 4h after the fill, then closed at market.
- One trade per (symbol, direction) per 4.5h (the longest a trade can live).
- No-skill baseline: every 18th 15m bar, alternating long/short, stop 1.5 × ATR(15m), same
  bracket. Reported only as the reference a rule must beat.

**Bar (A):**
- **PASS** (worth a forward paper test): pooled TEST n ≥ 30, profitable ≥ 70%, net > 0 — judged
  separately for A1 and A2.
- **Per-rule lead** (informational, 14 cells → ~0.7 false positives expected at 5%): TEST
  n ≥ 30, ≥ 60%, net > 0 AND TRAIN ≥ 60%, net > 0 AND TEST hit rate ≥ baseline TEST + 5pp. A
  lead earns a forward test, not a promotion.
- Anything else → **FAIL**: the 15m 1:1 scalp is closed for this rule family.

## Study B — 4h hold cap + news blackout

- Rules + management: today's harness trade (the enabled 4h/1h rules; T1 0.75R closes 50%,
  breakeven after T1, +0.3R lock after 1R, T2 per rule).
- **B0** = today's window (4h signals 48h, 1h signals 24h).
- **B1** = B0 with max hold 12h after the fill.
- **B2** = B1, and skip a signal when a scheduled US release (CPI, jobs report (NFP), FOMC
  statement) falls between 1h before the signal bar's close and 12.5h after it.
  Calendar: bls.gov CPI + Employment Situation schedules, federalreserve.gov FOMC calendar;
  08:30 ET / 14:00 ET → 12:30 / 18:00 UTC (US daylight time).

**Bar (B):** a variant **HELPS** when its pooled TEST net expectancy beats the previous
variant (B1 vs B0, B2 vs B1) by ≥ +0.03R AND the TRAIN difference has the same sign (> 0).
Otherwise **NO EFFECT / HURTS**. Per-rule SHIP bar as usual (TEST n ≥ 30, ≥ 70%, net > 0).

**Fence:** forward test #1 (`range_reversion_short` 4h) is frozen. A B result does not change
it while its clock runs; a "helps" result becomes the management for the next candidate and
the shadow lane, decided after FT#1 resolves.

**Honest priors (written before the run):** A is expected to FAIL (fees ≈ 0.13R on a losing
15m trade; 70% at 1:1 needs ≈ +0.3R/trade of edge, more than anything measured so far).
B1 may trim the long-hold tail; B2 removes ~5% of trades and is expected to be within noise.
