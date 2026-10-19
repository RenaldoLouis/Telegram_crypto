# Scalp / hold-time study — 2026-10-19

Pre-registration: `logs/backtest_reports/prereg_scalp_study_20261019.md`. Universe 26 symbols (BTCUSDT, DOGEUSDT, SUIUSDT, XLMUSDT, ENAUSDT, HBARUSDT, TRXUSDT, NEARUSDT, OPUSDT, ARBUSDT, INJUSDT, 1000PEPEUSDT, PUMPFUNUSDT, FARTCOINUSDT, ZECUSDT, ONDOUSDT, WLDUSDT, SOXLUSDT, SKHYNIXUSDT, CASHCATUSDT, XPLUSDT, 1000BONKUSDT, AKEUSDT, KORUUSDT, USUSDT, SNDKUSDT); 2026-04-22 → 2026-10-19. Entry: limit at next 15m open, 2-bar wait, maker entry/targets, taker+slippage stops/expiry, funding. TRAIN = first 60% by signal time, TEST = last 40%. profitable = net R > 0.

## Study A — 15m scalp, whole position at the target, max hold 4h

TRAIN/TEST cut: 2026-08-13 13:45 UTC.

| book | target | ALL | TRAIN | TEST | verdict |
|---|---|---|---|---|---|
| no-skill baseline | 1.0R | n=22001 prof=48.3% [47.6–48.9] net=-0.129 gross=-0.018 PF=0.77 stop=46.0% mfe=0.84 | n=13193 prof=48.2% [47.4–49.1] net=-0.131 gross=-0.019 PF=0.77 stop=46.3% mfe=0.84 | n=8808 prof=48.3% [47.3–49.4] net=-0.127 gross=-0.015 PF=0.77 stop=45.6% mfe=0.84 | reference |
| no-skill baseline | 1.5R | n=22001 prof=41.0% [40.4–41.7] net=-0.138 gross=-0.013 PF=0.78 stop=51.0% mfe=0.99 | n=13193 prof=41.2% [40.4–42.0] net=-0.137 gross=-0.011 PF=0.78 stop=51.3% mfe=0.98 | n=8808 prof=40.7% [39.7–41.7] net=-0.139 gross=-0.015 PF=0.78 stop=50.5% mfe=0.99 | reference |
| all 7 rules pooled | 1.0R | n=19058 prof=47.4% [46.6–48.1] net=-0.151 gross=-0.034 PF=0.73 stop=45.2% mfe=0.83 | n=11422 prof=47.7% [46.8–48.6] net=-0.149 gross=-0.030 PF=0.73 stop=45.1% mfe=0.83 | n=7636 prof=46.9% [45.7–48.0] net=-0.154 gross=-0.039 PF=0.72 stop=45.3% mfe=0.83 | **FAIL** |
| all 7 rules pooled | 1.5R | n=19058 prof=40.8% [40.1–41.5] net=-0.153 gross=-0.024 PF=0.75 stop=49.8% mfe=0.97 | n=11422 prof=41.4% [40.4–42.3] net=-0.146 gross=-0.015 PF=0.76 stop=49.6% mfe=0.97 | n=7636 prof=40.0% [38.9–41.1] net=-0.163 gross=-0.036 PF=0.74 stop=50.2% mfe=0.97 | **FAIL** |

- A1 rules: median hold 1.2h; exits stop_loss 8617, target_2 7905, expired 2536
- A1 baseline: median hold 1.2h; exits stop_loss 10129, target_2 9725, expired 2147

- A2 rules: median hold 1.5h; exits stop_loss 9495, target_2 5428, expired 4135
- A2 baseline: median hold 1.8h; exits stop_loss 11214, target_2 6644, expired 4143

### Per rule (informational — 14 cells, ~0.7 false positives expected)

