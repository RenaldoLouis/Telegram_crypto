# Order-book depth as a new input (20261103)

Pre-registration: `logs/backtest_reports/prereg_orderbook_20261103.md` (written before this code). Data: Binance USDT-M `bookDepth` snapshots (PROXY — Bybit publishes none), reduced by `orderbook_data.py`. Cells: n · profitable % · net R per trade (the managed trade, maker entry) · net profit factor (· % of weeks green). Fit half = OLDER + TRAIN; unseen half = TEST + H.

**Depth coverage:** 1000BONKUSDT 97%, 1000PEPEUSDT 97%, ADAUSDT 97%, AKEUSDT 97%, ARBUSDT 97%, BTCUSDT 97%, DOGEUSDT 97%, ENAUSDT 97%, ETHUSDT 97%, FARTCOINUSDT 97%, HBARUSDT 97%, INJUSDT 97%, NEARUSDT 97%, ONDOUSDT 97%, OPUSDT 97%, PENGUUSDT 97%, PUMPFUNUSDT 97%, SANDUSDT 97%, SOLUSDT 97%, STRKUSDT 97%, SUIUSDT 97%, TRXUSDT 97%, USELESSUSDT 97%, USUSDT 89%, WLDUSDT 97%, XLMUSDT 97%, XPLUSDT 97%, XRPUSDT 97%, ZECUSDT 97%

## Test A — the book as a filter on the live rules (3531 recorded trades)

| variant | fit: all | fit: aligned | fit: against | unseen: all | unseen: aligned | unseen: against | unseen gap |
|---|---|---|---|---|---|---|---|
| imb_1_0.1 | n=2580 -0.065R | n=690 -0.113R | n=449 -0.053R | n=869 -0.107R | n=190 -0.124R | n=171 -0.035R | -0.017R |
| imb_1_0.2 | n=2580 -0.065R | n=219 -0.023R | n=133 -0.132R | n=869 -0.107R | n=74 -0.242R | n=74 +0.181R | -0.135R |
| imb_2_0.1 | n=2580 -0.065R | n=866 -0.108R | n=476 +0.038R | n=869 -0.107R | n=225 -0.148R | n=167 +0.056R | -0.041R |
| imb_2_0.2 | n=2580 -0.065R | n=234 -0.039R | n=119 -0.058R | n=869 -0.107R | n=78 -0.254R | n=67 +0.123R | -0.147R |
| tilt_1_0.1 **←selected** | n=2082 -0.066R | n=126 +0.178R | n=198 -0.082R | n=869 -0.107R | n=52 -0.292R | n=122 -0.024R | -0.185R |
| tilt_1_0.2 | n=2082 -0.066R | n=33 +0.332R | n=48 -0.038R | n=869 -0.107R | n=14 -0.551R | n=39 +0.059R | -0.444R |
| tilt_2_0.1 | n=2082 -0.066R | n=67 +0.050R | n=101 +0.007R | n=869 -0.107R | n=32 -0.384R | n=75 -0.080R | -0.277R |
| tilt_2_0.2 | n=2082 -0.066R | n=14 +0.108R | n=18 +0.184R | n=869 -0.107R | n=3 -0.047R | n=19 -0.186R | +0.060R |

**Selected on the fit half:** `tilt_1_0.1` (fit gap +0.244R). Unseen half: aligned n=52 · 44% · -0.292R · PF 0.43 · wk 33% vs all n=869 · 54% · -0.107R · PF 0.76 · wk 23%; against n=122 · 57% · -0.024R · PF 0.94 · wk 46%.

Checks: aligned_n_ge_30 ✓, gap_ge_0.05 ✗, aligned_net_gt_0 ✗, aligned_pf_ge_1.3 ✗, gap_ge_0_in_TEST_and_H ✗, against_not_better ✗

### Verdict A: **NO**

Per period (aligned vs all):
| period | all | aligned |
|---|---|---|
| OLDER | n=1131 -0.060R | n=67 +0.209R |
| TRAIN | n=951 -0.074R | n=59 +0.143R |
| TEST | n=699 -0.126R | n=47 -0.357R |
| H | n=170 -0.030R | n=5 +0.326R |

Unseen half by rule (descriptive, not selected on):
| rule | all | aligned | against |
|---|---|---|---|
| failed_breakout_short 4h | n=177 -0.049R | n=16 -0.008R | n=28 -0.082R |
| liquidity_sweep_long 1h | n=375 -0.177R | n=15 -0.385R | n=62 -0.086R |
| range_reversion_long 4h | n=26 -0.089R | n=1 -1.048R | n=4 +0.251R |
| range_reversion_short 4h | n=25 +0.232R | n=3 -0.109R | n=4 +0.714R |
| rsi_bounce_long 4h | n=103 -0.049R | n=5 -0.646R | n=10 +0.050R |
| trend_pullback_short 4h | n=163 -0.099R | n=12 -0.388R | n=14 +0.027R |

Unseen half by direction:
| direction | all | aligned | against |
|---|---|---|---|
| long | n=504 -0.147R | n=21 -0.479R | n=76 -0.050R |
| short | n=365 -0.052R | n=31 -0.165R | n=46 +0.020R |

## Test B — the book as a signal of its own (every closed 4h bar, band 2 %)

| variant | no-data closes | fit: book | fit: random | unseen: book | unseen: random | unseen: flipped |
|---|---|---|---|---|---|---|
| imb_0.2 | 1176 | n=2584 · 55% · -0.063R · PF 0.87 · wk 33% | n=7562 -0.048R | n=980 · 56% · -0.054R · PF 0.88 · wk 38% | n=2894 -0.047R | n=944 -0.042R |
| imb_0.3 | 1176 | n=723 · 55% · -0.060R · PF 0.87 · wk 44% | n=2130 -0.032R | n=530 · 55% · -0.089R · PF 0.81 · wk 23% | n=1556 -0.038R | n=509 -0.012R |
| tilt_0.1 **←selected** | 7879 | n=1445 · 57% · -0.016R · PF 0.96 · wk 42% | n=4261 -0.041R | n=727 · 59% · -0.017R · PF 0.96 · wk 62% | n=2157 -0.023R | n=707 -0.044R |
| tilt_0.2 | 7879 | n=310 · 54% · -0.076R · PF 0.84 · wk 44% | n=925 -0.038R | n=189 · 57% · -0.052R · PF 0.88 · wk 46% | n=564 -0.048R | n=187 +0.011R |

**Selected on the fit half:** `tilt_0.1`. Checks: n_ge_100 ✓, net_gt_0 ✗, pf_ge_1.3 ✗, weeks_green_ge_55 ✓, beats_random_by_0.05 ✗, net_gt_0_in_TEST_and_H ✗

### Verdict B: **NO**

| period | book | random |
|---|---|---|
| OLDER | n=747 · 56% · -0.034R · PF 0.92 · wk 40% | n=2204 -0.031R |
| TRAIN | n=698 · 58% · +0.004R · PF 1.01 · wk 47% | n=2057 -0.052R |
| TEST | n=590 · 58% · -0.045R · PF 0.89 · wk 50% | n=1750 -0.043R |
| H | n=137 · 62% · +0.103R · PF 1.26 · wk 100% | n=407 +0.062R |

Unseen half by direction: long n=347 · 61% · +0.047R · PF 1.12 · wk 54%, short n=380 · 57% · -0.076R · PF 0.83 · wk 54%

---
12 selected trials in total (≈ 0.6 false PASS expected at 5 % with no edge). Nothing was varied after the run. Run time 22s.
