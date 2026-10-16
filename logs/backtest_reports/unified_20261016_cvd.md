# Unified backtest — 20261016

Universe: 19 symbols (ADAUSDT, ARBUSDT, AVAXUSDT, BTCUSDT, DOGEUSDT, ENAUSDT, ETHUSDT, HBARUSDT, INJUSDT, LINKUSDT, LTCUSDT, NEARUSDT, OPUSDT, SOLUSDT, SUIUSDT, TRXUSDT, WLDUSDT, XLMUSDT, XRPUSDT); days=75; trades=701; window 4h→192×15m, 1h→96×15m; entry per ENTRY_MODEL (below); T1=0.75R partial 50%, BE after T1, +0.3R trail after 1R MFE; costs per config (taker 0.055% + slip 0.03% per side; maker 0.020%). **Entry model: limit_open** (limit at next open ∓ 0.0×ATR, wait 2 bars; 701/724 signals filled, 23 unfilled dropped).

Metric: **profitable%** = net-of-cost blended R > 0. Bar: SHIP ≥70% & net>0 & n≥30 on TEST; CANDIDATE ≥60%.

## (a) Per signal × tf — default config

| signal | tf | tier | ALL | TRAIN (60%) | TEST (40%) |
|---|---|---|---|---|---|
| rsi_rejection_short | 1h | watch | n=267 prof=51.3% [45.3–57.2] net=-0.121 gross=-0.060 PF=0.73 stop=39.7% mfe=0.85 | n=160 prof=52.5% [44.8–60.1] net=-0.151 gross=-0.080 PF=0.68 stop=41.2% mfe=0.82 | n=107 prof=49.5% [40.2–58.9] net=-0.077 gross=-0.029 PF=0.82 stop=37.4% mfe=0.90 |
| liquidity_sweep_long | 1h | watch | n=228 prof=54.4% [47.9–60.7] net=-0.148 gross=-0.053 PF=0.69 stop=43.4% mfe=0.95 | n=136 prof=52.2% [43.9–60.4] net=-0.185 gross=-0.082 PF=0.63 stop=44.9% mfe=0.95 | n=92 prof=57.6% [47.4–67.2] net=-0.094 gross=-0.010 PF=0.79 stop=41.3% mfe=0.94 |
| rsi_bounce_long | 4h | watch | n=58 prof=55.2% [42.5–67.3] net=-0.004 gross=+0.035 PF=0.99 stop=27.6% mfe=0.79 | n=34 prof=44.1% [28.9–60.5] net=-0.141 gross=-0.098 PF=0.68 stop=35.3% mfe=0.78 | n=24 prof=70.8% [50.8–85.1] net=+0.191 gross=+0.224 PF=1.97 stop=16.7% mfe=0.80 |
| trend_pullback_short | 4h | watch | n=54 prof=48.1% [35.4–61.1] net=-0.117 gross=-0.057 PF=0.76 stop=44.4% mfe=0.96 | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=22 prof=45.5% [26.9–65.3] net=+0.077 gross=+0.136 PF=1.19 stop=36.4% mfe=1.09 |
| failed_breakout_short | 4h | watch | n=41 prof=61.0% [45.7–74.3] net=+0.170 gross=+0.205 PF=1.44 stop=36.6% mfe=1.10 | n=24 prof=58.3% [38.8–75.5] net=+0.078 gross=+0.116 PF=1.18 stop=41.7% mfe=1.03 | n=17 prof=64.7% [41.3–82.7] net=+0.300 gross=+0.330 PF=1.92 stop=29.4% mfe=1.20 |
| rsi_rejection_short | 4h | watch | n=32 prof=40.6% [25.5–57.7] net=-0.271 gross=-0.239 PF=0.47 stop=46.9% mfe=0.55 | n=19 prof=26.3% [11.8–48.8] net=-0.432 gross=-0.399 PF=0.30 stop=57.9% mfe=0.43 | n=13 prof=61.5% [35.5–82.3] net=-0.035 gross=-0.005 PF=0.90 stop=30.8% mfe=0.73 |
| range_reversion_long | 4h | watch | n=12 prof=58.3% [32.0–80.7] net=-0.040 gross=+0.027 PF=0.91 stop=41.7% mfe=0.98 | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |
| range_reversion_short | 4h | watch | n=9 prof=44.4% [18.9–73.3] net=-0.356 gross=-0.289 PF=0.41 stop=55.6% mfe=0.60 | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |

Total filter cuts tested across signals: 366.

### rsi_rejection_short (1h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-08 | 103 | 53.4 | -0.123 |
| 2026-09 | 106 | 50.9 | -0.151 |
| 2026-10 | 58 | 48.3 | -0.064 |

