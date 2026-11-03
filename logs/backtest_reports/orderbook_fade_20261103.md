# Fade the book — confirmation on untouched data (20261103)

Pre-registration: `logs/backtest_reports/prereg_orderbook_fade_20261103.md` (frozen before the data was downloaded). Window: signals 2024-10-20 → 2025-10-19 UTC; six live rules, unified engine (limit-open entry, live levels), Binance bookDepth band 2 % / thr 0.1. 3687 filled trades, 19 without a snapshot.

Skipped (insufficient history in the window): AKEUSDT (22d 4h, 2154 15m bars), USUSDT (0d 4h, 0 15m bars), XPLUSDT (58d 4h, 5524 15m bars)

**Depth coverage (window):** 1000BONKUSDT 100%, 1000PEPEUSDT 100%, ADAUSDT 100%, AKEUSDT 6%, ARBUSDT 100%, BTCUSDT 100%, DOGEUSDT 99%, ENAUSDT 100%, ETHUSDT 100%, FARTCOINUSDT 83%, HBARUSDT 100%, INJUSDT 100%, NEARUSDT 100%, ONDOUSDT 100%, OPUSDT 100%, PENGUUSDT 83%, PUMPFUNUSDT 44%, SANDUSDT 99%, SOLUSDT 100%, STRKUSDT 99%, SUIUSDT 100%, TRXUSDT 100%, USELESSUSDT 17%, USUSDT 0%, WLDUSDT 100%, XLMUSDT 100%, XPLUSDT 16%, XRPUSDT 100%, ZECUSDT 100%

## The one test — against the book vs all

| bucket | result |
|---|---|
| all | n=3668 · 54% · **-0.101R** · PF 0.78 · weeks+ 26% · DD 403.4R |
| against | n=1058 · 56% · **-0.029R** · PF 0.93 · weeks+ 44% · DD 79.8R |
| aligned | n=1434 · 52% · **-0.189R** · PF 0.63 · weeks+ 32% · DD 282.9R |
| neutral | n=1176 · 56% · **-0.059R** · PF 0.87 · weeks+ 40% · DD 97.6R |

Gap (against − all): **+0.072R**

| half | all | against | aligned |
|---|---|---|---|
| H1 | n=1766 · 55% · **-0.086R** · PF 0.81 · weeks+ 26% · DD 173.2R | n=511 · 57% · **-0.009R** · PF 0.98 · weeks+ 46% · DD 34.7R | n=693 · 53% · **-0.166R** · PF 0.66 · weeks+ 30% · DD 130.7R |
| H2 | n=1902 · 54% · **-0.115R** · PF 0.76 · weeks+ 26% · DD 237.5R | n=547 · 55% · **-0.047R** · PF 0.89 · weeks+ 44% · DD 59.9R | n=741 · 52% · **-0.211R** · PF 0.60 · weeks+ 33% · DD 159.3R |

Checks: against_n_ge_100 ✓, against_net_gt_0 ✗, gap_ge_0.05 ✓, against_pf_ge_1.3 ✗, against_weeks_ge_55 ✗, gap_ge_0_in_both_halves ✓

### Verdict: **NO**

## Descriptive only (not graded)

| rule | all | against |
|---|---|---|
| failed_breakout_short 4h | n=667 · 53% · **-0.090R** · PF 0.81 · weeks+ 48% · DD 88.0R | n=472 · 54% · **-0.052R** · PF 0.89 · weeks+ 53% · DD 47.6R |
| liquidity_sweep_long 1h | n=1553 · 52% · **-0.201R** · PF 0.62 · weeks+ 34% · DD 326.1R | n=40 · 65% · **-0.024R** · PF 0.94 · weeks+ 45% · DD 4.6R |
| range_reversion_long 4h | n=72 · 54% · **-0.222R** · PF 0.55 · weeks+ 46% · DD 17.0R | n=5 · 40% · **-0.251R** · PF 0.46 · weeks+ 0% · DD 1.3R |
| range_reversion_short 4h | n=83 · 64% · **-0.024R** · PF 0.94 · weeks+ 60% · DD 10.4R | n=36 · 61% · **-0.029R** · PF 0.93 · weeks+ 68% · DD 4.9R |
| rsi_bounce_long 4h | n=486 · 57% · **-0.009R** · PF 0.97 · weeks+ 48% · DD 25.4R | n=27 · 52% · **-0.015R** · PF 0.92 · weeks+ 45% · DD 2.5R |
| trend_pullback_short 4h | n=807 · 57% · **+0.028R** · PF 1.07 · weeks+ 51% · DD 66.5R | n=478 · 56% · **-0.004R** · PF 0.99 · weeks+ 50% · DD 44.2R |

| direction | all | against |
|---|---|---|
| long | n=2111 · 53% · **-0.157R** · PF 0.67 · weeks+ 34% · DD 348.5R | n=72 · 58% · **-0.036R** · PF 0.88 · weeks+ 50% · DD 8.4R |
| short | n=1557 · 56% · **-0.025R** · PF 0.94 · weeks+ 49% · DD 127.1R | n=986 · 56% · **-0.028R** · PF 0.94 · weeks+ 44% · DD 77.8R |

`tilt_2_0.1` against: n=206 · 52% · **-0.071R** · PF 0.84 · weeks+ 51% · DD 24.7R vs all-with-tilt n=3518 · 54% · **-0.109R** · PF 0.77 · weeks+ 25% · DD 410.5R

---
1 trial. Nothing was varied after the run. Run time 95s.
