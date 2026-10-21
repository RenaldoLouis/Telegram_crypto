# Trader's checklist study (20261021)

Pre-registration: `logs/backtest_reports/prereg_checklist_20261021.md` (written before this code). Cells: n · profitable % · net R per trade (managed trade, limit entry, net of costs). TRAIN < 2026-07-20 ≤ TEST < 2026-09-24 ≤ H (holdout, untouched by every filter study).

**Reproduction check** (my checklist vs the harness's recorded fields, primary trades): trend_4h 1884/1884 (100.0%), trend_1h 1884/1884 (100.0%), funding 1882/1884 (99.9%), oi_trapped 1881/1884 (99.8%), volume 1883/1884 (99.9%), entry 1845/1884 (97.9%).

## Verdicts

- **Arm A — checklist score picks our candidates (score ≥ 4, the TRAIN 75th percentile): BETTER-BUT-NEGATIVE**
- **Arm B — the trader's method on its own, 15m trigger entry: NO**

## Arm A — score as the selector

| period | all candidates | score ≥ N (pick) | Spearman ρ(score, net R) |
|---|---|---|---|
| TRAIN | n=1115 · 56.8% · -0.054R | n=406 · 62.3% · +0.079R | +0.119 |
| TEST | n=769 · 53.6% · -0.116R | n=288 · 54.9% · -0.103R | +0.015 |
| H | n=292 · 51.4% · -0.108R | n=111 · 58.6% · +0.028R | +0.119 |

### By score

| score | TRAIN | TEST | H |
|---|---|---|---|
| 0–2 | n=428 · 52.6% · -0.149R | n=275 · 52.7% · -0.095R | n=106 · 44.3% · -0.222R |
| 3 | n=281 · 55.2% · -0.102R | n=206 · 52.9% · -0.164R | n=75 · 50.7% · -0.149R |
| 4 | n=235 · 63.4% · +0.099R | n=163 · 49.1% · -0.216R | n=64 · 54.7% · -0.056R |
| 5 | n=118 · 62.7% · +0.080R | n=90 · 61.1% · +0.045R | n=37 · 64.9% · +0.202R |
| 6 | n=44 · 56.8% · -0.024R | n=29 · 65.5% · +0.055R | n=10 · 60.0% · -0.082R |
| 7–9 | n=9 · 55.6% · +0.025R | n=6 · 66.7% · -0.016R | n=0 |

### Each item alone (point earned vs not) — descriptive

| item | coverage | TRAIN with / without | TEST with / without | H with / without |
|---|---|---|---|---|
| trend_4h | 51% earn it | n=571 · 60.1% · +0.017R / n=544 · 53.3% · -0.129R | n=392 · 53.6% · -0.145R / n=377 · 53.6% · -0.086R | n=143 · 58.7% · +0.009R / n=149 · 44.3% · -0.221R |
| trend_1h | 29% earn it | n=341 · 58.7% · -0.043R / n=774 · 55.9% · -0.059R | n=215 · 53.5% · -0.122R / n=554 · 53.6% · -0.114R | n=80 · 57.5% · -0.030R / n=212 · 49.1% · -0.138R |
| ma200_d | 39% earn it | n=419 · 62.1% · +0.092R / n=696 · 53.6% · -0.142R | n=307 · 54.7% · -0.103R / n=462 · 52.8% · -0.126R | n=129 · 53.5% · -0.092R / n=163 · 49.7% · -0.121R |
| sd_zone | 9% earn it | n=94 · 60.6% · -0.011R / n=1021 · 56.4% · -0.058R | n=67 · 55.2% · -0.119R / n=702 · 53.4% · -0.116R | n=42 · 42.9% · -0.244R / n=250 · 52.8% · -0.086R |
| trendline | 10% earn it | n=105 · 60.0% · -0.027R / n=1010 · 56.4% · -0.057R | n=84 · 59.5% · -0.034R / n=685 · 52.8% · -0.127R | n=30 · 43.3% · -0.206R / n=262 · 52.3% · -0.097R |
| btc_4h | 51% earn it | n=581 · 58.5% · -0.024R / n=534 · 54.9% · -0.087R | n=390 · 52.8% · -0.142R / n=379 · 54.4% · -0.090R | n=148 · 58.8% · +0.020R / n=144 · 43.8% · -0.241R |
| funding | 37% earn it | n=405 · 57.5% · -0.015R / n=710 · 56.3% · -0.077R | n=292 · 55.8% · -0.093R / n=477 · 52.2% · -0.131R | n=109 · 56.0% · -0.025R / n=183 · 48.6% · -0.158R |
| oi_trapped | 34% earn it | n=387 · 54.5% · -0.068R / n=728 · 58.0% · -0.047R | n=263 · 55.9% · -0.081R / n=506 · 52.4% · -0.135R | n=94 · 52.1% · -0.131R / n=198 · 51.0% · -0.098R |
| volume | 39% earn it | n=409 · 59.4% · +0.012R / n=706 · 55.2% · -0.093R | n=337 · 54.6% · -0.082R / n=432 · 52.8% · -0.143R | n=104 · 45.2% · -0.178R / n=188 · 54.8% · -0.070R |

### By direction (pick vs all)

| period | longs: all → pick | shorts: all → pick |
|---|---|---|
| TRAIN | n=684 · 55.4% · -0.097R → n=183 · 62.8% · +0.050R | n=431 · 58.9% · +0.014R → n=223 · 61.9% · +0.102R |
| TEST | n=442 · 52.3% · -0.135R → n=144 · 53.5% · -0.116R | n=327 · 55.4% · -0.092R → n=144 · 56.2% · -0.090R |
| H | n=187 · 49.7% · -0.178R → n=63 · 58.7% · -0.054R | n=105 · 54.3% · +0.015R → n=48 · 58.3% · +0.135R |

## Arm B — the trader's method on its own

Setup = 4h trend + 1h trend + MA200 side + (zone or trendline) + score ≥ 6, one per symbol and direction per 24 h, 30 symbols; entry = the 15m trigger; control = 3 random twins per setup.

| period | setups | 15m trigger entry (judged) | random twins, same entry | next-open entry (diagnostic) |
|---|---|---|---|---|
| TRAIN | 192 | n=157 · 63.1% · +0.047R | n=451 · 56.3% · -0.087R | n=187 · 60.4% · +0.060R |
| TEST | 177 | n=131 · 55.7% · -0.090R | n=393 · 57.5% · -0.073R | n=173 · 62.4% · +0.083R |
| H | 40 | n=24 · 50.0% · -0.177R | n=92 · 54.3% · -0.148R | n=39 · 41.0% · -0.186R |

| period | longs (trigger) | shorts (trigger) |
|---|---|---|
| TRAIN | n=19 · 73.7% · +0.124R | n=138 · 61.6% · +0.037R |
| TEST | n=65 · 49.2% · -0.156R | n=66 · 62.1% · -0.024R |
| H | n=17 · 47.1% · -0.183R | n=7 · 57.1% · -0.160R |

**Trigger outcomes:** filled 312, invalidated 13, no_trigger 69, unfilled 15.

Two judged trials (Arm A, Arm B); everything else is descriptive. Nothing was varied after the run. Control seed 21. Daily candles cached by `ub.fetch_closed_klines` (logs/backtest_cache/unified/).

_Generated by `checklist_study.py` in 166s._

## Post-hoc (NOT judged — threshold chosen after seeing the results; 4 thresholds × directions × rules were looked at)

| cut | TRAIN | TEST | H |
|---|---|---|---|
| score ≥ 3 | n=687 · 59.4% · +0.005R | n=494 · 54.0% · -0.128R | n=186 · 55.4% · -0.044R |
| score ≥ 4 (pre-registered N) | n=406 · 62.3% · +0.079R | n=288 · 54.9% · -0.103R | n=111 · 58.6% · +0.028R |
| score ≥ 5 | n=171 · 60.8% · +0.050R | n=125 · 62.4% · +0.045R | n=47 · 63.8% · +0.142R |
| score ≥ 6 | n=53 · 56.6% · -0.016R | n=35 · 65.7% · +0.043R | n=10 · 60.0% · -0.082R |
| score ≥ 5, longs | n=64 · 62.5% · +0.081R | n=57 · 66.7% · +0.112R | n=25 · 76.0% · +0.241R |
| score ≥ 5, shorts | n=107 · 59.8% · +0.032R | n=68 · 58.8% · -0.012R | n=22 · 50.0% · +0.030R |
| score ≥ 5, failed_breakout_short 4h | n=19 · 63.2% · +0.137R | n=7 · 57.1% · +0.065R | n=3 · 66.7% · +0.285R |
| score ≥ 5, liquidity_sweep_long 1h | n=64 · 62.5% · +0.081R | n=56 · 66.1% · +0.106R | n=24 · 79.2% · +0.295R |
| score ≥ 5, range_reversion_long 4h | n=0 | n=1 · 100.0% · +0.484R | n=0 |
| score ≥ 5, range_reversion_short 4h | n=5 · 100.0% · +0.820R | n=5 · 60.0% · -0.206R | n=1 · 100.0% · +1.119R |
| score ≥ 5, rsi_bounce_long 4h | n=0 | n=0 | n=1 · 0.0% · -1.061R |
| score ≥ 5, trend_pullback_short 4h | n=83 · 56.6% · -0.039R | n=56 · 58.9% · -0.004R | n=18 · 44.4% · -0.073R |
Score ≥ 5 is positive in all three periods, carried by `liquidity_sweep_long` 1h. It can only become a candidate through its own pre-registered test on data not used here (an older untouched period and/or forward).
