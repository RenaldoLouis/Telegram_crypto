# Basis-tilt fade filter — confirmation on the untouched 2024-25 year (20261104)

Pre-registration: `logs/backtest_reports/prereg_venue_confirm_20261104.md` (written before this code and before the venue series of this window were downloaded). Population: `orderbook_fade_20261103_trades.json` (six live rules, signals 2024-10-20 → 2025-10-19, 26 symbols). One variant: `basis_disp_tilt` at 1.0, faded (a 4-hour rise of Bybit's premium over the other venues → short aligned; a fall → long aligned). Cells: n · profitable % · net R per trade (the managed trade) · net PF · % of weeks green.

Trades: 3687 (5 without a feature, excluded).

| bucket | n | profitable | net R | PF | weeks green |
|---|---|---|---|---|---|
| all | 3682 | 54% | -0.102 | 0.78 | 26% |
| aligned | 513 | 58% | -0.054 | 0.87 | 28% |
| against | 514 | 52% | -0.148 | 0.70 | 37% |
| neutral | 2655 | 54% | -0.102 | 0.78 | 30% |

Gap (aligned − all): **+0.048R**

Checks: aligned_n_ge_100 ✓, gap_ge_0.05 ✗, aligned_net_gt_0 ✗, aligned_pf_ge_1.3 ✗, aligned_weeks_ge_55 ✗, gap_ge_0_in_both_halves ✓, against_not_better ✓, gap_ge_0_in_both_directions ✗

## Verdict: **NO**

| half | all | aligned | against |
|---|---|---|---|
| H1 | n=1766 -0.086R | n=252 · 59% · -0.016R · PF 0.96 · wk 22% | n=249 -0.157R |
| H2 | n=1916 -0.116R | n=261 · 57% · -0.090R · PF 0.80 · wk 37% | n=265 -0.139R |

| direction | all | aligned | against |
|---|---|---|---|
| long | n=2119 -0.158R | n=299 · 61% · -0.031R · PF 0.92 · wk 54% | n=288 -0.202R |
| short | n=1563 -0.025R | n=214 · 54% · -0.086R · PF 0.81 · wk 47% | n=226 -0.078R |

By rule (descriptive):
| rule | all | aligned | against |
|---|---|---|---|
| failed_breakout_short 4h | n=668 -0.088R | n=98 -0.105R | n=121 -0.168R |
| liquidity_sweep_long 1h | n=1560 -0.203R | n=239 -0.033R | n=203 -0.256R |
| range_reversion_long 4h | n=72 -0.222R | n=9 -0.343R | n=7 -0.364R |
| range_reversion_short 4h | n=85 -0.032R | n=11 -0.319R | n=17 -0.051R |
| rsi_bounce_long 4h | n=487 -0.007R | n=51 +0.036R | n=78 -0.046R |
| trend_pullback_short 4h | n=810 +0.027R | n=105 -0.044R | n=88 +0.040R |

---
1 trial. Nothing was varied after the run. Run time 5s.
