# PRE-REGISTRATION — daily cross-sectional long/short book (2026-10-20)

_Written before any code for this study existed and before any result was seen. User decision 2026-10-19 night: "do both — the daily long/short book and the weekly carry line." The bar below may not be changed after the run; a later change is a new study with its own trial count._

## Why

The 2026-10-19 replay showed the daily directional book loses over six months (526 picks, −0.087R), and our signal entries are indistinguishable from random entries at every target size (`win_rate_geometry.py`). The research write-up (`research/edge_sources_20261019.md`) found that inputs with evidence at our horizon are cross-sectional (rank coins against each other, market-neutral). This study asks whether a **daily-rebalanced** long/short book on such an input clears the same portfolio bar as paper test #2.

## Honest priors (stated before the run)

- **S1 basis.** Chi, Hao, Hu & Ran (2023, *J. Futures Markets* 43(8)) report basis as the strongest cross-sectional signal in crypto futures, daily factor returns much stronger than weekly, 2017–21 sample. Full text not accessible: the basis definition and the sign were **not** verified; the sign used here is the commodity-futures convention the paper says it is consistent with. Against: our 2026-10-04 carry test (long the 10 most negative-funding perps, BTC-hedged, weekly) was Sharpe −0.64 / MDD 78% — that is close to S1's long leg, and it lost. Carry has decayed since 2024 (Borri et al. 2025, WP). Prior: low.
- **S2 BTC catch-up.** Guo, Sang, Tu & Wang (2024, *JEDC* 163) find cross-coin lead-lag in **minute** data lasting about ten minutes (working-paper abstract); a 2026 working paper (Khan) finds next-hour correlation ≈ 0. Nothing documents it at a daily horizon. The research summary of 2026-10-19 called it daily — that was wrong and is corrected in the write-up. Included because it costs nothing to test with data in hand. Prior: near zero.

## Data (frozen)

- Daily Bybit USDT-perp klines already cached by the momentum study (`logs/backtest_cache/xs_<SYMBOL>_D.json`, fetched 2026-10-04), bars 2025-04-12 → **2026-10-03** (same `PANEL_END` as `xs_momentum_v2_crypto.py`); funding settlements from `logs/backtest_cache/xs_funding_<SYMBOL>.json`. No new download.
- Universe: every cached symbol except Bybit's TradFi types and the pegged supplement listed in `logs/backtest_reports/xs_momentum_tradfi_list_20261004.json` (the crypto-only universe of paper test #2). Survivorship caveat as in that study: today's listings only.

## Rules (frozen)

Day *t* = the daily bar opening at *t* 00:00 UTC; it closes at *t*+1d 00:00 UTC. The book is set at that close using data up to and including bar *t*, and held over bar *t*+1.

- **Eligible on day t:** crypto-only; close of bar *t* present; first cached bar ≥ 30 days before *t*; trailing 7-day mean daily turnover ≥ $10M; plus the signal's own data requirement. Fewer than 20 eligible → no position that day.
- **Weights:** nd = ⌊n/10⌋ names per leg; each long +0.5 × min(1/nd, 0.10), each short −0.5 × min(1/nd, 0.10) (dollar-neutral, gross ≤ 1, 10%-of-leg cap — identical to paper test #2).
- **S1 `basis_24h`:** f = sum of the symbol's funding settlements with timestamp in (close_t − 24h, close_t]; requires ≥ 1 settlement in that window. **Long the nd lowest f, short the nd highest f.**
- **S2 `btc_catchup`:** r = daily close-to-close return; β = OLS slope of the coin's r on BTCUSDT's r over bars *t*−29 … *t* (≥ 25 valid pairs); signal = β · r_BTC,t − r_coin,t. **Long the nd highest, short the nd lowest.** BTCUSDT itself is not ranked.
- **P&L per day:** gross = Σ w · (close_{t+1}/close_t − 1) (missing next close → 0); turnover = Σ |w_t − drifted w_{t−1}|; cost = turnover × (0.055% taker + 0.03% slippage); funding = Σ w · (settlements in (close_t, close_{t+1}]) paid by longs / received by shorts (flat 0.01%/8h fallback when a symbol has no funding file). net = gross − cost − funding.
- **First rebalance:** the 31st bar of the panel; last: the second-to-last bar.

## Metrics

Daily net series → annualised Sharpe (mean/sd × √365), max drawdown of the compounded daily equity, % of 7-day blocks (from the first rebalance) with compounded net > 0 ("% weeks green"), % days green, annualised net and gross return, mean daily turnover. Halves = first and second half of the rebalance days.

**No-skill baseline:** the same book with a random ranking (S1's eligibility), 20 seeds; report the mean and 95th percentile of the full-period Sharpe.

## Decision (per signal; 2 judged trials)

- **SHIP-CANDIDATE** — full period, H1 and H2 each have net Sharpe ≥ 1.0, max drawdown ≤ 25% and ≥ 55% weeks green, **and** full-period Sharpe > the random baseline's 95th percentile → a daily forward paper test with its own bar, written before it starts; the user decides.
- **CANDIDATE** — net Sharpe ≥ 0.5 on both halves and full-period Sharpe > the baseline's 95th percentile → the user decides whether to paper it.
- **NO** — otherwise; that signal is closed.

Context only, not judged: the same books at maker cost (0.02% per unit turnover, no slippage). No parameter (window, decile, β window, cost) is varied for the verdict.

Multiple testing: 2 judged trials here, on top of 90 momentum/carry variants in the xs_momentum reports. At 1 trial a zero-edge daily series over ~500 days (≈ 1.4 years) shows annualised Sharpe ≥ 1.0 with p ≈ 0.12 (z = 1.0 × √1.4); the both-halves requirement and the baseline guard tighten that.
