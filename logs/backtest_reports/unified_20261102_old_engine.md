# Unified backtest — 20261102

Universe: 30 symbols (BTCUSDT, ADAUSDT, XRPUSDT, SOLUSDT, ETHUSDT, DOGEUSDT, SUIUSDT, XLMUSDT, ENAUSDT, HBARUSDT, TRXUSDT, NEARUSDT, OPUSDT, ARBUSDT, INJUSDT, 1000PEPEUSDT, PUMPFUNUSDT, FARTCOINUSDT, WLDUSDT, ONDOUSDT, ZECUSDT, XPLUSDT, 1000BONKUSDT, CASHCATUSDT, STRKUSDT, AKEUSDT, USELESSUSDT, SANDUSDT, PENGUUSDT, USUSDT); days=180; trades=2151; window 4h→192×15m, 1h→96×15m; entry per ENTRY_MODEL (below); T1=0.75R partial 50%, BE after T1, +0.3R trail after 1R MFE; costs per config (taker 0.055% + slip 0.03% per side; maker 0.020%). **Entry model: limit_open** (limit at next open ∓ 0.0×ATR, wait 2 bars; 2151/2239 signals filled, 88 unfilled dropped).

Metric: **profitable%** = net-of-cost blended R > 0. Bar: SHIP ≥70% & net>0 & n≥30 on TEST; CANDIDATE ≥60%.

## (a) Per signal × tf — default config

| signal | tf | tier | ALL | TRAIN (60%) | TEST (40%) |
|---|---|---|---|---|---|
| liquidity_sweep_long | 1h | watch | n=955 prof=51.9% [48.8–55.1] net=-0.160 gross=-0.083 PF=0.69 stop=46.5% mfe=0.93 | n=573 prof=54.3% [50.2–58.3] net=-0.131 gross=-0.047 PF=0.74 stop=44.7% mfe=0.96 | n=382 prof=48.4% [43.5–53.4] net=-0.204 gross=-0.137 PF=0.62 stop=49.2% mfe=0.90 |
| trend_pullback_short | 4h | watch | n=476 prof=56.1% [51.6–60.5] net=-0.073 gross=-0.033 PF=0.82 stop=37.4% mfe=0.83 | n=285 prof=58.2% [52.4–63.8] net=-0.040 gross=+0.002 PF=0.90 stop=34.7% mfe=0.84 | n=191 prof=52.9% [45.8–59.8] net=-0.124 gross=-0.084 PF=0.72 stop=41.4% mfe=0.82 |
| failed_breakout_short | 4h | watch | n=341 prof=55.1% [49.8–60.3] net=-0.044 gross=-0.006 PF=0.90 stop=41.9% mfe=0.93 | n=204 prof=49.5% [42.7–56.3] net=-0.159 gross=-0.116 PF=0.69 stop=47.5% mfe=0.85 | n=137 prof=63.5% [55.2–71.1] net=+0.127 gross=+0.157 PF=1.36 stop=33.6% mfe=1.05 |
| rsi_bounce_long | 4h | watch | n=275 prof=52.4% [46.5–58.2] net=-0.074 gross=-0.044 PF=0.80 stop=29.8% mfe=0.71 | n=165 prof=53.9% [46.3–61.4] net=-0.076 gross=-0.045 PF=0.80 stop=30.9% mfe=0.72 | n=110 prof=50.0% [40.8–59.2] net=-0.071 gross=-0.042 PF=0.79 stop=28.2% mfe=0.71 |
| range_reversion_short | 4h | watch | n=45 prof=75.6% [61.3–85.8] net=+0.250 gross=+0.296 PF=1.96 stop=24.4% mfe=1.06 | n=27 prof=77.8% [59.2–89.4] net=+0.257 gross=+0.308 PF=2.08 stop=22.2% mfe=1.05 | n=18 prof=72.2% [49.1–87.5] net=+0.240 gross=+0.276 PF=1.82 stop=27.8% mfe=1.07 |
| range_reversion_long | 4h | watch | n=36 prof=50.0% [34.5–65.5] net=-0.220 gross=-0.158 PF=0.59 stop=50.0% mfe=0.82 | n=21 prof=52.4% [32.4–71.7] net=-0.238 gross=-0.173 PF=0.53 stop=47.6% mfe=0.78 | n=15 prof=46.7% [24.8–69.9] net=-0.194 gross=-0.138 PF=0.66 stop=53.3% mfe=0.87 |
| funding_squeeze_long | 4h | watch | n=15 prof=60.0% [35.7–80.2] net=+0.177 gross=+0.213 PF=1.52 stop=26.7% mfe=0.94 | n=9 prof=77.8% [45.3–93.7] net=+0.552 gross=+0.586 PF=3.35 stop=22.2% mfe=1.28 | n=6 prof=33.3% [9.7–70.0] net=-0.386 gross=-0.347 PF=0.22 stop=33.3% mfe=0.43 |
| funding_squeeze_short | 4h | watch | n=8 prof=50.0% [21.5–78.5] net=-0.141 gross=-0.125 PF=0.67 stop=37.5% mfe=0.70 | n=4 prof=25.0% [4.6–69.9] net=-0.498 gross=-0.475 PF=0.15 stop=50.0% mfe=0.52 | n=4 prof=75.0% [30.1–95.4] net=+0.217 gross=+0.226 PF=1.86 stop=25.0% mfe=0.88 |

Total filter cuts tested across signals: 361.

### liquidity_sweep_long (1h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-05 | 129 | 55.0 | -0.149 |
| 2026-06 | 151 | 45.7 | -0.259 |
| 2026-07 | 164 | 62.2 | -0.008 |
| 2026-08 | 161 | 47.2 | -0.227 |
| 2026-09 | 162 | 50.0 | -0.170 |
| 2026-10 | 180 | 51.7 | -0.156 |
| 2026-11 | 8 | 50.0 | -0.116 |

