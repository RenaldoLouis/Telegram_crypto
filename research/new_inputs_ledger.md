# New-input ledger — one new data input per week, pre-registered, graded within the week

_Started 2026-11-03 (user decision after the 2026-11-02 status: "one new input per week"). Protocol: the pre-registration is committed before any feature is computed; the fit half (OLDER + TRAIN) selects one variant, the unseen half (TEST + H) grades it; every bucket is checked for direction / rule / symbol / cluster composition; a lead is confirmed only on data no study has touched; verdicts come from the frozen bar, never from the number. Pass → shadow lane with its own clock; fail → written up here and closed. Zero hosted-model tokens, no order API, nothing live changes on a NO._

**Yardstick (2026-10-21):** net R per trade > 0 after costs, net PF ≥ 1.3, ≥ 55 % of weeks green, beats random entries with the same management by ≥ 0.05R; hit rate reported, not gated. The two study tests: **Test A** = the input as a filter on the 3,531 recorded live-rule trades (`unified_20261021_365d_trades.json`; "aligned" = the input agrees with the trade's side); **Test B** = the input as a 4h signal of its own (`orderbook_study.sim_book_trade`: limit at the first scored 15m open, 1-ATR stop, T1 0.75R, T2 2R, trail; random-side and flipped controls).

## Tally

| week | input | source (free, public) | Test A filter | Test B signal | confirmation | status |
|---|---|---|---|---|---|---|
| 1 (11-03) | resting order-book depth (±0.2–5 % of mid, 1-min) | Binance `bookDepth` archive (proxy; Bybit has none) | NO — selected gap reversed out of sample (−0.29R vs −0.11R) | NO — ≤ random + 0.03R | post-hoc "fade the book" → NO (lift was direction mix: 93 % shorts) | CLOSED |
| 1 (11-03) | crowd / top-trader positioning (7-day z, 4h tilt) | Binance `metrics` archive (5-min, the source itself) | NO — −0.134R vs −0.118R | NO — within 0.03R of random | — | CLOSED |
| 2 (11-04) | cross-venue funding & basis dispersion, faded | Bybit funding + premium-index kline; Binance funding + premium archives; OKX swap/index candles | NO by the bar — selected `basis_disp_tilt_1` +0.076R vs −0.118R (gap +0.19R, PF 1.22 < 1.3) | NO — `fund_disp_2` −0.132R vs random −0.064R | 2024-25 untouched year → NO (gap +0.05R, long-side only, book −0.054R) | CLOSED |

Trials: week 1 = 12 + 12 + 1 selected trials, week 2 = 9 + 1. Nothing passed. Nothing live changed.

## Week 1 — order book, fade-the-book, positioning (2026-11-03)

- **Order-book depth.** `orderbook_data.py` keeps the snapshot at each 15m boundary + the 15-minute mean for 29 symbols (store `logs/backtest_cache/orderbook/`, 665 MB incl. the 2024-25 year). Pre-registration `prereg_orderbook_20261103.md`; report `orderbook_20261103.md`. Resting depth as support/resistance (the trading-desk sign) adds nothing to the six live rules and is not a signal. Lesson kept: the "against" bucket looked better than "aligned" on every imbalance variant — that is what prompted the post-hoc fade cell.
- **Fade the book, confirmed on an untouched year.** `prereg_orderbook_fade_20261103.md`, `orderbook_fade_confirm.py`, report `orderbook_fade_20261103.md`: 3,687 filled trades of the six live rules rebuilt by the current engine for signals 2024-10-20 → 2025-10-19 (26 symbols). The +0.07R gap replicated in both halves, but 986 of 1,058 "against" trades were shorts and shorts simply lose less than longs that year; within shorts the book adds nothing (−0.028 vs −0.025R). **Composition trap:** a post-hoc bucket must be split by direction and rule before it is called a lead. This check is now part of every pre-registration.
- **Positioning.** `positioning_data.py` (84 MB), `prereg_positioning_20261103.md`, `positioning_study.py`, report `positioning_20261103.md`. Fading the crowd (global long/short account ratio) and following the top traders (position ratio), as z and tilt: nothing beats random; following top traders was +0.03/+0.05R out of sample but negative in sample, so never selectable.

## Week 2 — cross-venue funding & basis dispersion (2026-11-04/05)

- **Data.** `venue_data.py` (store `logs/backtest_cache/venues/`, 162 MB for two years, window `tag` keeps the study year and the untouched year apart). Bybit funding (interval inferred from spacing: 1h/4h/8h; 8h-normalised) + premium-index 15m kline; Binance monthly `fundingRate` / `premiumIndexKlines`; OKX 15m swap/index candles → basis (OKX funding history keeps only ~3 months, not used). Every row is stored by the time it became known; `VenueIndex` answers from rows ≤ T only. The three venues' premiums agree to ~0.5 bps on BTC. OKX gaps: USUSDT not listed, AKE from 2026-09, ZEC perp from 2025-11-06.
- **Features, all faded** (positive = Bybit richer than the other venues → favours a Bybit short): `fund_disp` (Bybit − Binance last settled rate, bps), `basis_disp_z` (Bybit premium − mean of the other venues' basis, 7-day z), `basis_disp_tilt` (its 4h change in sd units).
- **Study** (`prereg_venue_dispersion_20261103.md` 561269d, `venue_study.py`, report `venue_dispersion_20261104.md`). Test A: `basis_disp_tilt_1` was the first fit-selected variant to hold out of sample (+0.194R gap, both directions, 5/6 rules, 9/12 months, 95 % CI of the per-bet mean −0.10 … +0.22) and missed only PF (1.22). Funding dispersion itself adds nothing. Test B: the dispersion does not pick entries.
- **Confirmation** (`prereg_venue_confirm_20261104.md` f57d210, `venue_confirm.py`, report `venue_confirm_20261104.md`): one variant, eight checks, on the same 3,687-trade untouched year. Aligned n 513 · 58 % · −0.054R · PF 0.87 · 28 % weeks green vs all −0.102R; gap +0.048R (bar +0.05); against −0.148R. Ordering replicated in both halves, but the lift fell by three quarters and became long-only (longs +0.127R better, shorts −0.061R worse) → 3 of 8 checks → NO. Winner's curse on a selected variant.
- **Residual sign, recorded, not a product:** on both years a Bybit perp whose premium just fell against Binance/OKX is a slightly better long entry for `liquidity_sweep_long` 1h and `rsi_bounce_long` 4h. Too small to turn a −0.16R long book green; does not carry to shorts.

## Data that is no longer untouched

The 2024-10-20 → 2025-10-19 trade population (`orderbook_fade_20261103_trades.json`, klines tag `20240701_20251019`) has been read twice (fade-the-book, basis tilt). A future confirmation needs a window neither study read: e.g. 2023-10 → 2024-10 (Bybit klines + funding reach back; Binance depth/metrics/premium archives from 2023; OKX index candles deep).

## Candidates not yet tried (free unless noted)

- **Options-implied data** — Deribit DVOL / 25-delta skew / put-call flow for BTC and ETH (free public API; market-wide regime input, not per coin).
- **Stablecoin supply / market-cap flows** — USDT/USDC issuance and exchange balances (free aggregates; daily resolution).
- **Exchange reserve / on-chain flows** — paid (CryptoQuant, Glassnode); only if a free aggregate exists.
- **Binance taker buy/sell ratio** — same family as CVD (fork #4, closed 2026-10-16); low prior.

Closed by this cadence and not to be re-proposed without a new hypothesis: order-book depth (any reading), crowd/top-trader positioning, cross-venue funding or basis dispersion.
