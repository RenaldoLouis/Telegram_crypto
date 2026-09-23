# Unified backtest — 20260923

Universe: 29 symbols (BTCUSDT, ADAUSDT, XRPUSDT, SOLUSDT, ETHUSDT, DOGEUSDT, SUIUSDT, XLMUSDT, ENAUSDT, HBARUSDT, TRXUSDT, NEARUSDT, OPUSDT, ARBUSDT, INJUSDT, FARTCOINUSDT, 1000PEPEUSDT, SKHYNIXUSDT, 1000BONKUSDT, WLDUSDT, SOXLUSDT, KORUUSDT, AKEUSDT, ONDOUSDT, SNDKUSDT, LABUSDT, BEATUSDT, PENGUUSDT, SPCXUSDT); days=180; trades=101; window 4h→192×15m, 1h→96×15m; entry=market at next 15m open; T1=0.75R partial 50%, BE after T1, +0.3R trail after 1R MFE; costs per config (taker 0.055% + slip 0.03% per side).

Metric: **profitable%** = net-of-cost blended R > 0. Bar: SHIP ≥70% & net>0 & n≥30 on TEST; CANDIDATE ≥60%.

Skipped: CASHCATUSDT (49d 4h, 4694 15m bars)

## (a) Per signal × tf — default config

| signal | tf | tier | ALL | TRAIN (60%) | TEST (40%) |
|---|---|---|---|---|---|
| range_reversion_short | 4h | watch | n=101 prof=75.2% [66.0–82.6] net=+0.185 gross=+0.287 PF=1.68 stop=24.8% mfe=1.04 | n=60 prof=81.7% [70.1–89.4] net=+0.337 gross=+0.443 PF=2.67 stop=18.3% mfe=1.16 | n=41 prof=65.9% [50.5–78.4] net=-0.039 gross=+0.059 PF=0.90 stop=34.1% mfe=0.86 |

Total filter cuts tested across signals: 19.

### range_reversion_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-04 | 17 | 94.1 | +0.606 |
| 2026-05 | 12 | 91.7 | +0.723 |
| 2026-06 | 12 | 75.0 | +0.185 |
| 2026-07 | 20 | 70.0 | -0.036 |
| 2026-08 | 21 | 81.0 | +0.245 |
| 2026-09 | 19 | 47.4 | -0.367 |

