# Pre-registration — options-implied volatility (Deribit DVOL) as a new input (2026-11-17)

Written BEFORE `dvol_data.py` / `dvol_study.py` exist and before any feature of this data was computed. Week 3 of the weekly new-input cadence (`research/new_inputs_ledger.md`, first untried candidate). User 2026-11-17: "just choose whichever bring us closer to our goal". The engine has never read anything from the options market. Same protocol, periods, bars and trade population as `prereg_venue_dispersion_20261103.md`, so the inputs are judged alike.

## Idea
DVOL is Deribit's 30-day implied volatility index (the crypto VIX), built from BTC options prices. Implied vol jumps when traders pay up for protection — mostly in sell-offs — and fear premiums tend to be overpaid and to fade. Reading (fixed before the data): **high or rising implied vol, or implied vol far above realised vol, favours a LONG (fade the fear); low or falling implied vol favours a SHORT (complacency).** The opposite reading (follow the fear) is reported as the `against` bucket in Test A and the `flipped` control in Test B, never selected.

## Data (`dvol_data.py` → `logs/backtest_cache/dvol/`, gitignored)
- Deribit public `get_volatility_index_data`, currency BTC, resolution 1 h (OHLC). A bar is stored by its CLOSE time (open + 1 h); a feature at T reads only bars closed at or before T. Window fetched: 2025-10-01 → 2026-10-21 (the study window plus a 45-day warm-up).
- Realised vol for `vrp_z`: Bybit BTCUSDT 1h closes from the harness cache `BTCUSDT_60_20251021_20261021.json` (bar close time = open + 1 h).
- **Market-wide input:** every coin reads BTC's DVOL (ETH DVOL is not used, to keep one series and nine trials).

## Features (at a signal close T; z = against the trailing 30 days of hourly values, 720, needs ≥ 500 present and sd > 0)
- `dvol_z`: z-score of the last DVOL close ≤ T.
- `dvol_chg`: (DVOL(T) − DVOL(T − 24 h)) divided by the sd of the 24-hour changes over the trailing 30 days.
- `vrp_z`: z-score of VRP(T) = DVOL(T) − RV(T), RV = sd of the last 168 hourly log returns of BTCUSDT × √8760 × 100.
No data → `no_data`; the trade is excluded from that variant's denominator.

## Readings (signs fixed by trading logic, before the data)
All three features: positive favours a LONG. Aligned for a LONG = feature > +thr; aligned for a SHORT = feature < −thr; `against` = the opposite beyond thr; `neutral` between.

## Test A — the input as a filter on the six live rules
Population: the 3,531 recorded trades of the first study (`unified_20261021_365d_trades.json`, six live rules, filled, signals 2025-11-15 → 2026-10-14). Variants: each feature × thr {0.5, 1.0} = 6. Selection on the fit half (OLDER + TRAIN): largest (aligned − all) gap with aligned n ≥ 60. Grading on the unseen half (TEST + H), all required: aligned n ≥ 30; gap ≥ +0.05R; aligned net > 0; aligned net PF ≥ 1.3; gap ≥ 0 in TEST and in H; against not better than aligned. → PASS / NO. Composition check (reported, mandatory): the unseen gap by direction and by rule; a gap carried by one direction only is named in the verdict line (the order-book and basis-tilt leads both died of direction mix).

## Test B — the input as a signal of its own
At every closed 4h bar of the symbols with a harness cache (2025-11-15 → 2026-10-14): side from the feature — > +1.0 → LONG, < −1.0 → SHORT. Variants: the three features at thr 1.0 = 3. Trade shape `orderbook_study.sim_book_trade` (limit at the first scored 15m open, stop 1 ATR(4h), T1 0.75R, T2 2R, trail, 2-day window), one open trade per symbol per variant. Controls: random side at the same closes (3 draws, seed 7) and the flipped sign. Selection on the fit half (largest net with n ≥ 100). Grading on the unseen half, all required: n ≥ 100; net > 0; PF ≥ 1.3; ≥ 55 % weeks green; net ≥ random + 0.05R; net > 0 in TEST and in H. → PASS / NO.

**Trials:** 9 (≈ 0.45 false PASS expected at 5 % with no edge). Nothing is varied after the run; anything found afterwards is a post-hoc lead and needs its own pre-registration on untouched data.

## Follow-up rules
PASS on A or B → a pre-registered confirmation on an untouched window (DVOL exists from 2021; the 2024-25 year has been read by other studies, so the confirmation uses 2023-03 → 2024-10 or older, klines to be fetched), and only then a shadow lane with its own forward clock, fed live from the same public endpoint at scan time; changes no pick. NO → closed, written up in `progress.md` and the ledger.

## Honest priors
One market-wide number at a time: on a given 4h close every coin gets the same reading, so the effective number of independent observations is the number of distinct DVOL regimes (a few dozen over the year), not the trade count — a pass must survive the per-period and direction checks to mean anything. Implied vol rises in sell-offs, so `dvol_chg` is partly a lagged price-direction signal; the direction-composition check exists for exactly that. Expected: NO on both.