| rule | target | ALL | TRAIN | TEST | lead? |
|---|---|---|---|---|---|
| trend_pullback_short | 1.0R | n=4957 prof=48.9% [47.5–50.3] net=-0.125 gross=-0.011 PF=0.78 stop=46.1% mfe=0.85 | n=2987 prof=50.1% [48.3–51.8] net=-0.109 gross=+0.004 PF=0.80 stop=45.8% mfe=0.85 | n=1970 prof=47.2% [45.0–49.4] net=-0.148 gross=-0.035 PF=0.74 stop=46.5% mfe=0.84 |  |
| trend_pullback_short | 1.5R | n=4957 prof=41.6% [40.3–43.0] net=-0.130 gross=-0.003 PF=0.79 stop=50.8% mfe=1.01 | n=2987 prof=42.6% [40.8–44.4] net=-0.115 gross=+0.012 PF=0.81 stop=50.7% mfe=1.01 | n=1970 prof=40.2% [38.1–42.4] net=-0.152 gross=-0.026 PF=0.76 stop=51.0% mfe=1.00 |  |
| failed_breakout_short | 1.0R | n=3551 prof=46.9% [45.3–48.6] net=-0.201 gross=-0.055 PF=0.67 stop=49.7% mfe=0.87 | n=2129 prof=46.5% [44.4–48.7] net=-0.219 gross=-0.066 PF=0.65 stop=49.8% mfe=0.87 | n=1422 prof=47.5% [44.9–50.1] net=-0.175 gross=-0.039 PF=0.71 stop=49.5% mfe=0.86 |  |
| failed_breakout_short | 1.5R | n=3551 prof=39.3% [37.7–40.9] net=-0.213 gross=-0.053 PF=0.70 stop=56.0% mfe=1.03 | n=2129 prof=39.3% [37.3–41.4] net=-0.227 gross=-0.060 PF=0.68 stop=55.8% mfe=1.02 | n=1422 prof=39.3% [36.8–41.9] net=-0.192 gross=-0.043 PF=0.72 stop=56.3% mfe=1.04 |  |
| liquidity_sweep_long | 1.0R | n=3756 prof=46.2% [44.7–47.8] net=-0.212 gross=-0.065 PF=0.66 stop=50.7% mfe=0.86 | n=2251 prof=45.8% [43.8–47.9] net=-0.218 gross=-0.071 PF=0.65 stop=51.2% mfe=0.86 | n=1505 prof=46.8% [44.3–49.4] net=-0.203 gross=-0.057 PF=0.67 stop=50.0% mfe=0.87 |  |
| liquidity_sweep_long | 1.5R | n=3756 prof=39.1% [37.6–40.7] net=-0.195 gross=-0.037 PF=0.72 stop=56.6% mfe=1.03 | n=2251 prof=39.4% [37.4–41.5] net=-0.184 gross=-0.025 PF=0.74 stop=56.6% mfe=1.03 | n=1505 prof=38.6% [36.2–41.1] net=-0.212 gross=-0.054 PF=0.70 stop=56.5% mfe=1.02 |  |
| rsi_bounce_long | 1.0R | n=3650 prof=46.8% [45.2–48.4] net=-0.102 gross=-0.014 PF=0.79 stop=36.9% mfe=0.74 | n=2195 prof=47.3% [45.3–49.4] net=-0.092 gross=-0.004 PF=0.81 stop=36.9% mfe=0.76 | n=1455 prof=46.0% [43.5–48.6] net=-0.118 gross=-0.029 PF=0.75 stop=37.0% mfe=0.73 |  |
| rsi_bounce_long | 1.5R | n=3650 prof=41.8% [40.2–43.4] net=-0.106 gross=-0.009 PF=0.79 stop=39.5% mfe=0.85 | n=2195 prof=42.7% [40.6–44.8] net=-0.080 gross=+0.016 PF=0.84 stop=39.1% mfe=0.87 | n=1455 prof=40.5% [38.1–43.1] net=-0.145 gross=-0.046 PF=0.72 stop=40.1% mfe=0.83 |  |
| range_reversion_short | 1.0R | n=278 prof=47.5% [41.7–53.3] net=-0.108 gross=-0.047 PF=0.81 stop=52.2% mfe=1.00 | n=137 prof=45.3% [37.2–53.6] net=-0.151 gross=-0.087 PF=0.74 stop=54.0% mfe=0.98 | n=141 prof=49.6% [41.5–57.8] net=-0.067 gross=-0.007 PF=0.88 stop=50.4% mfe=1.03 |  |
| range_reversion_short | 1.5R | n=278 prof=39.6% [34.0–45.4] net=-0.085 gross=-0.018 PF=0.87 stop=59.7% mfe=1.18 | n=137 prof=37.2% [29.6–45.6] net=-0.136 gross=-0.067 PF=0.80 stop=61.3% mfe=1.10 | n=141 prof=41.8% [34.0–50.1] net=-0.035 gross=+0.030 PF=0.94 stop=58.2% mfe=1.26 |  |
| range_reversion_long | 1.0R | n=461 prof=50.3% [45.8–54.9] net=-0.084 gross=+0.008 PF=0.85 stop=48.6% mfe=1.16 | n=273 prof=50.5% [44.7–56.4] net=-0.076 gross=+0.015 PF=0.86 stop=48.0% mfe=1.12 | n=188 prof=50.0% [42.9–57.1] net=-0.095 gross=-0.003 PF=0.83 stop=49.5% mfe=1.22 |  |
| range_reversion_long | 1.5R | n=461 prof=44.7% [40.2–49.2] net=+0.000 gross=+0.098 PF=1.00 stop=54.0% mfe=1.32 | n=273 prof=44.0% [38.2–49.9] net=-0.013 gross=+0.085 PF=0.98 stop=54.2% mfe=1.27 | n=188 prof=45.7% [38.8–52.9] net=+0.019 gross=+0.116 PF=1.03 stop=53.7% mfe=1.39 |  |
| rsi_rejection_short | 1.0R | n=2405 prof=46.7% [44.7–48.7] net=-0.127 gross=-0.035 PF=0.74 stop=39.4% mfe=0.73 | n=1450 prof=47.5% [45.0–50.1] net=-0.119 gross=-0.026 PF=0.75 stop=38.7% mfe=0.72 | n=955 prof=45.4% [42.3–48.6] net=-0.140 gross=-0.048 PF=0.72 stop=40.5% mfe=0.74 |  |
| rsi_rejection_short | 1.5R | n=2405 prof=41.9% [39.9–43.9] net=-0.153 gross=-0.049 PF=0.71 stop=41.9% mfe=0.83 | n=1450 prof=42.6% [40.1–45.2] net=-0.157 gross=-0.052 PF=0.70 stop=41.2% mfe=0.81 | n=955 prof=40.7% [37.7–43.9] net=-0.146 gross=-0.044 PF=0.73 stop=42.8% mfe=0.85 |  |