**Filter study** (19 cuts tested — expect ~1.0 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=51 prof=80.4% [67.5–89.0] net=+0.322 gross=+0.432 PF=2.49 stop=19.6% mfe=1.16 | n=20 prof=60.0% [38.7–78.1] net=-0.111 gross=-0.010 PF=0.75 stop=40.0% mfe=0.81 |  |
| btc_aligned | yes | n=9 prof=88.9% [56.5–98.0] net=+0.427 gross=+0.506 PF=4.62 stop=11.1% mfe=1.19 | n=21 prof=71.4% [50.0–86.2] net=+0.029 gross=+0.125 PF=1.10 stop=28.6% mfe=0.91 | CANDIDATE |
| confluence3 | 0-1 | n=46 prof=82.6% [69.3–90.9] net=+0.368 gross=+0.469 PF=2.93 stop=17.4% mfe=1.20 | n=28 prof=60.7% [42.4–76.4] net=-0.145 gross=-0.053 PF=0.66 stop=39.3% mfe=0.76 |  |
| confluence3 | 2-3 | n=14 prof=78.6% [52.4–92.4] net=+0.238 gross=+0.359 PF=2.00 stop=21.4% mfe=1.05 | n=13 prof=76.9% [49.7–91.8] net=+0.189 gross=+0.300 PF=1.73 stop=23.1% mfe=1.08 |  |
| risk_pct | 2-4% | n=20 prof=80.0% [58.4–91.9] net=+0.269 gross=+0.340 PF=2.26 stop=20.0% mfe=1.00 | n=13 prof=61.5% [35.5–82.3] net=-0.050 gross=+0.019 PF=0.88 stop=38.5% mfe=0.89 |  |
| risk_pct | 4-8% | n=4 prof=75.0% [30.1–95.4] net=+0.217 gross=+0.256 PF=1.84 stop=25.0% mfe=1.24 | n=2 prof=50.0% [9.5–90.5] net=+0.022 gross=+0.062 PF=1.04 stop=50.0% mfe=0.81 |  |
| risk_pct | <2% | n=36 prof=83.3% [68.1–92.1] net=+0.389 gross=+0.521 PF=3.06 stop=16.7% mfe=1.25 | n=26 prof=69.2% [50.0–83.5] net=-0.038 gross=+0.079 PF=0.89 stop=30.8% mfe=0.85 |  |
| hour | 00-08 | n=14 prof=85.7% [60.1–96.0] net=+0.399 gross=+0.521 PF=3.49 stop=14.3% mfe=1.26 | n=11 prof=81.8% [52.3–94.9] net=+0.178 gross=+0.275 PF=1.87 stop=18.2% mfe=1.13 |  |
| hour | 08-16 | n=19 prof=73.7% [51.2–88.2] net=+0.240 gross=+0.345 PF=1.84 stop=26.3% mfe=1.12 | n=6 prof=50.0% [18.8–81.2] net=-0.244 gross=-0.163 PF=0.55 stop=50.0% mfe=0.71 |  |
| hour | 16-24 | n=27 prof=85.2% [67.5–94.1] net=+0.374 gross=+0.471 PF=3.29 stop=14.8% mfe=1.15 | n=24 prof=62.5% [42.7–78.8] net=-0.087 gross=+0.016 PF=0.79 stop=37.5% mfe=0.78 |  |
| weekend | weekday | n=54 prof=83.3% [71.3–91.0] net=+0.353 gross=+0.460 PF=2.91 stop=16.7% mfe=1.17 | n=34 prof=64.7% [47.9–78.5] net=-0.074 gross=+0.022 PF=0.81 stop=35.3% mfe=0.83 |  |
| weekend | weekend | n=6 prof=66.7% [30.0–90.3] net=+0.201 gross=+0.292 PF=1.57 stop=33.3% mfe=1.09 | n=7 prof=71.4% [35.9–91.8] net=+0.130 gross=+0.239 PF=1.41 stop=28.6% mfe=1.01 |  |
| adx | 20-30 | n=33 prof=84.8% [69.1–93.3] net=+0.440 gross=+0.539 PF=3.72 stop=15.2% mfe=1.21 | n=17 prof=64.7% [41.3–82.7] net=+0.009 gross=+0.102 PF=1.02 stop=35.3% mfe=0.90 |  |
| adx | <20 | n=27 prof=77.8% [59.2–89.4] net=+0.212 gross=+0.325 PF=1.85 stop=22.2% mfe=1.11 | n=24 prof=66.7% [46.7–82.0] net=-0.073 gross=+0.029 PF=0.80 stop=33.3% mfe=0.84 |  |
| vol_spike | >=1.5 | n=60 prof=81.7% [70.1–89.4] net=+0.337 gross=+0.443 PF=2.67 stop=18.3% mfe=1.16 | n=41 prof=65.9% [50.5–78.4] net=-0.039 gross=+0.059 PF=0.90 stop=34.1% mfe=0.86 |  |
| ema50_dist_atr | 0.5..2 | n=14 prof=78.6% [52.4–92.4] net=+0.339 gross=+0.434 PF=2.48 stop=21.4% mfe=1.10 | n=11 prof=81.8% [52.3–94.9] net=+0.146 gross=+0.261 PF=1.70 stop=18.2% mfe=0.98 |  |
| ema50_dist_atr | >2 | n=46 prof=82.6% [69.3–90.9] net=+0.337 gross=+0.446 PF=2.74 stop=17.4% mfe=1.18 | n=30 prof=60.0% [42.3–75.4] net=-0.107 gross=-0.015 PF=0.75 stop=40.0% mfe=0.82 |  |
| symbol_group | major | n=43 prof=86.0% [72.7–93.4] net=+0.427 gross=+0.542 PF=3.74 stop=14.0% mfe=1.24 | n=24 prof=58.3% [38.8–75.5] net=-0.242 gross=-0.135 PF=0.47 stop=41.7% mfe=0.71 |  |
| symbol_group | other | n=17 prof=70.6% [46.9–86.7] net=+0.110 gross=+0.191 PF=1.35 stop=29.4% mfe=0.98 | n=17 prof=76.5% [52.7–90.4] net=+0.249 gross=+0.334 PF=1.98 stop=23.5% mfe=1.07 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- chosen: T1=0.5R, stop×0.75, T2=2.0R, trail=on
- TRAIN chosen: n=60 prof=88.3% [77.8–94.2] net=+0.254 gross=+0.392 PF=2.96 stop=11.7% mfe=1.14
- TEST chosen: n=41 prof=70.7% [55.5–82.4] net=-0.098 gross=+0.029 PF=0.70 stop=29.3% mfe=0.91
- TEST default: n=41 prof=65.9% [50.5–78.4] net=-0.039 gross=+0.059 PF=0.90 stop=34.1% mfe=0.86

## (d) What would ship (TEST numbers; filter + management selected on TRAIN)

| signal | tf | default TEST | mgmt-only TEST | best filter+mgmt | best TEST | verdict |
|---|---|---|---|---|---|---|
| range_reversion_short | 4h | n=41 prof=65.9% [50.5–78.4] net=-0.039 gross=+0.059 PF=0.90 stop=34.1% mfe=0.86 | n=41 prof=70.7% [55.5–82.4] net=-0.098 gross=+0.029 PF=0.70 stop=29.3% mfe=0.91 | symbol_group=major + T1=0.5 stop×0.75 T2=2.0 trail=on | n=24 prof=62.5% [42.7–78.8] net=-0.313 gross=-0.175 PF=0.25 stop=37.5% mfe=0.66 | **NO** |

Runtime: 5s. Config knobs (getattr defaults): UB_DEDUP_DAYS, UB_MIN_HISTORY_DAYS, UB_DEFAULT_T1_R, UB_SHIP_PROFITABLE_PCT, UB_CANDIDATE_PROFITABLE_PCT, UB_MIN_TEST_N, UB_SHIP_MIN_N.