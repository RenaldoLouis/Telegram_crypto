# PRE-REGISTRATION — top-down cascade: 4h flow → 1h confirms → 30m liquidity sweep → 15m entry (2026-10-21)

_Written before any code for this study existed and before any result was seen. User 2026-10-21: "for 4h the purpose is to find the pattern or the flow, 1h is like refine or confirmation for the 4h, and the 30m is to find the liquidity and 15m is for the entry." Then: "yeah sure run it." The bar below may not be changed after the run._

## Prior (stated before the run)

Pieces failed before: 4h + 1h agreement on our signals (2026-10-20: better, still negative), a 15m trigger entry (2026-10-20 and today's checklist Arm B: worse on later data), `liquidity_sweep_long` 1h alone (51% / −0.25R TEST). The 30m sweep inside a 4h/1h flow was never tested. Expected: NO.

## Data (frozen)

- The 365-day harness caches written today (`logs/backtest_cache/unified/*_{240,60,15}_20251021_20261021.json`), the 34 symbols of `unified_20261021_365d` (a symbol without a complete 15m cache is skipped and named). 30m bars are built from the 15m bars (two consecutive 15m bars; incomplete pairs dropped). No new download.
- Periods by the sweep bar's close: **OLDER** 2025-11-15 → 2026-03-26 · **TRAIN** 2026-03-27 → 07-19 · **TEST** 07-20 → 09-23 · **H** 09-24 → end of data. Nothing is fitted, so every period is out of sample; the names keep the split used by every study since 2026-09-23.

## The rule (all on CLOSED bars; long shown, short mirrored)

1. **4h flow:** the last closed 4h bar has EMA20 > EMA50 → long flow (EMA20 < EMA50 → short flow).
2. **1h confirms:** the last closed 1h bar has EMA20 > EMA50 (same side as the 4h).
3. **30m liquidity sweep against the flow, reclaimed:** a closed 30m bar b whose low is ≥ 0.15 × ATR14(30m) below the lowest low of the 20 bars before it, that closes back above that low, with a lower wick ≥ 50% of its range (the `liquidity_sweep_long` shape, on 30m). Short: high above the 20-bar high, close back below, upper wick ≥ 50%.
4. **15m entry:** starting at the sweep bar's close, wait up to 8 × 15m bars (2 hours) for a 15m close above the highest high of the 4 bars before it (short: below the lowest low). If price touches the stop first → no trade. Entry = post-only limit at the next 15m open (2-bar wait) — the harness's `sim_trade_limit`, maker entry/targets, taker + slippage on stops, funding.
5. **Stop:** the sweep bar's low − 0.1 × ATR(30m); never closer than 0.5 × ATR(30m) to the entry (then set to that distance).
6. **Targets / management:** T1 0.75R (50% off), breakeven after T1, +0.3R lock after 1R, T2 2.0R; 1-day window (96 × 15m bars from the fill).
7. One setup per symbol and direction per 12 hours (the first sweep).

## Control and diagnostic

- **Control:** 3 random twins per setup — same symbol and period, a random 30m close, a random side, the same stop distance in % of price, the same 15m wait/trigger/invalidation/floor and targets.
- **Diagnostic (not judged):** the same setups entered at the next 15m open after the sweep (no trigger).

## Decision (net = managed trade net of costs; hit rate reported)

**PASS** only if all of:
- (a) TEST: n ≥ 30, net > 0, net ≥ control TEST net + 0.05R;
- (b) TRAIN: net > 0;
- (c) OLDER: n ≥ 30, net > 0, net ≥ control OLDER net + 0.05R;
- (d) H: net > 0 (if H n < 15 → "PASS (holdout pending)").

→ a PASS makes it a candidate setup source for the daily book with its own forward clock (built into `signal_rules` / `unified_backtest.py`); the user decides. Otherwise **NO** — no live change. One judged trial. No parameter (20-bar sweep, 0.15 ATR pierce, 50% wick, 8-bar wait, 4-bar trigger, 0.1 / 0.5 ATR stop, 2R, 12 h) is varied after the run.
