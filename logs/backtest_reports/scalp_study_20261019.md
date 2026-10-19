# Scalp / hold-time study — 2026-10-19

Pre-registration: `logs/backtest_reports/prereg_scalp_study_20261019.md`. Universe 30 symbols (BTCUSDT, ADAUSDT, XRPUSDT, SOLUSDT, ETHUSDT, DOGEUSDT, SUIUSDT, XLMUSDT, ENAUSDT, HBARUSDT, TRXUSDT, NEARUSDT, OPUSDT, ARBUSDT, INJUSDT, 1000PEPEUSDT, PUMPFUNUSDT, FARTCOINUSDT, ZECUSDT, ONDOUSDT, WLDUSDT, SOXLUSDT, SKHYNIXUSDT, CASHCATUSDT, XPLUSDT, 1000BONKUSDT, AKEUSDT, KORUUSDT, USUSDT, SNDKUSDT); 2026-04-22 → 2026-10-19. Entry: limit at next 15m open, 2-bar wait, maker entry/targets, taker+slippage stops/expiry, funding. TRAIN = first 60% by signal time, TEST = last 40%. profitable = net R > 0.

## Study A — 15m scalp, whole position at the target, max hold 4h

TRAIN/TEST cut: 2026-08-11 22:45 UTC.

| book | target | ALL | TRAIN | TEST | verdict |
|---|---|---|---|---|---|
| no-skill baseline | 1.0R | n=26005 prof=48.2% [47.6–48.8] net=-0.136 gross=-0.017 PF=0.76 stop=45.9% mfe=0.84 | n=15568 prof=48.0% [47.2–48.8] net=-0.140 gross=-0.019 PF=0.75 stop=46.1% mfe=0.84 | n=10437 prof=48.5% [47.5–49.4] net=-0.129 gross=-0.013 PF=0.77 stop=45.5% mfe=0.84 | reference |
| no-skill baseline | 1.5R | n=26005 prof=41.0% [40.4–41.6] net=-0.144 gross=-0.011 PF=0.77 stop=50.7% mfe=0.99 | n=15568 prof=41.3% [40.5–42.0] net=-0.141 gross=-0.006 PF=0.78 stop=50.8% mfe=0.99 | n=10437 prof=40.6% [39.7–41.6] net=-0.148 gross=-0.018 PF=0.76 stop=50.6% mfe=0.99 | reference |
| all 7 rules pooled | 1.0R | n=22506 prof=47.4% [46.7–48.0] net=-0.155 gross=-0.031 PF=0.72 stop=45.0% mfe=0.83 | n=13501 prof=47.9% [47.1–48.8] net=-0.149 gross=-0.022 PF=0.73 stop=44.6% mfe=0.83 | n=9005 prof=46.6% [45.6–47.6] net=-0.164 gross=-0.043 PF=0.71 stop=45.5% mfe=0.82 | **FAIL** |
| all 7 rules pooled | 1.5R | n=22506 prof=40.7% [40.1–41.4] net=-0.160 gross=-0.022 PF=0.74 stop=49.6% mfe=0.97 | n=13501 prof=41.4% [40.5–42.2] net=-0.151 gross=-0.011 PF=0.76 stop=49.2% mfe=0.97 | n=9005 prof=39.8% [38.8–40.8] net=-0.173 gross=-0.040 PF=0.72 stop=50.2% mfe=0.97 | **FAIL** |

- A1 rules: median hold 1.2h; exits stop_loss 10120, target_2 9335, expired 3051
- A1 baseline: median hold 1.2h; exits stop_loss 11935, target_2 11485, expired 2585

- A2 rules: median hold 1.5h; exits stop_loss 11157, target_2 6389, expired 4960
- A2 baseline: median hold 1.8h; exits stop_loss 13187, target_2 7841, expired 4977

### Per rule (informational — 14 cells, ~0.7 false positives expected)

