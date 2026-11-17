# Stablecoin supply flows (DefiLlama) as a new input (20261117)

Pre-registration: `logs/backtest_reports/prereg_stablecoin_20261117.md` (written before this code). Data: total USD stablecoin supply and USDT supply, daily (`stablecoin_data.py`), the row dated D used from D + 1 day; one market-wide value for every coin; every feature is read as FOLLOW THE MONEY (positive = supply growing faster than usual = favours a LONG). Cells: n · profitable % · net R per trade (the managed trade) · net PF (· % of weeks green). Fit half = OLDER + TRAIN; unseen half = TEST + H.

**Coverage (share of the study window with the feature defined):** stable_7d 100%, stable_30d 100%, usdt_7d 100%

## Test A — stablecoin supply as a filter on the live rules (3531 recorded trades)

| variant | fit: all | fit: aligned | fit: against | unseen: all | unseen: aligned | unseen: against | unseen gap |
|---|---|---|---|---|---|---|---|
| stable_7d_0.5 | n=2643 -0.064R | n=828 -0.003R | n=815 -0.060R | n=888 -0.118R | n=437 -0.161R | n=260 -0.078R | -0.043R |
| stable_7d_1 | n=2643 -0.064R | n=470 +0.085R | n=442 -0.137R | n=888 -0.118R | n=257 -0.102R | n=167 -0.149R | +0.016R |
| stable_30d_0.5 | n=2643 -0.064R | n=756 +0.017R | n=1104 -0.152R | n=888 -0.118R | n=398 -0.104R | n=335 -0.102R | +0.015R |
| stable_30d_1 | n=2643 -0.064R | n=563 +0.072R | n=833 -0.145R | n=888 -0.118R | n=196 -0.001R | n=142 -0.046R | +0.117R |
| usdt_7d_0.5 | n=2643 -0.064R | n=797 +0.051R | n=995 -0.133R | n=888 -0.118R | n=357 -0.153R | n=237 -0.093R | -0.034R |
| usdt_7d_1 **←selected** | n=2643 -0.064R | n=407 +0.120R | n=511 -0.133R | n=888 -0.118R | n=113 -0.415R | n=36 +0.076R | -0.297R |

**Selected on the fit half:** `usdt_7d_1` (fit gap +0.184R). Unseen half: aligned n=113 · 38% · -0.415R · PF 0.34 · wk 29% vs all n=888 · 53% · -0.118R · PF 0.74 · wk 15%; against n=36 · 64% · +0.076R · PF 1.22 · wk 71%.

Checks: aligned_n_ge_30 ✓, gap_ge_0.05 ✗, aligned_net_gt_0 ✗, aligned_pf_ge_1.3 ✗, gap_ge_0_in_TEST_and_H ✗, against_not_better ✗

Composition: unseen gap by direction — long -0.252R, short n/a → **carried by one direction only**

### Verdict A: **NO**

Per period (aligned vs all):
| period | all | aligned |
|---|---|---|
| OLDER | n=1452 -0.057R | n=179 +0.481R |
| TRAIN | n=1191 -0.074R | n=228 -0.164R |
| TEST | n=699 -0.126R | n=83 -0.422R |
| H | n=189 -0.091R | n=30 -0.396R |

Unseen half by rule (descriptive, not selected on):
| rule | all | aligned | against |
|---|---|---|---|
| failed_breakout_short 4h | n=178 -0.055R | n=0 | n=21 +0.448R |
| liquidity_sweep_long 1h | n=388 -0.193R | n=84 -0.473R | n=0 |
| range_reversion_long 4h | n=27 -0.125R | n=3 -0.087R | n=0 |
| range_reversion_short 4h | n=25 +0.232R | n=0 | n=3 +0.184R |
| rsi_bounce_long 4h | n=107 -0.064R | n=26 -0.268R | n=0 |
| trend_pullback_short 4h | n=163 -0.099R | n=0 | n=12 -0.601R |

Unseen half by direction:
| direction | all | aligned | against |
|---|---|---|---|
| long | n=522 -0.163R | n=113 -0.415R | n=0 |
| short | n=366 -0.055R | n=0 | n=36 +0.076R |

## Test B — stablecoin supply as a signal of its own (every closed 4h bar)

| variant | no-data closes | fit: signal | fit: random | unseen: signal | unseen: random | unseen: flipped |
|---|---|---|---|---|---|---|
| stable_7d_1 | 0 | n=3459 · 59% · +0.012R · PF 1.03 · wk 52% | n=10141 -0.048R | n=1859 · 62% · +0.050R · PF 1.13 · wk 58% | n=5454 -0.043R | n=1782 -0.158R |
| stable_30d_1 | 0 | n=5031 · 60% · +0.017R · PF 1.04 · wk 59% | n=14868 -0.041R | n=1438 · 58% · -0.028R · PF 0.94 · wk 62% | n=4236 -0.056R | n=1382 -0.079R |
| usdt_7d_1 **←selected** | 0 | n=3803 · 60% · +0.036R · PF 1.09 · wk 59% | n=11181 -0.056R | n=602 · 57% · -0.031R · PF 0.93 · wk 29% | n=1786 -0.088R | n=586 -0.094R |

**Selected on the fit half:** `usdt_7d_1`. Checks: n_ge_100 ✓, net_gt_0 ✗, pf_ge_1.3 ✗, weeks_green_ge_55 ✗, beats_random_by_0.05 ✓, net_gt_0_in_TEST_and_H ✗

### Verdict B: **NO**

| period | signal | random |
|---|---|---|
| OLDER | n=2092 · 61% · +0.079R · PF 1.19 · wk 67% | n=6180 -0.045R |
| TRAIN | n=1711 · 59% · -0.017R · PF 0.96 · wk 50% | n=5001 -0.069R |
| TEST | n=374 · 54% · -0.083R · PF 0.83 · wk 25% | n=1104 -0.083R |
| H | n=228 · 63% · +0.055R · PF 1.14 · wk 33% | n=682 -0.096R |

Unseen half by direction: long n=602 · 57% · -0.031R · PF 0.93 · wk 29%, short n=0

---
9 selected trials in total (≈ 0.45 false PASS expected at 5 % with no edge). Nothing was varied after the run. Run time 7s.
