# Pre-registration — cross-venue funding & basis dispersion as a new input (2026-11-03)

Written BEFORE `venue_data.py` / `venue_study.py` exist and before any feature of this data was computed. The input is new to the engine: it has only ever read Bybit's own funding and open interest (`derivs_data.py`; no edge 2026-09-23) and never compared Bybit with another venue. Same protocol, periods, bars and trade population as `prereg_orderbook_20261103.md` / `prereg_positioning_20261103.md`, so the three inputs are judged alike.

## Idea
A perp's funding and its premium over the index say how crowded its longs are on THAT venue. When Bybit's perp is richer (higher premium, longs paying more) than the same perp on Binance and OKX, the crowding is venue-specific: arbitrageurs sell the rich perp and buy the cheap one, so the Bybit perp — the instrument we trade — should converge down. Reading: a positive dispersion favours a SHORT on Bybit, a negative one a LONG (fade). The opposite reading (follow: Bybit leads) is reported as the `against` bucket in Test A and the `flipped` control in Test B, never selected.

## Data (`venue_data.py` → `logs/backtest_cache/venues/`, gitignored)
- **Bybit** (the venue traded): funding settlements from the existing `derivs_data` cache (`<SYM>_funding_20251021_20261021.json`, settlement timestamp = when the rate is known; the interval of a settlement = its spacing to the previous one, 1 h / 4 h / 8 h) and the public premium-index 15-minute kline (`/v5/market/premium-index-price-kline`: the close of the bar is the premium index at the bar's close).
- **Binance** USDT-M: monthly `fundingRate` archive (`calc_time`, `funding_interval_hours`, rate) and the monthly `premiumIndexKlines` 15-minute archive (close).
- **OKX**: 15-minute swap last-price candles and 15-minute index candles (`history-candles` / `history-index-candles`); basis = swap close / index close − 1. OKX funding is NOT used (the public history keeps ~3 months). USUSDT is not listed on OKX; a symbol listed on OKX after a bar simply has no OKX leg at that bar.
Window: bars 2025-11-01 → 2026-10-15 (the study window 2025-11-15 → 2026-10-14 plus the 7-day warm-up). Symbols: the 29 of the first study.

Every series is stored by the time it became known: a settlement at its timestamp, a 15-minute bar at its CLOSE. A feature at T reads only records with timestamp ≤ T.

## Features (at a signal close T)
- `fund_disp`: Bybit's last settled rate at or before T, normalised to an 8-hour equivalent (rate × 8 / interval hours), minus Binance's last settled rate at or before T, normalised the same way; in basis points. Each settlement must be at most 8 h 5 min old at T, else `no_data`.
- `basis_disp_z`: d(B) = Bybit premium close of the bar closing at B minus the mean of the other venues' basis for the same bar (Binance premium close, OKX basis; at least one must be present). The feature is the z-score of d at the last boundary ≤ T against its own trailing 7 days of boundaries (672; needs ≥ 400 present, sd > 0).
- `basis_disp_tilt`: d(T) − d(T − 4 h), divided by the sd of the same 4-hour changes over the trailing 7 days (needs ≥ 100 changes).
No data → `no_data`; the trade is excluded from that variant's denominator.

## Readings (signs fixed by trading logic, before the data)
All three features are FADED: aligned for a SHORT = feature > +thr (Bybit richer / Bybit longs paying more than elsewhere); aligned for a LONG = feature < −thr; `against` = the opposite beyond thr; `neutral` between.

## Test A — the input as a filter on the six live rules
Population: the 3,531 recorded trades of the first study (`unified_20261021_365d_trades.json`, six live rules, filled, 29 symbols, signals 2025-11-15 → 2026-10-14). Variants: `fund_disp` × thr {1, 2} bps per 8 h; `basis_disp_z` × thr {0.5, 1.0}; `basis_disp_tilt` × thr {0.5, 1.0} = 6. Selection on the fit half (OLDER + TRAIN): largest (aligned − all) gap with aligned n ≥ 60. Grading on the unseen half (TEST + H), all required: aligned n ≥ 30; gap ≥ +0.05R; aligned net > 0; aligned net PF ≥ 1.3; gap ≥ 0 in TEST and in H; against not better than aligned. → PASS / NO.

## Test B — the input as a signal of its own
At every closed 4h bar of the 29 symbols (2025-11-15 → 2026-10-14): side from the feature — feature > +thr → SHORT, < −thr → LONG. Variants: `fund_disp` 2 bps, `basis_disp_z` 1.0, `basis_disp_tilt` 1.0 = 3. Trade shape `orderbook_study.sim_book_trade` (limit at the first scored 15m open, stop 1 ATR(4h), T1 0.75R, T2 2R, trail, 2-day window), one open trade per symbol per variant. Controls: random side at the same closes (3 draws, seed 7) and the flipped sign. Selection on the fit half (largest net with n ≥ 100). Grading on the unseen half, all required: n ≥ 100; net > 0; PF ≥ 1.3; ≥ 55 % weeks green; net ≥ random + 0.05R; net > 0 in TEST and in H. → PASS / NO.

**Trials:** 9 (≈ 0.45 false PASS expected at 5 % with no edge). Nothing is varied after the run; anything found afterwards is a post-hoc lead and needs its own pre-registration on untouched data.

## Follow-up rules
PASS on A → the filter goes to the shadow lane with its own forward clock, fed live from the same public endpoints (Bybit premium kline / funding; Binance `fapi` premium index + funding; OKX swap/index tickers) at scan time; changes no pick. PASS on B → a shadow rule of its own, same clock. NO → closed, written up in `progress.md`. Binance and OKX are SOURCES of their own legs here (not proxies), so a PASS needs no on-venue re-confirmation of the data itself — only the forward clock.

## Honest priors
On the majors cross-venue basis is arbitraged within minutes, far below a 4h bar; a 4-hour effect can only live on the alts, where venue-specific premiums persist for hours around listings and liquidity gaps. The lead-lag study (2026-10-20) found cross-venue effects at the minute scale only. Expected: NO on both.