| rule | target | ALL | TRAIN | TEST | lead? |
|---|---|---|---|---|---|
| trend_pullback_short | 1.0R | n=5892 prof=49.4% [48.1–50.7] net=-0.119 gross=+0.001 PF=0.78 stop=45.3% mfe=0.85 | n=3559 prof=50.7% [49.1–52.4] net=-0.098 gross=+0.023 PF=0.82 stop=44.5% mfe=0.86 | n=2333 prof=47.4% [45.3–49.4] net=-0.152 gross=-0.033 PF=0.73 stop=46.5% mfe=0.84 |  |
| trend_pullback_short | 1.5R | n=5892 prof=42.0% [40.8–43.3] net=-0.126 gross=+0.009 PF=0.80 stop=50.0% mfe=1.01 | n=3559 prof=43.2% [41.5–44.8] net=-0.103 gross=+0.032 PF=0.83 stop=49.4% mfe=1.02 | n=2333 prof=40.2% [38.3–42.3] net=-0.159 gross=-0.027 PF=0.75 stop=50.9% mfe=1.00 |  |
| failed_breakout_short | 1.0R | n=4157 prof=47.3% [45.8–48.9] net=-0.196 gross=-0.043 PF=0.68 stop=49.0% mfe=0.87 | n=2497 prof=47.3% [45.3–49.3] net=-0.206 gross=-0.045 PF=0.67 stop=48.7% mfe=0.88 | n=1660 prof=47.4% [45.0–49.8] net=-0.181 gross=-0.038 PF=0.70 stop=49.5% mfe=0.87 |  |
| failed_breakout_short | 1.5R | n=4157 prof=39.6% [38.1–41.1] net=-0.210 gross=-0.042 PF=0.70 stop=55.4% mfe=1.03 | n=2497 prof=39.9% [38.0–41.8] net=-0.216 gross=-0.040 PF=0.69 stop=54.8% mfe=1.03 | n=1660 prof=39.1% [36.8–41.5] net=-0.201 gross=-0.044 PF=0.71 stop=56.2% mfe=1.04 |  |
| liquidity_sweep_long | 1.0R | n=4524 prof=45.8% [44.4–47.3] net=-0.230 gross=-0.073 PF=0.64 stop=51.1% mfe=0.85 | n=2725 prof=45.6% [43.8–47.5] net=-0.234 gross=-0.075 PF=0.63 stop=51.4% mfe=0.85 | n=1799 prof=46.1% [43.8–48.4] net=-0.224 gross=-0.071 PF=0.65 stop=50.8% mfe=0.86 |  |
| liquidity_sweep_long | 1.5R | n=4524 prof=38.3% [36.9–39.7] net=-0.224 gross=-0.054 PF=0.69 stop=57.3% mfe=1.02 | n=2725 prof=38.2% [36.4–40.1] net=-0.223 gross=-0.050 PF=0.69 stop=57.6% mfe=1.02 | n=1799 prof=38.4% [36.2–40.7] net=-0.225 gross=-0.059 PF=0.68 stop=56.9% mfe=1.01 |  |
| rsi_bounce_long | 1.0R | n=4288 prof=46.7% [45.2–48.2] net=-0.108 gross=-0.015 PF=0.77 stop=36.9% mfe=0.74 | n=2594 prof=47.3% [45.4–49.2] net=-0.100 gross=-0.006 PF=0.79 stop=37.1% mfe=0.76 | n=1694 prof=45.7% [43.3–48.1] net=-0.122 gross=-0.029 PF=0.75 stop=36.7% mfe=0.72 |  |
| rsi_bounce_long | 1.5R | n=4288 prof=41.8% [40.3–43.3] net=-0.111 gross=-0.008 PF=0.78 stop=39.3% mfe=0.85 | n=2594 prof=42.8% [40.9–44.7] net=-0.086 gross=+0.017 PF=0.83 stop=39.2% mfe=0.87 | n=1694 prof=40.3% [37.9–42.6] net=-0.150 gross=-0.047 PF=0.71 stop=39.6% mfe=0.82 |  |
| range_reversion_short | 1.0R | n=285 prof=47.0% [41.3–52.8] net=-0.118 gross=-0.056 PF=0.79 stop=52.6% mfe=1.01 | n=135 prof=44.4% [36.3–52.9] net=-0.168 gross=-0.103 PF=0.72 stop=54.8% mfe=0.98 | n=150 prof=49.3% [41.4–57.3] net=-0.074 gross=-0.013 PF=0.87 stop=50.7% mfe=1.03 |  |
| range_reversion_short | 1.5R | n=285 prof=38.9% [33.5–44.7] net=-0.101 gross=-0.033 PF=0.85 stop=60.4% mfe=1.18 | n=135 prof=36.3% [28.7–44.7] net=-0.160 gross=-0.090 PF=0.76 stop=62.2% mfe=1.09 | n=150 prof=41.3% [33.8–49.3] net=-0.048 gross=+0.018 PF=0.93 stop=58.7% mfe=1.25 |  |
| range_reversion_long | 1.0R | n=473 prof=50.7% [46.2–55.2] net=-0.076 gross=+0.016 PF=0.86 stop=48.2% mfe=1.16 | n=272 prof=51.8% [45.9–57.7] net=-0.050 gross=+0.041 PF=0.91 stop=46.7% mfe=1.13 | n=201 prof=49.3% [42.4–56.1] net=-0.111 gross=-0.018 PF=0.81 stop=50.2% mfe=1.20 |  |
| range_reversion_long | 1.5R | n=473 prof=45.0% [40.6–49.5] net=+0.004 gross=+0.101 PF=1.01 stop=53.7% mfe=1.31 | n=272 prof=45.2% [39.4–51.2] net=+0.015 gross=+0.112 PF=1.02 stop=52.9% mfe=1.27 | n=201 prof=44.8% [38.1–51.7] net=-0.012 gross=+0.086 PF=0.98 stop=54.7% mfe=1.37 |  |
| rsi_rejection_short | 1.0R | n=2887 prof=46.4% [44.6–48.2] net=-0.139 gross=-0.039 PF=0.72 stop=39.5% mfe=0.72 | n=1719 prof=47.3% [44.9–49.7] net=-0.127 gross=-0.026 PF=0.74 stop=38.4% mfe=0.72 | n=1168 prof=45.1% [42.3–48.0] net=-0.155 gross=-0.059 PF=0.70 stop=41.0% mfe=0.73 |  |
| rsi_rejection_short | 1.5R | n=2887 prof=41.5% [39.7–43.3] net=-0.161 gross=-0.050 PF=0.70 stop=41.7% mfe=0.82 | n=1719 prof=42.3% [40.0–44.6] net=-0.162 gross=-0.047 PF=0.69 stop=40.5% mfe=0.82 | n=1168 prof=40.3% [37.5–43.2] net=-0.160 gross=-0.054 PF=0.71 stop=43.3% mfe=0.83 |  |

