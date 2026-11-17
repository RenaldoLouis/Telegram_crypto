# PRE-REGISTRATION — cascade with a 2× stop, confirmation on the 2024-25 year (2026-11-17)

_Written and committed before any code for this test exists and before any trade of this window is simulated with this rule. User 2026-11-17: "stops getting hit … lets try something else approach for this 15m … check the flow at 4h 1h 30m then get in in 15m", then "go with what you recommend". The bar below may not be changed after the run._

## Where the idea comes from (post-hoc, stated plainly)

The 2026-10-21 cascade study (`prereg_cascade_20261021.md`, verdict NO, −0.07 to −0.12R in all four periods, = random) was re-read on 2026-11-17 by a scratchpad diagnostic (not committed as a study) on the SAME data (2025-11-15 → 2026-10-21, 1,477 filled trades, 4,452 random twins):

- 48% of trades stopped before T1 later reached T1 inside the day — random twins 46.5% → stop hunts are a market feature, not a cascade feature.
- Stop width ×1 / ×1.5 / ×2 / ×3 with targets scaled to the new risk: cascade −0.110 / −0.030 / +0.002 / +0.005R vs random −0.103 / −0.071 / −0.050 / −0.032R. Gap at ×2 = +0.053R (the largest).
- Targets fixed in price instead: net −0.110 / −0.042 / −0.018 / −0.017R.

8 variants were looked at; ×2 with scaled targets was picked because it looked best. Prior: most of the improvement is the fee share falling (random improves too); the +0.05R gap over random is the only thing that could be skill, and it is the size multiple testing produces. **Expected: NO or WEAK.**

## Data (frozen)

- The kline cache written by `orderbook_fade_confirm.py` (tag `20240701_20251019`, 4h / 1h / 15m, warm-up from 2024-07-01), the 29 symbols that have it (1000BONK, 1000PEPE, ADA, AKE, ARB, BTC, DOGE, ENA, ETH, FARTCOIN, HBAR, INJ, NEAR, ONDO, OP, PENGU, PUMPFUN, SAND, SOL, STRK, SUI, TRX, USELESS, US, WLD, XLM, XPL, XRP, ZEC). No download. A symbol whose cache does not cover the window simply contributes fewer setups.
- Window: 30m sweep bars closing in [2024-10-20, 2025-10-19). Halves: H1 = before 2025-04-20, H2 = from 2025-04-20.
- This year was read before by two studies (order-book fade, cross-venue basis-tilt) for OTHER rules; the cascade has never been run on it.

## The rule (identical to `cascade_study.py` except step 5)

1. 4h flow: last closed 4h bar EMA20 > EMA50 → long (else short).
2. 1h confirms: last closed 1h bar EMA20 vs EMA50 on the same side.
3. 30m sweep against the flow, reclaimed (20-bar extreme pierced by ≥ 0.15 × ATR14(30m), close back inside, wick ≥ 50% of range); 30m bars built from 15m.
4. 15m entry: up to 8 bars for a 15m close beyond the prior 4 bars' extreme; the ORIGINAL stop (sweep extreme ± 0.1 × ATR30, floor 0.5 × ATR30 from the fill) touched first → no trade. Entry = the harness's post-only limit at the next 15m open (`unified_backtest.sim_trade_limit`, 2-bar wait), maker entry/targets, taker + slippage on stops.
5. **Stop = 2 × the original stop distance from the entry** (`stop_scale = 2.0`); T1 = 0.75 × the new risk (50% off), breakeven after T1, +0.3R lock after 1R, T2 = 2.0 × the new risk; 1-day window (96 × 15m).
6. One setup per symbol and direction per 12 h.

## Control

3 random twins per setup, seed 31, built exactly as `cascade_study.py` (same symbol and half, a random 30m close, random side, the same stop distance in % of price, the same trigger/invalidation/floor), then the same ×2 stop and targets.

## Decision (net = managed trade net of costs; the quality yardstick of 2026-10-21)

- **PASS** — all of: n ≥ 100; net > 0; net ≥ control net + 0.05R; net PF ≥ 1.3; ≥ 55% of weeks green (signal week, sum of net R); net > 0 in BOTH halves.
  → candidate for a forward paper lane with its own clock (built into `signal_rules` / `unified_backtest.py`); the user decides. No live change from this test alone.
- **WEAK** — net > 0, ≥ control + 0.05R and net > 0 in both halves, but PF or green weeks below the bar → recorded as a lead; only a forward paper test can promote it.
- **NO** — anything else. The cascade family on 15m is then closed unless a new input arrives.

Composition check (reported, mandatory): longs vs shorts and each half; if the gap over random comes from one side only, the verdict line says so. One judged trial; nothing (×2, 0.75R / 2R, 20-bar sweep, 0.15 ATR, 50% wick, 8-bar wait, 4-bar trigger, 12 h, seed) is varied after the run.
