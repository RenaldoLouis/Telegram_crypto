# Crowd & top-trader positioning as a new input (20261103)

Pre-registration: `logs/backtest_reports/prereg_positioning_20261103.md` (written before this code). Data: Binance USDT-M `metrics` (global long/short ACCOUNT ratio = the crowd, faded; top-trader long/short POSITION ratio = followed), reduced by `positioning_data.py`. Cells: n · profitable % · net R per trade (the managed trade) · net PF (· % of weeks green). Fit half = OLDER + TRAIN; unseen half = TEST + H.

**Metrics coverage:** 1000BONKUSDT 100%, 1000PEPEUSDT 100%, ADAUSDT 100%, AKEUSDT 100%, ARBUSDT 100%, BTCUSDT 100%, DOGEUSDT 100%, ENAUSDT 100%, ETHUSDT 100%, FARTCOINUSDT 100%, HBARUSDT 100%, INJUSDT 100%, NEARUSDT 100%, ONDOUSDT 100%, OPUSDT 100%, PENGUUSDT 100%, PUMPFUNUSDT 100%, SANDUSDT 100%, SOLUSDT 100%, STRKUSDT 100%, SUIUSDT 100%, TRXUSDT 100%, USELESSUSDT 100%, USUSDT 92%, WLDUSDT 100%, XLMUSDT 100%, XPLUSDT 100%, XRPUSDT 100%, ZECUSDT 100%

## Test A — positioning as a filter on the live rules (3531 recorded trades)

| variant | fit: all | fit: aligned | fit: against | unseen: all | unseen: aligned | unseen: against | unseen gap |
|---|---|---|---|---|---|---|---|
| glob_z_0.5 | n=2643 -0.064R | n=909 -0.088R | n=1101 -0.037R | n=888 -0.118R | n=348 -0.158R | n=338 -0.062R | -0.039R |
| glob_z_1 | n=2643 -0.064R | n=613 -0.086R | n=755 -0.059R | n=888 -0.118R | n=238 -0.192R | n=225 -0.001R | -0.074R |
| top_z_0.5 | n=2643 -0.064R | n=997 -0.090R | n=945 -0.041R | n=888 -0.118R | n=340 -0.085R | n=325 -0.148R | +0.034R |
| top_z_1 | n=2643 -0.064R | n=647 -0.095R | n=636 -0.025R | n=888 -0.118R | n=217 -0.070R | n=221 -0.150R | +0.049R |
| glob_tilt_0.5 **←selected** | n=2643 -0.064R | n=818 -0.017R | n=697 -0.095R | n=888 -0.118R | n=290 -0.134R | n=212 -0.138R | -0.015R |
| glob_tilt_1 | n=2643 -0.064R | n=404 -0.021R | n=366 -0.090R | n=888 -0.118R | n=160 -0.144R | n=116 -0.136R | -0.025R |
| top_tilt_0.5 | n=2643 -0.064R | n=657 -0.120R | n=786 -0.013R | n=888 -0.118R | n=255 -0.116R | n=239 -0.045R | +0.002R |
| top_tilt_1 | n=2643 -0.064R | n=326 -0.114R | n=424 +0.008R | n=888 -0.118R | n=131 -0.142R | n=137 -0.029R | -0.023R |

**Selected on the fit half:** `glob_tilt_0.5` (fit gap +0.047R). Unseen half: aligned n=290 · 50% · -0.134R · PF 0.71 · wk 23% vs all n=888 · 53% · -0.118R · PF 0.74 · wk 15%; against n=212 · 55% · -0.138R · PF 0.70 · wk 15%.

Checks: aligned_n_ge_30 ✓, gap_ge_0.05 ✗, aligned_net_gt_0 ✗, aligned_pf_ge_1.3 ✗, gap_ge_0_in_TEST_and_H ✗, against_not_better ✓

### Verdict A: **NO**

Per period (aligned vs all):
| period | all | aligned |
|---|---|---|
| OLDER | n=1452 -0.057R | n=436 -0.016R |
| TRAIN | n=1191 -0.074R | n=382 -0.018R |
| TEST | n=699 -0.126R | n=233 -0.142R |
| H | n=189 -0.091R | n=57 -0.099R |

Unseen half by rule (descriptive, not selected on):
| rule | all | aligned | against |
|---|---|---|---|
| failed_breakout_short 4h | n=178 -0.055R | n=81 -0.028R | n=44 -0.192R |
| liquidity_sweep_long 1h | n=388 -0.193R | n=116 -0.266R | n=106 -0.116R |
| range_reversion_long 4h | n=27 -0.125R | n=14 -0.225R | n=0 |
| range_reversion_short 4h | n=25 +0.232R | n=3 +0.374R | n=14 -0.039R |
| rsi_bounce_long 4h | n=107 -0.064R | n=26 -0.137R | n=21 -0.046R |
| trend_pullback_short 4h | n=163 -0.099R | n=50 -0.002R | n=27 -0.256R |

Unseen half by direction:
| direction | all | aligned | against |
|---|---|---|---|
| long | n=522 -0.163R | n=156 -0.241R | n=127 -0.104R |
| short | n=366 -0.055R | n=134 -0.009R | n=85 -0.187R |

## Test B — positioning as a signal of its own (every closed 4h bar)

| variant | no-data closes | fit: signal | fit: random | unseen: signal | unseen: random | unseen: flipped |
|---|---|---|---|---|---|---|
| glob_z_1 | 25 | n=6266 · 56% · -0.053R · PF 0.88 · wk 31% | n=18414 -0.045R | n=2252 · 54% · -0.101R · PF 0.79 · wk 8% | n=6581 -0.049R | n=2145 -0.008R |
| top_z_1 | 25 | n=6366 · 55% · -0.077R · PF 0.83 · wk 19% | n=18760 -0.040R | n=2261 · 56% · -0.058R · PF 0.87 · wk 8% | n=6645 -0.052R | n=2157 -0.028R |
| glob_tilt_1 **←selected** | 7 | n=5590 · 56% · -0.048R · PF 0.89 · wk 31% | n=16452 -0.048R | n=1947 · 56% · -0.063R · PF 0.86 · wk 8% | n=5723 -0.058R | n=1865 -0.034R |
| top_tilt_1 | 7 | n=5541 · 55% · -0.070R · PF 0.85 · wk 22% | n=16275 -0.043R | n=1943 · 56% · -0.055R · PF 0.88 · wk 31% | n=5704 -0.046R | n=1859 -0.034R |

**Selected on the fit half:** `glob_tilt_1`. Checks: n_ge_100 ✓, net_gt_0 ✗, pf_ge_1.3 ✗, weeks_green_ge_55 ✗, beats_random_by_0.05 ✗, net_gt_0_in_TEST_and_H ✗

### Verdict B: **NO**

| period | signal | random |
|---|---|---|
| OLDER | n=2992 · 56% · -0.039R · PF 0.91 · wk 40% | n=8791 -0.045R |
| TRAIN | n=2598 · 56% · -0.060R · PF 0.87 · wk 24% | n=7661 -0.053R |
| TEST | n=1530 · 56% · -0.061R · PF 0.87 · wk 10% | n=4495 -0.067R |
| H | n=417 · 54% · -0.072R · PF 0.85 · wk 0% | n=1228 -0.026R |

Unseen half by direction: long n=925 · 55% · -0.052R · PF 0.89 · wk 38%, short n=1022 · 56% · -0.074R · PF 0.84 · wk 46%

---
12 selected trials in total (≈ 0.6 false PASS expected at 5 % with no edge). Nothing was varied after the run. Run time 59s.