**Pooled rules by month (1.0R):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-04 | 911 | 48.8 | -0.153 |
| 2026-05 | 3648 | 45.9 | -0.195 |
| 2026-06 | 3679 | 50.3 | -0.084 |
| 2026-07 | 3870 | 48.4 | -0.132 |
| 2026-08 | 3997 | 45.4 | -0.217 |
| 2026-09 | 3916 | 47.5 | -0.130 |
| 2026-10 | 2485 | 46.2 | -0.181 |

**Pooled rules by month (1.5R):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-04 | 911 | 40.2 | -0.185 |
| 2026-05 | 3648 | 39.8 | -0.197 |
| 2026-06 | 3679 | 44.1 | -0.065 |
| 2026-07 | 3870 | 41.5 | -0.141 |
| 2026-08 | 3997 | 39.0 | -0.230 |
| 2026-09 | 3916 | 40.3 | -0.139 |
| 2026-10 | 2485 | 39.6 | -0.185 |

## Study B — today's signals: hold cap and news blackout

TRAIN/TEST cut: 2026-08-10 23:00 UTC. 115/2011 trades fall in a news window (18 releases on the calendar).

| variant | ALL | TRAIN | TEST |
|---|---|---|---|
| B0 | n=2011 prof=53.7% [51.5–55.9] net=-0.105 gross=-0.048 PF=0.77 stop=41.3% mfe=0.88 | n=1206 prof=55.0% [52.2–57.8] net=-0.096 gross=-0.036 PF=0.79 stop=40.6% mfe=0.89 | n=805 prof=51.8% [48.3–55.2] net=-0.118 gross=-0.066 PF=0.75 stop=42.2% mfe=0.88 |
| B1 | n=2011 prof=49.3% [47.1–51.5] net=-0.115 gross=-0.059 PF=0.71 stop=31.4% mfe=0.73 | n=1206 prof=49.2% [46.4–52.0] net=-0.111 gross=-0.052 PF=0.72 stop=30.6% mfe=0.73 | n=805 prof=49.6% [46.1–53.0] net=-0.120 gross=-0.069 PF=0.70 stop=32.7% mfe=0.72 |
| B2 | n=1896 prof=48.9% [46.7–51.2] net=-0.121 gross=-0.065 PF=0.70 stop=31.4% mfe=0.71 | n=1130 prof=49.1% [46.2–52.0] net=-0.109 gross=-0.050 PF=0.72 stop=29.9% mfe=0.72 | n=766 prof=48.7% [45.2–52.2] net=-0.140 gross=-0.088 PF=0.66 stop=33.7% mfe=0.70 |