**Pooled rules by month (1.0R):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-04 | 722 | 47.1 | -0.187 |
| 2026-05 | 2945 | 46.2 | -0.179 |
| 2026-06 | 3035 | 50.2 | -0.082 |
| 2026-07 | 3325 | 48.3 | -0.131 |
| 2026-08 | 3470 | 45.3 | -0.213 |
| 2026-09 | 3396 | 47.7 | -0.123 |
| 2026-10 | 2165 | 46.4 | -0.172 |

**Pooled rules by month (1.5R):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-04 | 722 | 38.8 | -0.211 |
| 2026-05 | 2945 | 40.3 | -0.177 |
| 2026-06 | 3035 | 44.1 | -0.059 |
| 2026-07 | 3325 | 41.5 | -0.137 |
| 2026-08 | 3470 | 38.9 | -0.228 |
| 2026-09 | 3396 | 40.7 | -0.128 |
| 2026-10 | 2165 | 39.8 | -0.174 |

## Study B — today's signals: hold cap and news blackout

TRAIN/TEST cut: 2026-08-12 00:00 UTC. 96/1715 trades fall in a news window (18 releases on the calendar).

| variant | ALL | TRAIN | TEST |
|---|---|---|---|
| B0 | n=1715 prof=53.4% [51.0–55.8] net=-0.103 gross=-0.051 PF=0.77 stop=41.6% mfe=0.89 | n=1029 prof=54.8% [51.8–57.8] net=-0.089 gross=-0.035 PF=0.80 stop=40.7% mfe=0.89 | n=686 prof=51.3% [47.6–55.0] net=-0.124 gross=-0.075 PF=0.73 stop=43.0% mfe=0.87 |
| B1 | n=1715 prof=49.6% [47.2–51.9] net=-0.107 gross=-0.055 PF=0.73 stop=31.3% mfe=0.73 | n=1029 prof=49.9% [46.8–52.9] net=-0.095 gross=-0.041 PF=0.76 stop=30.4% mfe=0.74 | n=686 prof=49.1% [45.4–52.9] net=-0.124 gross=-0.076 PF=0.69 stop=32.5% mfe=0.71 |
| B2 | n=1619 prof=49.2% [46.8–51.7] net=-0.112 gross=-0.060 PF=0.72 stop=31.3% mfe=0.72 | n=970 prof=49.9% [46.8–53.0] net=-0.090 gross=-0.036 PF=0.77 stop=29.7% mfe=0.75 | n=649 prof=48.2% [44.4–52.1] net=-0.145 gross=-0.097 PF=0.65 stop=33.6% mfe=0.69 |