**Filter study** (52 cuts tested — expect ~2.6 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=108 prof=48.1% [39.0–57.5] net=-0.196 gross=-0.127 PF=0.62 stop=46.3% mfe=0.83 | n=67 prof=55.2% [43.4–66.5] net=+0.018 gross=+0.065 PF=1.04 stop=40.3% mfe=1.06 |  |
| btc_aligned | yes | n=52 prof=61.5% [48.0–73.5] net=-0.056 gross=+0.017 PF=0.84 stop=30.8% mfe=0.81 | n=40 prof=40.0% [26.3–55.4] net=-0.238 gross=-0.186 PF=0.46 stop=32.5% mfe=0.63 |  |
| confluence3 | 0-1 | n=111 prof=51.4% [42.2–60.4] net=-0.164 gross=-0.095 PF=0.66 stop=42.3% mfe=0.82 | n=76 prof=53.9% [42.8–64.7] net=-0.001 gross=+0.044 PF=1.00 stop=40.8% mfe=1.02 |  |
| confluence3 | 2-3 | n=49 prof=55.1% [41.3–68.1] net=-0.121 gross=-0.045 PF=0.72 stop=38.8% mfe=0.84 | n=31 prof=38.7% [23.7–56.2] net=-0.265 gross=-0.208 PF=0.38 stop=29.0% mfe=0.60 |  |
| risk_pct | 2-4% | n=61 prof=47.5% [35.5–59.8] net=-0.254 gross=-0.217 PF=0.50 stop=47.5% mfe=0.70 | n=54 prof=44.4% [32.0–57.6] net=-0.196 gross=-0.159 PF=0.60 stop=42.6% mfe=0.79 |  |
| risk_pct | 4-8% | n=18 prof=55.6% [33.7–75.4] net=-0.156 gross=-0.136 PF=0.62 stop=38.9% mfe=0.71 | n=18 prof=72.2% [49.1–87.5] net=+0.362 gross=+0.378 PF=2.53 stop=22.2% mfe=1.21 |  |
| risk_pct | <2% | n=77 prof=54.5% [43.5–65.2] net=-0.091 gross=+0.021 PF=0.80 stop=37.7% mfe=0.95 | n=34 prof=47.1% [31.5–63.3] net=-0.108 gross=-0.024 PF=0.77 stop=38.2% mfe=0.92 |  |
| risk_pct | >8% | n=4 prof=75.0% [30.1–95.4] net=+0.295 gross=+0.308 PF=2.17 stop=25.0% mfe=0.77 | n=1 prof=0.0% [0.0–79.3] net=-0.559 gross=-0.545 PF=0.00 stop=0.0% mfe=0.62 |  |
| hour | 00-08 | n=41 prof=56.1% [41.0–70.1] net=-0.044 gross=+0.023 PF=0.89 stop=36.6% mfe=0.87 | n=24 prof=29.2% [14.9–49.2] net=-0.266 gross=-0.221 PF=0.51 stop=41.7% mfe=0.73 |  |
| hour | 08-16 | n=54 prof=37.0% [25.4–50.4] net=-0.435 gross=-0.367 PF=0.31 stop=57.4% mfe=0.64 | n=45 prof=57.8% [43.3–71.0] net=+0.011 gross=+0.066 PF=1.02 stop=40.0% mfe=1.03 |  |
| hour | 16-24 | n=65 prof=63.1% [50.9–73.8] net=+0.018 gross=+0.093 PF=1.05 stop=30.8% mfe=0.95 | n=38 prof=52.6% [37.3–67.5] net=-0.062 gross=-0.021 PF=0.84 stop=31.6% mfe=0.86 |  |
| weekend | weekday | n=107 prof=47.7% [38.4–57.0] net=-0.267 gross=-0.206 PF=0.49 stop=47.7% mfe=0.71 | n=80 prof=47.5% [36.9–58.3] net=-0.076 gross=-0.035 PF=0.83 stop=36.2% mfe=0.88 |  |
| weekend | weekend | n=53 prof=62.3% [48.8–74.1] net=+0.083 gross=+0.175 PF=1.23 stop=28.3% mfe=1.05 | n=27 prof=55.6% [37.3–72.4] net=-0.080 gross=-0.012 PF=0.82 stop=40.7% mfe=0.95 |  |
| adx | 20-30 | n=61 prof=59.0% [46.5–70.5] net=+0.067 gross=+0.146 PF=1.17 stop=34.4% mfe=1.05 | n=44 prof=50.0% [35.8–64.2] net=-0.005 gross=+0.050 PF=0.99 stop=31.8% mfe=0.98 |  |
| adx | <20 | n=36 prof=44.4% [29.5–60.4] net=-0.370 gross=-0.278 PF=0.37 stop=52.8% mfe=0.70 | n=19 prof=63.2% [41.0–80.9] net=+0.091 gross=+0.149 PF=1.27 stop=31.6% mfe=1.05 |  |
| adx | >30 | n=63 prof=50.8% [38.8–62.7] net=-0.237 gross=-0.186 PF=0.49 stop=41.3% mfe=0.67 | n=44 prof=43.2% [29.7–57.8] net=-0.222 gross=-0.185 PF=0.56 stop=45.5% mfe=0.75 |  |
| vol_spike | <1.5 | n=110 prof=48.2% [39.1–57.4] net=-0.249 gross=-0.167 PF=0.54 stop=47.3% mfe=0.81 | n=86 prof=46.5% [36.3–57.0] net=-0.107 gross=-0.058 PF=0.77 stop=39.5% mfe=0.88 |  |
| vol_spike | >=1.5 | n=50 prof=62.0% [48.2–74.1] net=+0.064 gross=+0.111 PF=1.21 stop=28.0% mfe=0.86 | n=21 prof=61.9% [40.9–79.2] net=+0.044 gross=+0.087 PF=1.12 stop=28.6% mfe=0.99 | CANDIDATE |
| ema50_dist_atr | -0.5..0.5 | n=36 prof=52.8% [37.0–68.0] net=-0.197 gross=-0.127 PF=0.57 stop=41.7% mfe=0.76 | n=17 prof=35.3% [17.3–58.7] net=-0.201 gross=-0.147 PF=0.54 stop=29.4% mfe=0.72 |  |
| ema50_dist_atr | -2..-0.5 | n=12 prof=66.7% [39.1–86.2] net=+0.088 gross=+0.206 PF=1.26 stop=25.0% mfe=0.95 | n=7 prof=85.7% [48.7–97.4] net=+0.279 gross=+0.321 PF=2.86 stop=14.3% mfe=0.93 |  |
| ema50_dist_atr | 0.5..2 | n=70 prof=50.0% [38.6–61.4] net=-0.148 gross=-0.081 PF=0.69 stop=41.4% mfe=0.83 | n=46 prof=54.3% [40.2–67.8] net=+0.084 gross=+0.132 PF=1.21 stop=32.6% mfe=1.08 |  |
| ema50_dist_atr | <-2 | n=3 prof=33.3% [6.1–79.2] net=-0.630 gross=-0.492 PF=0.19 stop=66.7% mfe=0.41 | n=10 prof=40.0% [16.8–68.7] net=-0.487 gross=-0.420 PF=0.25 stop=60.0% mfe=0.62 |  |
| ema50_dist_atr | >2 | n=39 prof=53.8% [38.6–68.4] net=-0.149 gross=-0.092 PF=0.68 stop=43.6% mfe=0.85 | n=27 prof=44.4% [27.6–62.7] net=-0.215 gross=-0.176 PF=0.59 stop=48.1% mfe=0.80 |  |
| symbol_group | major | n=129 prof=55.0% [46.4–63.4] net=-0.100 gross=-0.027 PF=0.77 stop=38.0% mfe=0.85 | n=87 prof=50.6% [40.3–60.8] net=-0.044 gross=+0.005 PF=0.90 stop=36.8% mfe=0.93 |  |
| symbol_group | other | n=31 prof=41.9% [26.4–59.2] net=-0.364 gross=-0.302 PF=0.40 stop=54.8% mfe=0.72 | n=20 prof=45.0% [25.8–65.8] net=-0.220 gross=-0.177 PF=0.55 stop=40.0% mfe=0.78 |  |
| funding | na | n=160 prof=52.5% [44.8–60.1] net=-0.151 gross=-0.080 PF=0.68 stop=41.2% mfe=0.82 | n=107 prof=49.5% [40.2–58.9] net=-0.077 gross=-0.029 PF=0.82 stop=37.4% mfe=0.90 |  |
| funding_side | neutral | n=160 prof=52.5% [44.8–60.1] net=-0.151 gross=-0.080 PF=0.68 stop=41.2% mfe=0.82 | n=107 prof=49.5% [40.2–58.9] net=-0.077 gross=-0.029 PF=0.82 stop=37.4% mfe=0.90 |  |
| funding_z | na | n=160 prof=52.5% [44.8–60.1] net=-0.151 gross=-0.080 PF=0.68 stop=41.2% mfe=0.82 | n=107 prof=49.5% [40.2–58.9] net=-0.077 gross=-0.029 PF=0.82 stop=37.4% mfe=0.90 |  |
| oi_divergence | na | n=160 prof=52.5% [44.8–60.1] net=-0.151 gross=-0.080 PF=0.68 stop=41.2% mfe=0.82 | n=107 prof=49.5% [40.2–58.9] net=-0.077 gross=-0.029 PF=0.82 stop=37.4% mfe=0.90 |  |
| oi_chg_24h | na | n=160 prof=52.5% [44.8–60.1] net=-0.151 gross=-0.080 PF=0.68 stop=41.2% mfe=0.82 | n=107 prof=49.5% [40.2–58.9] net=-0.077 gross=-0.029 PF=0.82 stop=37.4% mfe=0.90 |  |
| settlement_bar | other | n=134 prof=51.5% [43.1–59.8] net=-0.158 gross=-0.084 PF=0.67 stop=42.5% mfe=0.84 | n=100 prof=49.0% [39.4–58.7] net=-0.103 gross=-0.055 PF=0.77 stop=39.0% mfe=0.89 |  |
| settlement_bar | settlement | n=26 prof=57.7% [38.9–74.5] net=-0.114 gross=-0.061 PF=0.70 stop=34.6% mfe=0.72 | n=7 prof=57.1% [25.0–84.2] net=+0.296 gross=+0.340 PF=2.42 stop=14.3% mfe=1.10 |  |
| session | 03-04 | n=9 prof=22.2% [6.3–54.7] net=-0.483 gross=-0.427 PF=0.25 stop=55.6% mfe=0.60 | n=5 prof=20.0% [3.6–62.4] net=-0.772 gross=-0.725 PF=0.07 stop=80.0% mfe=0.51 |  |
| session | 08-16 | n=54 prof=37.0% [25.4–50.4] net=-0.435 gross=-0.367 PF=0.31 stop=57.4% mfe=0.64 | n=45 prof=57.8% [43.3–71.0] net=+0.011 gross=+0.066 PF=1.02 stop=40.0% mfe=1.03 |  |
| session | 21-23 | n=15 prof=60.0% [35.7–80.2] net=-0.127 gross=-0.073 PF=0.69 stop=33.3% mfe=0.85 | n=15 prof=26.7% [10.9–52.0] net=-0.408 gross=-0.364 PF=0.23 stop=40.0% mfe=0.68 |  |
| session | other | n=82 prof=64.6% [53.8–74.1] net=+0.068 gross=+0.146 PF=1.20 stop=30.5% mfe=0.96 | n=42 prof=52.4% [37.7–66.6] net=+0.029 gross=+0.071 PF=1.08 stop=28.6% mfe=0.89 |  |
| cvd_confirm_0.05 | confirm | n=5 prof=20.0% [3.6–62.4] net=-0.754 gross=-0.695 PF=0.11 stop=80.0% mfe=0.39 | n=23 prof=60.9% [40.8–77.8] net=+0.139 gross=+0.182 PF=1.39 stop=30.4% mfe=1.17 |  |
| cvd_confirm_0.05 | contra | n=6 prof=66.7% [30.0–90.3] net=+0.427 gross=+0.477 PF=2.62 stop=16.7% mfe=1.39 | n=23 prof=52.2% [33.0–70.8] net=+0.027 gross=+0.079 PF=1.07 stop=26.1% mfe=0.96 |  |
| cvd_confirm_0.05 | na | n=149 prof=53.0% [45.0–60.9] net=-0.154 gross=-0.082 PF=0.67 stop=40.9% mfe=0.81 | n=60 prof=43.3% [31.6–55.9] net=-0.207 gross=-0.159 PF=0.60 stop=45.0% mfe=0.77 |  |
| cvd_confirm_0.05 | neutral | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.336 gross=+0.375 PF=inf stop=0.0% mfe=0.80 |  |
| cvd_confirm_0.1 | confirm | n=5 prof=20.0% [3.6–62.4] net=-0.754 gross=-0.695 PF=0.11 stop=80.0% mfe=0.39 | n=22 prof=63.6% [43.0–80.3] net=+0.193 gross=+0.236 PF=1.60 stop=27.3% mfe=1.20 |  |
| cvd_confirm_0.1 | contra | n=6 prof=66.7% [30.0–90.3] net=+0.427 gross=+0.477 PF=2.62 stop=16.7% mfe=1.39 | n=21 prof=57.1% [36.5–75.5] net=+0.092 gross=+0.145 PF=1.28 stop=23.8% mfe=1.01 |  |
| cvd_confirm_0.1 | na | n=149 prof=53.0% [45.0–60.9] net=-0.154 gross=-0.082 PF=0.67 stop=40.9% mfe=0.81 | n=60 prof=43.3% [31.6–55.9] net=-0.207 gross=-0.159 PF=0.60 stop=45.0% mfe=0.77 |  |
| cvd_confirm_0.1 | neutral | n=0 | n=4 prof=25.0% [4.6–69.9] net=-0.505 gross=-0.461 PF=0.14 stop=50.0% mfe=0.57 |  |
| cvd_confirm_0.2 | confirm | n=4 prof=25.0% [4.6–69.9] net=-0.677 gross=-0.619 PF=0.15 stop=75.0% mfe=0.48 | n=17 prof=64.7% [41.3–82.7] net=+0.148 gross=+0.192 PF=1.39 stop=35.3% mfe=1.22 |  |
| cvd_confirm_0.2 | contra | n=5 prof=80.0% [37.6–96.4] net=+0.623 gross=+0.649 PF=4.03 stop=20.0% mfe=1.57 | n=18 prof=50.0% [29.0–71.0] net=-0.069 gross=-0.012 PF=0.82 stop=27.8% mfe=0.90 |  |
| cvd_confirm_0.2 | na | n=149 prof=53.0% [45.0–60.9] net=-0.154 gross=-0.082 PF=0.67 stop=40.9% mfe=0.81 | n=60 prof=43.3% [31.6–55.9] net=-0.207 gross=-0.159 PF=0.60 stop=45.0% mfe=0.77 |  |
| cvd_confirm_0.2 | neutral | n=2 prof=0.0% [0.0–65.8] net=-0.808 gross=-0.690 PF=0.00 stop=50.0% mfe=0.26 | n=12 prof=58.3% [32.0–80.7] net=+0.239 gross=+0.279 PF=1.97 stop=16.7% mfe=1.07 |  |
| cvd_confirm_0.4 | confirm | n=1 prof=0.0% [0.0–79.3] net=-1.027 gross=-1.000 PF=0.00 stop=100.0% mfe=0.33 | n=13 prof=61.5% [35.5–82.3] net=+0.003 gross=+0.046 PF=1.01 stop=38.5% mfe=1.06 |  |
| cvd_confirm_0.4 | contra | n=4 prof=75.0% [30.1–95.4] net=+0.442 gross=+0.467 PF=2.72 stop=25.0% mfe=1.40 | n=11 prof=45.5% [21.3–72.0] net=-0.205 gross=-0.136 PF=0.55 stop=36.4% mfe=0.78 |  |
| cvd_confirm_0.4 | na | n=149 prof=53.0% [45.0–60.9] net=-0.154 gross=-0.082 PF=0.67 stop=40.9% mfe=0.81 | n=60 prof=43.3% [31.6–55.9] net=-0.207 gross=-0.159 PF=0.60 stop=45.0% mfe=0.77 |  |
| cvd_confirm_0.4 | neutral | n=6 prof=33.3% [9.7–70.0] net=-0.325 gross=-0.247 PF=0.48 stop=50.0% mfe=0.72 | n=23 prof=60.9% [40.8–77.8] net=+0.277 gross=+0.317 PF=2.05 stop=17.4% mfe=1.19 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

### liquidity_sweep_long (1h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-08 | 78 | 52.6 | -0.185 |
| 2026-09 | 102 | 52.9 | -0.165 |
| 2026-10 | 48 | 60.4 | -0.054 |

**Filter study** (51 cuts tested — expect ~2.6 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=42 prof=69.0% [54.0–80.9] net=+0.073 gross=+0.184 PF=1.23 stop=28.6% mfe=1.18 | n=27 prof=44.4% [27.6–62.7] net=-0.340 gross=-0.250 PF=0.45 stop=55.6% mfe=0.83 |  |
| btc_aligned | yes | n=94 prof=44.7% [35.0–54.7] net=-0.300 gross=-0.200 PF=0.48 stop=52.1% mfe=0.85 | n=65 prof=63.1% [50.9–73.8] net=+0.008 gross=+0.090 PF=1.02 stop=35.4% mfe=0.99 |  |
| confluence3 | 0-1 | n=49 prof=53.1% [39.4–66.3] net=-0.193 gross=-0.087 PF=0.63 stop=46.9% mfe=1.00 | n=21 prof=52.4% [32.4–71.7] net=-0.198 gross=-0.092 PF=0.63 stop=47.6% mfe=0.93 |  |
| confluence3 | 2-3 | n=87 prof=51.7% [41.4–61.9] net=-0.180 gross=-0.078 PF=0.63 stop=43.7% mfe=0.93 | n=71 prof=59.2% [47.5–69.8] net=-0.064 gross=+0.015 PF=0.85 stop=39.4% mfe=0.95 |  |
| risk_pct | 2-4% | n=19 prof=31.6% [15.4–54.0] net=-0.483 gross=-0.439 PF=0.28 stop=63.2% mfe=0.62 | n=15 prof=66.7% [41.7–84.8] net=-0.026 gross=+0.010 PF=0.93 stop=33.3% mfe=0.94 |  |
| risk_pct | 4-8% | n=0 | n=2 prof=100.0% [34.2–100.0] net=+1.360 gross=+1.375 PF=inf stop=0.0% mfe=2.00 |  |
| risk_pct | <2% | n=116 prof=56.0% [47.0–64.7] net=-0.134 gross=-0.021 PF=0.72 stop=42.2% mfe=1.01 | n=74 prof=54.1% [42.8–64.9] net=-0.161 gross=-0.064 PF=0.68 stop=44.6% mfe=0.91 |  |
| risk_pct | >8% | n=1 prof=0.0% [0.0–79.3] net=-0.393 gross=-0.378 PF=0.00 stop=0.0% mfe=0.08 | n=1 prof=100.0% [20.7–100.0] net=+0.926 gross=+0.939 PF=inf stop=0.0% mfe=1.28 |  |
| hour | 00-08 | n=30 prof=53.3% [36.1–69.8] net=-0.179 gross=-0.037 PF=0.59 stop=36.7% mfe=0.85 | n=24 prof=62.5% [42.7–78.8] net=+0.062 gross=+0.141 PF=1.15 stop=37.5% mfe=1.11 |  |
| hour | 08-16 | n=60 prof=56.7% [44.1–68.4] net=-0.145 gross=-0.057 PF=0.69 stop=43.3% mfe=1.03 | n=38 prof=39.5% [25.6–55.3] net=-0.482 gross=-0.395 PF=0.25 stop=57.9% mfe=0.61 |  |
| hour | 16-24 | n=46 prof=45.7% [32.2–59.8] net=-0.240 gross=-0.143 PF=0.59 stop=52.2% mfe=0.92 | n=30 prof=76.7% [59.1–88.2] net=+0.272 gross=+0.358 PF=2.01 stop=23.3% mfe=1.23 |  |
| weekend | weekday | n=114 prof=48.2% [39.3–57.3] net=-0.273 gross=-0.183 PF=0.51 stop=50.9% mfe=0.89 | n=81 prof=56.8% [45.9–67.0] net=-0.099 gross=-0.014 PF=0.79 stop=42.0% mfe=0.95 |  |
| weekend | weekend | n=22 prof=72.7% [51.8–86.8] net=+0.274 gross=+0.442 PF=2.46 stop=13.6% mfe=1.26 | n=11 prof=63.6% [35.4–84.8] net=-0.064 gross=+0.021 PF=0.84 stop=36.4% mfe=0.91 |  |
| adx | 20-30 | n=49 prof=55.1% [41.3–68.1] net=-0.184 gross=-0.062 PF=0.61 stop=40.8% mfe=0.92 | n=41 prof=61.0% [45.7–74.3] net=-0.062 gross=+0.014 PF=0.85 stop=39.0% mfe=0.92 |  |
| adx | <20 | n=64 prof=46.9% [35.2–58.9] net=-0.257 gross=-0.156 PF=0.54 stop=51.6% mfe=0.89 | n=30 prof=53.3% [36.1–69.8] net=-0.175 gross=-0.081 PF=0.64 stop=43.3% mfe=0.89 |  |
| adx | >30 | n=23 prof=60.9% [40.8–77.8] net=+0.014 gross=+0.084 PF=1.04 stop=34.8% mfe=1.20 | n=21 prof=57.1% [36.5–75.5] net=-0.042 gross=+0.045 PF=0.91 stop=42.9% mfe=1.06 |  |
| vol_spike | <1.5 | n=51 prof=51.0% [37.7–64.1] net=-0.241 gross=-0.119 PF=0.55 stop=47.1% mfe=0.92 | n=48 prof=60.4% [46.3–73.0] net=-0.085 gross=+0.011 PF=0.81 stop=39.6% mfe=0.98 |  |
| vol_spike | >=1.5 | n=85 prof=52.9% [42.4–63.2] net=-0.151 gross=-0.059 PF=0.68 stop=43.5% mfe=0.97 | n=44 prof=54.5% [40.1–68.3] net=-0.104 gross=-0.032 PF=0.78 stop=43.2% mfe=0.90 |  |
| ema50_dist_atr | -0.5..0.5 | n=21 prof=57.1% [36.5–75.5] net=-0.018 gross=+0.079 PF=0.96 stop=38.1% mfe=0.98 | n=21 prof=47.6% [28.3–67.6] net=-0.326 gross=-0.242 PF=0.44 stop=52.4% mfe=0.70 |  |
| ema50_dist_atr | -2..-0.5 | n=68 prof=50.0% [38.4–61.6] net=-0.267 gross=-0.150 PF=0.51 stop=48.5% mfe=0.88 | n=34 prof=67.6% [50.8–80.9] net=+0.127 gross=+0.216 PF=1.39 stop=29.4% mfe=1.14 |  |
| ema50_dist_atr | 0.5..2 | n=6 prof=0.0% [0.0–39.0] net=-0.951 gross=-0.896 PF=0.00 stop=83.3% mfe=0.28 | n=8 prof=62.5% [30.6–86.3] net=+0.005 gross=+0.059 PF=1.01 stop=37.5% mfe=1.12 |  |
| ema50_dist_atr | <-2 | n=41 prof=61.0% [45.7–74.3] net=-0.021 gross=+0.069 PF=0.95 stop=36.6% mfe=1.17 | n=29 prof=51.7% [34.4–68.6] net=-0.214 gross=-0.125 PF=0.60 stop=48.3% mfe=0.84 |  |
| symbol_group | major | n=114 prof=53.5% [44.4–62.4] net=-0.163 gross=-0.054 PF=0.66 stop=43.0% mfe=0.94 | n=70 prof=61.4% [49.7–72.0] net=-0.005 gross=+0.082 PF=0.99 stop=37.1% mfe=1.03 |  |
| symbol_group | other | n=22 prof=45.5% [26.9–65.3] net=-0.295 gross=-0.225 PF=0.50 stop=54.5% mfe=1.00 | n=22 prof=45.5% [26.9–65.3] net=-0.378 gross=-0.302 PF=0.36 stop=54.5% mfe=0.67 |  |
| funding | na | n=136 prof=52.2% [43.9–60.4] net=-0.185 gross=-0.082 PF=0.63 stop=44.9% mfe=0.95 | n=92 prof=57.6% [47.4–67.2] net=-0.094 gross=-0.010 PF=0.79 stop=41.3% mfe=0.94 |  |
| funding_side | neutral | n=136 prof=52.2% [43.9–60.4] net=-0.185 gross=-0.082 PF=0.63 stop=44.9% mfe=0.95 | n=92 prof=57.6% [47.4–67.2] net=-0.094 gross=-0.010 PF=0.79 stop=41.3% mfe=0.94 |  |
| funding_z | na | n=136 prof=52.2% [43.9–60.4] net=-0.185 gross=-0.082 PF=0.63 stop=44.9% mfe=0.95 | n=92 prof=57.6% [47.4–67.2] net=-0.094 gross=-0.010 PF=0.79 stop=41.3% mfe=0.94 |  |
| oi_divergence | na | n=136 prof=52.2% [43.9–60.4] net=-0.185 gross=-0.082 PF=0.63 stop=44.9% mfe=0.95 | n=92 prof=57.6% [47.4–67.2] net=-0.094 gross=-0.010 PF=0.79 stop=41.3% mfe=0.94 |  |
| oi_chg_24h | na | n=136 prof=52.2% [43.9–60.4] net=-0.185 gross=-0.082 PF=0.63 stop=44.9% mfe=0.95 | n=92 prof=57.6% [47.4–67.2] net=-0.094 gross=-0.010 PF=0.79 stop=41.3% mfe=0.94 |  |
| settlement_bar | other | n=125 prof=51.2% [42.5–59.8] net=-0.208 gross=-0.104 PF=0.59 stop=45.6% mfe=0.93 | n=86 prof=58.1% [47.6–68.0] net=-0.094 gross=-0.014 PF=0.79 stop=40.7% mfe=0.93 |  |
| settlement_bar | settlement | n=11 prof=63.6% [35.4–84.8] net=+0.076 gross=+0.175 PF=1.18 stop=36.4% mfe=1.16 | n=6 prof=50.0% [18.8–81.2] net=-0.095 gross=+0.046 PF=0.84 stop=50.0% mfe=1.20 |  |
| session | 03-04 | n=8 prof=50.0% [21.5–78.5] net=-0.155 gross=+0.106 PF=0.52 stop=25.0% mfe=0.91 | n=6 prof=66.7% [30.0–90.3] net=+0.218 gross=+0.275 PF=1.62 stop=33.3% mfe=1.28 |  |
| session | 08-16 | n=60 prof=56.7% [44.1–68.4] net=-0.145 gross=-0.057 PF=0.69 stop=43.3% mfe=1.03 | n=38 prof=39.5% [25.6–55.3] net=-0.482 gross=-0.395 PF=0.25 stop=57.9% mfe=0.61 |  |
| session | 21-23 | n=20 prof=35.0% [18.1–56.7] net=-0.513 gross=-0.410 PF=0.30 stop=65.0% mfe=0.62 | n=9 prof=66.7% [35.4–87.9] net=+0.155 gross=+0.250 PF=1.42 stop=33.3% mfe=1.10 |  |
| session | other | n=48 prof=54.2% [40.3–67.4] net=-0.102 gross=-0.007 PF=0.78 stop=41.7% mfe=1.00 | n=39 prof=71.8% [56.2–83.5] net=+0.178 gross=+0.262 PF=1.56 stop=28.2% mfe=1.18 |  |
| cvd_confirm_0.05 | confirm | n=1 prof=0.0% [0.0–79.3] net=-1.089 gross=-1.000 PF=0.00 stop=100.0% mfe=0.70 | n=7 prof=42.9% [15.8–75.0] net=-0.204 gross=-0.102 PF=0.59 stop=42.9% mfe=0.73 |  |
| cvd_confirm_0.05 | contra | n=14 prof=78.6% [52.4–92.4] net=+0.090 gross=+0.166 PF=1.39 stop=21.4% mfe=1.08 | n=39 prof=56.4% [41.0–70.7] net=-0.127 gross=-0.047 PF=0.74 stop=43.6% mfe=0.91 |  |
| cvd_confirm_0.05 | na | n=121 prof=49.6% [40.8–58.4] net=-0.209 gross=-0.103 PF=0.60 stop=47.1% mfe=0.94 | n=45 prof=60.0% [45.5–73.0] net=-0.058 gross=+0.028 PF=0.87 stop=40.0% mfe=1.01 |  |
| cvd_confirm_0.05 | neutral | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.332 gross=+0.375 PF=inf stop=0.0% mfe=0.94 |  |
| cvd_confirm_0.1 | confirm | n=1 prof=0.0% [0.0–79.3] net=-1.089 gross=-1.000 PF=0.00 stop=100.0% mfe=0.70 | n=5 prof=40.0% [11.8–76.9] net=-0.124 gross=-0.018 PF=0.74 stop=40.0% mfe=0.81 |  |
| cvd_confirm_0.1 | contra | n=14 prof=78.6% [52.4–92.4] net=+0.090 gross=+0.166 PF=1.39 stop=21.4% mfe=1.08 | n=38 prof=57.9% [42.2–72.1] net=-0.102 gross=-0.022 PF=0.78 stop=42.1% mfe=0.92 |  |
| cvd_confirm_0.1 | na | n=121 prof=49.6% [40.8–58.4] net=-0.209 gross=-0.103 PF=0.60 stop=47.1% mfe=0.94 | n=45 prof=60.0% [45.5–73.0] net=-0.058 gross=+0.028 PF=0.87 stop=40.0% mfe=1.01 |  |
| cvd_confirm_0.1 | neutral | n=0 | n=4 prof=50.0% [15.0–85.0] net=-0.396 gross=-0.312 PF=0.29 stop=50.0% mfe=0.54 |  |
| cvd_confirm_0.2 | confirm | n=0 | n=4 prof=50.0% [15.0–85.0] net=+0.110 gross=+0.228 PF=1.33 stop=25.0% mfe=0.96 |  |
| cvd_confirm_0.2 | contra | n=13 prof=76.9% [49.7–91.8] net=+0.059 gross=+0.139 PF=1.24 stop=23.1% mfe=1.04 | n=34 prof=55.9% [39.5–71.1] net=-0.127 gross=-0.045 PF=0.74 stop=44.1% mfe=0.93 |  |
| cvd_confirm_0.2 | na | n=121 prof=49.6% [40.8–58.4] net=-0.209 gross=-0.103 PF=0.60 stop=47.1% mfe=0.94 | n=45 prof=60.0% [45.5–73.0] net=-0.058 gross=+0.028 PF=0.87 stop=40.0% mfe=1.01 |  |
| cvd_confirm_0.2 | neutral | n=2 prof=50.0% [9.5–90.5] net=-0.298 gross=-0.237 PF=0.45 stop=50.0% mfe=1.20 | n=9 prof=55.6% [26.7–81.1] net=-0.243 gross=-0.173 PF=0.50 stop=44.4% mfe=0.64 |  |
| cvd_confirm_0.4 | confirm | n=0 | n=2 prof=50.0% [9.5–90.5] net=-0.367 gross=-0.237 PF=0.39 stop=50.0% mfe=0.62 |  |
| cvd_confirm_0.4 | contra | n=8 prof=75.0% [40.9–92.9] net=+0.015 gross=+0.106 PF=1.05 stop=25.0% mfe=1.00 | n=30 prof=53.3% [36.1–69.8] net=-0.152 gross=-0.065 PF=0.71 stop=46.7% mfe=0.94 |  |
| cvd_confirm_0.4 | na | n=121 prof=49.6% [40.8–58.4] net=-0.209 gross=-0.103 PF=0.60 stop=47.1% mfe=0.94 | n=45 prof=60.0% [45.5–73.0] net=-0.058 gross=+0.028 PF=0.87 stop=40.0% mfe=1.01 |  |
| cvd_confirm_0.4 | neutral | n=7 prof=71.4% [35.9–91.8] net=+0.009 gross=+0.068 PF=1.03 stop=28.6% mfe=1.13 | n=15 prof=60.0% [35.7–80.2] net=-0.051 gross=+0.017 PF=0.86 stop=33.3% mfe=0.80 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

### rsi_bounce_long (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-08 | 19 | 36.8 | -0.339 |
| 2026-09 | 21 | 66.7 | +0.264 |
| 2026-10 | 18 | 61.1 | +0.038 |

**Filter study** (51 cuts tested — expect ~2.6 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=16 prof=56.2% [33.2–76.9] net=+0.208 gross=+0.256 PF=1.94 stop=12.5% mfe=0.89 | n=15 prof=66.7% [41.7–84.8] net=+0.158 gross=+0.197 PF=1.88 stop=13.3% mfe=0.66 |  |
| btc_aligned | yes | n=18 prof=33.3% [16.3–56.3] net=-0.452 gross=-0.412 PF=0.30 stop=55.6% mfe=0.69 | n=9 prof=77.8% [45.3–93.7] net=+0.248 gross=+0.267 PF=2.09 stop=22.2% mfe=1.04 |  |
| confluence3 | 0-1 | n=22 prof=45.5% [26.9–65.3] net=-0.024 gross=+0.028 PF=0.94 stop=31.8% mfe=0.85 | n=17 prof=64.7% [41.3–82.7] net=+0.120 gross=+0.158 PF=1.55 stop=17.6% mfe=0.69 |  |
| confluence3 | 2-3 | n=12 prof=41.7% [19.3–68.0] net=-0.358 gross=-0.328 PF=0.32 stop=41.7% mfe=0.66 | n=7 prof=85.7% [48.7–97.4] net=+0.364 gross=+0.382 PF=3.48 stop=14.3% mfe=1.07 |  |
| risk_pct | 2-4% | n=11 prof=54.5% [28.0–78.7] net=+0.014 gross=+0.052 PF=1.04 stop=27.3% mfe=0.95 | n=3 prof=66.7% [20.8–93.9] net=+0.173 gross=+0.213 PF=2.16 stop=0.0% mfe=0.86 |  |
| risk_pct | 4-8% | n=14 prof=35.7% [16.3–61.2] net=-0.141 gross=-0.116 PF=0.67 stop=28.6% mfe=0.68 | n=18 prof=66.7% [43.7–83.7] net=+0.159 gross=+0.183 PF=1.67 stop=22.2% mfe=0.73 |  |
| risk_pct | <2% | n=8 prof=50.0% [21.5–78.5] net=-0.248 gross=-0.159 PF=0.54 stop=50.0% mfe=0.77 | n=1 prof=100.0% [20.7–100.0] net=+0.335 gross=+0.525 PF=inf stop=0.0% mfe=1.25 |  |
| risk_pct | >8% | n=1 prof=0.0% [0.0–79.3] net=-1.012 gross=-1.000 PF=0.00 stop=100.0% mfe=0.52 | n=2 prof=100.0% [34.2–100.0] net=+0.438 gross=+0.450 PF=inf stop=0.0% mfe=1.08 |  |
| hour | 00-08 | n=11 prof=36.4% [15.2–64.6] net=-0.205 gross=-0.160 PF=0.50 stop=27.3% mfe=0.69 | n=11 prof=72.7% [43.4–90.3] net=+0.095 gross=+0.137 PF=1.34 stop=27.3% mfe=0.70 |  |
| hour | 08-16 | n=11 prof=63.6% [35.4–84.8] net=+0.157 gross=+0.201 PF=1.45 stop=27.3% mfe=1.03 | n=8 prof=62.5% [30.6–86.3] net=+0.129 gross=+0.153 PF=1.85 stop=12.5% mfe=0.77 |  |
| hour | 16-24 | n=12 prof=33.3% [13.8–60.9] net=-0.357 gross=-0.314 PF=0.37 stop=50.0% mfe=0.65 | n=5 prof=80.0% [37.6–96.4] net=+0.503 gross=+0.527 PF=6.63 stop=0.0% mfe=1.07 |  |
| weekend | weekday | n=18 prof=50.0% [29.0–71.0] net=-0.001 gross=+0.047 PF=1.00 stop=33.3% mfe=0.91 | n=18 prof=66.7% [43.7–83.7] net=+0.092 gross=+0.115 PF=1.39 stop=22.2% mfe=0.68 |  |
| weekend | weekend | n=16 prof=37.5% [18.5–61.4] net=-0.300 gross=-0.260 PF=0.39 stop=37.5% mfe=0.64 | n=6 prof=83.3% [43.6–97.0] net=+0.490 gross=+0.549 PF=7.58 stop=0.0% mfe=1.18 |  |
| adx | 20-30 | n=15 prof=53.3% [30.1–75.2] net=+0.054 gross=+0.099 PF=1.17 stop=20.0% mfe=0.86 | n=10 prof=60.0% [31.3–83.2] net=-0.077 gross=-0.057 PF=0.81 stop=40.0% mfe=0.72 |  |
| adx | <20 | n=10 prof=40.0% [16.8–68.7] net=-0.341 gross=-0.300 PF=0.43 stop=50.0% mfe=0.71 | n=4 prof=100.0% [51.0–100.0] net=+0.681 gross=+0.744 PF=inf stop=0.0% mfe=1.34 |  |
| adx | >30 | n=9 prof=33.3% [12.1–64.6] net=-0.245 gross=-0.200 PF=0.49 stop=44.4% mfe=0.74 | n=10 prof=70.0% [39.7–89.2] net=+0.264 gross=+0.296 PF=5.11 stop=0.0% mfe=0.67 |  |
| vol_spike | <1.5 | n=29 prof=41.4% [25.5–59.3] net=-0.187 gross=-0.145 PF=0.61 stop=37.9% mfe=0.77 | n=24 prof=70.8% [50.8–85.1] net=+0.191 gross=+0.224 PF=1.97 stop=16.7% mfe=0.80 |  |
| vol_spike | >=1.5 | n=5 prof=60.0% [23.1–88.2] net=+0.120 gross=+0.178 PF=1.44 stop=20.0% mfe=0.88 | n=0 |  |
| ema50_dist_atr | -0.5..0.5 | n=7 prof=28.6% [8.2–64.1] net=-0.423 gross=-0.390 PF=0.24 stop=42.9% mfe=0.52 | n=2 prof=100.0% [34.2–100.0] net=+0.758 gross=+0.781 PF=inf stop=0.0% mfe=1.31 |  |
| ema50_dist_atr | -2..-0.5 | n=16 prof=56.2% [33.2–76.9] net=+0.038 gross=+0.087 PF=1.12 stop=25.0% mfe=0.83 | n=6 prof=66.7% [30.0–90.3] net=+0.169 gross=+0.189 PF=1.49 stop=33.3% mfe=0.98 |  |
| ema50_dist_atr | 0.5..2 | n=4 prof=50.0% [15.0–85.0] net=-0.217 gross=-0.187 PF=0.49 stop=25.0% mfe=0.72 | n=3 prof=100.0% [43.8–100.0] net=+0.463 gross=+0.475 PF=inf stop=0.0% mfe=1.15 |  |
| ema50_dist_atr | <-2 | n=5 prof=40.0% [11.8–76.9] net=+0.102 gross=+0.154 PF=1.23 stop=40.0% mfe=1.11 | n=13 prof=61.5% [35.5–82.3] net=+0.052 gross=+0.096 PF=1.25 stop=15.4% mfe=0.56 |  |
| ema50_dist_atr | >2 | n=2 prof=0.0% [0.0–65.8] net=-1.054 gross=-1.000 PF=0.00 stop=100.0% mfe=0.58 | n=0 |  |
| symbol_group | major | n=30 prof=43.3% [27.4–60.8] net=-0.166 gross=-0.120 PF=0.63 stop=36.7% mfe=0.77 | n=19 prof=68.4% [46.0–84.6] net=+0.195 gross=+0.228 PF=2.00 stop=15.8% mfe=0.83 |  |
| symbol_group | other | n=4 prof=50.0% [15.0–85.0] net=+0.043 gross=+0.070 PF=1.10 stop=25.0% mfe=0.85 | n=5 prof=80.0% [37.6–96.4] net=+0.180 gross=+0.205 PF=1.88 stop=20.0% mfe=0.67 |  |
| funding | na | n=34 prof=44.1% [28.9–60.5] net=-0.141 gross=-0.098 PF=0.68 stop=35.3% mfe=0.78 | n=24 prof=70.8% [50.8–85.1] net=+0.191 gross=+0.224 PF=1.97 stop=16.7% mfe=0.80 |  |
| funding_side | neutral | n=34 prof=44.1% [28.9–60.5] net=-0.141 gross=-0.098 PF=0.68 stop=35.3% mfe=0.78 | n=24 prof=70.8% [50.8–85.1] net=+0.191 gross=+0.224 PF=1.97 stop=16.7% mfe=0.80 |  |
| funding_z | na | n=34 prof=44.1% [28.9–60.5] net=-0.141 gross=-0.098 PF=0.68 stop=35.3% mfe=0.78 | n=24 prof=70.8% [50.8–85.1] net=+0.191 gross=+0.224 PF=1.97 stop=16.7% mfe=0.80 |  |
| oi_divergence | na | n=34 prof=44.1% [28.9–60.5] net=-0.141 gross=-0.098 PF=0.68 stop=35.3% mfe=0.78 | n=24 prof=70.8% [50.8–85.1] net=+0.191 gross=+0.224 PF=1.97 stop=16.7% mfe=0.80 |  |
| oi_chg_24h | na | n=34 prof=44.1% [28.9–60.5] net=-0.141 gross=-0.098 PF=0.68 stop=35.3% mfe=0.78 | n=24 prof=70.8% [50.8–85.1] net=+0.191 gross=+0.224 PF=1.97 stop=16.7% mfe=0.80 |  |
| settlement_bar | other | n=11 prof=54.5% [28.0–78.7] net=-0.113 gross=-0.072 PF=0.72 stop=36.4% mfe=0.69 | n=8 prof=87.5% [52.9–97.8] net=+0.395 gross=+0.419 PF=19.47 stop=0.0% mfe=0.83 |  |
| settlement_bar | settlement | n=23 prof=39.1% [22.2–59.2] net=-0.155 gross=-0.110 PF=0.67 stop=34.8% mfe=0.83 | n=16 prof=62.5% [38.6–81.5] net=+0.090 gross=+0.125 PF=1.32 stop=25.0% mfe=0.78 |  |
| session | 03-04 | n=2 prof=50.0% [9.5–90.5] net=-0.037 gross=+0.015 PF=0.59 stop=0.0% mfe=0.28 | n=0 |  |
| session | 08-16 | n=11 prof=63.6% [35.4–84.8] net=+0.157 gross=+0.201 PF=1.45 stop=27.3% mfe=1.03 | n=8 prof=62.5% [30.6–86.3] net=+0.129 gross=+0.153 PF=1.85 stop=12.5% mfe=0.77 |  |
| session | other | n=21 prof=33.3% [17.2–54.6] net=-0.308 gross=-0.265 PF=0.42 stop=42.9% mfe=0.70 | n=16 prof=75.0% [50.5–89.8] net=+0.223 gross=+0.259 PF=2.01 stop=18.8% mfe=0.82 |  |
| cvd_confirm_0.05 | confirm | n=2 prof=0.0% [0.0–65.8] net=-1.022 gross=-1.000 PF=0.00 stop=100.0% mfe=0.10 | n=4 prof=50.0% [15.0–85.0] net=-0.107 gross=-0.082 PF=0.71 stop=25.0% mfe=0.62 |  |
| cvd_confirm_0.05 | contra | n=2 prof=50.0% [9.5–90.5] net=+0.495 gross=+0.529 PF=3.80 stop=0.0% mfe=1.22 | n=9 prof=88.9% [56.5–98.0] net=+0.367 gross=+0.389 PF=4.24 stop=11.1% mfe=0.83 |  |
| cvd_confirm_0.05 | na | n=30 prof=46.7% [30.2–63.9] net=-0.125 gross=-0.079 PF=0.70 stop=33.3% mfe=0.80 | n=10 prof=60.0% [31.3–83.2] net=+0.101 gross=+0.146 PF=1.45 stop=20.0% mfe=0.76 |  |
| cvd_confirm_0.05 | neutral | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.703 gross=+0.725 PF=inf stop=0.0% mfe=1.64 |  |
| cvd_confirm_0.1 | confirm | n=2 prof=0.0% [0.0–65.8] net=-1.022 gross=-1.000 PF=0.00 stop=100.0% mfe=0.10 | n=4 prof=50.0% [15.0–85.0] net=-0.107 gross=-0.082 PF=0.71 stop=25.0% mfe=0.62 |  |
| cvd_confirm_0.1 | contra | n=2 prof=50.0% [9.5–90.5] net=+0.495 gross=+0.529 PF=3.80 stop=0.0% mfe=1.22 | n=7 prof=85.7% [48.7–97.4] net=+0.366 gross=+0.386 PF=3.51 stop=14.3% mfe=0.94 |  |
| cvd_confirm_0.1 | na | n=30 prof=46.7% [30.2–63.9] net=-0.125 gross=-0.079 PF=0.70 stop=33.3% mfe=0.80 | n=10 prof=60.0% [31.3–83.2] net=+0.101 gross=+0.146 PF=1.45 stop=20.0% mfe=0.76 |  |
| cvd_confirm_0.1 | neutral | n=0 | n=3 prof=100.0% [43.8–100.0] net=+0.482 gross=+0.509 PF=inf stop=0.0% mfe=0.84 |  |
| cvd_confirm_0.2 | confirm | n=1 prof=0.0% [0.0–79.3] net=-1.019 gross=-1.000 PF=0.00 stop=100.0% mfe=0.14 | n=4 prof=50.0% [15.0–85.0] net=-0.107 gross=-0.082 PF=0.71 stop=25.0% mfe=0.62 |  |
| cvd_confirm_0.2 | contra | n=1 prof=0.0% [0.0–79.3] net=-0.354 gross=-0.316 PF=0.00 stop=0.0% mfe=0.34 | n=5 prof=80.0% [37.6–96.4] net=+0.345 gross=+0.367 PF=2.69 stop=20.0% mfe=0.97 |  |
| cvd_confirm_0.2 | na | n=30 prof=46.7% [30.2–63.9] net=-0.125 gross=-0.079 PF=0.70 stop=33.3% mfe=0.80 | n=10 prof=60.0% [31.3–83.2] net=+0.101 gross=+0.146 PF=1.45 stop=20.0% mfe=0.76 |  |
| cvd_confirm_0.2 | neutral | n=2 prof=50.0% [9.5–90.5] net=+0.161 gross=+0.188 PF=1.31 stop=50.0% mfe=1.07 | n=5 prof=100.0% [56.6–100.0] net=+0.457 gross=+0.479 PF=inf stop=0.0% mfe=0.85 |  |
| cvd_confirm_0.4 | confirm | n=1 prof=0.0% [0.0–79.3] net=-1.019 gross=-1.000 PF=0.00 stop=100.0% mfe=0.14 | n=2 prof=50.0% [9.5–90.5] net=-0.171 gross=-0.150 PF=0.66 stop=50.0% mfe=0.50 |  |
| cvd_confirm_0.4 | contra | n=1 prof=0.0% [0.0–79.3] net=-0.354 gross=-0.316 PF=0.00 stop=0.0% mfe=0.34 | n=3 prof=100.0% [43.8–100.0] net=+0.750 gross=+0.770 PF=inf stop=0.0% mfe=1.18 |  |
| cvd_confirm_0.4 | na | n=30 prof=46.7% [30.2–63.9] net=-0.125 gross=-0.079 PF=0.70 stop=33.3% mfe=0.80 | n=10 prof=60.0% [31.3–83.2] net=+0.101 gross=+0.146 PF=1.45 stop=20.0% mfe=0.76 |  |
| cvd_confirm_0.4 | neutral | n=2 prof=50.0% [9.5–90.5] net=+0.161 gross=+0.188 PF=1.31 stop=50.0% mfe=1.07 | n=9 prof=77.8% [45.3–93.7] net=+0.186 gross=+0.210 PF=2.14 stop=11.1% mfe=0.79 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

### trend_pullback_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-08 | 15 | 53.3 | -0.124 |
| 2026-09 | 20 | 50.0 | -0.278 |
| 2026-10 | 19 | 42.1 | +0.059 |

**Filter study** (48 cuts tested — expect ~2.4 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=15 prof=40.0% [19.8–64.3] net=-0.391 gross=-0.343 PF=0.38 stop=60.0% mfe=0.72 | n=4 prof=50.0% [15.0–85.0] net=+0.135 gross=+0.268 PF=3.42 stop=0.0% mfe=0.90 |  |
| btc_aligned | yes | n=17 prof=58.8% [36.0–78.4] net=-0.124 gross=-0.053 PF=0.72 stop=41.2% mfe=0.98 | n=18 prof=44.4% [24.6–66.3] net=+0.064 gross=+0.106 PF=1.13 stop=44.4% mfe=1.14 |  |
| confluence3 | 0-1 | n=2 prof=0.0% [0.0–65.8] net=-1.038 gross=-1.000 PF=0.00 stop=100.0% mfe=0.26 | n=8 prof=62.5% [30.6–86.3] net=+0.427 gross=+0.495 PF=2.54 stop=25.0% mfe=1.35 |  |
| confluence3 | 2-3 | n=30 prof=53.3% [36.1–69.8] net=-0.197 gross=-0.135 PF=0.61 stop=46.7% mfe=0.90 | n=14 prof=35.7% [16.3–61.2] net=-0.123 gross=-0.070 PF=0.74 stop=42.9% mfe=0.94 |  |
| risk_pct | 2-4% | n=19 prof=42.1% [23.1–63.7] net=-0.423 gross=-0.382 PF=0.30 stop=57.9% mfe=0.71 | n=9 prof=44.4% [18.9–73.3] net=+0.129 gross=+0.161 PF=1.27 stop=44.4% mfe=1.19 |  |
| risk_pct | 4-8% | n=1 prof=0.0% [0.0–79.3] net=-1.031 gross=-1.000 PF=0.00 stop=100.0% mfe=0.36 | n=3 prof=33.3% [6.1–79.2] net=-0.240 gross=-0.220 PF=0.41 stop=33.3% mfe=0.79 |  |
| risk_pct | <2% | n=12 prof=66.7% [39.1–86.2] net=+0.091 gross=+0.183 PF=1.25 stop=33.3% mfe=1.15 | n=10 prof=50.0% [23.7–76.3] net=+0.124 gross=+0.220 PF=1.36 stop=30.0% mfe=1.10 |  |
| hour | 00-08 | n=5 prof=60.0% [23.1–88.2] net=-0.076 gross=+0.004 PF=0.83 stop=40.0% mfe=0.95 | n=1 prof=0.0% [0.0–79.3] net=-0.089 gross=-0.054 PF=0.00 stop=0.0% mfe=0.28 |  |
| hour | 08-16 | n=13 prof=46.2% [23.2–70.9] net=-0.228 gross=-0.177 PF=0.60 stop=53.8% mfe=0.93 | n=9 prof=44.4% [18.9–73.3] net=-0.113 gross=-0.056 PF=0.80 stop=55.6% mfe=0.92 |  |
| hour | 16-24 | n=14 prof=50.0% [26.8–73.2] net=-0.331 gross=-0.270 PF=0.37 stop=50.0% mfe=0.77 | n=12 prof=50.0% [25.4–74.6] net=+0.233 gross=+0.295 PF=1.78 stop=25.0% mfe=1.29 |  |
| weekend | weekday | n=16 prof=43.8% [23.1–66.8] net=-0.347 gross=-0.289 PF=0.42 stop=56.2% mfe=0.75 | n=14 prof=64.3% [38.8–83.7] net=+0.547 gross=+0.598 PF=4.14 stop=14.3% mfe=1.56 |  |
| weekend | weekend | n=16 prof=56.2% [33.2–76.9] net=-0.152 gross=-0.089 PF=0.67 stop=43.8% mfe=0.98 | n=8 prof=12.5% [2.2–47.1] net=-0.746 gross=-0.674 PF=0.07 stop=75.0% mfe=0.27 |  |
| adx | 20-30 | n=14 prof=50.0% [26.8–73.2] net=-0.184 gross=-0.127 PF=0.66 stop=50.0% mfe=0.95 | n=10 prof=80.0% [49.0–94.3] net=+0.847 gross=+0.908 PF=8.62 stop=10.0% mfe=1.85 |  |
| adx | <20 | n=11 prof=36.4% [15.2–64.6] net=-0.535 gross=-0.486 PF=0.20 stop=63.6% mfe=0.63 | n=5 prof=20.0% [3.6–62.4] net=-0.550 gross=-0.478 PF=0.16 stop=60.0% mfe=0.57 |  |
| adx | >30 | n=7 prof=71.4% [35.9–91.8] net=+0.070 gross=+0.153 PF=1.24 stop=28.6% mfe=1.06 | n=7 prof=14.3% [2.6–51.3] net=-0.576 gross=-0.531 PF=0.11 stop=57.1% mfe=0.38 |  |
| vol_spike | <1.5 | n=29 prof=51.7% [34.4–68.6] net=-0.217 gross=-0.158 PF=0.58 stop=48.3% mfe=0.89 | n=19 prof=42.1% [23.1–63.7] net=+0.007 gross=+0.065 PF=1.02 stop=36.8% mfe=0.98 |  |
| vol_spike | >=1.5 | n=3 prof=33.3% [6.1–79.2] net=-0.565 gross=-0.492 PF=0.23 stop=66.7% mfe=0.56 | n=3 prof=66.7% [20.8–93.9] net=+0.520 gross=+0.583 PF=2.49 stop=33.3% mfe=1.80 |  |
| ema50_dist_atr | -0.5..0.5 | n=6 prof=50.0% [18.8–81.2] net=-0.154 gross=-0.096 PF=0.71 stop=50.0% mfe=1.20 | n=3 prof=33.3% [6.1–79.2] net=+0.369 gross=+0.515 PF=5.96 stop=0.0% mfe=1.11 |  |
| ema50_dist_atr | -2..-0.5 | n=24 prof=45.8% [27.9–64.9] net=-0.327 gross=-0.272 PF=0.43 stop=54.2% mfe=0.74 | n=17 prof=52.9% [31.0–73.8] net=+0.159 gross=+0.202 PF=1.41 stop=35.3% mfe=1.22 |  |
| ema50_dist_atr | <-2 | n=2 prof=100.0% [34.2–100.0] net=+0.395 gross=+0.525 PF=inf stop=0.0% mfe=1.38 | n=2 prof=0.0% [0.0–65.8] net=-1.058 gross=-1.000 PF=0.00 stop=100.0% mfe=0.02 |  |
| symbol_group | major | n=26 prof=46.2% [28.8–64.5] net=-0.319 gross=-0.258 PF=0.44 stop=53.8% mfe=0.82 | n=15 prof=60.0% [35.7–80.2] net=+0.377 gross=+0.444 PF=2.59 stop=20.0% mfe=1.33 |  |
| symbol_group | other | n=6 prof=66.7% [30.0–90.3] net=+0.050 gross=+0.108 PF=1.14 stop=33.3% mfe=1.03 | n=7 prof=14.3% [2.6–51.3] net=-0.567 gross=-0.526 PF=0.25 stop=71.4% mfe=0.57 |  |
| funding | na | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=22 prof=45.5% [26.9–65.3] net=+0.077 gross=+0.136 PF=1.19 stop=36.4% mfe=1.09 |  |
| funding_side | neutral | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=22 prof=45.5% [26.9–65.3] net=+0.077 gross=+0.136 PF=1.19 stop=36.4% mfe=1.09 |  |
| funding_z | na | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=22 prof=45.5% [26.9–65.3] net=+0.077 gross=+0.136 PF=1.19 stop=36.4% mfe=1.09 |  |
| oi_divergence | na | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=22 prof=45.5% [26.9–65.3] net=+0.077 gross=+0.136 PF=1.19 stop=36.4% mfe=1.09 |  |
| oi_chg_24h | na | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=22 prof=45.5% [26.9–65.3] net=+0.077 gross=+0.136 PF=1.19 stop=36.4% mfe=1.09 |  |
| settlement_bar | other | n=17 prof=58.8% [36.0–78.4] net=-0.108 gross=-0.053 PF=0.75 stop=41.2% mfe=0.95 | n=15 prof=40.0% [19.8–64.3] net=-0.022 gross=+0.020 PF=0.96 stop=46.7% mfe=1.10 |  |
| settlement_bar | settlement | n=15 prof=40.0% [19.8–64.3] net=-0.410 gross=-0.343 PF=0.36 stop=60.0% mfe=0.77 | n=7 prof=57.1% [25.0–84.2] net=+0.289 gross=+0.383 PF=2.54 stop=14.3% mfe=1.07 |  |
| session | 03-04 | n=4 prof=50.0% [15.0–85.0] net=-0.207 gross=-0.126 PF=0.62 stop=50.0% mfe=0.86 | n=0 |  |
| session | 08-16 | n=13 prof=46.2% [23.2–70.9] net=-0.228 gross=-0.177 PF=0.60 stop=53.8% mfe=0.93 | n=9 prof=44.4% [18.9–73.3] net=-0.113 gross=-0.056 PF=0.80 stop=55.6% mfe=0.92 |  |
| session | other | n=15 prof=53.3% [30.1–75.2] net=-0.279 gross=-0.217 PF=0.43 stop=46.7% mfe=0.81 | n=13 prof=46.2% [23.2–70.9] net=+0.208 gross=+0.268 PF=1.74 stop=23.1% mfe=1.21 |  |
| cvd_confirm_0.05 | confirm | n=0 | n=6 prof=16.7% [3.0–56.4] net=-0.346 gross=-0.311 PF=0.39 stop=50.0% mfe=0.49 |  |
| cvd_confirm_0.05 | contra | n=0 | n=5 prof=60.0% [23.1–88.2] net=+0.388 gross=+0.425 PF=1.93 stop=40.0% mfe=1.68 |  |
| cvd_confirm_0.05 | na | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=10 prof=60.0% [31.3–83.2] net=+0.286 gross=+0.372 PF=2.22 stop=20.0% mfe=1.27 |  |
| cvd_confirm_0.05 | neutral | n=0 | n=1 prof=0.0% [0.0–79.3] net=-1.032 gross=-1.000 PF=0.00 stop=100.0% mfe=0.04 |  |
| cvd_confirm_0.1 | confirm | n=0 | n=5 prof=20.0% [3.6–62.4] net=-0.398 gross=-0.362 PF=0.40 stop=60.0% mfe=0.53 |  |
| cvd_confirm_0.1 | contra | n=0 | n=5 prof=60.0% [23.1–88.2] net=+0.388 gross=+0.425 PF=1.93 stop=40.0% mfe=1.68 |  |
| cvd_confirm_0.1 | na | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=10 prof=60.0% [31.3–83.2] net=+0.286 gross=+0.372 PF=2.22 stop=20.0% mfe=1.27 |  |
| cvd_confirm_0.1 | neutral | n=0 | n=2 prof=0.0% [0.0–65.8] net=-0.560 gross=-0.527 PF=0.00 stop=50.0% mfe=0.16 |  |
| cvd_confirm_0.2 | confirm | n=0 | n=3 prof=0.0% [0.0–56.2] net=-0.770 gross=-0.728 PF=0.00 stop=66.7% mfe=0.13 |  |
| cvd_confirm_0.2 | contra | n=0 | n=3 prof=66.7% [20.8–93.9] net=+0.551 gross=+0.583 PF=2.62 stop=33.3% mfe=1.86 |  |
| cvd_confirm_0.2 | na | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=10 prof=60.0% [31.3–83.2] net=+0.286 gross=+0.372 PF=2.22 stop=20.0% mfe=1.27 |  |
| cvd_confirm_0.2 | neutral | n=0 | n=6 prof=33.3% [9.7–70.0] net=-0.086 gross=-0.051 PF=0.84 stop=50.0% mfe=0.90 |  |
| cvd_confirm_0.4 | confirm | n=0 | n=1 prof=0.0% [0.0–79.3] net=-1.060 gross=-1.000 PF=0.00 stop=100.0% mfe=0.03 |  |
| cvd_confirm_0.4 | contra | n=0 | n=2 prof=100.0% [34.2–100.0] net=+1.337 gross=+1.375 PF=inf stop=0.0% mfe=2.61 |  |
| cvd_confirm_0.4 | na | n=32 prof=50.0% [33.6–66.4] net=-0.249 gross=-0.189 PF=0.53 stop=50.0% mfe=0.86 | n=10 prof=60.0% [31.3–83.2] net=+0.286 gross=+0.372 PF=2.22 stop=20.0% mfe=1.27 |  |
| cvd_confirm_0.4 | neutral | n=0 | n=9 prof=22.2% [6.3–54.7] net=-0.309 gross=-0.277 PF=0.49 stop=55.6% mfe=0.68 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

### failed_breakout_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-08 | 9 | 33.3 | -0.515 |
| 2026-09 | 25 | 76.0 | +0.510 |
| 2026-10 | 7 | 42.9 | -0.162 |

**Filter study** (47 cuts tested — expect ~2.4 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=20 prof=55.0% [34.2–74.2] net=+0.010 gross=+0.045 PF=1.02 stop=45.0% mfe=0.97 | n=14 prof=71.4% [45.4–88.3] net=+0.423 gross=+0.445 PF=2.77 stop=21.4% mfe=1.25 |  |
| btc_aligned | yes | n=4 prof=75.0% [30.1–95.4] net=+0.419 gross=+0.469 PF=2.45 stop=25.0% mfe=1.35 | n=3 prof=33.3% [6.1–79.2] net=-0.274 gross=-0.208 PF=0.62 stop=66.7% mfe=0.99 |  |
| confluence3 | 0-1 | n=24 prof=58.3% [38.8–75.5] net=+0.078 gross=+0.116 PF=1.18 stop=41.7% mfe=1.03 | n=17 prof=64.7% [41.3–82.7] net=+0.300 gross=+0.330 PF=1.92 stop=29.4% mfe=1.20 |  |
| risk_pct | 2-4% | n=7 prof=57.1% [25.0–84.2] net=+0.329 gross=+0.357 PF=1.74 stop=42.9% mfe=1.49 | n=6 prof=50.0% [18.8–81.2] net=+0.019 gross=+0.046 PF=1.04 stop=50.0% mfe=1.12 |  |
| risk_pct | 4-8% | n=8 prof=62.5% [30.6–86.3] net=+0.099 gross=+0.121 PF=1.26 stop=37.5% mfe=0.82 | n=8 prof=75.0% [40.9–92.9] net=+0.628 gross=+0.647 PF=4.92 stop=12.5% mfe=1.38 |  |
| risk_pct | <2% | n=5 prof=40.0% [11.8–76.9] net=-0.411 gross=-0.313 PF=0.37 stop=60.0% mfe=0.85 | n=2 prof=50.0% [9.5–90.5] net=-0.333 gross=-0.237 PF=0.42 stop=50.0% mfe=0.84 |  |
| risk_pct | >8% | n=4 prof=75.0% [30.1–95.4] net=+0.209 gross=+0.219 PF=1.83 stop=25.0% mfe=0.87 | n=1 prof=100.0% [20.7–100.0] net=+0.621 gross=+0.637 PF=inf stop=0.0% mfe=0.97 |  |
| hour | 00-08 | n=6 prof=50.0% [18.8–81.2] net=+0.000 gross=+0.039 PF=1.00 stop=50.0% mfe=1.11 | n=5 prof=40.0% [11.8–76.9] net=-0.076 gross=-0.050 PF=0.88 stop=60.0% mfe=1.00 |  |
| hour | 08-16 | n=8 prof=50.0% [21.5–78.5] net=-0.237 gross=-0.200 PF=0.55 stop=50.0% mfe=0.74 | n=7 prof=85.7% [48.7–97.4] net=+0.774 gross=+0.798 PF=21.60 stop=0.0% mfe=1.51 |  |
| hour | 16-24 | n=10 prof=70.0% [39.7–89.2] net=+0.378 gross=+0.414 PF=2.22 stop=30.0% mfe=1.21 | n=5 prof=60.0% [23.1–88.2] net=+0.011 gross=+0.055 PF=1.03 stop=40.0% mfe=0.96 |  |
| weekend | weekday | n=19 prof=57.9% [36.3–76.9] net=+0.043 gross=+0.087 PF=1.10 stop=42.1% mfe=1.03 | n=11 prof=63.6% [35.4–84.8] net=+0.188 gross=+0.212 PF=1.50 stop=36.4% mfe=1.10 |  |
| weekend | weekend | n=5 prof=60.0% [23.1–88.2] net=+0.212 gross=+0.225 PF=1.52 stop=40.0% mfe=1.03 | n=6 prof=66.7% [30.0–90.3] net=+0.504 gross=+0.546 PF=3.15 stop=16.7% mfe=1.38 |  |
| adx | 20-30 | n=6 prof=83.3% [43.6–97.0] net=+0.468 gross=+0.524 PF=3.63 stop=16.7% mfe=1.30 | n=6 prof=50.0% [18.8–81.2] net=+0.001 gross=+0.046 PF=1.00 stop=50.0% mfe=1.18 |  |
| adx | <20 | n=5 prof=60.0% [23.1–88.2] net=+0.287 gross=+0.340 PF=1.66 stop=40.0% mfe=1.43 | n=3 prof=33.3% [6.1–79.2] net=-0.272 gross=-0.234 PF=0.37 stop=33.3% mfe=0.69 |  |
| adx | >30 | n=13 prof=46.2% [23.2–70.9] net=-0.182 gross=-0.159 PF=0.67 stop=53.8% mfe=0.75 | n=8 prof=87.5% [52.9–97.8] net=+0.738 gross=+0.755 PF=6.79 stop=12.5% mfe=1.41 |  |
| vol_spike | <1.5 | n=11 prof=63.6% [35.4–84.8] net=+0.234 gross=+0.276 PF=1.62 stop=36.4% mfe=1.18 | n=12 prof=66.7% [39.1–86.2] net=+0.401 gross=+0.435 PF=2.38 stop=25.0% mfe=1.35 |  |
| vol_spike | >=1.5 | n=13 prof=53.8% [29.1–76.8] net=-0.054 gross=-0.020 PF=0.89 stop=46.2% mfe=0.91 | n=5 prof=60.0% [23.1–88.2] net=+0.057 gross=+0.077 PF=1.14 stop=40.0% mfe=0.84 |  |
| ema50_dist_atr | -0.5..0.5 | n=0 | n=2 prof=0.0% [0.0–65.8] net=-0.705 gross=-0.613 PF=0.00 stop=50.0% mfe=0.61 |  |
| ema50_dist_atr | 0.5..2 | n=10 prof=60.0% [31.3–83.2] net=+0.189 gross=+0.241 PF=1.44 stop=40.0% mfe=1.25 | n=8 prof=62.5% [30.6–86.3] net=+0.245 gross=+0.272 PF=1.63 stop=37.5% mfe=1.25 |  |
| ema50_dist_atr | >2 | n=14 prof=57.1% [32.6–78.6] net=-0.000 gross=+0.026 PF=1.00 stop=42.9% mfe=0.88 | n=7 prof=85.7% [48.7–97.4] net=+0.650 gross=+0.666 PF=5.46 stop=14.3% mfe=1.32 |  |
| symbol_group | major | n=16 prof=62.5% [38.6–81.5] net=+0.195 gross=+0.236 PF=1.50 stop=37.5% mfe=1.16 | n=13 prof=53.8% [29.1–76.8] net=+0.051 gross=+0.086 PF=1.12 stop=38.5% mfe=1.02 |  |
| symbol_group | other | n=8 prof=50.0% [21.5–78.5] net=-0.155 gross=-0.124 PF=0.70 stop=50.0% mfe=0.78 | n=4 prof=100.0% [51.0–100.0] net=+1.108 gross=+1.125 PF=inf stop=0.0% mfe=1.79 |  |
| funding | na | n=24 prof=58.3% [38.8–75.5] net=+0.078 gross=+0.116 PF=1.18 stop=41.7% mfe=1.03 | n=17 prof=64.7% [41.3–82.7] net=+0.300 gross=+0.330 PF=1.92 stop=29.4% mfe=1.20 |  |
| funding_side | neutral | n=24 prof=58.3% [38.8–75.5] net=+0.078 gross=+0.116 PF=1.18 stop=41.7% mfe=1.03 | n=17 prof=64.7% [41.3–82.7] net=+0.300 gross=+0.330 PF=1.92 stop=29.4% mfe=1.20 |  |
| funding_z | na | n=24 prof=58.3% [38.8–75.5] net=+0.078 gross=+0.116 PF=1.18 stop=41.7% mfe=1.03 | n=17 prof=64.7% [41.3–82.7] net=+0.300 gross=+0.330 PF=1.92 stop=29.4% mfe=1.20 |  |
| oi_divergence | na | n=24 prof=58.3% [38.8–75.5] net=+0.078 gross=+0.116 PF=1.18 stop=41.7% mfe=1.03 | n=17 prof=64.7% [41.3–82.7] net=+0.300 gross=+0.330 PF=1.92 stop=29.4% mfe=1.20 |  |
| oi_chg_24h | na | n=24 prof=58.3% [38.8–75.5] net=+0.078 gross=+0.116 PF=1.18 stop=41.7% mfe=1.03 | n=17 prof=64.7% [41.3–82.7] net=+0.300 gross=+0.330 PF=1.92 stop=29.4% mfe=1.20 |  |
| settlement_bar | other | n=11 prof=54.5% [28.0–78.7] net=+0.093 gross=+0.128 PF=1.20 stop=45.5% mfe=0.99 | n=10 prof=70.0% [39.7–89.2] net=+0.357 gross=+0.393 PF=2.11 stop=30.0% mfe=1.25 |  |
| settlement_bar | settlement | n=13 prof=61.5% [35.5–82.3] net=+0.066 gross=+0.105 PF=1.16 stop=38.5% mfe=1.07 | n=7 prof=57.1% [25.0–84.2] net=+0.219 gross=+0.241 PF=1.66 stop=28.6% mfe=1.13 |  |
| session | 03-04 | n=2 prof=50.0% [9.5–90.5] net=-0.040 gross=-0.025 PF=0.92 stop=50.0% mfe=0.73 | n=3 prof=33.3% [6.1–79.2] net=-0.236 gross=-0.208 PF=0.66 stop=66.7% mfe=0.87 |  |
| session | 08-16 | n=8 prof=50.0% [21.5–78.5] net=-0.237 gross=-0.200 PF=0.55 stop=50.0% mfe=0.74 | n=7 prof=85.7% [48.7–97.4] net=+0.774 gross=+0.798 PF=21.60 stop=0.0% mfe=1.51 |  |
| session | other | n=14 prof=64.3% [38.8–83.7] net=+0.276 gross=+0.316 PF=1.74 stop=35.7% mfe=1.24 | n=7 prof=57.1% [25.0–84.2] net=+0.055 gross=+0.093 PF=1.12 stop=42.9% mfe=1.03 |  |
| cvd_confirm_0.05 | confirm | n=5 prof=60.0% [23.1–88.2] net=+0.291 gross=+0.313 PF=1.72 stop=40.0% mfe=1.18 | n=10 prof=70.0% [39.7–89.2] net=+0.543 gross=+0.562 PF=2.76 stop=30.0% mfe=1.38 |  |
| cvd_confirm_0.05 | contra | n=2 prof=50.0% [9.5–90.5] net=+0.163 gross=+0.188 PF=1.31 stop=50.0% mfe=1.42 | n=2 prof=50.0% [9.5–90.5] net=-0.321 gross=-0.237 PF=0.44 stop=50.0% mfe=0.88 |  |
| cvd_confirm_0.05 | na | n=17 prof=58.8% [36.0–78.4] net=+0.006 gross=+0.049 PF=1.01 stop=41.2% mfe=0.94 | n=5 prof=60.0% [23.1–88.2] net=+0.061 gross=+0.092 PF=1.24 stop=20.0% mfe=0.96 |  |
| cvd_confirm_0.1 | confirm | n=5 prof=60.0% [23.1–88.2] net=+0.291 gross=+0.313 PF=1.72 stop=40.0% mfe=1.18 | n=8 prof=75.0% [40.9–92.9] net=+0.636 gross=+0.656 PF=3.46 stop=25.0% mfe=1.47 |  |
| cvd_confirm_0.1 | contra | n=2 prof=50.0% [9.5–90.5] net=+0.163 gross=+0.188 PF=1.31 stop=50.0% mfe=1.42 | n=2 prof=50.0% [9.5–90.5] net=-0.321 gross=-0.237 PF=0.44 stop=50.0% mfe=0.88 |  |
| cvd_confirm_0.1 | na | n=17 prof=58.8% [36.0–78.4] net=+0.006 gross=+0.049 PF=1.01 stop=41.2% mfe=0.94 | n=5 prof=60.0% [23.1–88.2] net=+0.061 gross=+0.092 PF=1.24 stop=20.0% mfe=0.96 |  |
| cvd_confirm_0.1 | neutral | n=0 | n=2 prof=50.0% [9.5–90.5] net=+0.172 gross=+0.188 PF=1.34 stop=50.0% mfe=1.05 |  |
| cvd_confirm_0.2 | confirm | n=5 prof=60.0% [23.1–88.2] net=+0.291 gross=+0.313 PF=1.72 stop=40.0% mfe=1.18 | n=7 prof=71.4% [35.9–91.8] net=+0.533 gross=+0.554 PF=2.80 stop=28.6% mfe=1.38 |  |
| cvd_confirm_0.2 | contra | n=2 prof=50.0% [9.5–90.5] net=+0.163 gross=+0.188 PF=1.31 stop=50.0% mfe=1.42 | n=2 prof=50.0% [9.5–90.5] net=-0.321 gross=-0.237 PF=0.44 stop=50.0% mfe=0.88 |  |
| cvd_confirm_0.2 | na | n=17 prof=58.8% [36.0–78.4] net=+0.006 gross=+0.049 PF=1.01 stop=41.2% mfe=0.94 | n=5 prof=60.0% [23.1–88.2] net=+0.061 gross=+0.092 PF=1.24 stop=20.0% mfe=0.96 |  |
| cvd_confirm_0.2 | neutral | n=0 | n=3 prof=66.7% [20.8–93.9] net=+0.566 gross=+0.583 PF=2.66 stop=33.3% mfe=1.39 |  |
| cvd_confirm_0.4 | confirm | n=4 prof=75.0% [30.1–95.4] net=+0.616 gross=+0.641 PF=3.42 stop=25.0% mfe=1.46 | n=6 prof=83.3% [43.6–97.0] net=+0.795 gross=+0.812 PF=5.62 stop=16.7% mfe=1.58 |  |
| cvd_confirm_0.4 | contra | n=2 prof=50.0% [9.5–90.5] net=+0.163 gross=+0.188 PF=1.31 stop=50.0% mfe=1.42 | n=2 prof=50.0% [9.5–90.5] net=-0.321 gross=-0.237 PF=0.44 stop=50.0% mfe=0.88 |  |
| cvd_confirm_0.4 | na | n=17 prof=58.8% [36.0–78.4] net=+0.006 gross=+0.049 PF=1.01 stop=41.2% mfe=0.94 | n=5 prof=60.0% [23.1–88.2] net=+0.061 gross=+0.092 PF=1.24 stop=20.0% mfe=0.96 |  |
| cvd_confirm_0.4 | neutral | n=1 prof=0.0% [0.0–79.3] net=-1.008 gross=-1.000 PF=0.00 stop=100.0% mfe=0.06 | n=4 prof=50.0% [15.0–85.0] net=+0.166 gross=+0.188 PF=1.32 stop=50.0% mfe=1.09 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- chosen: T1=0.5R, stop×0.75, T2=1.5R, trail=off
- TRAIN chosen: n=24 prof=75.0% [55.1–88.0] net=+0.094 gross=+0.134 PF=1.36 stop=25.0% mfe=0.82
- TEST chosen: n=17 prof=76.5% [52.7–90.4] net=+0.163 gross=+0.197 PF=1.66 stop=23.5% mfe=0.95
- TEST default: n=17 prof=64.7% [41.3–82.7] net=+0.300 gross=+0.330 PF=1.92 stop=29.4% mfe=1.20

### rsi_rejection_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-08 | 5 | 40.0 | -0.009 |
| 2026-09 | 23 | 34.8 | -0.434 |
| 2026-10 | 4 | 75.0 | +0.339 |

**Filter study** (46 cuts tested — expect ~2.3 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=17 prof=23.5% [9.6–47.3] net=-0.465 gross=-0.436 PF=0.26 stop=58.8% mfe=0.42 | n=10 prof=60.0% [31.3–83.2] net=-0.045 gross=-0.011 PF=0.87 stop=30.0% mfe=0.62 |  |
| btc_aligned | yes | n=2 prof=50.0% [9.5–90.5] net=-0.157 gross=-0.084 PF=0.70 stop=50.0% mfe=0.54 | n=3 prof=66.7% [20.8–93.9] net=-0.000 gross=+0.017 PF=1.00 stop=33.3% mfe=1.10 |  |
| confluence3 | 0-1 | n=19 prof=26.3% [11.8–48.8] net=-0.432 gross=-0.399 PF=0.30 stop=57.9% mfe=0.43 | n=13 prof=61.5% [35.5–82.3] net=-0.035 gross=-0.005 PF=0.90 stop=30.8% mfe=0.73 |  |
| risk_pct | 2-4% | n=6 prof=0.0% [0.0–39.0] net=-0.743 gross=-0.699 PF=0.00 stop=66.7% mfe=0.14 | n=3 prof=66.7% [20.8–93.9] net=-0.149 gross=-0.110 PF=0.57 stop=33.3% mfe=0.46 |  |
| risk_pct | 4-8% | n=7 prof=28.6% [8.2–64.1] net=-0.456 gross=-0.430 PF=0.38 stop=71.4% mfe=0.61 | n=6 prof=83.3% [43.6–97.0] net=+0.344 gross=+0.362 PF=3.02 stop=16.7% mfe=1.24 |  |
| risk_pct | <2% | n=1 prof=100.0% [20.7–100.0] net=+0.717 gross=+0.833 PF=inf stop=0.0% mfe=0.94 | n=1 prof=0.0% [0.0–79.3] net=-1.127 gross=-1.000 PF=0.00 stop=100.0% mfe=0.00 |  |
| risk_pct | >8% | n=5 prof=40.0% [11.8–76.9] net=-0.256 gross=-0.242 PF=0.40 stop=40.0% mfe=0.43 | n=3 prof=33.3% [6.1–79.2] net=-0.316 gross=-0.302 PF=0.30 stop=33.3% mfe=0.23 |  |
| hour | 00-08 | n=8 prof=25.0% [7.1–59.1] net=-0.306 gross=-0.275 PF=0.44 stop=50.0% mfe=0.56 | n=5 prof=40.0% [11.8–76.9] net=-0.451 gross=-0.406 PF=0.29 stop=60.0% mfe=0.38 |  |
| hour | 08-16 | n=5 prof=0.0% [-0.0–43.4] net=-1.027 gross=-1.000 PF=0.00 stop=100.0% mfe=0.12 | n=3 prof=66.7% [20.8–93.9] net=+0.228 gross=+0.243 PF=3.04 stop=0.0% mfe=1.05 |  |
| hour | 16-24 | n=6 prof=50.0% [18.8–81.2] net=-0.104 gross=-0.063 PF=0.71 stop=33.3% mfe=0.53 | n=5 prof=80.0% [37.6–96.4] net=+0.223 gross=+0.248 PF=2.09 stop=20.0% mfe=0.89 |  |
| weekend | weekday | n=8 prof=50.0% [21.5–78.5] net=-0.143 gross=-0.109 PF=0.72 stop=50.0% mfe=0.72 | n=7 prof=85.7% [48.7–97.4] net=+0.319 gross=+0.358 PF=2.98 stop=14.3% mfe=1.06 |  |
| weekend | weekend | n=11 prof=9.1% [1.6–37.7] net=-0.642 gross=-0.610 PF=0.07 stop=63.6% mfe=0.22 | n=6 prof=33.3% [9.7–70.0] net=-0.449 gross=-0.428 PF=0.21 stop=50.0% mfe=0.35 |  |
| adx | 20-30 | n=5 prof=0.0% [-0.0–43.4] net=-0.866 gross=-0.822 PF=0.00 stop=80.0% mfe=0.14 | n=4 prof=50.0% [15.0–85.0] net=-0.322 gross=-0.275 PF=0.40 stop=50.0% mfe=0.67 |  |
| adx | <20 | n=0 | n=1 prof=100.0% [20.7–100.0] net=+1.357 gross=+1.375 PF=inf stop=0.0% mfe=2.55 |  |
| adx | >30 | n=14 prof=35.7% [16.3–61.2] net=-0.277 gross=-0.248 PF=0.48 stop=50.0% mfe=0.54 | n=8 prof=62.5% [30.6–86.3] net=-0.066 gross=-0.042 PF=0.78 stop=25.0% mfe=0.53 |  |
| vol_spike | <1.5 | n=15 prof=33.3% [15.2–58.3] net=-0.272 gross=-0.239 PF=0.46 stop=46.7% mfe=0.48 | n=11 prof=54.5% [28.0–78.7] net=-0.095 gross=-0.067 PF=0.77 stop=36.4% mfe=0.75 |  |
| vol_spike | >=1.5 | n=4 prof=0.0% [0.0–49.0] net=-1.032 gross=-1.000 PF=0.00 stop=100.0% mfe=0.24 | n=2 prof=100.0% [34.2–100.0] net=+0.292 gross=+0.336 PF=inf stop=0.0% mfe=0.63 |  |
| ema50_dist_atr | -0.5..0.5 | n=3 prof=0.0% [0.0–56.2] net=-1.034 gross=-1.000 PF=0.00 stop=100.0% mfe=0.21 | n=2 prof=100.0% [34.2–100.0] net=+0.932 gross=+0.950 PF=inf stop=0.0% mfe=2.14 |  |
| ema50_dist_atr | 0.5..2 | n=7 prof=42.9% [15.8–75.0] net=-0.266 gross=-0.244 PF=0.55 stop=57.1% mfe=0.68 | n=4 prof=75.0% [30.1–95.4] net=-0.033 gross=-0.006 PF=0.87 stop=25.0% mfe=0.69 |  |
| ema50_dist_atr | >2 | n=9 prof=22.2% [6.3–54.7] net=-0.361 gross=-0.319 PF=0.28 stop=44.4% mfe=0.31 | n=7 prof=42.9% [15.8–75.0] net=-0.313 gross=-0.277 PF=0.38 stop=42.9% mfe=0.35 |  |
| symbol_group | major | n=13 prof=30.8% [12.7–57.6] net=-0.310 gross=-0.275 PF=0.39 stop=46.2% mfe=0.47 | n=12 prof=58.3% [32.0–80.7] net=-0.068 gross=-0.036 PF=0.82 stop=33.3% mfe=0.72 |  |
| symbol_group | other | n=6 prof=16.7% [3.0–56.4] net=-0.697 gross=-0.668 PF=0.19 stop=83.3% mfe=0.34 | n=1 prof=100.0% [20.7–100.0] net=+0.356 gross=+0.375 PF=inf stop=0.0% mfe=0.81 |  |
| funding | na | n=19 prof=26.3% [11.8–48.8] net=-0.432 gross=-0.399 PF=0.30 stop=57.9% mfe=0.43 | n=13 prof=61.5% [35.5–82.3] net=-0.035 gross=-0.005 PF=0.90 stop=30.8% mfe=0.73 |  |
| funding_side | neutral | n=19 prof=26.3% [11.8–48.8] net=-0.432 gross=-0.399 PF=0.30 stop=57.9% mfe=0.43 | n=13 prof=61.5% [35.5–82.3] net=-0.035 gross=-0.005 PF=0.90 stop=30.8% mfe=0.73 |  |
| funding_z | na | n=19 prof=26.3% [11.8–48.8] net=-0.432 gross=-0.399 PF=0.30 stop=57.9% mfe=0.43 | n=13 prof=61.5% [35.5–82.3] net=-0.035 gross=-0.005 PF=0.90 stop=30.8% mfe=0.73 |  |
| oi_divergence | na | n=19 prof=26.3% [11.8–48.8] net=-0.432 gross=-0.399 PF=0.30 stop=57.9% mfe=0.43 | n=13 prof=61.5% [35.5–82.3] net=-0.035 gross=-0.005 PF=0.90 stop=30.8% mfe=0.73 |  |
| oi_chg_24h | na | n=19 prof=26.3% [11.8–48.8] net=-0.432 gross=-0.399 PF=0.30 stop=57.9% mfe=0.43 | n=13 prof=61.5% [35.5–82.3] net=-0.035 gross=-0.005 PF=0.90 stop=30.8% mfe=0.73 |  |
| settlement_bar | other | n=9 prof=22.2% [6.3–54.7] net=-0.522 gross=-0.501 PF=0.25 stop=66.7% mfe=0.47 | n=4 prof=50.0% [15.0–85.0] net=-0.244 gross=-0.220 PF=0.52 stop=50.0% mfe=0.71 |  |
| settlement_bar | settlement | n=10 prof=30.0% [10.8–60.3] net=-0.351 gross=-0.307 PF=0.36 stop=50.0% mfe=0.40 | n=9 prof=66.7% [35.4–87.9] net=+0.058 gross=+0.091 PF=1.21 stop=22.2% mfe=0.74 |  |
| session | 03-04 | n=5 prof=20.0% [3.6–62.4] net=-0.439 gross=-0.417 PF=0.31 stop=60.0% mfe=0.52 | n=3 prof=33.3% [6.1–79.2] net=-0.494 gross=-0.468 PF=0.27 stop=66.7% mfe=0.37 |  |
| session | 08-16 | n=5 prof=0.0% [-0.0–43.4] net=-1.027 gross=-1.000 PF=0.00 stop=100.0% mfe=0.12 | n=3 prof=66.7% [20.8–93.9] net=+0.228 gross=+0.243 PF=3.04 stop=0.0% mfe=1.05 |  |
| session | other | n=9 prof=44.4% [18.9–73.3] net=-0.098 gross=-0.055 PF=0.74 stop=33.3% mfe=0.56 | n=7 prof=71.4% [35.9–91.8] net=+0.049 gross=+0.088 PF=1.16 stop=28.6% mfe=0.75 |  |
| cvd_confirm_0.05 | confirm | n=5 prof=20.0% [3.6–62.4] net=-0.764 gross=-0.740 PF=0.07 stop=80.0% mfe=0.30 | n=7 prof=71.4% [35.9–91.8] net=+0.055 gross=+0.095 PF=1.26 stop=14.3% mfe=0.61 |  |
| cvd_confirm_0.05 | contra | n=0 | n=1 prof=0.0% [0.0–79.3] net=-1.021 gross=-1.000 PF=0.00 stop=100.0% mfe=0.18 |  |
| cvd_confirm_0.05 | na | n=14 prof=28.6% [11.7–54.6] net=-0.314 gross=-0.277 PF=0.42 stop=50.0% mfe=0.48 | n=5 prof=60.0% [23.1–88.2] net=+0.036 gross=+0.055 PF=1.09 stop=40.0% mfe=1.00 |  |
| cvd_confirm_0.1 | confirm | n=5 prof=20.0% [3.6–62.4] net=-0.764 gross=-0.740 PF=0.07 stop=80.0% mfe=0.30 | n=6 prof=66.7% [30.0–90.3] net=-0.029 gross=+0.011 PF=0.88 stop=16.7% mfe=0.58 |  |
| cvd_confirm_0.1 | contra | n=0 | n=1 prof=0.0% [0.0–79.3] net=-1.021 gross=-1.000 PF=0.00 stop=100.0% mfe=0.18 |  |
| cvd_confirm_0.1 | na | n=14 prof=28.6% [11.7–54.6] net=-0.314 gross=-0.277 PF=0.42 stop=50.0% mfe=0.48 | n=5 prof=60.0% [23.1–88.2] net=+0.036 gross=+0.055 PF=1.09 stop=40.0% mfe=1.00 |  |
| cvd_confirm_0.1 | neutral | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.562 gross=+0.595 PF=inf stop=0.0% mfe=0.83 |  |
| cvd_confirm_0.2 | confirm | n=5 prof=20.0% [3.6–62.4] net=-0.764 gross=-0.740 PF=0.07 stop=80.0% mfe=0.30 | n=5 prof=80.0% [37.6–96.4] net=+0.190 gross=+0.214 PF=3.84 stop=0.0% mfe=0.70 |  |
| cvd_confirm_0.2 | contra | n=0 | n=1 prof=0.0% [0.0–79.3] net=-1.021 gross=-1.000 PF=0.00 stop=100.0% mfe=0.18 |  |
| cvd_confirm_0.2 | na | n=14 prof=28.6% [11.7–54.6] net=-0.314 gross=-0.277 PF=0.42 stop=50.0% mfe=0.48 | n=5 prof=60.0% [23.1–88.2] net=+0.036 gross=+0.055 PF=1.09 stop=40.0% mfe=1.00 |  |
| cvd_confirm_0.2 | neutral | n=0 | n=2 prof=50.0% [9.5–90.5] net=-0.282 gross=-0.203 PF=0.50 stop=50.0% mfe=0.41 |  |
| cvd_confirm_0.4 | confirm | n=4 prof=25.0% [4.6–69.9] net=-0.698 gross=-0.674 PF=0.09 stop=75.0% mfe=0.30 | n=5 prof=80.0% [37.6–96.4] net=+0.190 gross=+0.214 PF=3.84 stop=0.0% mfe=0.70 |  |
| cvd_confirm_0.4 | na | n=14 prof=28.6% [11.7–54.6] net=-0.314 gross=-0.277 PF=0.42 stop=50.0% mfe=0.48 | n=5 prof=60.0% [23.1–88.2] net=+0.036 gross=+0.055 PF=1.09 stop=40.0% mfe=1.00 |  |
| cvd_confirm_0.4 | neutral | n=1 prof=0.0% [0.0–79.3] net=-1.029 gross=-1.000 PF=0.00 stop=100.0% mfe=0.34 | n=3 prof=33.3% [6.1–79.2] net=-0.529 gross=-0.468 PF=0.26 stop=66.7% mfe=0.34 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

### range_reversion_long (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-08 | 3 | 66.7 | -0.090 |
| 2026-09 | 6 | 83.3 | +0.512 |
| 2026-10 | 3 | 0.0 | -1.095 |

**Filter study** (37 cuts tested — expect ~1.9 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=5 prof=60.0% [23.1–88.2] net=+0.092 gross=+0.155 PF=1.22 stop=40.0% mfe=1.12 | n=4 prof=50.0% [15.0–85.0] net=-0.172 gross=-0.087 PF=0.69 stop=50.0% mfe=0.88 |  |
| btc_aligned | yes | n=2 prof=100.0% [34.2–100.0] net=+0.405 gross=+0.450 PF=inf stop=0.0% mfe=1.24 | n=1 prof=0.0% [0.0–79.3] net=-1.068 gross=-1.000 PF=0.00 stop=100.0% mfe=0.19 |  |
| confluence3 | 0-1 | n=6 prof=66.7% [30.0–90.3] net=+0.157 gross=+0.217 PF=1.44 stop=33.3% mfe=1.19 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| confluence3 | 2-3 | n=1 prof=100.0% [20.7–100.0] net=+0.328 gross=+0.375 PF=inf stop=0.0% mfe=0.99 | n=0 |  |
| risk_pct | 2-4% | n=2 prof=50.0% [9.5–90.5] net=-0.283 gross=-0.237 PF=0.46 stop=50.0% mfe=0.83 | n=0 |  |
| risk_pct | <2% | n=5 prof=80.0% [37.6–96.4] net=+0.368 gross=+0.430 PF=2.71 stop=20.0% mfe=1.29 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| hour | 00-08 | n=4 prof=100.0% [51.0–100.0] net=+0.767 gross=+0.825 PF=inf stop=0.0% mfe=1.56 | n=3 prof=33.3% [6.1–79.2] net=-0.377 gross=-0.292 PF=0.49 stop=66.7% mfe=0.69 |  |
| hour | 08-16 | n=2 prof=50.0% [9.5–90.5] net=-0.360 gross=-0.312 PF=0.31 stop=50.0% mfe=0.58 | n=1 prof=0.0% [0.0–79.3] net=-1.068 gross=-1.000 PF=0.00 stop=100.0% mfe=0.19 |  |
| hour | 16-24 | n=1 prof=0.0% [0.0–79.3] net=-1.078 gross=-1.000 PF=0.00 stop=100.0% mfe=0.71 | n=1 prof=100.0% [20.7–100.0] net=+0.443 gross=+0.525 PF=inf stop=0.0% mfe=1.46 |  |
| weekend | weekday | n=5 prof=60.0% [23.1–88.2] net=+0.092 gross=+0.155 PF=1.22 stop=40.0% mfe=1.12 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| weekend | weekend | n=2 prof=100.0% [34.2–100.0] net=+0.405 gross=+0.450 PF=inf stop=0.0% mfe=1.24 | n=0 |  |
| adx | <20 | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| vol_spike | <1.5 | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=1 prof=100.0% [20.7–100.0] net=+1.088 gross=+1.125 PF=inf stop=0.0% mfe=1.90 |  |
| vol_spike | >=1.5 | n=0 | n=4 prof=25.0% [4.6–69.9] net=-0.711 gross=-0.619 PF=0.13 stop=75.0% mfe=0.46 |  |
| ema50_dist_atr | -0.5..0.5 | n=1 prof=100.0% [20.7–100.0] net=+0.328 gross=+0.375 PF=inf stop=0.0% mfe=0.99 | n=0 |  |
| ema50_dist_atr | -2..-0.5 | n=2 prof=50.0% [9.5–90.5] net=-0.298 gross=-0.237 PF=0.45 stop=50.0% mfe=1.10 | n=0 |  |
| ema50_dist_atr | <-2 | n=4 prof=75.0% [30.1–95.4] net=+0.385 gross=+0.444 PF=2.47 stop=25.0% mfe=1.23 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| symbol_group | major | n=5 prof=60.0% [23.1–88.2] net=-0.044 gross=+0.005 PF=0.90 stop=40.0% mfe=1.01 | n=4 prof=25.0% [4.6–69.9] net=-0.711 gross=-0.619 PF=0.13 stop=75.0% mfe=0.46 |  |
| symbol_group | other | n=2 prof=100.0% [34.2–100.0] net=+0.745 gross=+0.825 PF=inf stop=0.0% mfe=1.53 | n=1 prof=100.0% [20.7–100.0] net=+1.088 gross=+1.125 PF=inf stop=0.0% mfe=1.90 |  |
| funding | na | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| funding_side | neutral | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| funding_z | na | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| oi_divergence | na | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| oi_chg_24h | na | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 |  |
| settlement_bar | other | n=4 prof=50.0% [15.0–85.0] net=-0.329 gross=-0.275 PF=0.38 stop=50.0% mfe=0.84 | n=1 prof=0.0% [0.0–79.3] net=-1.068 gross=-1.000 PF=0.00 stop=100.0% mfe=0.19 |  |
| settlement_bar | settlement | n=3 prof=100.0% [43.8–100.0] net=+0.863 gross=+0.925 PF=inf stop=0.0% mfe=1.58 | n=4 prof=50.0% [15.0–85.0] net=-0.172 gross=-0.087 PF=0.69 stop=50.0% mfe=0.88 |  |
| session | 03-04 | n=1 prof=100.0% [20.7–100.0] net=+0.481 gross=+0.525 PF=inf stop=0.0% mfe=1.49 | n=0 |  |
| session | 08-16 | n=2 prof=50.0% [9.5–90.5] net=-0.360 gross=-0.312 PF=0.31 stop=50.0% mfe=0.58 | n=1 prof=0.0% [0.0–79.3] net=-1.068 gross=-1.000 PF=0.00 stop=100.0% mfe=0.19 |  |
| session | other | n=4 prof=75.0% [30.1–95.4] net=+0.378 gross=+0.444 PF=2.40 stop=25.0% mfe=1.36 | n=4 prof=50.0% [15.0–85.0] net=-0.172 gross=-0.087 PF=0.69 stop=50.0% mfe=0.88 |  |
| cvd_confirm_0.05 | contra | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.443 gross=+0.525 PF=inf stop=0.0% mfe=1.46 |  |
| cvd_confirm_0.05 | na | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=4 prof=25.0% [4.6–69.9] net=-0.549 gross=-0.469 PF=0.33 stop=75.0% mfe=0.56 |  |
| cvd_confirm_0.1 | contra | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.443 gross=+0.525 PF=inf stop=0.0% mfe=1.46 |  |
| cvd_confirm_0.1 | na | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=4 prof=25.0% [4.6–69.9] net=-0.549 gross=-0.469 PF=0.33 stop=75.0% mfe=0.56 |  |
| cvd_confirm_0.2 | contra | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.443 gross=+0.525 PF=inf stop=0.0% mfe=1.46 |  |
| cvd_confirm_0.2 | na | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=4 prof=25.0% [4.6–69.9] net=-0.549 gross=-0.469 PF=0.33 stop=75.0% mfe=0.56 |  |
| cvd_confirm_0.4 | contra | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.443 gross=+0.525 PF=inf stop=0.0% mfe=1.46 |  |
| cvd_confirm_0.4 | na | n=7 prof=71.4% [35.9–91.8] net=+0.182 gross=+0.239 PF=1.60 stop=28.6% mfe=1.16 | n=4 prof=25.0% [4.6–69.9] net=-0.549 gross=-0.469 PF=0.33 stop=75.0% mfe=0.56 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- chosen: T1=0.5R, stop×1.0, T2=2.0R, trail=on
- TRAIN chosen: n=7 prof=85.7% [48.7–97.4] net=+0.198 gross=+0.257 PF=2.32 stop=14.3% mfe=1.09
- TEST chosen: n=5 prof=40.0% [11.8–76.9] net=-0.556 gross=-0.470 PF=0.15 stop=60.0% mfe=0.52
- TEST default: n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74

### range_reversion_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-08 | 3 | 0.0 | -1.072 |
| 2026-09 | 5 | 60.0 | -0.218 |
| 2026-10 | 1 | 100.0 | +1.100 |

**Filter study** (34 cuts tested — expect ~1.7 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=2 prof=100.0% [34.2–100.0] net=+0.785 gross=+0.825 PF=inf stop=0.0% mfe=1.47 |  |
| btc_aligned | yes | n=0 | n=2 prof=50.0% [9.5–90.5] net=-0.389 gross=-0.312 PF=0.29 stop=50.0% mfe=0.53 |  |
| confluence3 | 0-1 | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |  |
| risk_pct | 2-4% | n=0 | n=1 prof=100.0% [20.7–100.0] net=+1.100 gross=+1.125 PF=inf stop=0.0% mfe=1.86 |  |
| risk_pct | <2% | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=3 prof=66.7% [20.8–93.9] net=-0.103 gross=-0.033 PF=0.72 stop=33.3% mfe=0.71 |  |
| hour | 00-08 | n=0 | n=2 prof=100.0% [34.2–100.0] net=+0.395 gross=+0.450 PF=inf stop=0.0% mfe=0.97 |  |
| hour | 08-16 | n=1 prof=0.0% [0.0–79.3] net=-1.094 gross=-1.000 PF=0.00 stop=100.0% mfe=0.44 | n=2 prof=50.0% [9.5–90.5] net=+0.002 gross=+0.062 PF=1.00 stop=50.0% mfe=1.03 |  |
| hour | 16-24 | n=4 prof=25.0% [4.6–69.9] net=-0.726 gross=-0.656 PF=0.10 stop=75.0% mfe=0.25 | n=0 |  |
| weekend | weekday | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |  |
| adx | 20-30 | n=4 prof=25.0% [4.6–69.9] net=-0.726 gross=-0.656 PF=0.10 stop=75.0% mfe=0.25 | n=2 prof=50.0% [9.5–90.5] net=-0.314 gross=-0.237 PF=0.43 stop=50.0% mfe=0.64 |  |
| adx | <20 | n=1 prof=0.0% [0.0–79.3] net=-1.094 gross=-1.000 PF=0.00 stop=100.0% mfe=0.44 | n=2 prof=100.0% [34.2–100.0] net=+0.710 gross=+0.750 PF=inf stop=0.0% mfe=1.35 |  |
| vol_spike | >=1.5 | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |  |
| ema50_dist_atr | 0.5..2 | n=1 prof=0.0% [0.0–79.3] net=-1.094 gross=-1.000 PF=0.00 stop=100.0% mfe=0.44 | n=0 |  |
| ema50_dist_atr | >2 | n=4 prof=25.0% [4.6–69.9] net=-0.726 gross=-0.656 PF=0.10 stop=75.0% mfe=0.25 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |  |
| symbol_group | major | n=3 prof=33.3% [6.1–79.2] net=-0.601 gross=-0.542 PF=0.15 stop=66.7% mfe=0.34 | n=1 prof=100.0% [20.7–100.0] net=+1.100 gross=+1.125 PF=inf stop=0.0% mfe=1.86 |  |
| symbol_group | other | n=2 prof=0.0% [0.0–65.8] net=-1.096 gross=-1.000 PF=0.00 stop=100.0% mfe=0.22 | n=3 prof=66.7% [20.8–93.9] net=-0.103 gross=-0.033 PF=0.72 stop=33.3% mfe=0.71 |  |
| funding | na | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |  |
| funding_side | neutral | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |  |
| funding_z | na | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |  |
| oi_divergence | na | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |  |
| oi_chg_24h | na | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 |  |
| settlement_bar | other | n=3 prof=0.0% [0.0–56.2] net=-1.083 gross=-1.000 PF=0.00 stop=100.0% mfe=0.15 | n=1 prof=100.0% [20.7–100.0] net=+0.319 gross=+0.375 PF=inf stop=0.0% mfe=0.85 |  |
| settlement_bar | settlement | n=2 prof=50.0% [9.5–90.5] net=-0.373 gross=-0.312 PF=0.30 stop=50.0% mfe=0.51 | n=3 prof=66.7% [20.8–93.9] net=+0.158 gross=+0.217 PF=1.43 stop=33.3% mfe=1.04 |  |
| session | 03-04 | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.319 gross=+0.375 PF=inf stop=0.0% mfe=0.85 |  |
| session | 08-16 | n=1 prof=0.0% [0.0–79.3] net=-1.094 gross=-1.000 PF=0.00 stop=100.0% mfe=0.44 | n=2 prof=50.0% [9.5–90.5] net=+0.002 gross=+0.062 PF=1.00 stop=50.0% mfe=1.03 |  |
| session | other | n=4 prof=25.0% [4.6–69.9] net=-0.726 gross=-0.656 PF=0.10 stop=75.0% mfe=0.25 | n=1 prof=100.0% [20.7–100.0] net=+0.470 gross=+0.525 PF=inf stop=0.0% mfe=1.08 |  |
| cvd_confirm_0.05 | contra | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.319 gross=+0.375 PF=inf stop=0.0% mfe=0.85 |  |
| cvd_confirm_0.05 | na | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=3 prof=66.7% [20.8–93.9] net=+0.158 gross=+0.217 PF=1.43 stop=33.3% mfe=1.04 |  |
| cvd_confirm_0.1 | contra | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.319 gross=+0.375 PF=inf stop=0.0% mfe=0.85 |  |
| cvd_confirm_0.1 | na | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=3 prof=66.7% [20.8–93.9] net=+0.158 gross=+0.217 PF=1.43 stop=33.3% mfe=1.04 |  |
| cvd_confirm_0.2 | contra | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.319 gross=+0.375 PF=inf stop=0.0% mfe=0.85 |  |
| cvd_confirm_0.2 | na | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=3 prof=66.7% [20.8–93.9] net=+0.158 gross=+0.217 PF=1.43 stop=33.3% mfe=1.04 |  |
| cvd_confirm_0.4 | contra | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.319 gross=+0.375 PF=inf stop=0.0% mfe=0.85 |  |
| cvd_confirm_0.4 | na | n=5 prof=20.0% [3.6–62.4] net=-0.799 gross=-0.725 PF=0.07 stop=80.0% mfe=0.29 | n=3 prof=66.7% [20.8–93.9] net=+0.158 gross=+0.217 PF=1.43 stop=33.3% mfe=1.04 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

## (g) CVD on-venue — PRE-REGISTERED test (bar fixed 2026-10-16 before the run)

Feature: cvd_slope (k=6, 20-bar |delta| normaliser) from Bybit minute taker buckets; bars with < 50% minute coverage are NA and excluded from baseline and buckets, deltas of valid bars are scaled by 1/coverage (amendment 2026-10-16: the collector captured a median 45/60 minutes inside covered hours, so the original 80% gate left zero valid 4h bars). Confirm = flow momentum aligned with the trade and |slope| ≥ thr; contra = opposed. Split: chronological 60/40 by signal time among CVD-available trades, per rule/tf.

**PASS** (→ shadow-lane variant with its own forward clock): some thr has TEST confirm n ≥ 30, TEST confirm profitable% ≥ TEST baseline + 5 pp, TEST confirm net > baseline net and > 0, TRAIN confirm beats TRAIN baseline (profitable% and net), and TRAIN monotonic (confirm net at thr 0.4 ≥ at 0.05). **INCONCLUSIVE** (→ one extension, re-run ~2026-12-15, final): confirm > baseline on both halves (profitable% and net) with TEST confirm n in [15, 30). **FAIL** otherwise (→ fork #4 closed, collector stopped).


### failed_breakout_short (4h) — 19 trades with CVD (of 41)

- baseline TRAIN n=11 prof=63.6% [35.4–84.8] net=+0.362 gross=+0.383 PF=1.98 stop=36.4% mfe=1.28 · TEST n=8 prof=62.5% [30.6–86.3] net=+0.323 gross=+0.359 PF=1.80 stop=37.5% mfe=1.27

| thr | TRAIN confirm | TRAIN contra | TEST confirm | TEST contra | flag |
|---|---|---|---|---|---|
| 0.05 | n=8 prof=62.5% [30.6–86.3] net=+0.394 gross=+0.414 PF=2.04 stop=37.5% mfe=1.26 | n=3 prof=66.7% [20.8–93.9] net=+0.277 gross=+0.300 PF=1.80 stop=33.3% mfe=1.34 | n=7 prof=71.4% [35.9–91.8] net=+0.533 gross=+0.554 PF=2.80 stop=28.6% mfe=1.37 | n=1 prof=0.0% [0.0–79.3] net=-1.147 gross=-1.000 PF=0.00 stop=100.0% mfe=0.59 |  |
| 0.1 | n=7 prof=71.4% [35.9–91.8] net=+0.596 gross=+0.616 PF=3.06 stop=28.6% mfe=1.43 | n=3 prof=66.7% [20.8–93.9] net=+0.277 gross=+0.300 PF=1.80 stop=33.3% mfe=1.34 | n=6 prof=66.7% [30.0–90.3] net=+0.395 gross=+0.417 PF=2.14 stop=33.3% mfe=1.26 | n=1 prof=0.0% [0.0–79.3] net=-1.147 gross=-1.000 PF=0.00 stop=100.0% mfe=0.59 |  |
| 0.2 | n=7 prof=71.4% [35.9–91.8] net=+0.596 gross=+0.616 PF=3.06 stop=28.6% mfe=1.43 | n=3 prof=66.7% [20.8–93.9] net=+0.277 gross=+0.300 PF=1.80 stop=33.3% mfe=1.34 | n=5 prof=60.0% [23.1–88.2] net=+0.202 gross=+0.225 PF=1.49 stop=40.0% mfe=1.10 | n=1 prof=0.0% [0.0–79.3] net=-1.147 gross=-1.000 PF=0.00 stop=100.0% mfe=0.59 |  |
| 0.4 | n=6 prof=83.3% [43.6–97.0] net=+0.864 gross=+0.885 PF=6.09 stop=16.7% mfe=1.66 | n=3 prof=66.7% [20.8–93.9] net=+0.277 gross=+0.300 PF=1.80 stop=33.3% mfe=1.34 | n=4 prof=75.0% [30.1–95.4] net=+0.512 gross=+0.531 PF=2.98 stop=25.0% mfe=1.33 | n=1 prof=0.0% [0.0–79.3] net=-1.147 gross=-1.000 PF=0.00 stop=100.0% mfe=0.59 |  |

- TRAIN monotonic (net at 0.4 ≥ at 0.05): True → **rule verdict: FAIL**

### liquidity_sweep_long (1h) — 62 trades with CVD (of 228)

- baseline TRAIN n=37 prof=56.8% [40.9–71.3] net=-0.131 gross=-0.047 PF=0.71 stop=40.5% mfe=0.94 · TEST n=25 prof=64.0% [44.5–79.8] net=-0.042 gross=+0.036 PF=0.89 stop=36.0% mfe=0.90

| thr | TRAIN confirm | TRAIN contra | TEST confirm | TEST contra | flag |
|---|---|---|---|---|---|
| 0.05 | n=5 prof=40.0% [11.8–76.9] net=-0.130 gross=-0.018 PF=0.73 stop=40.0% mfe=0.91 | n=32 prof=59.4% [42.3–74.5] net=-0.131 gross=-0.052 PF=0.71 stop=40.6% mfe=0.94 | n=3 prof=33.3% [6.1–79.2] net=-0.623 gross=-0.542 PF=0.15 stop=66.7% mfe=0.42 | n=21 prof=66.7% [45.4–82.8] net=+0.024 gross=+0.102 PF=1.06 stop=33.3% mfe=0.97 |  |
| 0.1 | n=5 prof=40.0% [11.8–76.9] net=-0.130 gross=-0.018 PF=0.73 stop=40.0% mfe=0.91 | n=31 prof=61.3% [43.8–76.3] net=-0.100 gross=-0.021 PF=0.77 stop=38.7% mfe=0.96 | n=1 prof=0.0% [0.0–79.3] net=-1.058 gross=-1.000 PF=0.00 stop=100.0% mfe=0.23 | n=21 prof=66.7% [45.4–82.8] net=+0.024 gross=+0.102 PF=1.06 stop=33.3% mfe=0.97 |  |
| 0.2 | n=4 prof=50.0% [15.0–85.0] net=+0.110 gross=+0.228 PF=1.33 stop=25.0% mfe=0.96 | n=28 prof=60.7% [42.4–76.4] net=-0.123 gross=-0.040 PF=0.72 stop=39.3% mfe=0.95 | n=0 | n=19 prof=63.2% [41.0–80.9] net=-0.005 gross=+0.074 PF=0.99 stop=36.8% mfe=0.98 |  |
| 0.4 | n=2 prof=50.0% [9.5–90.5] net=-0.367 gross=-0.237 PF=0.39 stop=50.0% mfe=0.62 | n=20 prof=55.0% [34.2–74.2] net=-0.201 gross=-0.106 PF=0.60 stop=45.0% mfe=0.91 | n=0 | n=18 prof=61.1% [38.6–79.7] net=-0.023 gross=+0.057 PF=0.95 stop=38.9% mfe=1.00 |  |

- TRAIN monotonic (net at 0.4 ≥ at 0.05): False → **rule verdict: FAIL**

### range_reversion_long (4h) — 1 trades with CVD (of 12) → SKIPPED (too few)

### range_reversion_short (4h) — 1 trades with CVD (of 9) → SKIPPED (too few)

### rsi_bounce_long (4h) — 18 trades with CVD (of 58)

- baseline TRAIN n=10 prof=70.0% [39.7–89.2] net=+0.305 gross=+0.327 PF=2.27 stop=20.0% mfe=1.08 · TEST n=8 prof=62.5% [30.6–86.3] net=-0.066 gross=-0.039 PF=0.79 stop=25.0% mfe=0.43

| thr | TRAIN confirm | TRAIN contra | TEST confirm | TEST contra | flag |
|---|---|---|---|---|---|
| 0.05 | n=3 prof=33.3% [6.1–79.2] net=-0.561 gross=-0.542 PF=0.18 stop=66.7% mfe=0.32 | n=6 prof=83.3% [43.6–97.0] net=+0.672 gross=+0.696 PF=12.40 stop=0.0% mfe=1.36 | n=3 prof=33.3% [6.1–79.2] net=-0.263 gross=-0.234 PF=0.46 stop=33.3% mfe=0.58 | n=5 prof=80.0% [37.6–96.4] net=+0.053 gross=+0.078 PF=1.26 stop=20.0% mfe=0.35 |  |
| 0.1 | n=3 prof=33.3% [6.1–79.2] net=-0.561 gross=-0.542 PF=0.18 stop=66.7% mfe=0.32 | n=6 prof=83.3% [43.6–97.0] net=+0.672 gross=+0.696 PF=12.40 stop=0.0% mfe=1.36 | n=3 prof=33.3% [6.1–79.2] net=-0.263 gross=-0.234 PF=0.46 stop=33.3% mfe=0.58 | n=3 prof=66.7% [20.8–93.9] net=-0.160 gross=-0.137 PF=0.53 stop=33.3% mfe=0.28 |  |
| 0.2 | n=2 prof=50.0% [9.5–90.5] net=-0.330 gross=-0.312 PF=0.35 stop=50.0% mfe=0.45 | n=4 prof=75.0% [30.1–95.4] net=+0.543 gross=+0.568 PF=7.14 stop=0.0% mfe=1.20 | n=3 prof=33.3% [6.1–79.2] net=-0.263 gross=-0.234 PF=0.46 stop=33.3% mfe=0.58 | n=2 prof=50.0% [9.5–90.5] net=-0.401 gross=-0.377 PF=0.21 stop=50.0% mfe=0.20 |  |
| 0.4 | n=1 prof=0.0% [0.0–79.3] net=-1.019 gross=-1.000 PF=0.00 stop=100.0% mfe=0.14 | n=3 prof=66.7% [20.8–93.9] net=+0.559 gross=+0.583 PF=5.74 stop=0.0% mfe=1.19 | n=2 prof=50.0% [9.5–90.5] net=-0.171 gross=-0.150 PF=0.66 stop=50.0% mfe=0.50 | n=1 prof=100.0% [20.7–100.0] net=+0.219 gross=+0.246 PF=inf stop=0.0% mfe=0.31 |  |

- TRAIN monotonic (net at 0.4 ≥ at 0.05): False → **rule verdict: FAIL**

### rsi_rejection_short (1h) — 58 trades with CVD (of 267)

- baseline TRAIN n=34 prof=55.9% [39.5–71.1] net=+0.001 gross=+0.044 PF=1.00 stop=38.2% mfe=1.04 · TEST n=24 prof=54.2% [35.1–72.1] net=+0.120 gross=+0.178 PF=1.39 stop=20.8% mfe=1.02

| thr | TRAIN confirm | TRAIN contra | TEST confirm | TEST contra | flag |
|---|---|---|---|---|---|
| 0.05 | n=17 prof=52.9% [31.0–73.8] net=-0.135 gross=-0.091 PF=0.73 stop=47.1% mfe=0.94 | n=17 prof=58.8% [36.0–78.4] net=+0.138 gross=+0.180 PF=1.37 stop=29.4% mfe=1.15 | n=11 prof=54.5% [28.0–78.7] net=+0.156 gross=+0.206 PF=1.44 stop=27.3% mfe=1.17 | n=12 prof=50.0% [25.4–74.6] net=+0.070 gross=+0.135 PF=1.24 stop=16.7% mfe=0.91 |  |
| 0.1 | n=16 prof=56.2% [33.2–76.9] net=-0.078 gross=-0.035 PF=0.83 stop=43.8% mfe=0.96 | n=16 prof=62.5% [38.6–81.5] net=+0.212 gross=+0.254 PF=1.64 stop=25.0% mfe=1.21 | n=11 prof=54.5% [28.0–78.7] net=+0.156 gross=+0.206 PF=1.44 stop=27.3% mfe=1.17 | n=11 prof=54.5% [28.0–78.7] net=+0.100 gross=+0.167 PF=1.34 stop=18.2% mfe=0.93 |  |
| 0.2 | n=13 prof=53.8% [29.1–76.8] net=-0.169 gross=-0.125 PF=0.66 stop=46.2% mfe=0.92 | n=13 prof=61.5% [35.5–82.3] net=+0.111 gross=+0.147 PF=1.30 stop=30.8% mfe=1.14 | n=8 prof=62.5% [30.6–86.3] net=+0.249 gross=+0.301 PF=1.60 stop=37.5% mfe=1.35 | n=10 prof=50.0% [23.7–76.3] net=+0.043 gross=+0.111 PF=1.13 stop=20.0% mfe=0.92 |  |
| 0.4 | n=9 prof=55.6% [26.7–81.1] net=-0.208 gross=-0.169 PF=0.55 stop=44.4% mfe=0.89 | n=8 prof=50.0% [21.5–78.5] net=-0.057 gross=-0.019 PF=0.88 stop=37.5% mfe=1.00 | n=5 prof=60.0% [23.1–88.2] net=+0.178 gross=+0.225 PF=1.41 stop=40.0% mfe=1.23 | n=7 prof=57.1% [25.0–84.2] net=-0.005 gross=+0.075 PF=0.99 stop=28.6% mfe=0.88 |  |

- TRAIN monotonic (net at 0.4 ≥ at 0.05): False → **rule verdict: FAIL**

### rsi_rejection_short (4h) — 13 trades with CVD (of 32)

- baseline TRAIN n=7 prof=14.3% [2.6–51.3] net=-0.755 gross=-0.717 PF=0.05 stop=71.4% mfe=0.22 · TEST n=6 prof=83.3% [43.6–97.0] net=+0.138 gross=+0.164 PF=1.81 stop=16.7% mfe=0.74

| thr | TRAIN confirm | TRAIN contra | TEST confirm | TEST contra | flag |
|---|---|---|---|---|---|
| 0.05 | n=7 prof=14.3% [2.6–51.3] net=-0.755 gross=-0.717 PF=0.05 stop=71.4% mfe=0.22 | n=0 | n=5 prof=100.0% [56.6–100.0] net=+0.370 gross=+0.397 PF=inf stop=0.0% mfe=0.85 | n=1 prof=0.0% [0.0–79.3] net=-1.021 gross=-1.000 PF=0.00 stop=100.0% mfe=0.18 |  |
| 0.1 | n=7 prof=14.3% [2.6–51.3] net=-0.755 gross=-0.717 PF=0.05 stop=71.4% mfe=0.22 | n=0 | n=4 prof=100.0% [51.0–100.0] net=+0.322 gross=+0.347 PF=inf stop=0.0% mfe=0.86 | n=1 prof=0.0% [0.0–79.3] net=-1.021 gross=-1.000 PF=0.00 stop=100.0% mfe=0.18 |  |
| 0.2 | n=6 prof=16.7% [3.0–56.4] net=-0.693 gross=-0.670 PF=0.06 stop=66.7% mfe=0.26 | n=0 | n=4 prof=100.0% [51.0–100.0] net=+0.322 gross=+0.347 PF=inf stop=0.0% mfe=0.86 | n=1 prof=0.0% [0.0–79.3] net=-1.021 gross=-1.000 PF=0.00 stop=100.0% mfe=0.18 |  |
| 0.4 | n=5 prof=20.0% [3.6–62.4] net=-0.625 gross=-0.604 PF=0.08 stop=60.0% mfe=0.25 | n=0 | n=4 prof=100.0% [51.0–100.0] net=+0.322 gross=+0.347 PF=inf stop=0.0% mfe=0.86 | n=0 |  |

- TRAIN monotonic (net at 0.4 ≥ at 0.05): True → **rule verdict: FAIL**

### trend_pullback_short (4h) — 12 trades with CVD (of 54)

- baseline TRAIN n=7 prof=28.6% [8.2–64.1] net=-0.361 gross=-0.321 PF=0.52 stop=71.4% mfe=0.74 · TEST n=5 prof=40.0% [11.8–76.9] net=+0.271 gross=+0.302 PF=2.03 stop=20.0% mfe=1.24

| thr | TRAIN confirm | TRAIN contra | TEST confirm | TEST contra | flag |
|---|---|---|---|---|---|
| 0.05 | n=4 prof=25.0% [4.6–69.9] net=-0.445 gross=-0.406 PF=0.43 stop=75.0% mfe=0.57 | n=2 prof=50.0% [9.5–90.5] net=+0.144 gross=+0.188 PF=1.27 stop=50.0% mfe=1.41 | n=2 prof=0.0% [0.0–65.8] net=-0.149 gross=-0.119 PF=0.00 stop=0.0% mfe=0.32 | n=3 prof=66.7% [20.8–93.9] net=+0.551 gross=+0.583 PF=2.62 stop=33.3% mfe=1.86 |  |
| 0.1 | n=4 prof=25.0% [4.6–69.9] net=-0.445 gross=-0.406 PF=0.43 stop=75.0% mfe=0.57 | n=2 prof=50.0% [9.5–90.5] net=+0.144 gross=+0.188 PF=1.27 stop=50.0% mfe=1.41 | n=1 prof=0.0% [0.0–79.3] net=-0.209 gross=-0.185 PF=0.00 stop=0.0% mfe=0.35 | n=3 prof=66.7% [20.8–93.9] net=+0.551 gross=+0.583 PF=2.62 stop=33.3% mfe=1.86 |  |
| 0.2 | n=2 prof=0.0% [0.0–65.8] net=-1.050 gross=-1.000 PF=0.00 stop=100.0% mfe=0.01 | n=0 | n=1 prof=0.0% [0.0–79.3] net=-0.209 gross=-0.185 PF=0.00 stop=0.0% mfe=0.35 | n=3 prof=66.7% [20.8–93.9] net=+0.551 gross=+0.583 PF=2.62 stop=33.3% mfe=1.86 |  |
| 0.4 | n=1 prof=0.0% [0.0–79.3] net=-1.060 gross=-1.000 PF=0.00 stop=100.0% mfe=0.03 | n=0 | n=0 | n=2 prof=100.0% [34.2–100.0] net=+1.337 gross=+1.375 PF=inf stop=0.0% mfe=2.61 |  |

- TRAIN monotonic (net at 0.4 ≥ at 0.05): False → **rule verdict: FAIL**

**FORK #4 VERDICT: FAIL** — 24 confirm cells examined (expect ~1.2 chance winners at 5%; the TRAIN/TEST agreement, monotonicity and n floors are the guards). Next: close fork #4 — remove the collector cron (keep the store), close Phase 5's CVD input.

## (f) Fill model — passive (maker) entry vs market (taker)

Limit rests at the next 15m open improved by offset×ATR; fills only when price trades THROUGH it within `wait` bars (touch ≠ fill); maker fee 0.020% on entry + take-profits, stops still taker+slippage. 'market same subset' re-costs the identical filled trades at taker fees, so (limit − market same subset) = pure fee effect and (market same subset − baseline) = selection effect of waiting for a fill. Unfilled signals are lost opportunities, not losses.


### rsi_rejection_short (1h) — market baseline: n=267 prof=50.2% [44.2–56.1] net=-0.175 gross=-0.060 PF=0.63 stop=39.7% mfe=0.85

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=267 prof=51.3% [45.3–57.2] net=-0.121 gross=-0.060 PF=0.73 stop=39.7% mfe=0.85 | n=267 prof=50.2% [44.2–56.1] net=-0.175 gross=-0.060 PF=0.63 stop=39.7% mfe=0.85 |
| 0.0 | 4 | 100% | n=267 prof=51.3% [45.3–57.2] net=-0.121 gross=-0.060 PF=0.73 stop=39.7% mfe=0.85 | n=267 prof=50.2% [44.2–56.1] net=-0.175 gross=-0.060 PF=0.63 stop=39.7% mfe=0.85 |
| 0.0 | 8 | 100% | n=267 prof=51.3% [45.3–57.2] net=-0.121 gross=-0.060 PF=0.73 stop=39.7% mfe=0.85 | n=267 prof=50.2% [44.2–56.1] net=-0.175 gross=-0.060 PF=0.63 stop=39.7% mfe=0.85 |
| 0.15 | 2 | 75% | n=200 prof=57.5% [50.6–64.1] net=-0.042 gross=+0.023 PF=0.89 stop=35.0% mfe=0.92 | n=200 prof=56.0% [49.1–62.7] net=-0.101 gross=+0.023 PF=0.76 stop=35.0% mfe=0.92 |
| 0.15 | 4 | 85% | n=226 prof=56.2% [49.7–62.5] net=-0.074 gross=-0.008 PF=0.82 stop=37.2% mfe=0.90 | n=226 prof=54.9% [48.4–61.2] net=-0.133 gross=-0.008 PF=0.70 stop=37.2% mfe=0.90 |
| 0.15 | 8 | 91% | n=242 prof=55.8% [49.5–61.9] net=-0.080 gross=-0.015 PF=0.81 stop=37.6% mfe=0.90 | n=242 prof=54.5% [48.2–60.7] net=-0.138 gross=-0.015 PF=0.69 stop=37.6% mfe=0.90 |
| 0.3 | 2 | 49% | n=131 prof=60.3% [51.7–68.3] net=+0.005 gross=+0.077 PF=1.01 stop=35.9% mfe=1.03 | n=131 prof=59.5% [51.0–67.6] net=-0.062 gross=+0.077 PF=0.86 stop=35.9% mfe=1.03 |
| 0.3 | 4 | 62% | n=165 prof=58.8% [51.2–66.0] net=-0.041 gross=+0.031 PF=0.90 stop=38.2% mfe=1.00 | n=165 prof=57.6% [49.9–64.9] net=-0.108 gross=+0.031 PF=0.76 stop=38.2% mfe=1.00 |
| 0.3 | 8 | 75% | n=200 prof=57.0% [50.1–63.7] net=-0.078 gross=-0.009 PF=0.82 stop=39.0% mfe=0.95 | n=200 prof=56.0% [49.1–62.7] net=-0.141 gross=-0.009 PF=0.70 stop=39.0% mfe=0.95 |

### liquidity_sweep_long (1h) — market baseline: n=228 prof=51.8% [45.3–58.2] net=-0.251 gross=-0.053 PF=0.52 stop=43.4% mfe=0.95

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=228 prof=54.4% [47.9–60.7] net=-0.148 gross=-0.053 PF=0.69 stop=43.4% mfe=0.95 | n=228 prof=51.8% [45.3–58.2] net=-0.251 gross=-0.053 PF=0.52 stop=43.4% mfe=0.95 |
| 0.0 | 4 | 100% | n=228 prof=54.4% [47.9–60.7] net=-0.148 gross=-0.053 PF=0.69 stop=43.4% mfe=0.95 | n=228 prof=51.8% [45.3–58.2] net=-0.251 gross=-0.053 PF=0.52 stop=43.4% mfe=0.95 |
| 0.0 | 8 | 100% | n=228 prof=54.4% [47.9–60.7] net=-0.148 gross=-0.053 PF=0.69 stop=43.4% mfe=0.95 | n=228 prof=51.8% [45.3–58.2] net=-0.251 gross=-0.053 PF=0.52 stop=43.4% mfe=0.95 |
| 0.15 | 2 | 68% | n=156 prof=53.2% [45.4–60.9] net=-0.131 gross=-0.028 PF=0.74 stop=44.2% mfe=1.02 | n=156 prof=51.3% [43.5–59.0] net=-0.245 gross=-0.028 PF=0.55 stop=44.2% mfe=1.02 |
| 0.15 | 4 | 75% | n=171 prof=53.2% [45.7–60.5] net=-0.148 gross=-0.041 PF=0.70 stop=44.4% mfe=1.01 | n=171 prof=50.3% [42.9–57.7] net=-0.270 gross=-0.041 PF=0.51 stop=44.4% mfe=1.01 |
| 0.15 | 8 | 86% | n=197 prof=53.3% [46.3–60.1] net=-0.157 gross=-0.049 PF=0.69 stop=44.7% mfe=1.00 | n=197 prof=49.2% [42.3–56.2] net=-0.281 gross=-0.049 PF=0.49 stop=44.7% mfe=1.00 |
| 0.3 | 2 | 48% | n=109 prof=53.2% [43.9–62.3] net=-0.173 gross=-0.051 PF=0.67 stop=45.0% mfe=1.07 | n=109 prof=48.6% [39.4–57.9] net=-0.307 gross=-0.051 PF=0.47 stop=45.0% mfe=1.07 |
| 0.3 | 4 | 55% | n=125 prof=56.0% [47.2–64.4] net=-0.118 gross=+0.001 PF=0.76 stop=42.4% mfe=1.13 | n=125 prof=52.0% [43.3–60.6] net=-0.254 gross=+0.001 PF=0.53 stop=42.4% mfe=1.13 |
| 0.3 | 8 | 73% | n=166 prof=57.2% [49.6–64.5] net=-0.110 gross=+0.015 PF=0.77 stop=41.0% mfe=1.13 | n=166 prof=54.2% [46.6–61.6] net=-0.250 gross=+0.015 PF=0.53 stop=41.0% mfe=1.13 |

### rsi_bounce_long (4h) — market baseline: n=58 prof=55.2% [42.5–67.3] net=-0.030 gross=+0.035 PF=0.91 stop=27.6% mfe=0.79

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=58 prof=55.2% [42.5–67.3] net=-0.004 gross=+0.035 PF=0.99 stop=27.6% mfe=0.79 | n=58 prof=55.2% [42.5–67.3] net=-0.030 gross=+0.035 PF=0.91 stop=27.6% mfe=0.79 |
| 0.0 | 4 | 100% | n=58 prof=55.2% [42.5–67.3] net=-0.004 gross=+0.035 PF=0.99 stop=27.6% mfe=0.79 | n=58 prof=55.2% [42.5–67.3] net=-0.030 gross=+0.035 PF=0.91 stop=27.6% mfe=0.79 |
| 0.0 | 8 | 100% | n=58 prof=55.2% [42.5–67.3] net=-0.004 gross=+0.035 PF=0.99 stop=27.6% mfe=0.79 | n=58 prof=55.2% [42.5–67.3] net=-0.030 gross=+0.035 PF=0.91 stop=27.6% mfe=0.79 |
| 0.15 | 2 | 19% | n=11 prof=45.5% [21.3–72.0] net=-0.083 gross=-0.053 PF=0.80 stop=36.4% mfe=0.85 | n=11 prof=45.5% [21.3–72.0] net=-0.103 gross=-0.053 PF=0.76 stop=36.4% mfe=0.85 |
| 0.15 | 4 | 43% | n=25 prof=56.0% [37.1–73.3] net=-0.065 gross=-0.031 PF=0.83 stop=32.0% mfe=0.77 | n=25 prof=56.0% [37.1–73.3] net=-0.086 gross=-0.031 PF=0.77 stop=32.0% mfe=0.77 |
| 0.15 | 8 | 52% | n=30 prof=56.7% [39.2–72.6] net=-0.027 gross=+0.012 PF=0.92 stop=30.0% mfe=0.78 | n=30 prof=56.7% [39.2–72.6] net=-0.052 gross=+0.012 PF=0.86 stop=30.0% mfe=0.78 |
| 0.3 | 2 | 3% | n=2 prof=50.0% [9.5–90.5] net=-0.257 gross=-0.237 PF=0.50 stop=50.0% mfe=1.08 | n=2 prof=50.0% [9.5–90.5] net=-0.271 gross=-0.237 PF=0.48 stop=50.0% mfe=1.08 |
| 0.3 | 4 | 16% | n=9 prof=55.6% [26.7–81.1] net=+0.001 gross=+0.040 PF=1.00 stop=33.3% mfe=0.95 | n=9 prof=55.6% [26.7–81.1] net=-0.023 gross=+0.040 PF=0.93 stop=33.3% mfe=0.95 |
| 0.3 | 8 | 21% | n=12 prof=58.3% [32.0–80.7] net=-0.024 gross=+0.013 PF=0.93 stop=33.3% mfe=0.83 | n=12 prof=58.3% [32.0–80.7] net=-0.047 gross=+0.013 PF=0.87 stop=33.3% mfe=0.83 |

### trend_pullback_short (4h) — market baseline: n=54 prof=48.1% [35.4–61.1] net=-0.167 gross=-0.057 PF=0.66 stop=44.4% mfe=0.96

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=54 prof=48.1% [35.4–61.1] net=-0.117 gross=-0.057 PF=0.76 stop=44.4% mfe=0.96 | n=54 prof=48.1% [35.4–61.1] net=-0.167 gross=-0.057 PF=0.66 stop=44.4% mfe=0.96 |
| 0.0 | 4 | 100% | n=54 prof=48.1% [35.4–61.1] net=-0.117 gross=-0.057 PF=0.76 stop=44.4% mfe=0.96 | n=54 prof=48.1% [35.4–61.1] net=-0.167 gross=-0.057 PF=0.66 stop=44.4% mfe=0.96 |
| 0.0 | 8 | 100% | n=54 prof=48.1% [35.4–61.1] net=-0.117 gross=-0.057 PF=0.76 stop=44.4% mfe=0.96 | n=54 prof=48.1% [35.4–61.1] net=-0.167 gross=-0.057 PF=0.66 stop=44.4% mfe=0.96 |
| 0.15 | 2 | 57% | n=31 prof=58.1% [40.8–73.6] net=-0.015 gross=+0.049 PF=0.96 stop=38.7% mfe=1.00 | n=31 prof=54.8% [37.8–70.8] net=-0.070 gross=+0.049 PF=0.84 stop=38.7% mfe=1.00 |
| 0.15 | 4 | 70% | n=38 prof=57.9% [42.2–72.1] net=-0.028 gross=+0.035 PF=0.93 stop=39.5% mfe=1.01 | n=38 prof=55.3% [39.7–69.9] net=-0.084 gross=+0.035 PF=0.81 stop=39.5% mfe=1.01 |
| 0.15 | 8 | 74% | n=40 prof=60.0% [44.6–73.7] net=-0.003 gross=+0.060 PF=0.99 stop=37.5% mfe=1.03 | n=40 prof=57.5% [42.2–71.5] net=-0.058 gross=+0.060 PF=0.86 stop=37.5% mfe=1.03 |
| 0.3 | 2 | 28% | n=15 prof=66.7% [41.7–84.8] net=+0.073 gross=+0.134 PF=1.21 stop=33.3% mfe=1.01 | n=15 prof=66.7% [41.7–84.8] net=+0.006 gross=+0.134 PF=1.02 stop=33.3% mfe=1.01 |
| 0.3 | 4 | 43% | n=23 prof=65.2% [44.9–81.2] net=+0.052 gross=+0.108 PF=1.14 stop=34.8% mfe=1.03 | n=23 prof=65.2% [44.9–81.2] net=-0.008 gross=+0.108 PF=0.98 stop=34.8% mfe=1.03 |
| 0.3 | 8 | 50% | n=27 prof=70.4% [51.5–84.1] net=+0.133 gross=+0.190 PF=1.43 stop=29.6% mfe=1.08 | n=27 prof=70.4% [51.5–84.1] net=+0.072 gross=+0.190 PF=1.22 stop=29.6% mfe=1.08 |

### failed_breakout_short (4h) — market baseline: n=41 prof=61.0% [45.7–74.3] net=+0.139 gross=+0.205 PF=1.35 stop=36.6% mfe=1.10

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=41 prof=61.0% [45.7–74.3] net=+0.170 gross=+0.205 PF=1.44 stop=36.6% mfe=1.10 | n=41 prof=61.0% [45.7–74.3] net=+0.139 gross=+0.205 PF=1.35 stop=36.6% mfe=1.10 |
| 0.0 | 4 | 100% | n=41 prof=61.0% [45.7–74.3] net=+0.170 gross=+0.205 PF=1.44 stop=36.6% mfe=1.10 | n=41 prof=61.0% [45.7–74.3] net=+0.139 gross=+0.205 PF=1.35 stop=36.6% mfe=1.10 |
| 0.0 | 8 | 100% | n=41 prof=61.0% [45.7–74.3] net=+0.170 gross=+0.205 PF=1.44 stop=36.6% mfe=1.10 | n=41 prof=61.0% [45.7–74.3] net=+0.139 gross=+0.205 PF=1.35 stop=36.6% mfe=1.10 |
| 0.15 | 2 | 54% | n=22 prof=59.1% [38.7–76.7] net=+0.006 gross=+0.033 PF=1.01 stop=40.9% mfe=0.93 | n=22 prof=59.1% [38.7–76.7] net=-0.021 gross=+0.033 PF=0.95 stop=40.9% mfe=0.93 |
| 0.15 | 4 | 68% | n=28 prof=60.7% [42.4–76.4] net=+0.028 gross=+0.060 PF=1.07 stop=39.3% mfe=0.95 | n=28 prof=60.7% [42.4–76.4] net=-0.005 gross=+0.060 PF=0.99 stop=39.3% mfe=0.95 |
| 0.15 | 8 | 71% | n=29 prof=62.1% [44.0–77.3] net=+0.074 gross=+0.106 PF=1.19 stop=37.9% mfe=1.00 | n=29 prof=62.1% [44.0–77.3] net=+0.041 gross=+0.106 PF=1.10 stop=37.9% mfe=1.00 |
| 0.3 | 2 | 20% | n=8 prof=37.5% [13.7–69.4] net=-0.399 gross=-0.359 PF=0.39 stop=62.5% mfe=0.65 | n=8 prof=37.5% [13.7–69.4] net=-0.431 gross=-0.359 PF=0.36 stop=62.5% mfe=0.65 |
| 0.3 | 4 | 32% | n=13 prof=53.8% [29.1–76.8] net=-0.194 gross=-0.153 PF=0.60 stop=46.2% mfe=0.81 | n=13 prof=53.8% [29.1–76.8] net=-0.230 gross=-0.153 PF=0.54 stop=46.2% mfe=0.81 |
| 0.3 | 8 | 41% | n=17 prof=58.8% [36.0–78.4] net=-0.087 gross=-0.051 PF=0.80 stop=41.2% mfe=0.87 | n=17 prof=58.8% [36.0–78.4] net=-0.123 gross=-0.051 PF=0.72 stop=41.2% mfe=0.87 |

### rsi_rejection_short (4h) — market baseline: n=32 prof=40.6% [25.5–57.7] net=-0.289 gross=-0.239 PF=0.44 stop=46.9% mfe=0.55

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=32 prof=40.6% [25.5–57.7] net=-0.271 gross=-0.239 PF=0.47 stop=46.9% mfe=0.55 | n=32 prof=40.6% [25.5–57.7] net=-0.289 gross=-0.239 PF=0.44 stop=46.9% mfe=0.55 |
| 0.0 | 4 | 100% | n=32 prof=40.6% [25.5–57.7] net=-0.271 gross=-0.239 PF=0.47 stop=46.9% mfe=0.55 | n=32 prof=40.6% [25.5–57.7] net=-0.289 gross=-0.239 PF=0.44 stop=46.9% mfe=0.55 |
| 0.0 | 8 | 100% | n=32 prof=40.6% [25.5–57.7] net=-0.271 gross=-0.239 PF=0.47 stop=46.9% mfe=0.55 | n=32 prof=40.6% [25.5–57.7] net=-0.289 gross=-0.239 PF=0.44 stop=46.9% mfe=0.55 |
| 0.15 | 2 | 41% | n=13 prof=23.1% [8.2–50.3] net=-0.609 gross=-0.566 PF=0.10 stop=61.5% mfe=0.33 | n=13 prof=23.1% [8.2–50.3] net=-0.630 gross=-0.566 PF=0.09 stop=61.5% mfe=0.33 |
| 0.15 | 4 | 47% | n=15 prof=26.7% [10.9–52.0] net=-0.506 gross=-0.466 PF=0.22 stop=60.0% mfe=0.48 | n=15 prof=26.7% [10.9–52.0] net=-0.528 gross=-0.466 PF=0.21 stop=60.0% mfe=0.48 |
| 0.15 | 8 | 78% | n=25 prof=36.0% [20.2–55.5] net=-0.322 gross=-0.284 PF=0.42 stop=52.0% mfe=0.58 | n=25 prof=36.0% [20.2–55.5] net=-0.344 gross=-0.284 PF=0.40 stop=52.0% mfe=0.58 |
| 0.3 | 2 | 12% | n=4 prof=0.0% [0.0–49.0] net=-0.858 gross=-0.800 PF=0.00 stop=75.0% mfe=0.22 | n=4 prof=0.0% [0.0–49.0] net=-0.886 gross=-0.800 PF=0.00 stop=75.0% mfe=0.22 |
| 0.3 | 4 | 28% | n=9 prof=11.1% [2.0–43.5] net=-0.582 gross=-0.531 PF=0.21 stop=66.7% mfe=0.56 | n=9 prof=11.1% [2.0–43.5] net=-0.610 gross=-0.531 PF=0.19 stop=66.7% mfe=0.56 |
| 0.3 | 8 | 50% | n=16 prof=25.0% [10.2–49.5] net=-0.531 gross=-0.487 PF=0.21 stop=62.5% mfe=0.49 | n=16 prof=25.0% [10.2–49.5] net=-0.553 gross=-0.487 PF=0.19 stop=62.5% mfe=0.49 |

### range_reversion_long (4h) — market baseline: n=12 prof=58.3% [32.0–80.7] net=-0.294 gross=-0.148 PF=0.38 stop=41.7% mfe=0.79

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=12 prof=58.3% [32.0–80.7] net=-0.040 gross=+0.027 PF=0.91 stop=41.7% mfe=0.98 | n=12 prof=58.3% [32.0–80.7] net=-0.119 gross=+0.027 PF=0.75 stop=41.7% mfe=0.98 |
| 0.0 | 4 | 100% | n=12 prof=58.3% [32.0–80.7] net=-0.040 gross=+0.027 PF=0.91 stop=41.7% mfe=0.98 | n=12 prof=58.3% [32.0–80.7] net=-0.119 gross=+0.027 PF=0.75 stop=41.7% mfe=0.98 |
| 0.0 | 8 | 100% | n=12 prof=58.3% [32.0–80.7] net=-0.040 gross=+0.027 PF=0.91 stop=41.7% mfe=0.98 | n=12 prof=58.3% [32.0–80.7] net=-0.119 gross=+0.027 PF=0.75 stop=41.7% mfe=0.98 |
| 0.15 | 2 | 58% | n=7 prof=42.9% [15.8–75.0] net=-0.376 gross=-0.261 PF=0.42 stop=57.1% mfe=1.01 | n=7 prof=42.9% [15.8–75.0] net=-0.501 gross=-0.261 PF=0.27 stop=57.1% mfe=1.01 |
| 0.15 | 4 | 75% | n=9 prof=55.6% [26.7–81.1] net=-0.120 gross=-0.019 PF=0.76 stop=44.4% mfe=1.09 | n=9 prof=55.6% [26.7–81.1] net=-0.234 gross=-0.019 PF=0.56 stop=44.4% mfe=1.09 |
| 0.15 | 8 | 75% | n=9 prof=55.6% [26.7–81.1] net=-0.120 gross=-0.019 PF=0.76 stop=44.4% mfe=1.09 | n=9 prof=55.6% [26.7–81.1] net=-0.234 gross=-0.019 PF=0.56 stop=44.4% mfe=1.09 |
| 0.3 | 2 | 42% | n=5 prof=60.0% [23.1–88.2] net=-0.093 gross=+0.275 PF=0.87 stop=40.0% mfe=3.98 | n=5 prof=60.0% [23.1–88.2] net=-0.503 gross=+0.275 PF=0.43 stop=40.0% mfe=3.98 |
| 0.3 | 4 | 58% | n=7 prof=71.4% [35.9–91.8] net=+0.066 gross=+0.346 PF=1.13 stop=28.6% mfe=3.20 | n=7 prof=71.4% [35.9–91.8] net=-0.248 gross=+0.346 PF=0.61 stop=28.6% mfe=3.20 |
| 0.3 | 8 | 67% | n=8 prof=62.5% [30.6–86.3] net=-0.079 gross=+0.178 PF=0.86 stop=37.5% mfe=2.85 | n=8 prof=62.5% [30.6–86.3] net=-0.362 gross=+0.178 PF=0.48 stop=37.5% mfe=2.85 |

### range_reversion_short (4h) — market baseline: n=9 prof=44.4% [18.9–73.3] net=-0.415 gross=-0.289 PF=0.34 stop=55.6% mfe=0.60

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=9 prof=44.4% [18.9–73.3] net=-0.356 gross=-0.289 PF=0.41 stop=55.6% mfe=0.60 | n=9 prof=44.4% [18.9–73.3] net=-0.415 gross=-0.289 PF=0.34 stop=55.6% mfe=0.60 |
| 0.0 | 4 | 100% | n=9 prof=44.4% [18.9–73.3] net=-0.356 gross=-0.289 PF=0.41 stop=55.6% mfe=0.60 | n=9 prof=44.4% [18.9–73.3] net=-0.415 gross=-0.289 PF=0.34 stop=55.6% mfe=0.60 |
| 0.0 | 8 | 100% | n=9 prof=44.4% [18.9–73.3] net=-0.356 gross=-0.289 PF=0.41 stop=55.6% mfe=0.60 | n=9 prof=44.4% [18.9–73.3] net=-0.415 gross=-0.289 PF=0.34 stop=55.6% mfe=0.60 |
| 0.15 | 2 | 89% | n=8 prof=50.0% [21.5–78.5] net=-0.352 gross=-0.275 PF=0.35 stop=50.0% mfe=0.70 | n=8 prof=50.0% [21.5–78.5] net=-0.421 gross=-0.275 PF=0.27 stop=50.0% mfe=0.70 |
| 0.15 | 4 | 100% | n=9 prof=55.6% [26.7–81.1] net=-0.280 gross=-0.203 PF=0.42 stop=44.4% mfe=0.71 | n=9 prof=55.6% [26.7–81.1] net=-0.352 gross=-0.203 PF=0.31 stop=44.4% mfe=0.71 |
| 0.15 | 8 | 100% | n=9 prof=55.6% [26.7–81.1] net=-0.280 gross=-0.203 PF=0.42 stop=44.4% mfe=0.71 | n=9 prof=55.6% [26.7–81.1] net=-0.352 gross=-0.203 PF=0.31 stop=44.4% mfe=0.71 |
| 0.3 | 2 | 67% | n=6 prof=33.3% [9.7–70.0] net=-0.383 gross=-0.292 PF=0.48 stop=66.7% mfe=0.88 | n=6 prof=33.3% [9.7–70.0] net=-0.482 gross=-0.292 PF=0.39 stop=66.7% mfe=0.88 |
| 0.3 | 4 | 67% | n=6 prof=33.3% [9.7–70.0] net=-0.383 gross=-0.292 PF=0.48 stop=66.7% mfe=0.88 | n=6 prof=33.3% [9.7–70.0] net=-0.482 gross=-0.292 PF=0.39 stop=66.7% mfe=0.88 |
| 0.3 | 8 | 67% | n=6 prof=33.3% [9.7–70.0] net=-0.383 gross=-0.292 PF=0.48 stop=66.7% mfe=0.88 | n=6 prof=33.3% [9.7–70.0] net=-0.482 gross=-0.292 PF=0.39 stop=66.7% mfe=0.88 |

## (d) What would ship (TEST numbers; filter + management selected on TRAIN)

| signal | tf | default TEST | mgmt-only TEST | best filter+mgmt | best TEST | verdict |
|---|---|---|---|---|---|---|
| rsi_rejection_short | 1h | n=107 prof=49.5% [40.2–58.9] net=-0.077 gross=-0.029 PF=0.82 stop=37.4% mfe=0.90 | n/a | session=other + T1=0.75 stop×1.0 T2=default trail=on | n=42 prof=52.4% [37.7–66.6] net=+0.029 gross=+0.071 PF=1.08 stop=28.6% mfe=0.89 | **NO (default NO; train-selected NO)** |
| liquidity_sweep_long | 1h | n=92 prof=57.6% [47.4–67.2] net=-0.094 gross=-0.010 PF=0.79 stop=41.3% mfe=0.94 | n/a | weekend=weekend + T1=0.75 stop×1.0 T2=default trail=on | n=11 prof=63.6% [35.4–84.8] net=-0.064 gross=+0.021 PF=0.84 stop=36.4% mfe=0.91 | **NO (default NO; train-selected NO)** |
| rsi_bounce_long | 4h | n=24 prof=70.8% [50.8–85.1] net=+0.191 gross=+0.224 PF=1.97 stop=16.7% mfe=0.80 | n/a | none | n/a | **CANDIDATE (default CANDIDATE; train-selected NO)** |
| trend_pullback_short | 4h | n=22 prof=45.5% [26.9–65.3] net=+0.077 gross=+0.136 PF=1.19 stop=36.4% mfe=1.09 | n/a | none | n/a | **NO (default NO; train-selected NO)** |
| failed_breakout_short | 4h | n=17 prof=64.7% [41.3–82.7] net=+0.300 gross=+0.330 PF=1.92 stop=29.4% mfe=1.20 | n=17 prof=76.5% [52.7–90.4] net=+0.163 gross=+0.197 PF=1.66 stop=23.5% mfe=0.95 | confluence3=0-1 + T1=0.5 stop×0.75 T2=1.5 trail=off | n=17 prof=76.5% [52.7–90.4] net=+0.163 gross=+0.197 PF=1.66 stop=23.5% mfe=0.95 | **NO (default NO; train-selected NO)** |
| rsi_rejection_short | 4h | n=13 prof=61.5% [35.5–82.3] net=-0.035 gross=-0.005 PF=0.90 stop=30.8% mfe=0.73 | n/a | none | n/a | **NO (default NO; train-selected NO)** |
| range_reversion_long | 4h | n=5 prof=40.0% [11.8–76.9] net=-0.351 gross=-0.270 PF=0.47 stop=60.0% mfe=0.74 | n=5 prof=40.0% [11.8–76.9] net=-0.556 gross=-0.470 PF=0.15 stop=60.0% mfe=0.52 | none | n/a | **NO (default NO; train-selected NO)** |
| range_reversion_short | 4h | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.256 PF=1.72 stop=25.0% mfe=1.00 | n/a | none | n/a | **NO (default NO; train-selected NO)** |

Runtime: 8s. Config knobs (getattr defaults): UB_DEDUP_DAYS, UB_MIN_HISTORY_DAYS, UB_DEFAULT_T1_R, UB_SHIP_PROFITABLE_PCT, UB_CANDIDATE_PROFITABLE_PCT, UB_MIN_TEST_N, UB_SHIP_MIN_N.