- **B1 vs B0: NO EFFECT** — TEST net -0.003R, TRAIN net -0.015R, TEST hit rate -2.2pp

- **B2 vs B1: NO EFFECT** — TEST net -0.020R, TRAIN net +0.003R, TEST hit rate -0.9pp

- B0: median hold 7.5h; exits stop_loss 830, trail_stop 381, target_2 260, be_stop 249, expired 168, target_1 123
- B1: median hold 7.5h; exits stop_loss 632, expired 602, trail_stop 255, target_1 183, target_2 171, be_stop 168
- the trades B2 removes, under B1: n=115 prof=55.7% [46.5–64.4] net=-0.007 gross=+0.045 PF=0.98 stop=31.3% mfe=0.91

### Per rule × tf (each split 60/40 on its own trades, as the harness does)

| rule | tf | B0 TEST | B1 TEST | B2 TEST | ship? |
|---|---|---|---|---|---|
| liquidity_sweep_long | 1h | n=365 prof=52.1% [46.9–57.1] net=-0.139 gross=-0.070 PF=0.72 stop=45.2% mfe=0.95 | n=365 prof=52.3% [47.2–57.4] net=-0.135 gross=-0.066 PF=0.72 stop=43.0% mfe=0.90 | n=350 prof=51.1% [45.9–56.3] net=-0.162 gross=-0.091 PF=0.67 stop=44.3% mfe=0.87 | NO |
| trend_pullback_short | 4h | n=166 prof=50.0% [42.5–57.5] net=-0.138 gross=-0.093 PF=0.70 stop=41.6% mfe=0.83 | n=166 prof=49.4% [41.9–56.9] net=-0.097 gross=-0.054 PF=0.69 stop=19.3% mfe=0.52 | n=160 prof=49.4% [41.7–57.0] net=-0.099 gross=-0.055 PF=0.68 stop=18.8% mfe=0.52 | NO |
| failed_breakout_short | 4h | n=136 prof=58.8% [50.4–66.7] net=+0.003 gross=+0.033 PF=1.01 stop=38.2% mfe=0.91 | n=136 prof=47.8% [39.6–56.1] net=-0.068 gross=-0.039 PF=0.82 stop=30.9% mfe=0.70 | n=127 prof=46.5% [38.0–55.1] net=-0.107 gross=-0.078 PF=0.73 stop=32.3% mfe=0.67 | NO |
| rsi_bounce_long | 4h | n=109 prof=46.8% [37.7–56.1] net=-0.117 gross=-0.084 PF=0.70 stop=32.1% mfe=0.71 | n=109 prof=42.2% [33.4–51.6] net=-0.122 gross=-0.093 PF=0.49 stop=9.2% mfe=0.38 | n=103 prof=42.7% [33.6–52.4] net=-0.112 gross=-0.082 PF=0.52 stop=9.7% mfe=0.38 | NO |
| range_reversion_short | 4h | n=19 prof=68.4% [46.0–84.6] net=+0.161 gross=+0.201 PF=1.48 stop=31.6% mfe=0.97 | n=19 prof=68.4% [46.0–84.6] net=+0.145 gross=+0.186 PF=1.43 stop=31.6% mfe=0.96 | n=19 prof=68.4% [46.0–84.6] net=+0.145 gross=+0.186 PF=1.43 stop=31.6% mfe=0.96 | NO |
| range_reversion_long | 4h | n=12 prof=50.0% [25.4–74.6] net=-0.098 gross=-0.037 PF=0.82 stop=50.0% mfe=0.99 | n=12 prof=50.0% [25.4–74.6] net=-0.098 gross=-0.037 PF=0.82 stop=50.0% mfe=0.99 | n=11 prof=45.5% [21.3–72.0] net=-0.147 gross=-0.089 PF=0.75 stop=54.5% mfe=0.94 | NO |

Frozen rule note: `range_reversion_short` 4h is forward test #1 — nothing here changes it while its clock runs.