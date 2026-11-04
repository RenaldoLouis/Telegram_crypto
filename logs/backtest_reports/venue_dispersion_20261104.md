# Cross-venue funding & basis dispersion as a new input (20261104)

Pre-registration: `logs/backtest_reports/prereg_venue_dispersion_20261103.md` (written before this code). Data: Bybit vs Binance vs OKX funding settlements and 15-minute premium/basis (`venue_data.py`); every feature is FADED (positive = Bybit richer than the other venues → favours a SHORT on Bybit). Cells: n · profitable % · net R per trade (the managed trade) · net PF (· % of weeks green). Fit half = OLDER + TRAIN; unseen half = TEST + H.

**Coverage (15m boundaries with a basis dispersion / with the OKX leg):** 1000BONKUSDT 100%/100%, 1000PEPEUSDT 100%/100%, ADAUSDT 100%/100%, AKEUSDT 100%/8%, ARBUSDT 100%/100%, BTCUSDT 100%/100%, DOGEUSDT 100%/100%, ENAUSDT 100%/100%, ETHUSDT 100%/100%, FARTCOINUSDT 100%/100%, HBARUSDT 100%/100%, INJUSDT 100%/100%, NEARUSDT 100%/100%, ONDOUSDT 100%/100%, OPUSDT 100%/100%, PENGUUSDT 100%/100%, PUMPFUNUSDT 100%/100%, SANDUSDT 100%/100%, SOLUSDT 100%/100%, STRKUSDT 100%/100%, SUIUSDT 100%/100%, TRXUSDT 100%/100%, USELESSUSDT 100%/100%, USUSDT 91%/0%, WLDUSDT 100%/100%, XLMUSDT 100%/100%, XPLUSDT 100%/100%, XRPUSDT 100%/100%, ZECUSDT 100%/100%

## Test A — dispersion as a filter on the live rules (3531 recorded trades)

| variant | fit: all | fit: aligned | fit: against | unseen: all | unseen: aligned | unseen: against | unseen gap |
|---|---|---|---|---|---|---|---|
| fund_disp_1 | n=2643 -0.064R | n=247 -0.146R | n=327 -0.069R | n=888 -0.118R | n=99 -0.111R | n=89 -0.134R | +0.008R |
| fund_disp_2 | n=2643 -0.064R | n=85 -0.132R | n=115 -0.070R | n=888 -0.118R | n=43 -0.014R | n=31 -0.132R | +0.104R |
| basis_disp_z_0.5 | n=2643 -0.064R | n=748 -0.065R | n=824 -0.105R | n=888 -0.118R | n=271 -0.024R | n=249 -0.170R | +0.095R |
| basis_disp_z_1 | n=2643 -0.064R | n=367 -0.076R | n=433 -0.156R | n=888 -0.118R | n=131 +0.058R | n=138 -0.153R | +0.177R |
| basis_disp_tilt_0.5 | n=2643 -0.064R | n=758 -0.024R | n=832 -0.064R | n=888 -0.118R | n=268 -0.056R | n=259 -0.166R | +0.062R |
| basis_disp_tilt_1 **←selected** | n=2643 -0.064R | n=357 +0.024R | n=426 -0.137R | n=888 -0.118R | n=135 +0.076R | n=128 -0.164R | +0.194R |

**Selected on the fit half:** `basis_disp_tilt_1` (fit gap +0.088R). Unseen half: aligned n=135 · 66% · +0.076R · PF 1.22 · wk 85% vs all n=888 · 53% · -0.118R · PF 0.74 · wk 15%; against n=128 · 48% · -0.164R · PF 0.66 · wk 31%.

Checks: aligned_n_ge_30 ✓, gap_ge_0.05 ✓, aligned_net_gt_0 ✓, aligned_pf_ge_1.3 ✗, gap_ge_0_in_TEST_and_H ✓, against_not_better ✓

### Verdict A: **NO**

Per period (aligned vs all):
| period | all | aligned |
|---|---|---|
| OLDER | n=1452 -0.057R | n=173 +0.037R |
| TRAIN | n=1191 -0.074R | n=184 +0.011R |
| TEST | n=699 -0.126R | n=111 +0.102R |
| H | n=189 -0.091R | n=24 -0.046R |

Unseen half by rule (descriptive, not selected on):
| rule | all | aligned | against |
|---|---|---|---|
| failed_breakout_short 4h | n=178 -0.055R | n=17 +0.187R | n=28 -0.249R |
| liquidity_sweep_long 1h | n=388 -0.193R | n=72 -0.019R | n=47 -0.264R |
| range_reversion_long 4h | n=27 -0.125R | n=4 -0.327R | n=6 -0.090R |
| range_reversion_short 4h | n=25 +0.232R | n=6 +0.604R | n=6 +0.605R |
| rsi_bounce_long 4h | n=107 -0.064R | n=15 +0.254R | n=16 +0.004R |
| trend_pullback_short 4h | n=163 -0.099R | n=21 +0.109R | n=25 -0.189R |

Unseen half by direction:
| direction | all | aligned | against |
|---|---|---|---|
| long | n=522 -0.163R | n=91 +0.013R | n=69 -0.187R |
| short | n=366 -0.055R | n=44 +0.207R | n=59 -0.136R |

## Test B — dispersion as a signal of its own (every closed 4h bar)

| variant | no-data closes | fit: signal | fit: random | unseen: signal | unseen: random | unseen: flipped |
|---|---|---|---|---|---|---|
| fund_disp_2 **←selected** | 0 | n=1376 · 56% · -0.044R · PF 0.90 · wk 44% | n=4042 -0.046R | n=461 · 52% · -0.132R · PF 0.72 · wk 8% | n=1354 -0.064R | n=443 +0.060R |
| basis_disp_z_1 | 37 | n=5536 · 55% · -0.067R · PF 0.86 · wk 25% | n=16254 -0.044R | n=1964 · 57% · -0.037R · PF 0.92 · wk 23% | n=5759 -0.033R | n=1878 -0.054R |
| basis_disp_tilt_1 | 22 | n=5324 · 56% · -0.047R · PF 0.90 · wk 33% | n=15655 -0.041R | n=1825 · 56% · -0.058R · PF 0.87 · wk 15% | n=5337 -0.037R | n=1736 -0.040R |

**Selected on the fit half:** `fund_disp_2`. Checks: n_ge_100 ✓, net_gt_0 ✗, pf_ge_1.3 ✗, weeks_green_ge_55 ✗, beats_random_by_0.05 ✗, net_gt_0_in_TEST_and_H ✗

### Verdict B: **NO**

| period | signal | random |
|---|---|---|
| OLDER | n=662 · 54% · -0.083R · PF 0.82 · wk 40% | n=1954 -0.031R |
| TRAIN | n=714 · 58% · -0.008R · PF 0.98 · wk 53% | n=2088 -0.061R |
| TEST | n=374 · 53% · -0.138R · PF 0.71 · wk 10% | n=1102 -0.095R |
| H | n=87 · 52% · -0.106R · PF 0.78 · wk 0% | n=252 +0.074R |

Unseen half by direction: long n=247 · 53% · -0.117R · PF 0.75 · wk 23%, short n=214 · 51% · -0.149R · PF 0.69 · wk 25%

---
9 selected trials in total (≈ 0.45 false PASS expected at 5 % with no edge). Nothing was varied after the run. Run time 119s.