- **B1 vs B0: NO EFFECT** — TEST net +0.000R, TRAIN net -0.006R, TEST hit rate -2.2pp

- **B2 vs B1: NO EFFECT** — TEST net -0.022R, TRAIN net +0.005R, TEST hit rate -0.9pp

- B0: median hold 7.2h; exits stop_loss 714, trail_stop 323, target_2 225, be_stop 203, expired 143, target_1 107
- B1: median hold 7.2h; exits stop_loss 536, expired 515, trail_stop 218, target_1 158, target_2 151, be_stop 137
- the trades B2 removes, under B1: n=96 prof=55.2% [45.3–64.8] net=-0.013 gross=+0.033 PF=0.96 stop=31.2% mfe=0.86

### Per rule × tf (each split 60/40 on its own trades, as the harness does)

| rule | tf | B0 TEST | B1 TEST | B2 TEST | ship? |
|---|---|---|---|---|---|
| liquidity_sweep_long | 1h | n=308 prof=51.6% [46.1–57.2] net=-0.139 gross=-0.074 PF=0.72 stop=45.5% mfe=0.95 | n=308 prof=51.6% [46.1–57.2] net=-0.140 gross=-0.075 PF=0.71 stop=43.5% mfe=0.91 | n=293 prof=50.2% [44.5–55.9] net=-0.173 gross=-0.106 PF=0.65 stop=45.1% mfe=0.87 | NO |
| trend_pullback_short | 4h | n=141 prof=46.8% [38.8–55.0] net=-0.175 gross=-0.131 PF=0.64 stop=44.7% mfe=0.81 | n=141 prof=47.5% [39.5–55.7] net=-0.130 gross=-0.088 PF=0.60 stop=20.6% mfe=0.49 | n=135 prof=47.4% [39.2–55.8] net=-0.133 gross=-0.091 PF=0.59 stop=20.0% mfe=0.49 | NO |
| failed_breakout_short | 4h | n=121 prof=56.2% [47.3–64.7] net=-0.048 gross=-0.018 PF=0.89 stop=40.5% mfe=0.87 | n=121 prof=46.3% [37.6–55.1] net=-0.097 gross=-0.068 PF=0.75 stop=32.2% mfe=0.68 | n=114 prof=45.6% [36.8–54.8] net=-0.130 gross=-0.102 PF=0.68 stop=33.3% mfe=0.65 | NO |
| rsi_bounce_long | 4h | n=94 prof=48.9% [39.1–58.9] net=-0.108 gross=-0.075 PF=0.73 stop=34.0% mfe=0.71 | n=94 prof=43.6% [34.0–53.7] net=-0.102 gross=-0.073 PF=0.55 stop=7.4% mfe=0.38 | n=88 prof=44.3% [34.4–54.7] net=-0.088 gross=-0.059 PF=0.60 stop=8.0% mfe=0.38 | NO |
| range_reversion_short | 4h | n=13 prof=76.9% [49.7–91.8] net=+0.346 gross=+0.381 PF=2.43 stop=23.1% mfe=1.12 | n=13 prof=76.9% [49.7–91.8] net=+0.323 gross=+0.359 PF=2.34 stop=23.1% mfe=1.09 | n=13 prof=76.9% [49.7–91.8] net=+0.323 gross=+0.359 PF=2.34 stop=23.1% mfe=1.09 | NO |
| range_reversion_long | 4h | n=10 prof=60.0% [31.3–83.2] net=+0.102 gross=+0.155 PF=1.24 stop=40.0% mfe=1.16 | n=10 prof=60.0% [31.3–83.2] net=+0.102 gross=+0.155 PF=1.24 stop=40.0% mfe=1.16 | n=9 prof=55.6% [26.7–81.1] net=+0.065 gross=+0.114 PF=1.14 stop=44.4% mfe=1.13 | NO |

Frozen rule note: `range_reversion_short` 4h is forward test #1 — nothing here changes it while its clock runs.