# Pre-registration — confirmation of the basis-tilt fade filter on the untouched 2024-25 year (2026-11-04)

Written BEFORE `venue_confirm.py` exists and before any venue series of the confirmation window was downloaded or read. Approved by the user ("lets try that and check it").

## The lead
`venue_dispersion_20261104.md`, Test A: the variant selected on the fit half, `basis_disp_tilt_1` (the 4-hour change of Bybit's premium minus the other venues' basis, in sd units, FADED: a rise favours a SHORT on Bybit, a fall a LONG, |tilt| > 1.0), held on the unseen half — aligned n=135 · +0.076R · PF 1.22 · 85 % weeks green vs all −0.118R (gap +0.194R), both directions improved — and was graded **NO** on profit factor alone. 114 independent bets, 95 % CI of the per-bet mean −0.10 … +0.22R. This is one selected variant out of nine trials on a year that was then read; the confirmation below asks whether the same rule holds on a year it never saw.

## Population (fixed, already built)
`logs/backtest_reports/orderbook_fade_20261103_trades.json`: 3,687 filled trades of the six live rules, signals 2024-10-20 → 2025-10-19 UTC, 26 symbols (AKE / US / XPL not yet listed), rebuilt by the current parity-fixed engine with `deriv=None`. The year has been read once for the order-book "against" bucket (NO); no venue series of it has ever been computed. Halves: H1 = signals before 2025-04-20, H2 = from 2025-04-20.

## Data
`venue_data.py` series for the 26 symbols, window 2024-10-01 → 2025-10-20 (a 7-day warm-up before the first signal), stored under tag `20241001_20251020`. Same sources, reducers and timestamp rules as the first study. Symbols listed later on a venue simply have no leg until then; a trade with no feature is `no_data` and leaves the denominator.

## The one variant
`basis_disp_tilt` exactly as pre-registered on 2026-11-03 (Z_BARS 672 boundaries, TILT_BARS 16, TILT_MIN 100 changes), threshold **1.0**, fade orientation. No other threshold, bar count, orientation or feature is computed. One trial.

## Grading (whole year unless stated; `all` = trades with data)
1. aligned n ≥ 100
2. gap = aligned net − all net ≥ +0.05R
3. aligned net > 0
4. aligned net PF ≥ 1.3
5. aligned weeks green ≥ 55 %
6. gap ≥ 0 in H1 and in H2
7. against not better than aligned
8. gap ≥ 0 within longs and within shorts (the composition check the fade-the-book lead failed)

**PASS** = all eight → the filter goes to the shadow lane with its own forward clock: every candidate is stamped with the tilt at scan time from the three venues' public endpoints; the Monday review reports aligned vs all; no pick changes until the forward log clears the quality yardstick and the user decides.
**REPLICATED, BELOW BAR** = 1, 2, 3, 6, 7, 8 hold and 4 or 5 fails → the effect exists out of sample on two separate years but does not meet the yardstick; written up, the user decides whether to stamp it forward as instrumentation.
**NO** otherwise → the lead is closed; the dispersion input is closed with it.

## Honest priors
A selected variant shrinks out of sample (winner's curse): expect a gap below +0.19R. With ~500 aligned trades, a true gap of +0.05R would be seen; PF ≥ 1.3 was not reached even on the fit year's unseen half, so PASS is the less likely outcome and REPLICATED, BELOW BAR the more likely one if the effect is real.