**Filter study** (52 cuts tested — expect ~2.6 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=354 prof=50.3% [45.1–55.5] net=-0.207 gross=-0.124 PF=0.62 stop=49.4% mfe=0.91 | n=164 prof=54.3% [46.6–61.7] net=-0.082 gross=-0.009 PF=0.82 stop=42.1% mfe=1.00 |  |
| btc_aligned | yes | n=219 prof=60.7% [54.1–67.0] net=-0.008 gross=+0.079 PF=0.98 stop=37.0% mfe=1.03 | n=218 prof=44.0% [37.6–50.7] net=-0.295 gross=-0.233 PF=0.50 stop=54.6% mfe=0.82 |  |
| confluence3 | 0-1 | n=363 prof=52.9% [47.8–58.0] net=-0.176 gross=-0.090 PF=0.66 stop=46.8% mfe=0.93 | n=168 prof=44.6% [37.3–52.2] net=-0.255 gross=-0.183 PF=0.56 stop=53.6% mfe=0.88 |  |
| confluence3 | 2-3 | n=210 prof=56.7% [49.9–63.2] net=-0.052 gross=+0.028 PF=0.88 stop=41.0% mfe=1.01 | n=214 prof=51.4% [44.7–58.0] net=-0.163 gross=-0.101 PF=0.67 stop=45.8% mfe=0.92 |  |
| risk_pct | 2-4% | n=112 prof=58.9% [49.7–67.6] net=-0.004 gross=+0.031 PF=0.99 stop=41.1% mfe=1.00 | n=94 prof=40.4% [31.1–50.5] net=-0.315 gross=-0.279 PF=0.47 stop=56.4% mfe=0.79 |  |
| risk_pct | 4-8% | n=27 prof=51.9% [34.0–69.3] net=-0.154 gross=-0.137 PF=0.69 stop=48.1% mfe=0.82 | n=25 prof=48.0% [30.0–66.5] net=-0.096 gross=-0.077 PF=0.81 stop=48.0% mfe=0.90 |  |
| risk_pct | <2% | n=425 prof=52.9% [48.2–57.6] net=-0.173 gross=-0.070 PF=0.67 stop=46.4% mfe=0.96 | n=251 prof=51.4% [45.2–57.5] net=-0.183 gross=-0.097 PF=0.65 stop=47.8% mfe=0.95 |  |
| risk_pct | >8% | n=9 prof=66.7% [35.4–87.9] net=+0.367 gross=+0.374 PF=3.86 stop=0.0% mfe=0.89 | n=12 prof=50.0% [25.4–74.6] net=+0.012 gross=+0.019 PF=1.04 stop=25.0% mfe=0.75 |  |
| hour | 00-08 | n=167 prof=63.5% [55.9–70.4] net=+0.018 gross=+0.099 PF=1.05 stop=33.5% mfe=1.02 | n=93 prof=50.5% [40.6–60.5] net=-0.159 gross=-0.077 PF=0.69 stop=47.3% mfe=0.97 |  |
| hour | 08-16 | n=233 prof=48.9% [42.6–55.3] net=-0.228 gross=-0.143 PF=0.59 stop=50.6% mfe=0.91 | n=152 prof=44.1% [36.4–52.0] net=-0.343 gross=-0.277 PF=0.42 stop=55.3% mfe=0.80 |  |
| hour | 16-24 | n=173 prof=52.6% [45.2–59.9] net=-0.144 gross=-0.058 PF=0.73 stop=47.4% mfe=0.96 | n=137 prof=51.8% [43.5–60.0] net=-0.079 gross=-0.022 PF=0.83 stop=43.8% mfe=0.96 |  |
| weekend | weekday | n=416 prof=54.6% [49.8–59.3] net=-0.150 gross=-0.068 PF=0.70 stop=45.4% mfe=0.93 | n=295 prof=44.1% [38.5–49.8] net=-0.293 gross=-0.226 PF=0.49 stop=52.9% mfe=0.81 |  |
| weekend | weekend | n=157 prof=53.5% [45.7–61.1] net=-0.079 gross=+0.009 PF=0.84 stop=42.7% mfe=1.02 | n=87 prof=63.2% [52.7–72.6] net=+0.099 gross=+0.167 PF=1.25 stop=36.8% mfe=1.19 |  |
| adx | 20-30 | n=219 prof=57.1% [50.5–63.5] net=-0.074 gross=+0.015 PF=0.84 stop=42.5% mfe=1.01 | n=143 prof=55.2% [47.1–63.2] net=-0.064 gross=+0.006 PF=0.86 stop=40.6% mfe=0.99 |  |
| adx | <20 | n=247 prof=52.2% [46.0–58.4] net=-0.196 gross=-0.109 PF=0.63 stop=47.4% mfe=0.91 | n=142 prof=39.4% [31.8–47.7] net=-0.389 gross=-0.325 PF=0.39 stop=59.2% mfe=0.76 |  |
| adx | >30 | n=107 prof=53.3% [43.9–62.4] net=-0.095 gross=-0.028 PF=0.80 stop=43.0% mfe=0.96 | n=97 prof=51.5% [41.7–61.2] net=-0.139 gross=-0.071 PF=0.73 stop=47.4% mfe=0.96 |  |
| vol_spike | <1.5 | n=286 prof=49.0% [43.2–54.7] net=-0.231 gross=-0.137 PF=0.59 stop=50.7% mfe=0.92 | n=187 prof=49.2% [42.1–56.3] net=-0.240 gross=-0.167 PF=0.56 stop=50.8% mfe=0.90 |  |
| vol_spike | >=1.5 | n=287 prof=59.6% [53.8–65.1] net=-0.031 gross=+0.043 PF=0.93 stop=38.7% mfe=1.00 | n=195 prof=47.7% [40.8–54.7] net=-0.168 gross=-0.108 PF=0.67 stop=47.7% mfe=0.90 |  |
| ema50_dist_atr | -0.5..0.5 | n=91 prof=51.6% [41.5–61.6] net=-0.188 gross=-0.100 PF=0.63 stop=46.2% mfe=0.90 | n=57 prof=49.1% [36.6–61.7] net=-0.147 gross=-0.086 PF=0.72 stop=49.1% mfe=0.92 |  |
| ema50_dist_atr | -2..-0.5 | n=273 prof=55.3% [49.4–61.1] net=-0.143 gross=-0.053 PF=0.71 stop=44.3% mfe=0.97 | n=182 prof=43.4% [36.4–50.7] net=-0.306 gross=-0.235 PF=0.47 stop=52.7% mfe=0.81 |  |
| ema50_dist_atr | 0.5..2 | n=21 prof=66.7% [45.4–82.8] net=+0.204 gross=+0.257 PF=1.69 stop=23.8% mfe=1.13 | n=15 prof=53.3% [30.1–75.2] net=-0.144 gross=-0.093 PF=0.71 stop=46.7% mfe=0.97 |  |
| ema50_dist_atr | <-2 | n=188 prof=52.7% [45.5–59.7] net=-0.123 gross=-0.045 PF=0.76 stop=46.8% mfe=0.95 | n=128 prof=54.7% [46.1–63.0] net=-0.090 gross=-0.025 PF=0.81 stop=44.5% mfe=1.01 |  |
| symbol_group | major | n=296 prof=54.4% [48.7–60.0] net=-0.159 gross=-0.049 PF=0.68 stop=44.3% mfe=0.96 | n=186 prof=53.2% [46.1–60.3] net=-0.126 gross=-0.036 PF=0.75 stop=45.2% mfe=0.98 |  |
| symbol_group | other | n=277 prof=54.2% [48.3–59.9] net=-0.100 gross=-0.044 PF=0.79 stop=45.1% mfe=0.95 | n=196 prof=43.9% [37.1–50.9] net=-0.277 gross=-0.232 PF=0.51 stop=53.1% mfe=0.82 |  |
| funding | -0.01..0.005% | n=237 prof=50.2% [43.9–56.5] net=-0.210 gross=-0.112 PF=0.61 stop=48.9% mfe=0.92 | n=129 prof=49.6% [41.1–58.1] net=-0.222 gross=-0.144 PF=0.58 stop=48.8% mfe=0.91 |  |
| funding | 0.005..0.02% | n=258 prof=57.0% [50.9–62.9] net=-0.071 gross=-0.001 PF=0.85 stop=41.9% mfe=0.99 | n=216 prof=45.4% [38.9–52.0] net=-0.249 gross=-0.193 PF=0.56 stop=52.8% mfe=0.86 |  |
| funding | 0.02..0.05% | n=7 prof=42.9% [15.8–75.0] net=-0.392 gross=-0.368 PF=0.33 stop=57.1% mfe=0.69 | n=1 prof=100.0% [20.7–100.0] net=+1.366 gross=+1.375 PF=inf stop=0.0% mfe=2.07 |  |
| funding | <-0.01% | n=69 prof=59.4% [47.6–70.2] net=-0.050 gross=+0.044 PF=0.89 stop=39.1% mfe=1.02 | n=33 prof=60.6% [43.7–75.3] net=+0.073 gross=+0.176 PF=1.21 stop=30.3% mfe=1.04 |  |
| funding | >0.05% | n=2 prof=50.0% [9.5–90.5] net=-0.247 gross=-0.195 PF=0.55 stop=50.0% mfe=0.47 | n=3 prof=66.7% [20.8–93.9] net=+0.288 gross=+0.300 PF=1.85 stop=33.3% mfe=1.16 |  |
| funding_side | fading_crowd | n=133 prof=54.1% [45.7–62.4] net=-0.144 gross=-0.053 PF=0.71 stop=45.1% mfe=0.95 | n=56 prof=53.6% [40.7–66.0] net=-0.080 gross=+0.004 PF=0.82 stop=39.3% mfe=0.96 |  |
| funding_side | neutral | n=173 prof=50.9% [43.5–58.2] net=-0.198 gross=-0.095 PF=0.63 stop=48.0% mfe=0.94 | n=106 prof=50.9% [41.6–60.3] net=-0.206 gross=-0.122 PF=0.61 stop=48.1% mfe=0.92 |  |
| funding_side | with_crowd | n=267 prof=56.6% [50.6–62.4] net=-0.081 gross=-0.012 PF=0.83 stop=42.3% mfe=0.98 | n=220 prof=45.9% [39.5–52.5] net=-0.234 gross=-0.179 PF=0.58 stop=52.3% mfe=0.87 |  |
| funding_z | -1..1 | n=364 prof=54.1% [49.0–59.2] net=-0.107 gross=-0.026 PF=0.78 stop=44.8% mfe=0.98 | n=274 prof=50.7% [44.8–56.6] net=-0.173 gross=-0.108 PF=0.67 stop=47.8% mfe=0.91 |  |
| funding_z | 1..2 | n=36 prof=58.3% [42.2–72.9] net=-0.098 gross=-0.005 PF=0.79 stop=41.7% mfe=1.00 | n=19 prof=42.1% [23.1–63.7] net=-0.317 gross=-0.232 PF=0.50 stop=57.9% mfe=0.91 |  |
| funding_z | <-1 | n=121 prof=52.9% [44.0–61.6] net=-0.196 gross=-0.100 PF=0.61 stop=45.5% mfe=0.89 | n=73 prof=46.6% [35.6–57.9] net=-0.202 gross=-0.127 PF=0.61 stop=46.6% mfe=0.93 |  |
| funding_z | >2 | n=5 prof=40.0% [11.8–76.9] net=-0.458 gross=-0.403 PF=0.30 stop=60.0% mfe=0.49 | n=1 prof=100.0% [20.7–100.0] net=+0.514 gross=+0.525 PF=inf stop=0.0% mfe=1.34 |  |
| funding_z | na | n=47 prof=57.4% [43.3–70.5] net=-0.137 gross=-0.062 PF=0.71 stop=42.6% mfe=0.99 | n=15 prof=20.0% [7.0–45.2] net=-0.682 gross=-0.638 PF=0.18 stop=80.0% mfe=0.57 |  |
| oi_divergence | down_down | n=227 prof=53.7% [47.2–60.1] net=-0.138 gross=-0.064 PF=0.73 stop=45.8% mfe=0.94 | n=179 prof=46.9% [39.8–54.2] net=-0.204 gross=-0.148 PF=0.62 stop=50.3% mfe=0.90 |  |
| oi_divergence | down_up | n=146 prof=53.4% [45.3–61.3] net=-0.139 gross=-0.062 PF=0.73 stop=46.6% mfe=0.94 | n=93 prof=57.0% [46.8–66.6] net=-0.069 gross=-0.008 PF=0.85 stop=41.9% mfe=0.98 |  |
| oi_divergence | flat | n=152 prof=55.3% [47.3–62.9] net=-0.163 gross=-0.049 PF=0.67 stop=43.4% mfe=0.96 | n=86 prof=44.2% [34.2–54.7] net=-0.298 gross=-0.204 PF=0.49 stop=53.5% mfe=0.86 |  |
| oi_divergence | up_down | n=23 prof=60.9% [40.8–77.8] net=+0.103 gross=+0.167 PF=1.24 stop=39.1% mfe=1.26 | n=12 prof=41.7% [19.3–68.0] net=-0.325 gross=-0.250 PF=0.42 stop=50.0% mfe=0.74 |  |
| oi_divergence | up_up | n=25 prof=52.0% [33.5–70.0] net=-0.038 gross=+0.020 PF=0.91 stop=36.0% mfe=0.97 | n=12 prof=41.7% [19.3–68.0] net=-0.434 gross=-0.377 PF=0.30 stop=58.3% mfe=0.77 |  |
| oi_chg_24h | -5..0% | n=243 prof=57.2% [50.9–63.3] net=-0.084 gross=-0.000 PF=0.82 stop=42.4% mfe=1.00 | n=176 prof=48.9% [41.6–56.2] net=-0.182 gross=-0.111 PF=0.65 stop=47.2% mfe=0.90 |  |
| oi_chg_24h | 0..5% | n=197 prof=52.8% [45.8–59.6] net=-0.177 gross=-0.076 PF=0.66 stop=46.2% mfe=0.93 | n=118 prof=55.1% [46.1–63.8] net=-0.117 gross=-0.043 PF=0.76 stop=44.1% mfe=0.97 |  |
| oi_chg_24h | <-5% | n=80 prof=43.8% [33.4–54.7] net=-0.256 gross=-0.197 PF=0.57 stop=55.0% mfe=0.86 | n=60 prof=36.7% [25.6–49.3] net=-0.400 gross=-0.351 PF=0.39 stop=61.7% mfe=0.76 |  |
| oi_chg_24h | >5% | n=53 prof=62.3% [48.8–74.1] net=+0.018 gross=+0.079 PF=1.05 stop=34.0% mfe=1.01 | n=28 prof=42.9% [26.5–60.9] net=-0.286 gross=-0.233 PF=0.53 stop=57.1% mfe=0.88 |  |
| settlement_bar | other | n=489 prof=55.6% [51.2–60.0] net=-0.110 gross=-0.028 PF=0.77 stop=43.4% mfe=0.97 | n=346 prof=47.7% [42.5–52.9] net=-0.228 gross=-0.161 PF=0.58 stop=49.7% mfe=0.87 |  |
| settlement_bar | settlement | n=84 prof=46.4% [36.2–57.0] net=-0.249 gross=-0.154 PF=0.57 stop=52.4% mfe=0.88 | n=36 prof=55.6% [39.6–70.5] net=+0.029 gross=+0.099 PF=1.06 stop=44.4% mfe=1.15 |  |
| session | 03-04 | n=40 prof=65.0% [49.5–77.9] net=-0.030 gross=+0.086 PF=0.91 stop=30.0% mfe=1.03 | n=34 prof=44.1% [28.9–60.5] net=-0.341 gross=-0.261 PF=0.44 stop=55.9% mfe=0.85 |  |
| session | 08-16 | n=233 prof=48.9% [42.6–55.3] net=-0.228 gross=-0.143 PF=0.59 stop=50.6% mfe=0.91 | n=152 prof=44.1% [36.4–52.0] net=-0.343 gross=-0.277 PF=0.42 stop=55.3% mfe=0.80 |  |
| session | 21-23 | n=64 prof=45.3% [33.7–57.4] net=-0.217 gross=-0.134 PF=0.64 stop=54.7% mfe=0.92 | n=34 prof=47.1% [31.5–63.3] net=-0.132 gross=-0.074 PF=0.77 stop=52.9% mfe=0.97 |  |
| session | other | n=236 prof=60.2% [53.8–66.2] net=-0.029 gross=+0.050 PF=0.93 stop=38.6% mfe=1.00 | n=162 prof=53.7% [46.0–61.2] net=-0.059 gross=+0.007 PF=0.87 stop=41.4% mfe=0.98 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

### trend_pullback_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-05 | 66 | 57.6 | +0.006 |
| 2026-06 | 92 | 59.8 | -0.053 |
| 2026-07 | 77 | 51.9 | -0.142 |
| 2026-08 | 71 | 57.7 | -0.059 |
| 2026-09 | 44 | 45.5 | -0.298 |
| 2026-10 | 115 | 58.3 | -0.023 |
| 2026-11 | 11 | 54.5 | +0.055 |

**Filter study** (49 cuts tested — expect ~2.5 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=49 prof=59.2% [45.2–71.8] net=-0.039 gross=+0.006 PF=0.90 stop=38.8% mfe=0.89 | n=44 prof=40.9% [27.7–55.6] net=-0.291 gross=-0.249 PF=0.45 stop=50.0% mfe=0.69 |  |
| btc_aligned | yes | n=236 prof=58.1% [51.7–64.2] net=-0.040 gross=+0.001 PF=0.90 stop=33.9% mfe=0.83 | n=147 prof=56.5% [48.4–64.2] net=-0.074 gross=-0.035 PF=0.83 stop=38.8% mfe=0.86 |  |
| confluence3 | 0-1 | n=16 prof=62.5% [38.6–81.5] net=+0.096 gross=+0.125 PF=1.29 stop=31.2% mfe=0.98 | n=44 prof=50.0% [35.8–64.2] net=-0.118 gross=-0.083 PF=0.75 stop=43.2% mfe=0.90 |  |
| confluence3 | 2-3 | n=269 prof=58.0% [52.0–63.7] net=-0.048 gross=-0.005 PF=0.88 stop=34.9% mfe=0.83 | n=147 prof=53.7% [45.7–61.6] net=-0.125 gross=-0.085 PF=0.71 stop=40.8% mfe=0.80 |  |
| risk_pct | 2-4% | n=141 prof=56.0% [47.8–64.0] net=-0.070 gross=-0.028 PF=0.83 stop=36.9% mfe=0.82 | n=72 prof=50.0% [38.7–61.3] net=-0.229 gross=-0.188 PF=0.54 stop=47.2% mfe=0.80 |  |
| risk_pct | 4-8% | n=90 prof=58.9% [48.6–68.5] net=-0.075 gross=-0.051 PF=0.80 stop=33.3% mfe=0.73 | n=77 prof=57.1% [46.0–67.6] net=-0.032 gross=-0.009 PF=0.92 stop=37.7% mfe=0.82 |  |
| risk_pct | <2% | n=46 prof=69.6% [55.2–80.9] net=+0.223 gross=+0.303 PF=1.75 stop=26.1% mfe=1.20 | n=28 prof=46.4% [29.5–64.2] net=-0.161 gross=-0.067 PF=0.68 stop=42.9% mfe=0.89 |  |
| risk_pct | >8% | n=8 prof=25.0% [7.1–59.1] net=-0.622 gross=-0.609 PF=0.15 stop=62.5% mfe=0.33 | n=14 prof=57.1% [32.6–78.6] net=-0.011 gross=+0.002 PF=0.97 stop=28.6% mfe=0.75 |  |
| hour | 00-08 | n=112 prof=61.6% [52.4–70.1] net=-0.003 gross=+0.036 PF=0.99 stop=30.4% mfe=0.83 | n=71 prof=54.9% [43.4–66.0] net=-0.180 gross=-0.138 PF=0.62 stop=45.1% mfe=0.78 |  |
| hour | 08-16 | n=102 prof=60.8% [51.1–69.7] net=+0.031 gross=+0.074 PF=1.09 stop=32.4% mfe=0.88 | n=53 prof=45.3% [32.7–58.5] net=-0.204 gross=-0.162 PF=0.57 stop=43.4% mfe=0.75 |  |
| hour | 16-24 | n=71 prof=49.3% [38.0–60.7] net=-0.199 gross=-0.156 PF=0.58 stop=45.1% mfe=0.78 | n=67 prof=56.7% [44.8–67.9] net=-0.001 gross=+0.035 PF=1.00 stop=35.8% mfe=0.92 |  |
| weekend | weekday | n=197 prof=54.8% [47.8–61.6] net=-0.069 gross=-0.031 PF=0.83 stop=38.1% mfe=0.83 | n=131 prof=51.9% [43.4–60.3] net=-0.142 gross=-0.103 PF=0.70 stop=44.3% mfe=0.86 |  |
| weekend | weekend | n=88 prof=65.9% [55.5–75.0] net=+0.027 gross=+0.076 PF=1.09 stop=27.3% mfe=0.86 | n=60 prof=55.0% [42.5–66.9] net=-0.084 gross=-0.043 PF=0.78 stop=35.0% mfe=0.73 |  |
| adx | 20-30 | n=113 prof=61.1% [51.8–69.5] net=+0.016 gross=+0.059 PF=1.04 stop=33.6% mfe=0.87 | n=92 prof=53.3% [43.1–63.1] net=-0.094 gross=-0.056 PF=0.78 stop=39.1% mfe=0.88 |  |
| adx | <20 | n=73 prof=52.1% [40.8–63.1] net=-0.106 gross=-0.064 PF=0.76 stop=41.1% mfe=0.81 | n=45 prof=57.8% [43.3–71.0] net=-0.039 gross=+0.001 PF=0.90 stop=35.6% mfe=0.77 |  |
| adx | >30 | n=99 prof=59.6% [49.7–68.7] net=-0.054 gross=-0.015 PF=0.85 stop=31.3% mfe=0.81 | n=54 prof=48.1% [35.4–61.1] net=-0.245 gross=-0.204 PF=0.53 stop=50.0% mfe=0.76 |  |
| vol_spike | <1.5 | n=252 prof=60.7% [54.6–66.5] net=+0.006 gross=+0.048 PF=1.02 stop=31.3% mfe=0.85 | n=160 prof=51.9% [44.2–59.5] net=-0.158 gross=-0.119 PF=0.65 stop=41.9% mfe=0.77 |  |
| vol_spike | >=1.5 | n=33 prof=39.4% [24.7–56.3] net=-0.391 gross=-0.352 PF=0.38 stop=60.6% mfe=0.73 | n=31 prof=58.1% [40.8–73.6] net=+0.055 gross=+0.098 PF=1.13 stop=38.7% mfe=1.07 |  |
| ema50_dist_atr | -0.5..0.5 | n=45 prof=57.8% [43.3–71.0] net=-0.059 gross=-0.011 PF=0.85 stop=37.8% mfe=0.84 | n=42 prof=54.8% [39.9–68.8] net=-0.072 gross=-0.024 PF=0.82 stop=35.7% mfe=0.86 |  |
| ema50_dist_atr | -2..-0.5 | n=201 prof=59.7% [52.8–66.2] net=-0.015 gross=+0.025 PF=0.96 stop=33.3% mfe=0.85 | n=127 prof=48.8% [40.3–57.4] net=-0.176 gross=-0.139 PF=0.64 stop=45.7% mfe=0.81 |  |
| ema50_dist_atr | <-2 | n=39 prof=51.3% [36.2–66.1] net=-0.146 gross=-0.105 PF=0.65 stop=38.5% mfe=0.78 | n=22 prof=72.7% [51.8–86.8] net=+0.081 gross=+0.116 PF=1.28 stop=27.3% mfe=0.78 |  |
| symbol_group | major | n=163 prof=62.6% [54.9–69.6] net=+0.061 gross=+0.112 PF=1.19 stop=30.1% mfe=0.94 | n=101 prof=53.5% [43.8–62.9] net=-0.135 gross=-0.082 PF=0.70 stop=41.6% mfe=0.83 |  |
| symbol_group | other | n=122 prof=52.5% [43.7–61.1] net=-0.174 gross=-0.145 PF=0.61 stop=41.0% mfe=0.70 | n=90 prof=52.2% [42.0–62.2] net=-0.110 gross=-0.086 PF=0.75 stop=41.1% mfe=0.80 |  |
| funding | -0.01..0.005% | n=100 prof=68.0% [58.3–76.3] net=+0.102 gross=+0.149 PF=1.35 stop=27.0% mfe=0.94 | n=57 prof=61.4% [48.4–72.9] net=+0.064 gross=+0.108 PF=1.18 stop=31.6% mfe=0.99 | CANDIDATE |
| funding | 0.005..0.02% | n=157 prof=53.5% [45.7–61.1] net=-0.088 gross=-0.051 PF=0.79 stop=38.2% mfe=0.80 | n=120 prof=50.0% [41.2–58.8] net=-0.194 gross=-0.160 PF=0.60 stop=45.8% mfe=0.77 |  |
| funding | 0.02..0.05% | n=3 prof=33.3% [6.1–79.2] net=-0.559 gross=-0.542 PF=0.18 stop=66.7% mfe=0.40 | n=4 prof=50.0% [15.0–85.0] net=-0.247 gross=-0.233 PF=0.51 stop=50.0% mfe=0.64 |  |
| funding | <-0.01% | n=25 prof=52.0% [33.5–70.0] net=-0.240 gross=-0.190 PF=0.49 stop=40.0% mfe=0.71 | n=10 prof=40.0% [16.8–68.7] net=-0.303 gross=-0.207 PF=0.34 stop=40.0% mfe=0.55 |  |
| funding_side | fading_crowd | n=160 prof=53.1% [45.4–60.7] net=-0.097 gross=-0.060 PF=0.77 stop=38.8% mfe=0.80 | n=124 prof=50.0% [41.3–58.7] net=-0.196 gross=-0.163 PF=0.60 stop=46.0% mfe=0.76 |  |
| funding_side | neutral | n=89 prof=67.4% [57.1–76.3] net=+0.091 gross=+0.140 PF=1.31 stop=27.0% mfe=0.92 | n=48 prof=64.6% [50.4–76.6] net=+0.114 gross=+0.153 PF=1.38 stop=27.1% mfe=1.02 | CANDIDATE |
| funding_side | with_crowd | n=36 prof=58.3% [42.2–72.9] net=-0.108 gross=-0.064 PF=0.74 stop=36.1% mfe=0.82 | n=19 prof=42.1% [23.1–63.7] net=-0.254 gross=-0.171 PF=0.52 stop=47.4% mfe=0.69 |  |
| funding_z | -1..1 | n=200 prof=61.0% [54.1–67.5] net=+0.024 gross=+0.065 PF=1.07 stop=33.0% mfe=0.90 | n=149 prof=53.0% [45.0–60.9] net=-0.130 gross=-0.092 PF=0.71 stop=41.6% mfe=0.83 |  |
| funding_z | 1..2 | n=43 prof=48.8% [34.6–63.2] net=-0.201 gross=-0.156 PF=0.54 stop=39.5% mfe=0.69 | n=18 prof=66.7% [43.7–83.7] net=+0.084 gross=+0.126 PF=1.25 stop=33.3% mfe=0.87 |  |
| funding_z | <-1 | n=28 prof=57.1% [39.1–73.5] net=-0.181 gross=-0.137 PF=0.57 stop=39.3% mfe=0.67 | n=15 prof=46.7% [24.8–69.9] net=-0.158 gross=-0.094 PF=0.69 stop=46.7% mfe=0.87 |  |
| funding_z | >2 | n=4 prof=25.0% [4.6–69.9] net=-0.478 gross=-0.416 PF=0.16 stop=50.0% mfe=0.50 | n=2 prof=50.0% [9.5–90.5] net=-0.239 gross=-0.228 PF=0.53 stop=50.0% mfe=0.54 |  |
| funding_z | na | n=10 prof=60.0% [31.3–83.2] net=-0.044 gross=-0.022 PF=0.87 stop=30.0% mfe=0.76 | n=7 prof=28.6% [8.2–64.1] net=-0.415 gross=-0.396 PF=0.19 stop=42.9% mfe=0.42 |  |
| oi_divergence | down_down | n=30 prof=53.3% [36.1–69.8] net=-0.117 gross=-0.086 PF=0.72 stop=40.0% mfe=0.73 | n=13 prof=61.5% [35.5–82.3] net=+0.004 gross=+0.030 PF=1.01 stop=38.5% mfe=0.92 |  |
| oi_divergence | down_up | n=19 prof=47.4% [27.3–68.3] net=-0.305 gross=-0.258 PF=0.45 stop=52.6% mfe=0.59 | n=15 prof=46.7% [24.8–69.9] net=-0.140 gross=-0.091 PF=0.68 stop=33.3% mfe=0.75 |  |
| oi_divergence | flat | n=84 prof=66.7% [56.1–75.8] net=+0.059 gross=+0.110 PF=1.18 stop=29.8% mfe=0.90 | n=64 prof=50.0% [38.1–61.9] net=-0.207 gross=-0.158 PF=0.60 stop=48.4% mfe=0.79 |  |
| oi_divergence | up_down | n=75 prof=54.7% [43.4–65.4] net=-0.056 gross=-0.019 PF=0.85 stop=33.3% mfe=0.79 | n=47 prof=57.4% [43.3–70.5] net=-0.035 gross=-0.004 PF=0.91 stop=36.2% mfe=0.91 |  |
| oi_divergence | up_up | n=77 prof=57.1% [46.0–67.6] net=-0.035 gross=+0.003 PF=0.91 stop=35.1% mfe=0.91 | n=52 prof=51.9% [38.7–64.9] net=-0.128 gross=-0.092 PF=0.70 stop=40.4% mfe=0.76 |  |
| oi_chg_24h | -5..0% | n=126 prof=58.7% [50.0–66.9] net=-0.014 gross=+0.028 PF=0.96 stop=34.9% mfe=0.84 | n=89 prof=55.1% [44.7–65.0] net=-0.114 gross=-0.073 PF=0.75 stop=42.7% mfe=0.86 |  |
| oi_chg_24h | 0..5% | n=105 prof=62.9% [53.3–71.5] net=+0.032 gross=+0.077 PF=1.09 stop=31.4% mfe=0.93 | n=77 prof=53.2% [42.2–64.0] net=-0.107 gross=-0.069 PF=0.75 stop=39.0% mfe=0.79 |  |
| oi_chg_24h | <-5% | n=26 prof=53.8% [35.5–71.2] net=-0.114 gross=-0.083 PF=0.68 stop=30.8% mfe=0.62 | n=13 prof=53.8% [29.1–76.8] net=-0.006 gross=+0.022 PF=0.98 stop=30.8% mfe=0.88 |  |
| oi_chg_24h | >5% | n=28 prof=42.9% [26.5–60.9] net=-0.355 gross=-0.318 PF=0.35 stop=50.0% mfe=0.66 | n=12 prof=33.3% [13.8–60.9] net=-0.424 gross=-0.379 PF=0.31 stop=58.3% mfe=0.65 |  |
| settlement_bar | other | n=141 prof=61.7% [53.5–69.3] net=-0.006 gross=+0.040 PF=0.98 stop=31.9% mfe=0.86 | n=77 prof=50.6% [39.7–61.5] net=-0.108 gross=-0.069 PF=0.78 stop=45.5% mfe=0.85 |  |
| settlement_bar | settlement | n=144 prof=54.9% [46.7–62.8] net=-0.073 gross=-0.035 PF=0.82 stop=37.5% mfe=0.81 | n=114 prof=54.4% [45.2–63.2] net=-0.134 gross=-0.094 PF=0.68 stop=38.6% mfe=0.80 |  |
| session | 03-04 | n=49 prof=63.3% [49.3–75.3] net=-0.038 gross=+0.007 PF=0.90 stop=34.7% mfe=0.83 | n=26 prof=53.8% [35.5–71.2] net=-0.122 gross=-0.073 PF=0.75 stop=46.2% mfe=0.79 |  |
| session | 08-16 | n=102 prof=60.8% [51.1–69.7] net=+0.031 gross=+0.074 PF=1.09 stop=32.4% mfe=0.88 | n=53 prof=45.3% [32.7–58.5] net=-0.204 gross=-0.162 PF=0.57 stop=43.4% mfe=0.75 |  |
| session | other | n=134 prof=54.5% [46.0–62.7] net=-0.094 gross=-0.055 PF=0.77 stop=36.6% mfe=0.81 | n=112 prof=56.2% [47.0–65.1] net=-0.086 gross=-0.050 PF=0.80 stop=39.3% mfe=0.86 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- chosen: T1=0.5R, stop×1.5, T2=1.5R, trail=on
- TRAIN chosen: n=285 prof=67.0% [61.4–72.2] net=+0.007 gross=+0.036 PF=1.03 stop=20.4% mfe=0.63
- TEST chosen: n=191 prof=58.1% [51.0–64.9] net=-0.112 gross=-0.085 PF=0.68 stop=29.8% mfe=0.59
- TEST default: n=191 prof=52.9% [45.8–59.8] net=-0.124 gross=-0.084 PF=0.72 stop=41.4% mfe=0.82

### failed_breakout_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-05 | 21 | 33.3 | -0.412 |
| 2026-06 | 51 | 56.9 | +0.014 |
| 2026-07 | 55 | 47.3 | -0.143 |
| 2026-08 | 70 | 48.6 | -0.235 |
| 2026-09 | 98 | 59.2 | -0.000 |
| 2026-10 | 46 | 73.9 | +0.375 |

**Filter study** (51 cuts tested — expect ~2.6 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=119 prof=52.1% [43.2–60.9] net=-0.147 gross=-0.106 PF=0.69 stop=44.5% mfe=0.79 | n=91 prof=60.4% [50.2–69.9] net=+0.066 gross=+0.095 PF=1.18 stop=36.3% mfe=0.97 |  |
| btc_aligned | yes | n=85 prof=45.9% [35.7–56.4] net=-0.176 gross=-0.131 PF=0.68 stop=51.8% mfe=0.94 | n=46 prof=69.6% [55.2–80.9] net=+0.247 gross=+0.281 PF=1.84 stop=28.3% mfe=1.20 |  |
| confluence3 | 0-1 | n=160 prof=48.8% [41.1–56.4] net=-0.206 gross=-0.165 PF=0.60 stop=47.5% mfe=0.77 | n=127 prof=60.6% [51.9–68.7] net=+0.073 gross=+0.102 PF=1.19 stop=36.2% mfe=1.00 |  |
| confluence3 | 2-3 | n=44 prof=52.3% [37.9–66.2] net=+0.011 gross=+0.061 PF=1.02 stop=47.7% mfe=1.12 | n=10 prof=100.0% [72.2–100.0] net=+0.813 gross=+0.865 PF=inf stop=0.0% mfe=1.61 |  |
| risk_pct | 2-4% | n=69 prof=58.0% [46.2–68.9] net=+0.054 gross=+0.089 PF=1.13 stop=39.1% mfe=1.06 | n=38 prof=50.0% [34.8–65.2] net=-0.047 gross=-0.017 PF=0.90 stop=47.4% mfe=1.02 |  |
| risk_pct | 4-8% | n=59 prof=42.4% [30.6–55.1] net=-0.310 gross=-0.289 PF=0.47 stop=57.6% mfe=0.72 | n=59 prof=71.2% [58.6–81.2] net=+0.233 gross=+0.252 PF=1.83 stop=27.1% mfe=1.10 |  |
| risk_pct | <2% | n=37 prof=37.8% [24.1–53.9] net=-0.380 gross=-0.255 PF=0.45 stop=56.8% mfe=0.80 | n=18 prof=83.3% [60.8–94.2] net=+0.434 gross=+0.524 PF=4.34 stop=11.1% mfe=1.33 |  |
| risk_pct | >8% | n=39 prof=56.4% [41.0–70.7] net=-0.098 gross=-0.088 PF=0.75 stop=38.5% mfe=0.72 | n=22 prof=50.0% [30.7–69.3] net=-0.105 gross=-0.095 PF=0.77 stop=45.5% mfe=0.75 |  |
| hour | 00-08 | n=47 prof=48.9% [35.3–62.8] net=-0.172 gross=-0.117 PF=0.68 stop=48.9% mfe=0.87 | n=47 prof=66.0% [51.7–77.8] net=+0.176 gross=+0.208 PF=1.50 stop=34.0% mfe=1.14 |  |
| hour | 08-16 | n=62 prof=56.5% [44.1–68.1] net=-0.170 gross=-0.130 PF=0.63 stop=43.5% mfe=0.78 | n=37 prof=54.1% [38.4–69.0] net=-0.045 gross=-0.012 PF=0.89 stop=37.8% mfe=0.90 |  |
| hour | 16-24 | n=95 prof=45.3% [35.6–55.3] net=-0.146 gross=-0.107 PF=0.73 stop=49.5% mfe=0.88 | n=53 prof=67.9% [54.5–78.9] net=+0.204 gross=+0.231 PF=1.66 stop=30.2% mfe=1.07 |  |
| weekend | weekday | n=159 prof=48.4% [40.8–56.1] net=-0.156 gross=-0.113 PF=0.70 stop=48.4% mfe=0.85 | n=98 prof=63.3% [53.4–72.1] net=+0.133 gross=+0.162 PF=1.37 stop=34.7% mfe=1.07 |  |
| weekend | weekend | n=45 prof=53.3% [39.1–67.1] net=-0.171 gross=-0.127 PF=0.64 stop=44.4% mfe=0.85 | n=39 prof=64.1% [48.4–77.3] net=+0.113 gross=+0.146 PF=1.35 stop=30.8% mfe=0.99 |  |
| adx | 20-30 | n=73 prof=47.9% [36.9–59.2] net=-0.192 gross=-0.155 PF=0.63 stop=47.9% mfe=0.85 | n=47 prof=57.4% [43.3–70.5] net=+0.045 gross=+0.081 PF=1.11 stop=38.3% mfe=1.02 |  |
| adx | <20 | n=54 prof=50.0% [37.1–62.9] net=-0.093 gross=-0.029 PF=0.82 stop=46.3% mfe=0.95 | n=27 prof=66.7% [47.8–81.4] net=+0.192 gross=+0.236 PF=1.60 stop=29.6% mfe=1.19 |  |
| adx | >30 | n=77 prof=50.6% [39.7–61.5] net=-0.174 gross=-0.141 PF=0.65 stop=48.1% mfe=0.78 | n=63 prof=66.7% [54.4–77.1] net=+0.160 gross=+0.180 PF=1.49 stop=31.7% mfe=1.01 |  |
| vol_spike | <1.5 | n=101 prof=52.5% [42.8–61.9] net=-0.095 gross=-0.037 PF=0.81 stop=45.5% mfe=0.96 | n=77 prof=63.6% [52.5–73.5] net=+0.082 gross=+0.117 PF=1.22 stop=35.1% mfe=1.06 |  |
| vol_spike | >=1.5 | n=103 prof=46.6% [37.3–56.2] net=-0.223 gross=-0.194 PF=0.57 stop=49.5% mfe=0.74 | n=60 prof=63.3% [50.7–74.4] net=+0.185 gross=+0.209 PF=1.57 stop=31.7% mfe=1.04 |  |
| ema50_dist_atr | -0.5..0.5 | n=27 prof=59.3% [40.7–75.5] net=+0.170 gross=+0.206 PF=1.40 stop=40.7% mfe=1.21 | n=11 prof=63.6% [35.4–84.8] net=+0.096 gross=+0.126 PF=1.32 stop=27.3% mfe=0.89 |  |
| ema50_dist_atr | -2..-0.5 | n=4 prof=50.0% [15.0–85.0] net=+0.153 gross=+0.188 PF=1.29 stop=50.0% mfe=1.28 | n=5 prof=100.0% [56.6–100.0] net=+1.013 gross=+1.035 PF=inf stop=0.0% mfe=1.91 |  |
| ema50_dist_atr | 0.5..2 | n=86 prof=47.7% [37.4–58.1] net=-0.181 gross=-0.129 PF=0.64 stop=45.3% mfe=0.82 | n=59 prof=62.7% [50.0–73.9] net=+0.109 gross=+0.147 PF=1.31 stop=33.9% mfe=1.06 |  |
| ema50_dist_atr | >2 | n=87 prof=48.3% [38.1–58.6] net=-0.254 gross=-0.218 PF=0.53 stop=51.7% mfe=0.74 | n=62 prof=61.3% [48.8–72.4] net=+0.078 gross=+0.102 PF=1.21 stop=37.1% mfe=1.00 |  |
| symbol_group | major | n=98 prof=41.8% [32.6–51.7] net=-0.319 gross=-0.255 PF=0.48 stop=56.1% mfe=0.73 | n=69 prof=63.8% [52.0–74.1] net=+0.184 gross=+0.224 PF=1.55 stop=31.9% mfe=1.10 |  |
| symbol_group | other | n=106 prof=56.6% [47.1–65.6] net=-0.011 gross=+0.011 PF=0.97 stop=39.6% mfe=0.95 | n=68 prof=63.2% [51.4–73.7] net=+0.070 gross=+0.090 PF=1.19 stop=35.3% mfe=1.00 |  |
| funding | -0.01..0.005% | n=45 prof=37.8% [25.1–52.4] net=-0.355 gross=-0.290 PF=0.46 stop=60.0% mfe=0.80 | n=15 prof=53.3% [30.1–75.2] net=+0.110 gross=+0.168 PF=1.32 stop=33.3% mfe=1.10 |  |
| funding | 0.005..0.02% | n=141 prof=51.8% [43.6–59.9] net=-0.122 gross=-0.084 PF=0.75 stop=45.4% mfe=0.85 | n=116 prof=64.7% [55.6–72.8] net=+0.125 gross=+0.152 PF=1.36 stop=33.6% mfe=1.04 |  |
| funding | 0.02..0.05% | n=6 prof=50.0% [18.8–81.2] net=-0.278 gross=-0.263 PF=0.46 stop=50.0% mfe=0.73 | n=3 prof=66.7% [20.8–93.9] net=+0.285 gross=+0.300 PF=1.83 stop=33.3% mfe=1.39 |  |
| funding | <-0.01% | n=7 prof=71.4% [35.9–91.8] net=+0.180 gross=+0.232 PF=1.56 stop=28.6% mfe=1.23 | n=2 prof=100.0% [34.2–100.0] net=+0.735 gross=+0.750 PF=inf stop=0.0% mfe=1.20 |  |
| funding | >0.05% | n=5 prof=60.0% [23.1–88.2] net=+0.222 gross=+0.228 PF=2.07 stop=20.0% mfe=0.71 | n=1 prof=0.0% [0.0–79.3] net=-1.017 gross=-1.000 PF=0.00 stop=100.0% mfe=0.17 |  |
| funding_side | fading_crowd | n=152 prof=52.0% [44.1–59.8] net=-0.117 gross=-0.081 PF=0.75 stop=44.7% mfe=0.84 | n=120 prof=64.2% [55.3–72.2] net=+0.119 gross=+0.146 PF=1.34 stop=34.2% mfe=1.04 |  |
| funding_side | neutral | n=37 prof=40.5% [26.3–56.5] net=-0.293 gross=-0.238 PF=0.52 stop=56.8% mfe=0.85 | n=13 prof=53.8% [29.1–76.8] net=+0.178 gross=+0.242 PF=1.56 stop=30.8% mfe=1.17 |  |
| funding_side | with_crowd | n=15 prof=46.7% [24.8–69.9] net=-0.258 gross=-0.175 PF=0.57 stop=53.3% mfe=0.88 | n=4 prof=75.0% [30.1–95.4] net=+0.198 gross=+0.219 PF=1.77 stop=25.0% mfe=0.91 |  |
| funding_z | -1..1 | n=143 prof=51.0% [42.9–59.1] net=-0.149 gross=-0.110 PF=0.70 stop=47.6% mfe=0.87 | n=110 prof=64.5% [55.3–72.9] net=+0.131 gross=+0.158 PF=1.38 stop=33.6% mfe=1.06 |  |
| funding_z | 1..2 | n=36 prof=38.9% [24.8–55.1] net=-0.374 gross=-0.300 PF=0.40 stop=55.6% mfe=0.66 | n=14 prof=50.0% [26.8–73.2] net=-0.051 gross=+0.019 PF=0.89 stop=42.9% mfe=0.94 |  |
| funding_z | <-1 | n=10 prof=60.0% [31.3–83.2] net=+0.124 gross=+0.150 PF=1.36 stop=30.0% mfe=1.03 | n=7 prof=71.4% [35.9–91.8] net=+0.287 gross=+0.304 PF=1.98 stop=28.6% mfe=1.05 |  |
| funding_z | >2 | n=6 prof=66.7% [30.0–90.3] net=+0.270 gross=+0.277 PF=2.56 stop=16.7% mfe=0.76 | n=4 prof=50.0% [15.0–85.0] net=+0.207 gross=+0.235 PF=1.79 stop=25.0% mfe=1.21 |  |
| funding_z | na | n=9 prof=44.4% [18.9–73.3] net=-0.062 gross=-0.039 PF=0.89 stop=55.6% mfe=1.09 | n=2 prof=100.0% [34.2–100.0] net=+0.440 gross=+0.450 PF=inf stop=0.0% mfe=0.93 |  |
| oi_divergence | down_down | n=4 prof=25.0% [4.6–69.9] net=-0.478 gross=-0.456 PF=0.38 stop=75.0% mfe=0.66 | n=5 prof=80.0% [37.6–96.4] net=+0.153 gross=+0.165 PF=1.76 stop=20.0% mfe=0.81 |  |
| oi_divergence | down_up | n=4 prof=0.0% [0.0–49.0] net=-1.025 gross=-1.000 PF=0.00 stop=100.0% mfe=0.34 | n=3 prof=33.3% [6.1–79.2] net=-0.509 gross=-0.492 PF=0.25 stop=66.7% mfe=0.58 |  |
| oi_divergence | flat | n=33 prof=66.7% [49.6–80.2] net=+0.278 gross=+0.350 PF=1.75 stop=30.3% mfe=1.32 | n=23 prof=73.9% [53.5–87.5] net=+0.427 gross=+0.461 PF=2.89 stop=21.7% mfe=1.39 | CANDIDATE |
| oi_divergence | up_down | n=58 prof=46.6% [34.3–59.2] net=-0.245 gross=-0.200 PF=0.53 stop=48.3% mfe=0.75 | n=25 prof=72.0% [52.4–85.7] net=+0.198 gross=+0.247 PF=1.74 stop=24.0% mfe=1.07 |  |
| oi_divergence | up_up | n=105 prof=48.6% [39.2–58.0] net=-0.204 gross=-0.171 PF=0.61 stop=49.5% mfe=0.78 | n=81 prof=58.0% [47.2–68.2] net=+0.042 gross=+0.067 PF=1.10 stop=39.5% mfe=0.97 |  |
| oi_chg_24h | -5..0% | n=49 prof=46.9% [33.7–60.6] net=-0.179 gross=-0.107 PF=0.68 stop=49.0% mfe=0.90 | n=34 prof=76.5% [60.0–87.6] net=+0.223 gross=+0.270 PF=1.90 stop=23.5% mfe=1.12 |  |
| oi_chg_24h | 0..5% | n=76 prof=53.9% [42.8–64.7] net=-0.069 gross=-0.022 PF=0.85 stop=42.1% mfe=0.91 | n=44 prof=65.9% [51.1–78.1] net=+0.178 gross=+0.203 PF=1.54 stop=31.8% mfe=1.07 |  |
| oi_chg_24h | <-5% | n=24 prof=50.0% [31.4–68.6] net=-0.190 gross=-0.172 PF=0.60 stop=45.8% mfe=0.76 | n=8 prof=50.0% [21.5–78.5] net=+0.050 gross=+0.072 PF=1.12 stop=37.5% mfe=1.05 |  |
| oi_chg_24h | >5% | n=55 prof=45.5% [33.0–58.5] net=-0.252 gross=-0.231 PF=0.55 stop=54.5% mfe=0.75 | n=51 prof=54.9% [41.4–67.7] net=+0.032 gross=+0.056 PF=1.07 stop=41.2% mfe=0.98 |  |
| settlement_bar | other | n=93 prof=44.1% [34.4–54.2] net=-0.257 gross=-0.221 PF=0.53 stop=52.7% mfe=0.75 | n=67 prof=62.7% [50.7–73.3] net=+0.112 gross=+0.141 PF=1.31 stop=35.8% mfe=1.03 |  |
| settlement_bar | settlement | n=111 prof=54.1% [44.8–63.0] net=-0.077 gross=-0.029 PF=0.84 stop=43.2% mfe=0.93 | n=70 prof=64.3% [52.6–74.5] net=+0.141 gross=+0.173 PF=1.43 stop=31.4% mfe=1.07 |  |
| session | 03-04 | n=21 prof=47.6% [28.3–67.6] net=-0.176 gross=-0.135 PF=0.65 stop=47.6% mfe=0.82 | n=24 prof=50.0% [31.4–68.6] net=-0.158 gross=-0.128 PF=0.69 stop=50.0% mfe=0.84 |  |
| session | 08-16 | n=62 prof=56.5% [44.1–68.1] net=-0.170 gross=-0.130 PF=0.63 stop=43.5% mfe=0.78 | n=37 prof=54.1% [38.4–69.0] net=-0.045 gross=-0.012 PF=0.89 stop=37.8% mfe=0.90 |  |
| session | other | n=121 prof=46.3% [37.6–55.1] net=-0.150 gross=-0.106 PF=0.72 stop=49.6% mfe=0.89 | n=76 prof=72.4% [61.4–81.2] net=+0.301 gross=+0.330 PF=2.12 stop=26.3% mfe=1.19 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

### rsi_bounce_long (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-05 | 33 | 60.6 | +0.040 |
| 2026-06 | 63 | 46.0 | -0.230 |
| 2026-07 | 50 | 62.0 | +0.117 |
| 2026-08 | 45 | 40.0 | -0.328 |
| 2026-09 | 34 | 61.8 | +0.223 |
| 2026-10 | 50 | 50.0 | -0.119 |

**Filter study** (52 cuts tested — expect ~2.6 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=126 prof=53.2% [44.5–61.7] net=-0.080 gross=-0.050 PF=0.79 stop=30.2% mfe=0.69 | n=67 prof=49.3% [37.7–60.9] net=+0.003 gross=+0.034 PF=1.01 stop=19.4% mfe=0.67 |  |
| btc_aligned | yes | n=39 prof=56.4% [41.0–70.7] net=-0.064 gross=-0.028 PF=0.84 stop=33.3% mfe=0.79 | n=43 prof=51.2% [36.8–65.4] net=-0.186 gross=-0.160 PF=0.60 stop=41.9% mfe=0.77 |  |
| confluence3 | 0-1 | n=154 prof=51.9% [44.1–59.7] net=-0.111 gross=-0.079 PF=0.72 stop=31.8% mfe=0.68 | n=80 prof=50.0% [39.3–60.7] net=-0.040 gross=-0.007 PF=0.87 stop=26.2% mfe=0.71 |  |
| confluence3 | 2-3 | n=11 prof=81.8% [52.3–94.9] net=+0.406 gross=+0.428 PF=3.17 stop=18.2% mfe=1.25 | n=30 prof=50.0% [33.2–66.8] net=-0.154 gross=-0.134 PF=0.62 stop=33.3% mfe=0.70 |  |
| risk_pct | 2-4% | n=48 prof=60.4% [46.3–73.0] net=+0.053 gross=+0.096 PF=1.18 stop=20.8% mfe=0.83 | n=18 prof=44.4% [24.6–66.3] net=-0.149 gross=-0.111 PF=0.68 stop=38.9% mfe=0.83 |  |
| risk_pct | 4-8% | n=78 prof=42.3% [32.0–53.4] net=-0.255 gross=-0.230 PF=0.48 stop=41.0% mfe=0.58 | n=53 prof=49.1% [36.1–62.1] net=-0.019 gross=+0.006 PF=0.94 stop=26.4% mfe=0.71 |  |
| risk_pct | <2% | n=9 prof=55.6% [26.7–81.1] net=-0.047 gross=+0.036 PF=0.90 stop=44.4% mfe=1.14 | n=7 prof=57.1% [25.0–84.2] net=-0.161 gross=-0.039 PF=0.56 stop=28.6% mfe=0.71 |  |
| risk_pct | >8% | n=30 prof=73.3% [55.6–85.8] net=+0.172 gross=+0.185 PF=1.82 stop=16.7% mfe=0.77 | n=32 prof=53.1% [36.4–69.1] net=-0.095 gross=-0.083 PF=0.69 stop=25.0% mfe=0.62 |  |
| hour | 00-08 | n=47 prof=46.8% [33.3–60.8] net=-0.215 gross=-0.181 PF=0.53 stop=36.2% mfe=0.67 | n=35 prof=42.9% [28.0–59.1] net=-0.085 gross=-0.052 PF=0.71 stop=22.9% mfe=0.69 |  |
| hour | 08-16 | n=58 prof=51.7% [39.2–64.1] net=-0.109 gross=-0.080 PF=0.74 stop=36.2% mfe=0.70 | n=35 prof=51.4% [35.6–67.0] net=-0.095 gross=-0.067 PF=0.75 stop=31.4% mfe=0.66 |  |
| hour | 16-24 | n=60 prof=61.7% [49.0–72.9] net=+0.064 gross=+0.095 PF=1.22 stop=21.7% mfe=0.77 | n=40 prof=55.0% [39.8–69.3] net=-0.038 gross=-0.012 PF=0.89 stop=30.0% mfe=0.76 |  |
| weekend | weekday | n=104 prof=51.0% [41.5–60.4] net=-0.146 gross=-0.114 PF=0.65 stop=34.6% mfe=0.67 | n=65 prof=55.4% [43.3–66.8] net=+0.019 gross=+0.048 PF=1.06 stop=26.2% mfe=0.78 |  |
| weekend | weekend | n=61 prof=59.0% [46.5–70.5] net=+0.043 gross=+0.072 PF=1.14 stop=24.6% mfe=0.80 | n=45 prof=42.2% [29.0–56.7] net=-0.202 gross=-0.171 PF=0.48 stop=31.1% mfe=0.60 |  |
| adx | 20-30 | n=67 prof=55.2% [43.4–66.5] net=-0.046 gross=-0.011 PF=0.88 stop=31.3% mfe=0.81 | n=48 prof=56.2% [42.3–69.3] net=+0.015 gross=+0.041 PF=1.05 stop=25.0% mfe=0.74 |  |
| adx | <20 | n=17 prof=47.1% [26.2–69.0] net=-0.163 gross=-0.132 PF=0.62 stop=35.3% mfe=0.70 | n=27 prof=44.4% [27.6–62.7] net=-0.244 gross=-0.205 PF=0.50 stop=40.7% mfe=0.66 |  |
| adx | >30 | n=81 prof=54.3% [43.5–64.7] net=-0.083 gross=-0.055 PF=0.77 stop=29.6% mfe=0.65 | n=35 prof=45.7% [30.5–61.8] net=-0.058 gross=-0.030 PF=0.80 stop=22.9% mfe=0.69 |  |
| vol_spike | <1.5 | n=151 prof=55.6% [47.7–63.3] net=-0.067 gross=-0.037 PF=0.82 stop=31.8% mfe=0.72 | n=99 prof=48.5% [38.9–58.2] net=-0.087 gross=-0.058 PF=0.75 stop=28.3% mfe=0.69 |  |
| vol_spike | >=1.5 | n=14 prof=35.7% [16.3–61.2] net=-0.172 gross=-0.137 PF=0.58 stop=21.4% mfe=0.70 | n=11 prof=63.6% [35.4–84.8] net=+0.069 gross=+0.103 PF=1.22 stop=27.3% mfe=0.88 |  |
| ema50_dist_atr | -0.5..0.5 | n=10 prof=50.0% [23.7–76.3] net=-0.091 gross=-0.064 PF=0.83 stop=50.0% mfe=0.94 | n=20 prof=40.0% [21.9–61.3] net=-0.220 gross=-0.198 PF=0.51 stop=35.0% mfe=0.61 |  |
| ema50_dist_atr | -2..-0.5 | n=67 prof=56.7% [44.8–67.9] net=+0.005 gross=+0.037 PF=1.01 stop=25.4% mfe=0.76 | n=41 prof=53.7% [38.7–67.9] net=-0.021 gross=+0.012 PF=0.93 stop=26.8% mfe=0.71 |  |
| ema50_dist_atr | 0.5..2 | n=2 prof=50.0% [9.5–90.5] net=-0.264 gross=-0.237 PF=0.49 stop=50.0% mfe=1.19 | n=8 prof=62.5% [30.6–86.3] net=-0.019 gross=+0.001 PF=0.94 stop=25.0% mfe=0.85 |  |
| ema50_dist_atr | <-2 | n=86 prof=52.3% [41.9–62.6] net=-0.133 gross=-0.102 PF=0.66 stop=32.6% mfe=0.65 | n=39 prof=51.3% [36.2–66.1] net=-0.008 gross=+0.022 PF=0.97 stop=23.1% mfe=0.73 |  |
| ema50_dist_atr | >2 | n=0 | n=2 prof=0.0% [0.0–65.8] net=-1.054 gross=-1.000 PF=0.00 stop=100.0% mfe=0.58 |  |
| symbol_group | major | n=87 prof=50.6% [40.3–60.8] net=-0.119 gross=-0.079 PF=0.69 stop=29.9% mfe=0.67 | n=55 prof=50.9% [38.1–63.6] net=-0.050 gross=-0.009 PF=0.85 stop=25.5% mfe=0.74 |  |
| symbol_group | other | n=78 prof=57.7% [46.6–68.0] net=-0.029 gross=-0.007 PF=0.92 stop=32.1% mfe=0.78 | n=55 prof=49.1% [36.4–61.9] net=-0.093 gross=-0.075 PF=0.74 stop=30.9% mfe=0.67 |  |
| funding | -0.01..0.005% | n=69 prof=60.9% [49.1–71.5] net=+0.003 gross=+0.038 PF=1.01 stop=23.2% mfe=0.74 | n=36 prof=38.9% [24.8–55.1] net=-0.172 gross=-0.141 PF=0.58 stop=33.3% mfe=0.64 |  |
| funding | 0.005..0.02% | n=72 prof=50.0% [38.7–61.3] net=-0.083 gross=-0.058 PF=0.80 stop=33.3% mfe=0.72 | n=63 prof=57.1% [44.9–68.6] net=+0.033 gross=+0.054 PF=1.12 stop=23.8% mfe=0.78 |  |
| funding | 0.02..0.05% | n=3 prof=66.7% [20.8–93.9] net=-0.125 gross=-0.114 PF=0.63 stop=33.3% mfe=0.76 | n=0 |  |
| funding | <-0.01% | n=20 prof=40.0% [21.9–61.3] net=-0.352 gross=-0.310 PF=0.38 stop=50.0% mfe=0.57 | n=11 prof=45.5% [21.3–72.0] net=-0.337 gross=-0.266 PF=0.32 stop=36.4% mfe=0.53 |  |
| funding | >0.05% | n=1 prof=100.0% [20.7–100.0] net=+0.631 gross=+0.642 PF=inf stop=0.0% mfe=1.46 | n=0 |  |
| funding_side | fading_crowd | n=37 prof=51.4% [35.9–66.6] net=-0.143 gross=-0.104 PF=0.65 stop=32.4% mfe=0.65 | n=20 prof=50.0% [29.9–70.1] net=-0.086 gross=-0.034 PF=0.75 stop=25.0% mfe=0.64 |  |
| funding_side | neutral | n=52 prof=59.6% [46.1–71.8] net=-0.030 gross=+0.005 PF=0.91 stop=26.9% mfe=0.75 | n=27 prof=33.3% [18.6–52.2] net=-0.303 gross=-0.271 PF=0.38 stop=40.7% mfe=0.59 |  |
| funding_side | with_crowd | n=76 prof=51.3% [40.3–62.2] net=-0.075 gross=-0.051 PF=0.81 stop=32.9% mfe=0.73 | n=63 prof=57.1% [44.9–68.6] net=+0.033 gross=+0.054 PF=1.12 stop=23.8% mfe=0.78 |  |
| funding_z | -1..1 | n=118 prof=55.1% [46.1–63.8] net=-0.041 gross=-0.010 PF=0.88 stop=28.0% mfe=0.73 | n=83 prof=51.8% [41.2–62.2] net=-0.005 gross=+0.020 PF=0.99 stop=27.7% mfe=0.79 |  |
| funding_z | 1..2 | n=10 prof=80.0% [49.0–94.3] net=+0.323 gross=+0.350 PF=2.59 stop=20.0% mfe=0.99 | n=5 prof=40.0% [11.8–76.9] net=-0.296 gross=-0.245 PF=0.18 stop=20.0% mfe=0.40 |  |
| funding_z | <-1 | n=28 prof=42.9% [26.5–60.9] net=-0.330 gross=-0.293 PF=0.34 stop=42.9% mfe=0.55 | n=20 prof=40.0% [21.9–61.3] net=-0.342 gross=-0.297 PF=0.22 stop=35.0% mfe=0.41 |  |
| funding_z | >2 | n=1 prof=0.0% [0.0–79.3] net=-1.013 gross=-1.000 PF=0.00 stop=100.0% mfe=0.07 | n=0 |  |
| funding_z | na | n=8 prof=50.0% [21.5–78.5] net=-0.086 gross=-0.070 PF=0.81 stop=37.5% mfe=0.80 | n=2 prof=100.0% [34.2–100.0] net=+0.440 gross=+0.450 PF=inf stop=0.0% mfe=1.08 |  |
| oi_divergence | down_down | n=31 prof=61.3% [43.8–76.3] net=+0.010 gross=+0.040 PF=1.03 stop=29.0% mfe=0.79 | n=22 prof=40.9% [23.3–61.3] net=-0.271 gross=-0.251 PF=0.40 stop=40.9% mfe=0.58 |  |
| oi_divergence | down_up | n=37 prof=45.9% [31.0–61.6] net=-0.202 gross=-0.171 PF=0.59 stop=43.2% mfe=0.64 | n=20 prof=35.0% [18.1–56.7] net=-0.263 gross=-0.238 PF=0.45 stop=40.0% mfe=0.62 |  |
| oi_divergence | flat | n=43 prof=51.2% [36.8–65.4] net=-0.069 gross=-0.032 PF=0.83 stop=32.6% mfe=0.78 | n=33 prof=60.6% [43.7–75.3] net=+0.047 gross=+0.088 PF=1.20 stop=18.2% mfe=0.74 |  |
| oi_divergence | up_down | n=25 prof=48.0% [30.0–66.5] net=-0.208 gross=-0.178 PF=0.42 stop=24.0% mfe=0.54 | n=14 prof=50.0% [26.8–73.2] net=+0.035 gross=+0.058 PF=1.10 stop=28.6% mfe=0.77 |  |
| oi_divergence | up_up | n=29 prof=65.5% [47.3–80.1] net=+0.094 gross=+0.122 PF=1.35 stop=20.7% mfe=0.80 | n=21 prof=57.1% [36.5–75.5] net=+0.063 gross=+0.092 PF=1.22 stop=19.0% mfe=0.82 |  |
| oi_chg_24h | -5..0% | n=61 prof=50.8% [38.6–62.9] net=-0.156 gross=-0.121 PF=0.63 stop=34.4% mfe=0.69 | n=39 prof=43.6% [29.3–59.0] net=-0.154 gross=-0.127 PF=0.64 stop=38.5% mfe=0.69 |  |
| oi_chg_24h | 0..5% | n=70 prof=55.7% [44.1–66.8] net=-0.034 gross=-0.004 PF=0.91 stop=30.0% mfe=0.73 | n=51 prof=52.9% [39.5–65.9] net=-0.029 gross=+0.007 PF=0.91 stop=23.5% mfe=0.74 |  |
| oi_chg_24h | <-5% | n=14 prof=57.1% [32.6–78.6] net=-0.032 gross=-0.006 PF=0.90 stop=21.4% mfe=0.71 | n=10 prof=60.0% [31.3–83.2] net=+0.072 gross=+0.093 PF=1.51 stop=10.0% mfe=0.59 |  |
| oi_chg_24h | >5% | n=20 prof=55.0% [34.2–74.2] net=-0.012 gross=+0.017 PF=0.97 stop=30.0% mfe=0.77 | n=10 prof=50.0% [23.7–76.3] net=-0.109 gross=-0.094 PF=0.72 stop=30.0% mfe=0.72 |  |
| settlement_bar | other | n=67 prof=55.2% [43.4–66.5] net=-0.105 gross=-0.073 PF=0.72 stop=29.9% mfe=0.72 | n=43 prof=53.5% [38.9–67.5] net=-0.004 gross=+0.027 PF=0.99 stop=20.9% mfe=0.69 |  |
| settlement_bar | settlement | n=98 prof=53.1% [43.3–62.6] net=-0.056 gross=-0.026 PF=0.85 stop=31.6% mfe=0.71 | n=67 prof=47.8% [36.3–59.5] net=-0.115 gross=-0.086 PF=0.70 stop=32.8% mfe=0.72 |  |
| session | 03-04 | n=30 prof=43.3% [27.4–60.8] net=-0.274 gross=-0.240 PF=0.45 stop=40.0% mfe=0.66 | n=9 prof=44.4% [18.9–73.3] net=-0.111 gross=-0.060 PF=0.48 stop=11.1% mfe=0.53 |  |
| session | 08-16 | n=58 prof=51.7% [39.2–64.1] net=-0.109 gross=-0.080 PF=0.74 stop=36.2% mfe=0.70 | n=35 prof=51.4% [35.6–67.0] net=-0.095 gross=-0.067 PF=0.75 stop=31.4% mfe=0.66 |  |
| session | other | n=77 prof=59.7% [48.6–70.0] net=+0.025 gross=+0.057 PF=1.08 stop=23.4% mfe=0.75 | n=66 prof=50.0% [38.3–61.7] net=-0.053 gross=-0.026 PF=0.84 stop=28.8% mfe=0.75 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

### range_reversion_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-05 | 1 | 100.0 | +1.089 |
| 2026-06 | 8 | 87.5 | +0.451 |
| 2026-07 | 15 | 73.3 | +0.115 |
| 2026-08 | 8 | 50.0 | -0.152 |
| 2026-09 | 7 | 71.4 | -0.000 |
| 2026-10 | 6 | 100.0 | +1.008 |

**Filter study** (43 cuts tested — expect ~2.1 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=20 prof=80.0% [58.4–91.9] net=+0.289 gross=+0.340 PF=2.34 stop=20.0% mfe=1.08 | n=14 prof=78.6% [52.4–92.4] net=+0.302 gross=+0.338 PF=2.34 stop=21.4% mfe=1.04 |  |
| btc_aligned | yes | n=7 prof=71.4% [35.9–91.8] net=+0.166 gross=+0.218 PF=1.54 stop=28.6% mfe=0.95 | n=4 prof=50.0% [15.0–85.0] net=+0.021 gross=+0.062 PF=1.04 stop=50.0% mfe=1.16 |  |
| confluence3 | 0-1 | n=18 prof=72.2% [49.1–87.5] net=+0.082 gross=+0.135 PF=1.28 stop=27.8% mfe=0.89 | n=16 prof=68.8% [44.4–85.8] net=+0.131 gross=+0.170 PF=1.40 stop=31.2% mfe=0.95 |  |
| confluence3 | 2-3 | n=9 prof=88.9% [56.5–98.0] net=+0.606 gross=+0.656 PF=5.90 stop=11.1% mfe=1.36 | n=2 prof=100.0% [34.2–100.0] net=+1.111 gross=+1.125 PF=inf stop=0.0% mfe=2.01 |  |
| risk_pct | 2-4% | n=9 prof=77.8% [45.3–93.7] net=+0.154 gross=+0.186 PF=1.67 stop=22.2% mfe=0.91 | n=6 prof=83.3% [43.6–97.0] net=+0.646 gross=+0.671 PF=4.73 stop=16.7% mfe=1.32 |  |
| risk_pct | 4-8% | n=0 | n=3 prof=100.0% [43.8–100.0] net=+0.713 gross=+0.725 PF=inf stop=0.0% mfe=1.65 |  |
| risk_pct | <2% | n=18 prof=77.8% [54.8–91.0] net=+0.308 gross=+0.369 PF=2.27 stop=22.2% mfe=1.11 | n=9 prof=55.6% [26.7–81.1] net=-0.189 gross=-0.136 PF=0.60 stop=44.4% mfe=0.71 |  |
| hour | 00-08 | n=7 prof=85.7% [48.7–97.4] net=+0.241 gross=+0.307 PF=2.51 stop=14.3% mfe=1.01 | n=1 prof=100.0% [20.7–100.0] net=+0.492 gross=+0.525 PF=inf stop=0.0% mfe=1.40 |  |
| hour | 08-16 | n=7 prof=71.4% [35.9–91.8] net=+0.091 gross=+0.132 PF=1.30 stop=28.6% mfe=0.81 | n=8 prof=75.0% [40.9–92.9] net=+0.415 gross=+0.444 PF=2.56 stop=25.0% mfe=1.35 |  |
| hour | 16-24 | n=13 prof=76.9% [49.7–91.8] net=+0.355 gross=+0.404 PF=2.43 stop=23.1% mfe=1.19 | n=9 prof=66.7% [35.4–87.9] net=+0.055 gross=+0.100 PF=1.16 stop=33.3% mfe=0.79 |  |
| weekend | weekday | n=22 prof=81.8% [61.5–92.7] net=+0.326 gross=+0.377 PF=2.65 stop=18.2% mfe=1.11 | n=17 prof=70.6% [46.9–86.7] net=+0.189 gross=+0.227 PF=1.61 stop=29.4% mfe=1.04 |  |
| weekend | weekend | n=5 prof=60.0% [23.1–88.2] net=-0.045 gross=+0.005 PF=0.89 stop=40.0% mfe=0.78 | n=1 prof=100.0% [20.7–100.0] net=+1.104 gross=+1.125 PF=inf stop=0.0% mfe=1.52 |  |
| adx | 20-30 | n=11 prof=81.8% [52.3–94.9] net=+0.354 gross=+0.398 PF=2.85 stop=18.2% mfe=1.05 | n=8 prof=62.5% [30.6–86.3] net=-0.130 gross=-0.084 PF=0.68 stop=37.5% mfe=0.78 |  |
| adx | <20 | n=16 prof=75.0% [50.5–89.8] net=+0.191 gross=+0.247 PF=1.70 stop=25.0% mfe=1.04 | n=10 prof=80.0% [49.0–94.3] net=+0.535 gross=+0.565 PF=3.54 stop=20.0% mfe=1.30 |  |
| vol_spike | >=1.5 | n=27 prof=77.8% [59.2–89.4] net=+0.257 gross=+0.308 PF=2.08 stop=22.2% mfe=1.05 | n=18 prof=72.2% [49.1–87.5] net=+0.240 gross=+0.276 PF=1.82 stop=27.8% mfe=1.07 |  |
| ema50_dist_atr | 0.5..2 | n=7 prof=71.4% [35.9–91.8] net=+0.371 gross=+0.411 PF=2.25 stop=28.6% mfe=1.11 | n=3 prof=100.0% [43.8–100.0] net=+0.842 gross=+0.875 PF=inf stop=0.0% mfe=1.33 |  |
| ema50_dist_atr | >2 | n=20 prof=80.0% [58.4–91.9] net=+0.217 gross=+0.273 PF=1.99 stop=20.0% mfe=1.02 | n=15 prof=66.7% [41.7–84.8] net=+0.119 gross=+0.157 PF=1.34 stop=33.3% mfe=1.02 |  |
| symbol_group | major | n=17 prof=82.4% [59.0–93.8] net=+0.350 gross=+0.406 PF=2.82 stop=17.6% mfe=1.07 | n=11 prof=63.6% [35.4–84.8] net=+0.049 gross=+0.093 PF=1.13 stop=36.4% mfe=0.86 |  |
| symbol_group | other | n=10 prof=70.0% [39.7–89.2] net=+0.099 gross=+0.142 PF=1.31 stop=30.0% mfe=1.00 | n=7 prof=85.7% [48.7–97.4] net=+0.539 gross=+0.564 PF=4.57 stop=14.3% mfe=1.41 |  |
| funding | -0.01..0.005% | n=7 prof=71.4% [35.9–91.8] net=+0.137 gross=+0.196 PF=1.44 stop=28.6% mfe=0.95 | n=5 prof=60.0% [23.1–88.2] net=-0.072 gross=-0.025 PF=0.83 stop=40.0% mfe=0.74 |  |
| funding | 0.005..0.02% | n=20 prof=80.0% [58.4–91.9] net=+0.299 gross=+0.347 PF=2.39 stop=20.0% mfe=1.08 | n=10 prof=70.0% [39.7–89.2] net=+0.254 gross=+0.292 PF=1.79 stop=30.0% mfe=1.06 |  |
| funding | 0.02..0.05% | n=0 | n=1 prof=100.0% [20.7–100.0] net=+1.119 gross=+1.125 PF=inf stop=0.0% mfe=2.50 |  |
| funding | <-0.01% | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.508 gross=+0.525 PF=inf stop=0.0% mfe=1.29 |  |
| funding | >0.05% | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.512 gross=+0.525 PF=inf stop=0.0% mfe=1.17 |  |
| funding_side | fading_crowd | n=20 prof=80.0% [58.4–91.9] net=+0.299 gross=+0.347 PF=2.39 stop=20.0% mfe=1.08 | n=12 prof=75.0% [46.8–91.1] net=+0.347 gross=+0.381 PF=2.30 stop=25.0% mfe=1.19 |  |
| funding_side | neutral | n=6 prof=66.7% [30.0–90.3] net=-0.026 gross=+0.042 PF=0.93 stop=33.3% mfe=0.82 | n=4 prof=75.0% [30.1–95.4] net=+0.170 gross=+0.219 PF=1.64 stop=25.0% mfe=0.92 |  |
| funding_side | with_crowd | n=1 prof=100.0% [20.7–100.0] net=+1.111 gross=+1.125 PF=inf stop=0.0% mfe=1.73 | n=2 prof=50.0% [9.5–90.5] net=-0.266 gross=-0.237 PF=0.49 stop=50.0% mfe=0.66 |  |
| funding_z | -1..1 | n=19 prof=68.4% [46.0–84.6] net=+0.108 gross=+0.162 PF=1.32 stop=31.6% mfe=1.03 | n=11 prof=90.9% [62.3–98.4] net=+0.583 gross=+0.618 PF=7.06 stop=9.1% mfe=1.26 |  |
| funding_z | 1..2 | n=8 prof=100.0% [67.6–100.0] net=+0.612 gross=+0.656 PF=inf stop=0.0% mfe=1.08 | n=1 prof=0.0% [0.0–79.3] net=-1.064 gross=-1.000 PF=0.00 stop=100.0% mfe=0.12 |  |
| funding_z | <-1 | n=0 | n=2 prof=50.0% [9.5–90.5] net=-0.266 gross=-0.237 PF=0.49 stop=50.0% mfe=0.66 |  |
| funding_z | >2 | n=0 | n=4 prof=50.0% [15.0–85.0] net=-0.125 gross=-0.087 PF=0.77 stop=50.0% mfe=1.00 |  |
| oi_divergence | flat | n=7 prof=71.4% [35.9–91.8] net=+0.135 gross=+0.196 PF=1.44 stop=28.6% mfe=0.91 | n=0 |  |
| oi_divergence | up_down | n=8 prof=87.5% [52.9–97.8] net=+0.362 gross=+0.409 PF=3.60 stop=12.5% mfe=1.17 | n=5 prof=60.0% [23.1–88.2] net=+0.086 gross=+0.125 PF=1.20 stop=40.0% mfe=0.90 |  |
| oi_divergence | up_up | n=12 prof=75.0% [46.8–91.1] net=+0.259 gross=+0.306 PF=1.97 stop=25.0% mfe=1.04 | n=13 prof=76.9% [49.7–91.8] net=+0.299 gross=+0.335 PF=2.22 stop=23.1% mfe=1.14 |  |
| oi_chg_24h | -5..0% | n=10 prof=80.0% [49.0–94.3] net=+0.202 gross=+0.265 PF=1.92 stop=20.0% mfe=1.03 | n=4 prof=75.0% [30.1–95.4] net=+0.372 gross=+0.406 PF=2.41 stop=25.0% mfe=1.00 |  |
| oi_chg_24h | 0..5% | n=9 prof=55.6% [26.7–81.1] net=-0.037 gross=+0.014 PF=0.92 stop=44.4% mfe=0.91 | n=7 prof=85.7% [48.7–97.4] net=+0.398 gross=+0.436 PF=3.62 stop=14.3% mfe=1.08 |  |
| oi_chg_24h | <-5% | n=2 prof=100.0% [34.2–100.0] net=+0.731 gross=+0.750 PF=inf stop=0.0% mfe=1.24 | n=1 prof=0.0% [0.0–79.3] net=-1.058 gross=-1.000 PF=0.00 stop=100.0% mfe=0.49 |  |
| oi_chg_24h | >5% | n=6 prof=100.0% [61.0–100.0] net=+0.631 gross=+0.675 PF=inf stop=0.0% mfe=1.21 | n=6 prof=66.7% [30.0–90.3] net=+0.183 gross=+0.217 PF=1.52 stop=33.3% mfe=1.20 |  |
| settlement_bar | other | n=8 prof=62.5% [30.6–86.3] net=-0.067 gross=-0.028 PF=0.83 stop=37.5% mfe=0.85 | n=8 prof=62.5% [30.6–86.3] net=-0.027 gross=+0.009 PF=0.93 stop=37.5% mfe=0.84 |  |
| settlement_bar | settlement | n=19 prof=84.2% [62.4–94.5] net=+0.394 gross=+0.450 PF=3.26 stop=15.8% mfe=1.13 | n=10 prof=80.0% [49.0–94.3] net=+0.453 gross=+0.490 PF=3.12 stop=20.0% mfe=1.25 |  |
| session | 03-04 | n=2 prof=100.0% [34.2–100.0] net=+0.409 gross=+0.450 PF=inf stop=0.0% mfe=1.21 | n=1 prof=100.0% [20.7–100.0] net=+0.492 gross=+0.525 PF=inf stop=0.0% mfe=1.40 |  |
| session | 08-16 | n=7 prof=71.4% [35.9–91.8] net=+0.091 gross=+0.132 PF=1.30 stop=28.6% mfe=0.81 | n=8 prof=75.0% [40.9–92.9] net=+0.415 gross=+0.444 PF=2.56 stop=25.0% mfe=1.35 |  |
| session | other | n=18 prof=77.8% [54.8–91.0] net=+0.305 gross=+0.361 PF=2.27 stop=22.2% mfe=1.12 | n=9 prof=66.7% [35.4–87.9] net=+0.055 gross=+0.100 PF=1.16 stop=33.3% mfe=0.79 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- chosen: T1=0.5R, stop×0.75, T2=1.5R, trail=on
- TRAIN chosen: n=27 prof=92.6% [76.6–97.9] net=+0.272 gross=+0.335 PF=4.42 stop=7.4% mfe=0.97
- TEST chosen: n=18 prof=72.2% [49.1–87.5] net=+0.097 gross=+0.144 PF=1.33 stop=27.8% mfe=0.96
- TEST default: n=18 prof=72.2% [49.1–87.5] net=+0.240 gross=+0.276 PF=1.82 stop=27.8% mfe=1.07

### range_reversion_long (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-05 | 2 | 0.0 | -1.076 |
| 2026-07 | 9 | 33.3 | -0.575 |
| 2026-08 | 8 | 87.5 | +0.286 |
| 2026-09 | 10 | 60.0 | +0.109 |
| 2026-10 | 7 | 28.6 | -0.566 |

**Filter study** (43 cuts tested — expect ~2.1 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=7 prof=42.9% [15.8–75.0] net=-0.347 gross=-0.282 PF=0.44 stop=57.1% mfe=0.67 | n=12 prof=50.0% [25.4–74.6] net=-0.106 gross=-0.050 PF=0.80 stop=50.0% mfe=0.94 |  |
| btc_aligned | yes | n=14 prof=57.1% [32.6–78.6] net=-0.184 gross=-0.118 PF=0.60 stop=42.9% mfe=0.83 | n=3 prof=33.3% [6.1–79.2] net=-0.547 gross=-0.492 PF=0.23 stop=66.7% mfe=0.60 |  |
| confluence3 | 0-1 | n=18 prof=50.0% [29.0–71.0] net=-0.266 gross=-0.196 PF=0.51 stop=50.0% mfe=0.76 | n=14 prof=50.0% [26.8–73.2] net=-0.132 gross=-0.077 PF=0.75 stop=50.0% mfe=0.90 |  |
| confluence3 | 2-3 | n=3 prof=66.7% [20.8–93.9] net=-0.075 gross=-0.033 PF=0.78 stop=33.3% mfe=0.86 | n=1 prof=0.0% [0.0–79.3] net=-1.062 gross=-1.000 PF=0.00 stop=100.0% mfe=0.44 |  |
| risk_pct | 2-4% | n=5 prof=40.0% [11.8–76.9] net=-0.435 gross=-0.390 PF=0.31 stop=60.0% mfe=0.72 | n=5 prof=40.0% [11.8–76.9] net=-0.339 gross=-0.300 PF=0.46 stop=60.0% mfe=0.72 |  |
| risk_pct | <2% | n=16 prof=56.2% [33.2–76.9] net=-0.177 gross=-0.105 PF=0.63 stop=43.8% mfe=0.80 | n=10 prof=50.0% [23.7–76.3] net=-0.122 gross=-0.058 PF=0.78 stop=50.0% mfe=0.94 |  |
| hour | 00-08 | n=10 prof=60.0% [31.3–83.2] net=-0.022 gross=+0.035 PF=0.95 stop=40.0% mfe=1.02 | n=7 prof=42.9% [15.8–75.0] net=-0.242 gross=-0.175 PF=0.61 stop=57.1% mfe=0.81 |  |
| hour | 08-16 | n=5 prof=60.0% [23.1–88.2] net=-0.204 gross=-0.145 PF=0.52 stop=40.0% mfe=0.64 | n=3 prof=33.3% [6.1–79.2] net=-0.339 gross=-0.292 PF=0.52 stop=66.7% mfe=0.82 |  |
| hour | 16-24 | n=6 prof=33.3% [9.7–70.0] net=-0.628 gross=-0.542 PF=0.12 stop=66.7% mfe=0.48 | n=5 prof=60.0% [23.1–88.2] net=-0.041 gross=+0.005 PF=0.90 stop=40.0% mfe=0.98 |  |
| weekend | weekday | n=19 prof=47.4% [27.3–68.3] net=-0.306 gross=-0.238 PF=0.46 stop=52.6% mfe=0.73 | n=13 prof=46.2% [23.2–70.9] net=-0.227 gross=-0.169 PF=0.61 stop=53.8% mfe=0.82 |  |
| weekend | weekend | n=2 prof=100.0% [34.2–100.0] net=+0.405 gross=+0.450 PF=inf stop=0.0% mfe=1.24 | n=2 prof=50.0% [9.5–90.5] net=+0.015 gross=+0.062 PF=1.03 stop=50.0% mfe=1.18 |  |
| adx | <20 | n=21 prof=52.4% [32.4–71.7] net=-0.238 gross=-0.173 PF=0.53 stop=47.6% mfe=0.78 | n=15 prof=46.7% [24.8–69.9] net=-0.194 gross=-0.138 PF=0.66 stop=53.3% mfe=0.87 |  |
| vol_spike | <1.5 | n=15 prof=60.0% [35.7–80.2] net=-0.108 gross=-0.045 PF=0.75 stop=40.0% mfe=0.89 | n=10 prof=60.0% [31.3–83.2] net=+0.098 gross=+0.140 PF=1.23 stop=40.0% mfe=1.10 |  |
| vol_spike | >=1.5 | n=6 prof=33.3% [9.7–70.0] net=-0.564 gross=-0.492 PF=0.22 stop=66.7% mfe=0.50 | n=5 prof=20.0% [3.6–62.4] net=-0.779 gross=-0.695 PF=0.10 stop=80.0% mfe=0.41 |  |
| ema50_dist_atr | -0.5..0.5 | n=1 prof=100.0% [20.7–100.0] net=+0.328 gross=+0.375 PF=inf stop=0.0% mfe=0.99 | n=0 |  |
| ema50_dist_atr | -2..-0.5 | n=13 prof=53.8% [29.1–76.8] net=-0.221 gross=-0.156 PF=0.55 stop=46.2% mfe=0.84 | n=5 prof=60.0% [23.1–88.2] net=-0.044 gross=+0.005 PF=0.90 stop=40.0% mfe=0.99 |  |
| ema50_dist_atr | <-2 | n=7 prof=42.9% [15.8–75.0] net=-0.352 gross=-0.282 PF=0.43 stop=57.1% mfe=0.64 | n=10 prof=40.0% [16.8–68.7] net=-0.270 gross=-0.210 PF=0.58 stop=60.0% mfe=0.81 |  |
| symbol_group | major | n=11 prof=63.6% [35.4–84.8] net=-0.100 gross=-0.029 PF=0.74 stop=36.4% mfe=0.80 | n=7 prof=28.6% [8.2–64.1] net=-0.553 gross=-0.479 PF=0.28 stop=71.4% mfe=0.55 |  |
| symbol_group | other | n=10 prof=40.0% [16.8–68.7] net=-0.390 gross=-0.330 PF=0.39 stop=60.0% mfe=0.76 | n=8 prof=62.5% [30.6–86.3] net=+0.120 gross=+0.159 PF=1.30 stop=37.5% mfe=1.15 |  |
| funding | -0.01..0.005% | n=12 prof=41.7% [19.3–68.0] net=-0.458 gross=-0.390 PF=0.28 stop=58.3% mfe=0.62 | n=6 prof=33.3% [9.7–70.0] net=-0.356 gross=-0.292 PF=0.51 stop=66.7% mfe=0.67 |  |
| funding | 0.005..0.02% | n=7 prof=71.4% [35.9–91.8] net=+0.189 gross=+0.239 PF=1.63 stop=28.6% mfe=1.12 | n=7 prof=57.1% [25.0–84.2] net=-0.024 gross=+0.021 PF=0.95 stop=42.9% mfe=1.05 |  |
| funding | 0.02..0.05% | n=1 prof=0.0% [0.0–79.3] net=-1.044 gross=-1.000 PF=0.00 stop=100.0% mfe=0.22 | n=0 |  |
| funding | <-0.01% | n=1 prof=100.0% [20.7–100.0] net=+0.214 gross=+0.375 PF=inf stop=0.0% mfe=0.83 | n=2 prof=50.0% [9.5–90.5] net=-0.302 gross=-0.237 PF=0.42 stop=50.0% mfe=0.82 |  |
| funding_side | fading_crowd | n=4 prof=100.0% [51.0–100.0] net=+0.413 gross=+0.487 PF=inf stop=0.0% mfe=1.18 | n=3 prof=66.7% [20.8–93.9] net=+0.164 gross=+0.217 PF=1.47 stop=33.3% mfe=1.10 |  |
| funding_side | neutral | n=9 prof=22.2% [6.3–54.7] net=-0.770 gross=-0.694 PF=0.09 stop=77.8% mfe=0.39 | n=5 prof=20.0% [3.6–62.4] net=-0.647 gross=-0.575 PF=0.25 stop=80.0% mfe=0.47 |  |
| funding_side | with_crowd | n=8 prof=62.5% [30.6–86.3] net=+0.035 gross=+0.084 PF=1.09 stop=37.5% mfe=1.01 | n=7 prof=57.1% [25.0–84.2] net=-0.024 gross=+0.021 PF=0.95 stop=42.9% mfe=1.05 |  |
| funding_z | -1..1 | n=12 prof=50.0% [25.4–74.6] net=-0.228 gross=-0.163 PF=0.58 stop=50.0% mfe=0.79 | n=11 prof=45.5% [21.3–72.0] net=-0.213 gross=-0.157 PF=0.64 stop=54.5% mfe=0.87 |  |
| funding_z | 1..2 | n=1 prof=0.0% [0.0–79.3] net=-1.058 gross=-1.000 PF=0.00 stop=100.0% mfe=0.32 | n=0 |  |
| funding_z | <-1 | n=7 prof=71.4% [35.9–91.8] net=-0.024 gross=+0.046 PF=0.92 stop=28.6% mfe=0.90 | n=4 prof=50.0% [15.0–85.0] net=-0.144 gross=-0.087 PF=0.73 stop=50.0% mfe=0.88 |  |
| funding_z | >2 | n=1 prof=0.0% [0.0–79.3] net=-1.044 gross=-1.000 PF=0.00 stop=100.0% mfe=0.22 | n=0 |  |
| oi_divergence | down_down | n=11 prof=63.6% [35.4–84.8] net=-0.021 gross=+0.052 PF=0.95 stop=36.4% mfe=0.85 | n=9 prof=44.4% [18.9–73.3] net=-0.180 gross=-0.122 PF=0.70 stop=55.6% mfe=0.86 |  |
| oi_divergence | down_up | n=4 prof=25.0% [4.6–69.9] net=-0.719 gross=-0.656 PF=0.10 stop=75.0% mfe=0.60 | n=5 prof=60.0% [23.1–88.2] net=-0.046 gross=+0.005 PF=0.89 stop=40.0% mfe=1.03 |  |
| oi_divergence | flat | n=5 prof=40.0% [11.8–76.9] net=-0.445 gross=-0.390 PF=0.30 stop=60.0% mfe=0.71 | n=1 prof=0.0% [0.0–79.3] net=-1.068 gross=-1.000 PF=0.00 stop=100.0% mfe=0.19 |  |
| oi_divergence | up_up | n=1 prof=100.0% [20.7–100.0] net=+0.328 gross=+0.375 PF=inf stop=0.0% mfe=0.99 | n=0 |  |
| oi_chg_24h | -5..0% | n=14 prof=57.1% [32.6–78.6] net=-0.133 gross=-0.064 PF=0.71 stop=42.9% mfe=0.81 | n=6 prof=50.0% [18.8–81.2] net=-0.000 gross=+0.062 PF=1.00 stop=50.0% mfe=1.01 |  |
| oi_chg_24h | 0..5% | n=5 prof=40.0% [11.8–76.9] net=-0.508 gross=-0.450 PF=0.20 stop=60.0% mfe=0.56 | n=5 prof=40.0% [11.8–76.9] net=-0.328 gross=-0.270 PF=0.48 stop=60.0% mfe=0.88 |  |
| oi_chg_24h | <-5% | n=0 | n=3 prof=33.3% [6.1–79.2] net=-0.538 gross=-0.492 PF=0.23 stop=66.7% mfe=0.54 |  |
| oi_chg_24h | >5% | n=2 prof=50.0% [9.5–90.5] net=-0.298 gross=-0.237 PF=0.45 stop=50.0% mfe=1.10 | n=1 prof=100.0% [20.7–100.0] net=+0.343 gross=+0.375 PF=inf stop=0.0% mfe=0.93 |  |
| settlement_bar | other | n=10 prof=70.0% [39.7–89.2] net=-0.006 gross=+0.068 PF=0.98 stop=30.0% mfe=0.85 | n=8 prof=37.5% [13.7–69.4] net=-0.420 gross=-0.372 PF=0.37 stop=62.5% mfe=0.67 |  |
| settlement_bar | settlement | n=11 prof=36.4% [15.2–64.6] net=-0.450 gross=-0.391 PF=0.34 stop=63.6% mfe=0.71 | n=7 prof=57.1% [25.0–84.2] net=+0.064 gross=+0.129 PF=1.14 stop=42.9% mfe=1.10 |  |
| session | 03-04 | n=3 prof=66.7% [20.8–93.9] net=+0.144 gross=+0.217 PF=1.39 stop=33.3% mfe=1.02 | n=2 prof=50.0% [9.5–90.5] net=-0.299 gross=-0.237 PF=0.45 stop=50.0% mfe=0.76 |  |
| session | 08-16 | n=5 prof=60.0% [23.1–88.2] net=-0.204 gross=-0.145 PF=0.52 stop=40.0% mfe=0.64 | n=3 prof=33.3% [6.1–79.2] net=-0.339 gross=-0.292 PF=0.52 stop=66.7% mfe=0.82 |  |
| session | other | n=13 prof=46.2% [23.2–70.9] net=-0.340 gross=-0.273 PF=0.41 stop=53.8% mfe=0.77 | n=10 prof=50.0% [23.7–76.3] net=-0.130 gross=-0.072 PF=0.76 stop=50.0% mfe=0.91 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

### funding_squeeze_long (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-05 | 1 | 100.0 | +0.502 |
| 2026-06 | 4 | 50.0 | +0.029 |
| 2026-07 | 5 | 80.0 | +0.661 |
| 2026-08 | 1 | 0.0 | -1.030 |
| 2026-09 | 1 | 100.0 | +0.368 |
| 2026-10 | 3 | 33.3 | -0.204 |

**Filter study** (35 cuts tested — expect ~1.8 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=6 prof=66.7% [30.0–90.3] net=+0.279 gross=+0.317 PF=1.79 stop=33.3% mfe=1.13 | n=2 prof=0.0% [0.0–65.8] net=-0.439 gross=-0.416 PF=0.00 stop=0.0% mfe=0.07 |  |
| btc_aligned | yes | n=3 prof=100.0% [43.8–100.0] net=+1.099 gross=+1.125 PF=inf stop=0.0% mfe=1.58 | n=4 prof=50.0% [15.0–85.0] net=-0.359 gross=-0.312 PF=0.31 stop=50.0% mfe=0.61 |  |
| confluence3 | 0-1 | n=8 prof=87.5% [52.9–97.8] net=+0.749 gross=+0.784 PF=6.51 stop=12.5% mfe=1.44 | n=4 prof=50.0% [15.0–85.0] net=-0.183 gross=-0.142 PF=0.46 stop=25.0% mfe=0.62 |  |
| confluence3 | 2-3 | n=1 prof=0.0% [0.0–79.3] net=-1.025 gross=-1.000 PF=0.00 stop=100.0% mfe=0.01 | n=2 prof=0.0% [0.0–65.8] net=-0.791 gross=-0.756 PF=0.00 stop=50.0% mfe=0.05 |  |
| risk_pct | 2-4% | n=2 prof=100.0% [34.2–100.0] net=+0.806 gross=+0.825 PF=inf stop=0.0% mfe=1.50 | n=1 prof=0.0% [0.0–79.3] net=-1.043 gross=-1.000 PF=0.00 stop=100.0% mfe=0.08 |  |
| risk_pct | 4-8% | n=4 prof=75.0% [30.1–95.4] net=+0.579 gross=+0.594 PF=3.26 stop=25.0% mfe=1.24 | n=2 prof=0.0% [0.0–65.8] net=-0.784 gross=-0.756 PF=0.00 stop=50.0% mfe=0.25 |  |
| risk_pct | <2% | n=3 prof=66.7% [20.8–93.9] net=+0.347 gross=+0.417 PF=1.96 stop=33.3% mfe=1.20 | n=1 prof=100.0% [20.7–100.0] net=+0.267 gross=+0.375 PF=inf stop=0.0% mfe=0.92 |  |
| risk_pct | >8% | n=0 | n=2 prof=50.0% [9.5–90.5] net=+0.015 gross=+0.028 PF=1.09 stop=0.0% mfe=0.54 |  |
| hour | 00-08 | n=3 prof=100.0% [43.8–100.0] net=+1.111 gross=+1.125 PF=inf stop=0.0% mfe=1.62 | n=2 prof=0.0% [0.0–65.8] net=-0.684 gross=-0.660 PF=0.00 stop=50.0% mfe=0.30 |  |
| hour | 08-16 | n=3 prof=66.7% [20.8–93.9] net=+0.383 gross=+0.417 PF=2.12 stop=33.3% mfe=1.10 | n=1 prof=100.0% [20.7–100.0] net=+0.368 gross=+0.375 PF=inf stop=0.0% mfe=0.96 |  |
| hour | 16-24 | n=3 prof=66.7% [20.8–93.9] net=+0.163 gross=+0.217 PF=1.45 stop=33.3% mfe=1.12 | n=3 prof=33.3% [6.1–79.2] net=-0.438 gross=-0.379 PF=0.17 stop=33.3% mfe=0.34 |  |
| weekend | weekday | n=7 prof=85.7% [48.7–97.4] net=+0.703 gross=+0.736 PF=5.52 stop=14.3% mfe=1.43 | n=5 prof=40.0% [11.8–76.9] net=-0.355 gross=-0.314 PF=0.26 stop=40.0% mfe=0.51 |  |
| weekend | weekend | n=2 prof=50.0% [9.5–90.5] net=+0.025 gross=+0.062 PF=1.05 stop=50.0% mfe=0.76 | n=1 prof=0.0% [0.0–79.3] net=-0.539 gross=-0.512 PF=0.00 stop=0.0% mfe=0.03 |  |
| adx | 20-30 | n=2 prof=100.0% [34.2–100.0] net=+0.806 gross=+0.825 PF=inf stop=0.0% mfe=1.50 | n=4 prof=25.0% [4.6–69.9] net=-0.536 gross=-0.486 PF=0.11 stop=50.0% mfe=0.40 |  |
| adx | <20 | n=6 prof=83.3% [43.6–97.0] net=+0.741 gross=+0.771 PF=5.34 stop=16.7% mfe=1.35 | n=2 prof=50.0% [9.5–90.5] net=-0.086 gross=-0.069 PF=0.68 stop=0.0% mfe=0.49 |  |
| adx | >30 | n=1 prof=0.0% [0.0–79.3] net=-1.088 gross=-1.000 PF=0.00 stop=100.0% mfe=0.45 | n=0 |  |
| vol_spike | <1.5 | n=4 prof=75.0% [30.1–95.4] net=+0.568 gross=+0.594 PF=3.22 stop=25.0% mfe=1.19 | n=3 prof=0.0% [0.0–56.2] net=-0.636 gross=-0.611 PF=0.00 stop=33.3% mfe=0.21 |  |
| vol_spike | >=1.5 | n=5 prof=80.0% [37.6–96.4] net=+0.539 gross=+0.580 PF=3.48 stop=20.0% mfe=1.36 | n=3 prof=66.7% [20.8–93.9] net=-0.136 gross=-0.083 PF=0.61 stop=33.3% mfe=0.65 |  |
| ema50_dist_atr | -0.5..0.5 | n=5 prof=80.0% [37.6–96.4] net=+0.552 gross=+0.580 PF=3.69 stop=20.0% mfe=1.26 | n=2 prof=0.0% [0.0–65.8] net=-0.691 gross=-0.660 PF=0.00 stop=50.0% mfe=0.10 |  |
| ema50_dist_atr | -2..-0.5 | n=2 prof=100.0% [34.2–100.0] net=+1.111 gross=+1.125 PF=inf stop=0.0% mfe=1.63 | n=3 prof=33.3% [6.1–79.2] net=-0.434 gross=-0.379 PF=0.17 stop=33.3% mfe=0.47 |  |
| ema50_dist_atr | 0.5..2 | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.368 gross=+0.375 PF=inf stop=0.0% mfe=0.96 |  |
| ema50_dist_atr | <-2 | n=2 prof=50.0% [9.5–90.5] net=-0.007 gross=+0.062 PF=0.99 stop=50.0% mfe=0.98 | n=0 |  |
| symbol_group | major | n=5 prof=80.0% [37.6–96.4] net=+0.660 gross=+0.700 PF=4.03 stop=20.0% mfe=1.39 | n=2 prof=50.0% [9.5–90.5] net=-0.388 gross=-0.312 PF=0.26 stop=50.0% mfe=0.50 |  |
| symbol_group | other | n=4 prof=75.0% [30.1–95.4] net=+0.417 gross=+0.444 PF=2.63 stop=25.0% mfe=1.15 | n=4 prof=25.0% [4.6–69.9] net=-0.385 gross=-0.364 PF=0.19 stop=25.0% mfe=0.40 |  |
| funding | <-0.01% | n=9 prof=77.8% [45.3–93.7] net=+0.552 gross=+0.586 PF=3.35 stop=22.2% mfe=1.28 | n=6 prof=33.3% [9.7–70.0] net=-0.386 gross=-0.347 PF=0.22 stop=33.3% mfe=0.43 |  |
| funding_side | fading_crowd | n=9 prof=77.8% [45.3–93.7] net=+0.552 gross=+0.586 PF=3.35 stop=22.2% mfe=1.28 | n=6 prof=33.3% [9.7–70.0] net=-0.386 gross=-0.347 PF=0.22 stop=33.3% mfe=0.43 |  |
| funding_z | -1..1 | n=1 prof=100.0% [20.7–100.0] net=+0.502 gross=+0.525 PF=inf stop=0.0% mfe=1.38 | n=2 prof=0.0% [0.0–65.8] net=-0.684 gross=-0.660 PF=0.00 stop=50.0% mfe=0.30 |  |
| funding_z | <-1 | n=8 prof=75.0% [40.9–92.9] net=+0.558 gross=+0.594 PF=3.11 stop=25.0% mfe=1.27 | n=4 prof=50.0% [15.0–85.0] net=-0.237 gross=-0.191 PF=0.40 stop=25.0% mfe=0.50 |  |
| oi_divergence | down_up | n=5 prof=60.0% [23.1–88.2] net=+0.237 gross=+0.275 PF=1.56 stop=40.0% mfe=1.05 | n=3 prof=33.3% [6.1–79.2] net=-0.602 gross=-0.542 PF=0.13 stop=66.7% mfe=0.49 |  |
| oi_divergence | up_up | n=4 prof=100.0% [51.0–100.0] net=+0.947 gross=+0.975 PF=inf stop=0.0% mfe=1.57 | n=3 prof=33.3% [6.1–79.2] net=-0.170 gross=-0.152 PF=0.42 stop=0.0% mfe=0.37 |  |
| oi_chg_24h | 0..5% | n=2 prof=50.0% [9.5–90.5] net=-0.007 gross=+0.062 PF=0.99 stop=50.0% mfe=0.98 | n=1 prof=0.0% [0.0–79.3] net=-0.539 gross=-0.512 PF=0.00 stop=0.0% mfe=0.03 |  |
| oi_chg_24h | >5% | n=7 prof=85.7% [48.7–97.4] net=+0.712 gross=+0.736 PF=5.86 stop=14.3% mfe=1.37 | n=5 prof=40.0% [11.8–76.9] net=-0.355 gross=-0.314 PF=0.26 stop=40.0% mfe=0.51 |  |
| settlement_bar | settlement | n=9 prof=77.8% [45.3–93.7] net=+0.552 gross=+0.586 PF=3.35 stop=22.2% mfe=1.28 | n=6 prof=33.3% [9.7–70.0] net=-0.386 gross=-0.347 PF=0.22 stop=33.3% mfe=0.43 |  |
| session | 08-16 | n=3 prof=66.7% [20.8–93.9] net=+0.383 gross=+0.417 PF=2.12 stop=33.3% mfe=1.10 | n=1 prof=100.0% [20.7–100.0] net=+0.368 gross=+0.375 PF=inf stop=0.0% mfe=0.96 |  |
| session | other | n=6 prof=83.3% [43.6–97.0] net=+0.637 gross=+0.671 PF=4.51 stop=16.7% mfe=1.37 | n=5 prof=20.0% [3.6–62.4] net=-0.537 gross=-0.491 PF=0.09 stop=40.0% mfe=0.32 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- chosen: T1=1.0R, stop×1.0, T2=2.0R, trail=on
- TRAIN chosen: n=9 prof=77.8% [45.3–93.7] net=+0.668 gross=+0.709 PF=3.84 stop=22.2% mfe=1.49
- TEST chosen: n=6 prof=16.7% [3.0–56.4] net=-0.530 gross=-0.486 PF=0.20 stop=50.0% mfe=0.45
- TEST default: n=6 prof=33.3% [9.7–70.0] net=-0.386 gross=-0.347 PF=0.22 stop=33.3% mfe=0.43

### funding_squeeze_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-07 | 2 | 0.0 | -0.653 |
| 2026-08 | 4 | 75.0 | +0.199 |
| 2026-09 | 2 | 50.0 | -0.306 |

**Filter study** (36 cuts tested — expect ~1.8 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=4 prof=25.0% [4.6–69.9] net=-0.498 gross=-0.475 PF=0.15 stop=50.0% mfe=0.52 | n=3 prof=66.7% [20.8–93.9] net=+0.167 gross=+0.176 PF=1.49 stop=33.3% mfe=0.88 |  |
| btc_aligned | yes | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.366 gross=+0.375 PF=inf stop=0.0% mfe=0.91 |  |
| confluence3 | 0-1 | n=1 prof=0.0% [0.0–79.3] net=-0.286 gross=-0.277 PF=0.00 stop=0.0% mfe=0.52 | n=2 prof=50.0% [9.5–90.5] net=-0.306 gross=-0.298 PF=0.40 stop=50.0% mfe=0.50 |  |
| confluence3 | 2-3 | n=3 prof=33.3% [6.1–79.2] net=-0.568 gross=-0.542 PF=0.17 stop=66.7% mfe=0.52 | n=2 prof=100.0% [34.2–100.0] net=+0.740 gross=+0.750 PF=inf stop=0.0% mfe=1.27 |  |
| risk_pct | 2-4% | n=1 prof=0.0% [0.0–79.3] net=-1.045 gross=-1.000 PF=0.00 stop=100.0% mfe=0.10 | n=0 |  |
| risk_pct | 4-8% | n=2 prof=50.0% [9.5–90.5] net=-0.330 gross=-0.312 PF=0.35 stop=50.0% mfe=0.73 | n=1 prof=100.0% [20.7–100.0] net=+1.114 gross=+1.125 PF=inf stop=0.0% mfe=1.63 |  |
| risk_pct | >8% | n=1 prof=0.0% [0.0–79.3] net=-0.286 gross=-0.277 PF=0.00 stop=0.0% mfe=0.52 | n=3 prof=66.7% [20.8–93.9] net=-0.082 gross=-0.074 PF=0.76 stop=33.3% mfe=0.63 |  |
| hour | 00-08 | n=1 prof=100.0% [20.7–100.0] net=+0.360 gross=+0.375 PF=inf stop=0.0% mfe=0.86 | n=1 prof=100.0% [20.7–100.0] net=+0.401 gross=+0.404 PF=inf stop=0.0% mfe=0.51 |  |
| hour | 08-16 | n=2 prof=0.0% [0.0–65.8] net=-1.032 gross=-1.000 PF=0.00 stop=100.0% mfe=0.34 | n=1 prof=0.0% [0.0–79.3] net=-1.014 gross=-1.000 PF=0.00 stop=100.0% mfe=0.49 |  |
| hour | 16-24 | n=1 prof=0.0% [0.0–79.3] net=-0.286 gross=-0.277 PF=0.00 stop=0.0% mfe=0.52 | n=2 prof=100.0% [34.2–100.0] net=+0.740 gross=+0.750 PF=inf stop=0.0% mfe=1.27 |  |
| weekend | weekday | n=3 prof=33.3% [6.1–79.2] net=-0.315 gross=-0.301 PF=0.28 stop=33.3% mfe=0.66 | n=3 prof=66.7% [20.8–93.9] net=-0.082 gross=-0.074 PF=0.76 stop=33.3% mfe=0.63 |  |
| weekend | weekend | n=1 prof=0.0% [0.0–79.3] net=-1.045 gross=-1.000 PF=0.00 stop=100.0% mfe=0.10 | n=1 prof=100.0% [20.7–100.0] net=+1.114 gross=+1.125 PF=inf stop=0.0% mfe=1.63 |  |
| adx | 20-30 | n=0 | n=1 prof=0.0% [0.0–79.3] net=-1.014 gross=-1.000 PF=0.00 stop=100.0% mfe=0.49 |  |
| adx | <20 | n=1 prof=0.0% [0.0–79.3] net=-1.045 gross=-1.000 PF=0.00 stop=100.0% mfe=0.10 | n=0 |  |
| adx | >30 | n=3 prof=33.3% [6.1–79.2] net=-0.315 gross=-0.301 PF=0.28 stop=33.3% mfe=0.66 | n=3 prof=100.0% [43.8–100.0] net=+0.627 gross=+0.635 PF=inf stop=0.0% mfe=1.01 |  |
| vol_spike | <1.5 | n=2 prof=50.0% [9.5–90.5] net=-0.343 gross=-0.312 PF=0.34 stop=50.0% mfe=0.48 | n=4 prof=75.0% [30.1–95.4] net=+0.217 gross=+0.226 PF=1.86 stop=25.0% mfe=0.88 |  |
| vol_spike | >=1.5 | n=2 prof=0.0% [0.0–65.8] net=-0.653 gross=-0.638 PF=0.00 stop=50.0% mfe=0.55 | n=0 |  |
| ema50_dist_atr | -0.5..0.5 | n=1 prof=0.0% [0.0–79.3] net=-1.045 gross=-1.000 PF=0.00 stop=100.0% mfe=0.10 | n=0 |  |
| ema50_dist_atr | 0.5..2 | n=1 prof=0.0% [0.0–79.3] net=-0.286 gross=-0.277 PF=0.00 stop=0.0% mfe=0.52 | n=1 prof=100.0% [20.7–100.0] net=+0.401 gross=+0.404 PF=inf stop=0.0% mfe=0.51 |  |
| ema50_dist_atr | <-2 | n=2 prof=50.0% [9.5–90.5] net=-0.330 gross=-0.312 PF=0.35 stop=50.0% mfe=0.73 | n=2 prof=100.0% [34.2–100.0] net=+0.740 gross=+0.750 PF=inf stop=0.0% mfe=1.27 |  |
| ema50_dist_atr | >2 | n=0 | n=1 prof=0.0% [0.0–79.3] net=-1.014 gross=-1.000 PF=0.00 stop=100.0% mfe=0.49 |  |
| symbol_group | other | n=4 prof=25.0% [4.6–69.9] net=-0.498 gross=-0.475 PF=0.15 stop=50.0% mfe=0.52 | n=4 prof=75.0% [30.1–95.4] net=+0.217 gross=+0.226 PF=1.86 stop=25.0% mfe=0.88 |  |
| funding | 0.02..0.05% | n=4 prof=25.0% [4.6–69.9] net=-0.498 gross=-0.475 PF=0.15 stop=50.0% mfe=0.52 | n=2 prof=100.0% [34.2–100.0] net=+0.740 gross=+0.750 PF=inf stop=0.0% mfe=1.27 |  |
| funding | >0.05% | n=0 | n=2 prof=50.0% [9.5–90.5] net=-0.306 gross=-0.298 PF=0.40 stop=50.0% mfe=0.50 |  |
| funding_side | fading_crowd | n=4 prof=25.0% [4.6–69.9] net=-0.498 gross=-0.475 PF=0.15 stop=50.0% mfe=0.52 | n=4 prof=75.0% [30.1–95.4] net=+0.217 gross=+0.226 PF=1.86 stop=25.0% mfe=0.88 |  |
| funding_z | -1..1 | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.401 gross=+0.404 PF=inf stop=0.0% mfe=0.51 |  |
| funding_z | 1..2 | n=0 | n=2 prof=100.0% [34.2–100.0] net=+0.740 gross=+0.750 PF=inf stop=0.0% mfe=1.27 |  |
| funding_z | >2 | n=4 prof=25.0% [4.6–69.9] net=-0.498 gross=-0.475 PF=0.15 stop=50.0% mfe=0.52 | n=1 prof=0.0% [0.0–79.3] net=-1.014 gross=-1.000 PF=0.00 stop=100.0% mfe=0.49 |  |
| oi_divergence | down_up | n=0 | n=1 prof=100.0% [20.7–100.0] net=+0.401 gross=+0.404 PF=inf stop=0.0% mfe=0.51 |  |
| oi_divergence | flat | n=0 | n=2 prof=100.0% [34.2–100.0] net=+0.740 gross=+0.750 PF=inf stop=0.0% mfe=1.27 |  |
| oi_divergence | up_up | n=4 prof=25.0% [4.6–69.9] net=-0.498 gross=-0.475 PF=0.15 stop=50.0% mfe=0.52 | n=1 prof=0.0% [0.0–79.3] net=-1.014 gross=-1.000 PF=0.00 stop=100.0% mfe=0.49 |  |
| oi_chg_24h | 0..5% | n=2 prof=50.0% [9.5–90.5] net=-0.343 gross=-0.312 PF=0.34 stop=50.0% mfe=0.48 | n=1 prof=100.0% [20.7–100.0] net=+0.366 gross=+0.375 PF=inf stop=0.0% mfe=0.91 |  |
| oi_chg_24h | >5% | n=2 prof=0.0% [0.0–65.8] net=-0.653 gross=-0.638 PF=0.00 stop=50.0% mfe=0.55 | n=3 prof=66.7% [20.8–93.9] net=+0.167 gross=+0.176 PF=1.49 stop=33.3% mfe=0.88 |  |
| settlement_bar | settlement | n=4 prof=25.0% [4.6–69.9] net=-0.498 gross=-0.475 PF=0.15 stop=50.0% mfe=0.52 | n=4 prof=75.0% [30.1–95.4] net=+0.217 gross=+0.226 PF=1.86 stop=25.0% mfe=0.88 |  |
| session | 08-16 | n=2 prof=0.0% [0.0–65.8] net=-1.032 gross=-1.000 PF=0.00 stop=100.0% mfe=0.34 | n=1 prof=0.0% [0.0–79.3] net=-1.014 gross=-1.000 PF=0.00 stop=100.0% mfe=0.49 |  |
| session | other | n=2 prof=50.0% [9.5–90.5] net=+0.037 gross=+0.049 PF=1.26 stop=0.0% mfe=0.69 | n=3 prof=100.0% [43.8–100.0] net=+0.627 gross=+0.635 PF=inf stop=0.0% mfe=1.01 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- no combo reaches net>0 on train

## (f) Fill model — passive (maker) entry vs market (taker)

Limit rests at the next 15m open improved by offset×ATR; fills only when price trades THROUGH it within `wait` bars (touch ≠ fill); maker fee 0.020% on entry + take-profits, stops still taker+slippage. 'market same subset' re-costs the identical filled trades at taker fees, so (limit − market same subset) = pure fee effect and (market same subset − baseline) = selection effect of waiting for a fill. Unfilled signals are lost opportunities, not losses.


### liquidity_sweep_long (1h) — market baseline: n=955 prof=50.8% [47.6–53.9] net=-0.238 gross=-0.083 PF=0.56 stop=46.5% mfe=0.94

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=955 prof=51.9% [48.8–55.1] net=-0.160 gross=-0.083 PF=0.69 stop=46.5% mfe=0.93 | n=955 prof=50.8% [47.6–53.9] net=-0.238 gross=-0.083 PF=0.56 stop=46.5% mfe=0.93 |
| 0.0 | 4 | 100% | n=955 prof=51.9% [48.8–55.1] net=-0.160 gross=-0.083 PF=0.69 stop=46.5% mfe=0.93 | n=955 prof=50.8% [47.6–53.9] net=-0.238 gross=-0.083 PF=0.56 stop=46.5% mfe=0.93 |
| 0.0 | 8 | 100% | n=955 prof=51.9% [48.8–55.1] net=-0.160 gross=-0.083 PF=0.69 stop=46.5% mfe=0.93 | n=955 prof=50.8% [47.6–53.9] net=-0.238 gross=-0.083 PF=0.56 stop=46.5% mfe=0.93 |
| 0.15 | 2 | 75% | n=713 prof=53.2% [49.5–56.8] net=-0.131 gross=-0.045 PF=0.74 stop=45.0% mfe=1.01 | n=713 prof=51.8% [48.1–55.4] net=-0.222 gross=-0.045 PF=0.59 stop=45.0% mfe=1.01 |
| 0.15 | 4 | 81% | n=772 prof=52.7% [49.2–56.2] net=-0.145 gross=-0.057 PF=0.71 stop=45.6% mfe=1.00 | n=772 prof=51.2% [47.6–54.7] net=-0.237 gross=-0.057 PF=0.56 stop=45.6% mfe=1.00 |
| 0.15 | 8 | 88% | n=836 prof=53.3% [50.0–56.7] net=-0.138 gross=-0.049 PF=0.73 stop=45.0% mfe=1.01 | n=836 prof=51.6% [48.2–54.9] net=-0.232 gross=-0.049 PF=0.57 stop=45.0% mfe=1.01 |
| 0.3 | 2 | 51% | n=484 prof=57.0% [52.6–61.4] net=-0.080 gross=+0.018 PF=0.83 stop=41.3% mfe=1.10 | n=484 prof=54.3% [49.9–58.7] net=-0.188 gross=+0.018 PF=0.63 stop=41.3% mfe=1.10 |
| 0.3 | 4 | 60% | n=577 prof=56.7% [52.6–60.7] net=-0.099 gross=+0.001 PF=0.79 stop=41.8% mfe=1.08 | n=577 prof=53.6% [49.5–57.6] net=-0.209 gross=+0.001 PF=0.59 stop=41.8% mfe=1.08 |
| 0.3 | 8 | 73% | n=699 prof=56.8% [53.1–60.4] net=-0.108 gross=-0.003 PF=0.77 stop=41.8% mfe=1.08 | n=699 prof=54.1% [50.4–57.7] net=-0.220 gross=-0.003 PF=0.58 stop=41.8% mfe=1.08 |

### trend_pullback_short (4h) — market baseline: n=476 prof=55.9% [51.4–60.3] net=-0.104 gross=-0.033 PF=0.75 stop=37.4% mfe=0.83

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=476 prof=56.1% [51.6–60.5] net=-0.073 gross=-0.033 PF=0.82 stop=37.4% mfe=0.83 | n=476 prof=55.9% [51.4–60.3] net=-0.104 gross=-0.033 PF=0.75 stop=37.4% mfe=0.83 |
| 0.0 | 4 | 100% | n=476 prof=56.1% [51.6–60.5] net=-0.073 gross=-0.033 PF=0.82 stop=37.4% mfe=0.83 | n=476 prof=55.9% [51.4–60.3] net=-0.104 gross=-0.033 PF=0.75 stop=37.4% mfe=0.83 |
| 0.0 | 8 | 100% | n=476 prof=56.1% [51.6–60.5] net=-0.073 gross=-0.033 PF=0.82 stop=37.4% mfe=0.83 | n=476 prof=55.9% [51.4–60.3] net=-0.104 gross=-0.033 PF=0.75 stop=37.4% mfe=0.83 |
| 0.15 | 2 | 41% | n=197 prof=61.4% [54.5–67.9] net=+0.016 gross=+0.061 PF=1.04 stop=36.0% mfe=0.96 | n=197 prof=61.4% [54.5–67.9] net=-0.023 gross=+0.061 PF=0.94 stop=36.0% mfe=0.96 |
| 0.15 | 4 | 58% | n=278 prof=59.7% [53.9–65.3] net=-0.033 gross=+0.011 PF=0.92 stop=37.8% mfe=0.90 | n=278 prof=59.7% [53.9–65.3] net=-0.069 gross=+0.011 PF=0.83 stop=37.8% mfe=0.90 |
| 0.15 | 8 | 67% | n=320 prof=60.6% [55.2–65.8] net=-0.030 gross=+0.013 PF=0.92 stop=37.2% mfe=0.90 | n=320 prof=60.6% [55.2–65.8] net=-0.066 gross=+0.013 PF=0.84 stop=37.2% mfe=0.90 |
| 0.3 | 2 | 14% | n=67 prof=52.2% [40.5–63.7] net=-0.168 gross=-0.123 PF=0.66 stop=47.8% mfe=0.93 | n=67 prof=52.2% [40.5–63.7] net=-0.211 gross=-0.123 PF=0.59 stop=47.8% mfe=0.93 |
| 0.3 | 4 | 28% | n=131 prof=58.8% [50.2–66.8] net=-0.087 gross=-0.045 PF=0.79 stop=40.5% mfe=0.93 | n=131 prof=58.8% [50.2–66.8] net=-0.126 gross=-0.045 PF=0.71 stop=40.5% mfe=0.93 |
| 0.3 | 8 | 41% | n=193 prof=59.1% [52.0–65.8] net=-0.086 gross=-0.041 PF=0.80 stop=40.4% mfe=0.92 | n=193 prof=59.1% [52.0–65.8] net=-0.126 gross=-0.041 PF=0.71 stop=40.4% mfe=0.92 |

### failed_breakout_short (4h) — market baseline: n=341 prof=54.8% [49.5–60.0] net=-0.075 gross=-0.006 PF=0.84 stop=41.9% mfe=0.93

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=341 prof=55.1% [49.8–60.3] net=-0.044 gross=-0.006 PF=0.90 stop=41.9% mfe=0.93 | n=341 prof=54.8% [49.5–60.0] net=-0.075 gross=-0.006 PF=0.84 stop=41.9% mfe=0.93 |
| 0.0 | 4 | 100% | n=341 prof=55.1% [49.8–60.3] net=-0.044 gross=-0.006 PF=0.90 stop=41.9% mfe=0.93 | n=341 prof=54.8% [49.5–60.0] net=-0.075 gross=-0.006 PF=0.84 stop=41.9% mfe=0.93 |
| 0.0 | 8 | 100% | n=341 prof=55.1% [49.8–60.3] net=-0.044 gross=-0.006 PF=0.90 stop=41.9% mfe=0.93 | n=341 prof=54.8% [49.5–60.0] net=-0.075 gross=-0.006 PF=0.84 stop=41.9% mfe=0.93 |
| 0.15 | 2 | 57% | n=196 prof=57.1% [50.1–63.9] net=-0.052 gross=-0.011 PF=0.89 stop=42.9% mfe=0.96 | n=196 prof=56.1% [49.1–62.9] net=-0.089 gross=-0.011 PF=0.81 stop=42.9% mfe=0.96 |
| 0.15 | 4 | 69% | n=235 prof=57.4% [51.1–63.6] net=-0.038 gross=+0.003 PF=0.91 stop=42.1% mfe=0.97 | n=235 prof=56.2% [49.8–62.4] net=-0.076 gross=+0.003 PF=0.83 stop=42.1% mfe=0.97 |
| 0.15 | 8 | 78% | n=266 prof=58.3% [52.3–64.0] net=-0.018 gross=+0.022 PF=0.96 stop=41.4% mfe=0.98 | n=266 prof=57.1% [51.1–62.9] net=-0.057 gross=+0.022 PF=0.87 stop=41.4% mfe=0.98 |
| 0.3 | 2 | 27% | n=92 prof=57.6% [47.4–67.2] net=-0.088 gross=-0.046 PF=0.80 stop=42.4% mfe=0.93 | n=92 prof=55.4% [45.3–65.2] net=-0.129 gross=-0.046 PF=0.71 stop=42.4% mfe=0.93 |
| 0.3 | 4 | 40% | n=137 prof=57.7% [49.3–65.6] net=-0.090 gross=-0.043 PF=0.80 stop=42.3% mfe=0.96 | n=137 prof=54.7% [46.4–62.8] net=-0.139 gross=-0.043 PF=0.70 stop=42.3% mfe=0.96 |
| 0.3 | 8 | 54% | n=184 prof=57.1% [49.8–64.0] net=-0.088 gross=-0.038 PF=0.81 stop=42.9% mfe=0.96 | n=184 prof=54.9% [47.7–61.9] net=-0.139 gross=-0.038 PF=0.70 stop=42.9% mfe=0.96 |

### rsi_bounce_long (4h) — market baseline: n=275 prof=51.6% [45.7–57.5] net=-0.093 gross=-0.044 PF=0.75 stop=29.8% mfe=0.71

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=275 prof=52.4% [46.5–58.2] net=-0.074 gross=-0.044 PF=0.80 stop=29.8% mfe=0.71 | n=275 prof=51.6% [45.7–57.5] net=-0.093 gross=-0.044 PF=0.75 stop=29.8% mfe=0.71 |
| 0.0 | 4 | 100% | n=275 prof=52.4% [46.5–58.2] net=-0.074 gross=-0.044 PF=0.80 stop=29.8% mfe=0.71 | n=275 prof=51.6% [45.7–57.5] net=-0.093 gross=-0.044 PF=0.75 stop=29.8% mfe=0.71 |
| 0.0 | 8 | 100% | n=275 prof=52.4% [46.5–58.2] net=-0.074 gross=-0.044 PF=0.80 stop=29.8% mfe=0.71 | n=275 prof=51.6% [45.7–57.5] net=-0.093 gross=-0.044 PF=0.75 stop=29.8% mfe=0.71 |
| 0.15 | 2 | 36% | n=100 prof=46.0% [36.6–55.7] net=-0.177 gross=-0.151 PF=0.60 stop=37.0% mfe=0.69 | n=100 prof=45.0% [35.6–54.8] net=-0.194 gross=-0.151 PF=0.57 stop=37.0% mfe=0.69 |
| 0.15 | 4 | 54% | n=148 prof=51.4% [43.4–59.3] net=-0.117 gross=-0.088 PF=0.71 stop=33.8% mfe=0.73 | n=148 prof=50.7% [42.7–58.6] net=-0.135 gross=-0.088 PF=0.67 stop=33.8% mfe=0.73 |
| 0.15 | 8 | 62% | n=171 prof=52.6% [45.2–60.0] net=-0.101 gross=-0.071 PF=0.74 stop=32.7% mfe=0.73 | n=171 prof=52.0% [44.6–59.4] net=-0.120 gross=-0.071 PF=0.70 stop=32.7% mfe=0.73 |
| 0.3 | 2 | 10% | n=28 prof=71.4% [52.9–84.7] net=+0.167 gross=+0.190 PF=1.67 stop=21.4% mfe=0.94 | n=28 prof=71.4% [52.9–84.7] net=+0.148 gross=+0.190 PF=1.58 stop=21.4% mfe=0.94 |
| 0.3 | 4 | 23% | n=62 prof=56.5% [44.1–68.1] net=-0.054 gross=-0.024 PF=0.85 stop=32.3% mfe=0.78 | n=62 prof=54.8% [42.5–66.6] net=-0.075 gross=-0.024 PF=0.80 stop=32.3% mfe=0.78 |
| 0.3 | 8 | 33% | n=91 prof=54.9% [44.7–64.8] net=-0.072 gross=-0.043 PF=0.81 stop=34.1% mfe=0.76 | n=91 prof=53.8% [43.7–63.7] net=-0.092 gross=-0.043 PF=0.77 stop=34.1% mfe=0.76 |

### range_reversion_short (4h) — market baseline: n=45 prof=75.6% [61.3–85.8] net=+0.193 gross=+0.296 PF=1.71 stop=24.4% mfe=1.06

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=45 prof=75.6% [61.3–85.8] net=+0.250 gross=+0.296 PF=1.96 stop=24.4% mfe=1.06 | n=45 prof=75.6% [61.3–85.8] net=+0.193 gross=+0.296 PF=1.71 stop=24.4% mfe=1.06 |
| 0.0 | 4 | 100% | n=45 prof=75.6% [61.3–85.8] net=+0.250 gross=+0.296 PF=1.96 stop=24.4% mfe=1.06 | n=45 prof=75.6% [61.3–85.8] net=+0.193 gross=+0.296 PF=1.71 stop=24.4% mfe=1.06 |
| 0.0 | 8 | 100% | n=45 prof=75.6% [61.3–85.8] net=+0.250 gross=+0.296 PF=1.96 stop=24.4% mfe=1.06 | n=45 prof=75.6% [61.3–85.8] net=+0.193 gross=+0.296 PF=1.71 stop=24.4% mfe=1.06 |
| 0.15 | 2 | 60% | n=27 prof=77.8% [59.2–89.4] net=+0.248 gross=+0.303 PF=2.04 stop=22.2% mfe=1.01 | n=27 prof=77.8% [59.2–89.4] net=+0.178 gross=+0.303 PF=1.72 stop=22.2% mfe=1.01 |
| 0.15 | 4 | 62% | n=28 prof=78.6% [60.5–89.8] net=+0.279 gross=+0.332 PF=2.22 stop=21.4% mfe=1.03 | n=28 prof=78.6% [60.5–89.8] net=+0.210 gross=+0.332 PF=1.88 stop=21.4% mfe=1.03 |
| 0.15 | 8 | 69% | n=31 prof=74.2% [56.8–86.3] net=+0.196 gross=+0.252 PF=1.71 stop=25.8% mfe=1.00 | n=31 prof=74.2% [56.8–86.3] net=+0.128 gross=+0.252 PF=1.44 stop=25.8% mfe=1.00 |
| 0.3 | 2 | 31% | n=14 prof=71.4% [45.4–88.3] net=+0.275 gross=+0.336 PF=1.90 stop=28.6% mfe=1.33 | n=14 prof=71.4% [45.4–88.3] net=+0.176 gross=+0.336 PF=1.55 stop=28.6% mfe=1.33 |
| 0.3 | 4 | 40% | n=18 prof=72.2% [49.1–87.5] net=+0.267 gross=+0.326 PF=1.89 stop=27.8% mfe=1.29 | n=18 prof=72.2% [49.1–87.5] net=+0.177 gross=+0.326 PF=1.56 stop=27.8% mfe=1.29 |
| 0.3 | 8 | 53% | n=24 prof=75.0% [55.1–88.0] net=+0.233 gross=+0.300 PF=1.86 stop=25.0% mfe=1.21 | n=24 prof=75.0% [55.1–88.0] net=+0.137 gross=+0.300 PF=1.49 stop=25.0% mfe=1.21 |

### range_reversion_long (4h) — market baseline: n=36 prof=50.0% [34.5–65.5] net=-0.319 gross=-0.196 PF=0.43 stop=50.0% mfe=0.77

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=36 prof=50.0% [34.5–65.5] net=-0.220 gross=-0.158 PF=0.59 stop=50.0% mfe=0.82 | n=36 prof=50.0% [34.5–65.5] net=-0.282 gross=-0.158 PF=0.49 stop=50.0% mfe=0.82 |
| 0.0 | 4 | 100% | n=36 prof=50.0% [34.5–65.5] net=-0.220 gross=-0.158 PF=0.59 stop=50.0% mfe=0.82 | n=36 prof=50.0% [34.5–65.5] net=-0.282 gross=-0.158 PF=0.49 stop=50.0% mfe=0.82 |
| 0.0 | 8 | 100% | n=36 prof=50.0% [34.5–65.5] net=-0.220 gross=-0.158 PF=0.59 stop=50.0% mfe=0.82 | n=36 prof=50.0% [34.5–65.5] net=-0.282 gross=-0.158 PF=0.49 stop=50.0% mfe=0.82 |
| 0.15 | 2 | 50% | n=18 prof=38.9% [20.3–61.4] net=-0.479 gross=-0.390 PF=0.29 stop=61.1% mfe=0.80 | n=18 prof=38.9% [20.3–61.4] net=-0.550 gross=-0.390 PF=0.23 stop=61.1% mfe=0.80 |
| 0.15 | 4 | 72% | n=26 prof=46.2% [28.8–64.5] net=-0.318 gross=-0.238 PF=0.46 stop=53.8% mfe=0.82 | n=26 prof=46.2% [28.8–64.5] net=-0.388 gross=-0.238 PF=0.38 stop=53.8% mfe=0.82 |
| 0.15 | 8 | 75% | n=27 prof=44.4% [27.6–62.7] net=-0.347 gross=-0.267 PF=0.43 stop=55.6% mfe=0.80 | n=27 prof=44.4% [27.6–62.7] net=-0.416 gross=-0.267 PF=0.35 stop=55.6% mfe=0.80 |
| 0.3 | 2 | 25% | n=9 prof=55.6% [26.7–81.1] net=-0.249 gross=+0.014 PF=0.62 stop=44.4% mfe=2.99 | n=9 prof=55.6% [26.7–81.1] net=-0.492 gross=+0.014 PF=0.38 stop=44.4% mfe=2.99 |
| 0.3 | 4 | 42% | n=15 prof=66.7% [41.7–84.8] net=+0.056 gross=+0.237 PF=1.12 stop=33.3% mfe=2.30 | n=15 prof=66.7% [41.7–84.8] net=-0.131 gross=+0.237 PF=0.76 stop=33.3% mfe=2.30 |
| 0.3 | 8 | 56% | n=20 prof=60.0% [38.7–78.1] net=-0.091 gross=+0.065 PF=0.82 stop=40.0% mfe=1.88 | n=20 prof=60.0% [38.7–78.1] net=-0.247 gross=+0.065 PF=0.58 stop=40.0% mfe=1.88 |

### funding_squeeze_long (4h) — market baseline: n=15 prof=60.0% [35.7–80.2] net=+0.138 gross=+0.213 PF=1.40 stop=26.7% mfe=0.94

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=15 prof=60.0% [35.7–80.2] net=+0.177 gross=+0.213 PF=1.52 stop=26.7% mfe=0.94 | n=15 prof=60.0% [35.7–80.2] net=+0.138 gross=+0.213 PF=1.40 stop=26.7% mfe=0.94 |
| 0.0 | 4 | 100% | n=15 prof=60.0% [35.7–80.2] net=+0.177 gross=+0.213 PF=1.52 stop=26.7% mfe=0.94 | n=15 prof=60.0% [35.7–80.2] net=+0.138 gross=+0.213 PF=1.40 stop=26.7% mfe=0.94 |
| 0.0 | 8 | 100% | n=15 prof=60.0% [35.7–80.2] net=+0.177 gross=+0.213 PF=1.52 stop=26.7% mfe=0.94 | n=15 prof=60.0% [35.7–80.2] net=+0.138 gross=+0.213 PF=1.40 stop=26.7% mfe=0.94 |
| 0.15 | 2 | 53% | n=8 prof=62.5% [30.6–86.3] net=+0.403 gross=+0.423 PF=2.38 stop=25.0% mfe=1.08 | n=8 prof=62.5% [30.6–86.3] net=+0.377 gross=+0.423 PF=2.26 stop=25.0% mfe=1.08 |
| 0.15 | 4 | 53% | n=8 prof=62.5% [30.6–86.3] net=+0.403 gross=+0.423 PF=2.38 stop=25.0% mfe=1.08 | n=8 prof=62.5% [30.6–86.3] net=+0.377 gross=+0.423 PF=2.26 stop=25.0% mfe=1.08 |
| 0.15 | 8 | 67% | n=10 prof=60.0% [31.3–83.2] net=+0.382 gross=+0.405 PF=2.35 stop=20.0% mfe=1.03 | n=10 prof=60.0% [31.3–83.2] net=+0.352 gross=+0.405 PF=2.22 stop=20.0% mfe=1.03 |
| 0.3 | 2 | 20% | n=3 prof=66.7% [20.8–93.9] net=+0.390 gross=+0.417 PF=2.11 stop=33.3% mfe=1.24 | n=3 prof=66.7% [20.8–93.9] net=+0.354 gross=+0.417 PF=1.98 stop=33.3% mfe=1.24 |
| 0.3 | 4 | 40% | n=6 prof=50.0% [18.8–81.2] net=+0.179 gross=+0.204 PF=1.48 stop=33.3% mfe=1.03 | n=6 prof=50.0% [18.8–81.2] net=+0.151 gross=+0.204 PF=1.39 stop=33.3% mfe=1.03 |
| 0.3 | 8 | 53% | n=8 prof=62.5% [30.6–86.3] net=+0.334 gross=+0.359 PF=2.18 stop=25.0% mfe=1.14 | n=8 prof=62.5% [30.6–86.3] net=+0.299 gross=+0.359 PF=2.03 stop=25.0% mfe=1.14 |

### funding_squeeze_short (4h) — market baseline: n=8 prof=50.0% [21.5–78.5] net=-0.151 gross=-0.125 PF=0.64 stop=37.5% mfe=0.70

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=8 prof=50.0% [21.5–78.5] net=-0.141 gross=-0.125 PF=0.67 stop=37.5% mfe=0.70 | n=8 prof=50.0% [21.5–78.5] net=-0.151 gross=-0.125 PF=0.64 stop=37.5% mfe=0.70 |
| 0.0 | 4 | 100% | n=8 prof=50.0% [21.5–78.5] net=-0.141 gross=-0.125 PF=0.67 stop=37.5% mfe=0.70 | n=8 prof=50.0% [21.5–78.5] net=-0.151 gross=-0.125 PF=0.64 stop=37.5% mfe=0.70 |
| 0.0 | 8 | 100% | n=8 prof=50.0% [21.5–78.5] net=-0.141 gross=-0.125 PF=0.67 stop=37.5% mfe=0.70 | n=8 prof=50.0% [21.5–78.5] net=-0.151 gross=-0.125 PF=0.64 stop=37.5% mfe=0.70 |
| 0.15 | 2 | 38% | n=3 prof=66.7% [20.8–93.9] net=+0.220 gross=+0.234 PF=4.19 stop=0.0% mfe=0.84 | n=3 prof=66.7% [20.8–93.9] net=+0.207 gross=+0.234 PF=3.94 stop=0.0% mfe=0.84 |
| 0.15 | 4 | 62% | n=5 prof=60.0% [23.1–88.2] net=+0.025 gross=+0.046 PF=1.10 stop=20.0% mfe=0.77 | n=5 prof=60.0% [23.1–88.2] net=+0.011 gross=+0.046 PF=1.04 stop=20.0% mfe=0.77 |
| 0.15 | 8 | 62% | n=5 prof=60.0% [23.1–88.2] net=+0.025 gross=+0.046 PF=1.10 stop=20.0% mfe=0.77 | n=5 prof=60.0% [23.1–88.2] net=+0.011 gross=+0.046 PF=1.04 stop=20.0% mfe=0.77 |
| 0.3 | 2 | 0% | n=0 | n=0 |
| 0.3 | 4 | 0% | n=0 | n=0 |
| 0.3 | 8 | 0% | n=0 | n=0 |

## (e) Funding-squeeze parameter sweep (chosen on TRAIN, reported on TEST)

Grid: funding_min × oi_min × price_flat × settlement_only. Selection = max profitable% s.t. net>0 and n≥30 on TRAIN; every combo's TEST is listed so the landscape is visible (the top row is a selected result — treat it as optimistic).


### funding_squeeze_long

| funding_min | oi_min% | flat% | settle | TRAIN | TEST | ALL |
|---|---|---|---|---|---|---|
| 0.01% | 3.0 | 3.0 | n | n=86 prof=59.3% [48.7–69.1] net=+0.024 gross=+0.059 PF=1.06 stop=34.9% mfe=0.83 | n=58 prof=44.8% [32.7–57.5] net=-0.230 gross=-0.195 PF=0.54 stop=43.1% mfe=0.66 | n=144 prof=53.5% [45.3–61.4] net=-0.078 gross=-0.043 PF=0.82 stop=38.2% mfe=0.76 |
| 0.01% | 3.0 | 5.0 | n | n=110 prof=58.2% [48.8–67.0] net=+0.030 gross=+0.063 PF=1.08 stop=35.5% mfe=0.84 | n=74 prof=47.3% [36.3–58.5] net=-0.123 gross=-0.090 PF=0.71 stop=35.1% mfe=0.73 | n=184 prof=53.8% [46.6–60.9] net=-0.032 gross=+0.001 PF=0.92 stop=35.3% mfe=0.80 |
| 0.01% | 3.0 | 3.0 | y | n=57 prof=57.9% [45.0–69.8] net=+0.027 gross=+0.067 PF=1.06 stop=38.6% mfe=0.85 | n=38 prof=44.7% [30.1–60.3] net=-0.223 gross=-0.187 PF=0.55 stop=42.1% mfe=0.67 | n=95 prof=52.6% [42.7–62.4] net=-0.073 gross=-0.035 PF=0.84 stop=40.0% mfe=0.78 |
| 0.03% | 0.0 | 3.0 | n | n=33 prof=54.5% [38.0–70.2] net=+0.046 gross=+0.101 PF=1.11 stop=36.4% mfe=0.86 | n=22 prof=50.0% [30.7–69.3] net=-0.253 gross=-0.161 PF=0.46 stop=36.4% mfe=0.66 | n=55 prof=52.7% [39.8–65.3] net=-0.074 gross=-0.004 PF=0.83 stop=36.4% mfe=0.78 |
| 0.03% | 0.0 | 5.0 | n | n=39 prof=53.8% [38.6–68.4] net=+0.010 gross=+0.059 PF=1.02 stop=38.5% mfe=0.85 | n=26 prof=50.0% [32.1–67.9] net=-0.189 gross=-0.106 PF=0.56 stop=30.8% mfe=0.69 | n=65 prof=52.3% [40.4–64.0] net=-0.070 gross=-0.007 PF=0.84 stop=35.4% mfe=0.79 |
| 0.02% | 3.0 | 3.0 | n | n=32 prof=53.1% [36.4–69.1] net=+0.016 gross=+0.052 PF=1.04 stop=40.6% mfe=0.85 | n=22 prof=36.4% [19.7–57.0] net=-0.377 gross=-0.343 PF=0.30 stop=45.5% mfe=0.54 | n=54 prof=46.3% [33.7–59.4] net=-0.144 gross=-0.109 PF=0.70 stop=42.6% mfe=0.72 |
| 0.02% | 3.0 | 5.0 | n | n=40 prof=52.5% [37.5–67.1] net=+0.013 gross=+0.046 PF=1.03 stop=42.5% mfe=0.87 | n=28 prof=42.9% [26.5–60.9] net=-0.207 gross=-0.175 PF=0.50 stop=32.1% mfe=0.64 | n=68 prof=48.5% [37.1–60.2] net=-0.078 gross=-0.045 PF=0.82 stop=38.2% mfe=0.77 |
| 0.05% | 0.0 | 5.0 | n | n=17 prof=58.8% [36.0–78.4] net=+0.122 gross=+0.185 PF=1.36 stop=23.5% mfe=0.88 | n=12 prof=16.7% [4.7–44.8] net=-0.543 gross=-0.505 PF=0.09 stop=41.7% mfe=0.35 | n=29 prof=41.4% [25.5–59.3] net=-0.153 gross=-0.101 PF=0.66 stop=31.0% mfe=0.66 |
| 0.03% | 3.0 | 3.0 | y | n=16 prof=56.2% [33.2–76.9] net=+0.074 gross=+0.120 PF=1.16 stop=43.8% mfe=0.93 | n=11 prof=18.2% [5.1–47.7] net=-0.687 gross=-0.644 PF=0.08 stop=63.6% mfe=0.34 | n=27 prof=40.7% [24.5–59.3] net=-0.236 gross=-0.191 PF=0.59 stop=51.9% mfe=0.69 |
| 0.03% | 3.0 | 5.0 | y | n=18 prof=55.6% [33.7–75.4] net=+0.070 gross=+0.114 PF=1.15 stop=44.4% mfe=0.93 | n=13 prof=23.1% [8.2–50.3] net=-0.476 gross=-0.435 PF=0.22 stop=46.2% mfe=0.43 | n=31 prof=41.9% [26.4–59.2] net=-0.159 gross=-0.116 PF=0.70 stop=45.2% mfe=0.72 |
| 0.03% | 3.0 | 3.0 | n | n=20 prof=55.0% [34.2–74.2] net=+0.077 gross=+0.119 PF=1.18 stop=40.0% mfe=0.90 | n=14 prof=28.6% [11.7–54.6] net=-0.475 gross=-0.439 PF=0.24 stop=50.0% mfe=0.52 | n=34 prof=44.1% [28.9–60.5] net=-0.150 gross=-0.111 PF=0.71 stop=44.1% mfe=0.74 |
| 0.02% | 3.0 | 3.0 | y | n=22 prof=54.5% [34.7–73.1] net=-0.014 gross=+0.030 PF=0.97 stop=45.5% mfe=0.84 | n=16 prof=31.2% [14.2–55.6] net=-0.476 gross=-0.438 PF=0.18 stop=50.0% mfe=0.41 | n=38 prof=44.7% [30.1–60.3] net=-0.209 gross=-0.167 PF=0.60 stop=47.4% mfe=0.66 |

### funding_squeeze_short

| funding_min | oi_min% | flat% | settle | TRAIN | TEST | ALL |
|---|---|---|---|---|---|---|
| 0.01% | 3.0 | 5.0 | y | n=191 prof=62.3% [55.3–68.9] net=+0.046 gross=+0.080 PF=1.14 stop=30.4% mfe=0.83 | n=128 prof=57.0% [48.4–65.3] net=-0.010 gross=+0.017 PF=0.98 stop=40.6% mfe=0.87 | n=319 prof=60.2% [54.7–65.4] net=+0.023 gross=+0.054 PF=1.06 stop=34.5% mfe=0.84 |
| 0.01% | 0.0 | 3.0 | y | n=288 prof=61.5% [55.7–66.9] net=+0.065 gross=+0.103 PF=1.19 stop=30.9% mfe=0.88 | n=192 prof=52.1% [45.0–59.0] net=-0.087 gross=-0.058 PF=0.81 stop=42.7% mfe=0.81 | n=480 prof=57.7% [53.2–62.0] net=+0.004 gross=+0.039 PF=1.01 stop=35.6% mfe=0.85 |
| 0.01% | 3.0 | 3.0 | y | n=156 prof=61.5% [53.7–68.8] net=+0.054 gross=+0.088 PF=1.15 stop=32.1% mfe=0.84 | n=104 prof=53.8% [44.3–63.1] net=-0.062 gross=-0.033 PF=0.86 stop=41.3% mfe=0.82 | n=260 prof=58.5% [52.4–64.3] net=+0.007 gross=+0.040 PF=1.02 stop=35.8% mfe=0.83 |
| 0.01% | 0.0 | 5.0 | y | n=337 prof=60.8% [55.5–65.9] net=+0.040 gross=+0.076 PF=1.11 stop=32.6% mfe=0.87 | n=226 prof=53.1% [46.6–59.5] net=-0.089 gross=-0.060 PF=0.81 stop=43.8% mfe=0.80 | n=563 prof=57.7% [53.6–61.7] net=-0.012 gross=+0.021 PF=0.97 stop=37.1% mfe=0.84 |
| 0.01% | 0.0 | 3.0 | n | n=342 prof=60.5% [55.3–65.6] net=+0.052 gross=+0.089 PF=1.15 stop=31.0% mfe=0.88 | n=228 prof=50.0% [43.6–56.4] net=-0.129 gross=-0.100 PF=0.73 stop=45.6% mfe=0.79 | n=570 prof=56.3% [52.2–60.3] net=-0.021 gross=+0.013 PF=0.95 stop=36.8% mfe=0.84 |
| 0.01% | 0.0 | 5.0 | n | n=396 prof=59.6% [54.7–64.3] net=+0.023 gross=+0.059 PF=1.06 stop=33.3% mfe=0.86 | n=265 prof=51.3% [45.3–57.3] net=-0.126 gross=-0.096 PF=0.74 stop=45.3% mfe=0.79 | n=661 prof=56.3% [52.5–60.0] net=-0.037 gross=-0.004 PF=0.91 stop=38.1% mfe=0.83 |
| 0.01% | 3.0 | 3.0 | n | n=198 prof=59.1% [52.1–65.7] net=+0.002 gross=+0.037 PF=1.01 stop=33.3% mfe=0.83 | n=132 prof=54.5% [46.0–62.8] net=-0.033 gross=-0.005 PF=0.92 stop=40.2% mfe=0.83 | n=330 prof=57.3% [51.9–62.5] net=-0.012 gross=+0.021 PF=0.97 stop=36.1% mfe=0.83 |
| 0.05% | 3.0 | 3.0 | y | n=1 prof=100.0% [20.7–100.0] net=+0.516 gross=+0.525 PF=inf stop=0.0% mfe=1.30 | n=2 prof=50.0% [9.5–90.5] net=-0.306 gross=-0.298 PF=0.40 stop=50.0% mfe=0.39 | n=3 prof=66.7% [20.8–93.9] net=-0.032 gross=-0.024 PF=0.91 stop=33.3% mfe=0.69 |
| 0.05% | 3.0 | 5.0 | y | n=2 prof=100.0% [34.2–100.0] net=+0.514 gross=+0.525 PF=inf stop=0.0% mfe=1.18 | n=2 prof=100.0% [34.2–100.0] net=+0.384 gross=+0.390 PF=inf stop=0.0% mfe=0.67 | n=4 prof=100.0% [51.0–100.0] net=+0.449 gross=+0.457 PF=inf stop=0.0% mfe=0.93 |
| 0.05% | 0.0 | 3.0 | y | n=3 prof=66.7% [20.8–93.9] net=+0.135 gross=+0.143 PF=1.40 stop=33.3% mfe=0.86 | n=2 prof=50.0% [9.5–90.5] net=-0.385 gross=-0.377 PF=0.24 stop=50.0% mfe=0.35 | n=5 prof=60.0% [23.1–88.2] net=-0.073 gross=-0.065 PF=0.82 stop=40.0% mfe=0.66 |
| 0.05% | 0.0 | 5.0 | y | n=3 prof=66.7% [20.8–93.9] net=+0.007 gross=+0.017 PF=1.02 stop=33.3% mfe=0.81 | n=3 prof=100.0% [43.8–100.0] net=+0.327 gross=+0.332 PF=inf stop=0.0% mfe=0.74 | n=6 prof=83.3% [43.6–97.0] net=+0.167 gross=+0.174 PF=2.00 stop=16.7% mfe=0.77 |
| 0.05% | 3.0 | 3.0 | n | n=3 prof=66.7% [20.8–93.9] net=+0.007 gross=+0.017 PF=1.02 stop=33.3% mfe=1.00 | n=3 prof=33.3% [6.1–79.2] net=-0.652 gross=-0.645 PF=0.03 stop=66.7% mfe=0.20 | n=6 prof=50.0% [18.8–81.2] net=-0.322 gross=-0.314 PF=0.36 stop=50.0% mfe=0.60 |

## (d) What would ship (TEST numbers; filter + management selected on TRAIN)

| signal | tf | default TEST | mgmt-only TEST | best filter+mgmt | best TEST | verdict |
|---|---|---|---|---|---|---|
| liquidity_sweep_long | 1h | n=382 prof=48.4% [43.5–53.4] net=-0.204 gross=-0.137 PF=0.62 stop=49.2% mfe=0.90 | n/a | ema50_dist_atr=0.5..2 + T1=0.75 stop×1.0 T2=default trail=on | n=15 prof=53.3% [30.1–75.2] net=-0.144 gross=-0.093 PF=0.71 stop=46.7% mfe=0.97 | **NO (default NO; train-selected NO)** |
| trend_pullback_short | 4h | n=191 prof=52.9% [45.8–59.8] net=-0.124 gross=-0.084 PF=0.72 stop=41.4% mfe=0.82 | n=191 prof=58.1% [51.0–64.9] net=-0.112 gross=-0.085 PF=0.68 stop=29.8% mfe=0.59 | risk_pct=<2% + T1=0.5 stop×1.5 T2=1.5 trail=on | n=28 prof=46.4% [29.5–64.2] net=-0.141 gross=-0.074 PF=0.63 stop=25.0% mfe=0.61 | **NO (default NO; train-selected NO)** |
| failed_breakout_short | 4h | n=137 prof=63.5% [55.2–71.1] net=+0.127 gross=+0.157 PF=1.36 stop=33.6% mfe=1.05 | n/a | oi_divergence=flat + T1=0.75 stop×1.0 T2=default trail=on | n=23 prof=73.9% [53.5–87.5] net=+0.427 gross=+0.461 PF=2.89 stop=21.7% mfe=1.39 | **CANDIDATE (default CANDIDATE; train-selected CANDIDATE)** |
| rsi_bounce_long | 4h | n=110 prof=50.0% [40.8–59.2] net=-0.071 gross=-0.042 PF=0.79 stop=28.2% mfe=0.71 | n/a | risk_pct=>8% + T1=0.75 stop×1.0 T2=default trail=on | n=32 prof=53.1% [36.4–69.1] net=-0.095 gross=-0.083 PF=0.69 stop=25.0% mfe=0.62 | **NO (default NO; train-selected NO)** |
| range_reversion_short | 4h | n=18 prof=72.2% [49.1–87.5] net=+0.240 gross=+0.276 PF=1.82 stop=27.8% mfe=1.07 | n=18 prof=72.2% [49.1–87.5] net=+0.097 gross=+0.144 PF=1.33 stop=27.8% mfe=0.96 | weekend=weekday + T1=0.5 stop×0.75 T2=1.5 trail=on | n=17 prof=70.6% [46.9–86.7] net=+0.090 gross=+0.138 PF=1.29 stop=29.4% mfe=0.97 | **NO (default NO; train-selected NO)** |
| range_reversion_long | 4h | n=15 prof=46.7% [24.8–69.9] net=-0.194 gross=-0.138 PF=0.66 stop=53.3% mfe=0.87 | n/a | none | n/a | **NO (default NO; train-selected NO)** |
| funding_squeeze_long | 4h | n=6 prof=33.3% [9.7–70.0] net=-0.386 gross=-0.347 PF=0.22 stop=33.3% mfe=0.43 | n=6 prof=16.7% [3.0–56.4] net=-0.530 gross=-0.486 PF=0.20 stop=50.0% mfe=0.45 | none | n/a | **NO (default NO; train-selected NO)** |
| funding_squeeze_short | 4h | n=4 prof=75.0% [30.1–95.4] net=+0.217 gross=+0.226 PF=1.86 stop=25.0% mfe=0.88 | n/a | none | n/a | **NO (default NO; train-selected NO)** |

Runtime: 194s. Config knobs (getattr defaults): UB_DEDUP_DAYS, UB_MIN_HISTORY_DAYS, UB_DEFAULT_T1_R, UB_SHIP_PROFITABLE_PCT, UB_CANDIDATE_PROFITABLE_PCT, UB_MIN_TEST_N, UB_SHIP_MIN_N.