# Unified backtest — 20260923

Universe: 61 symbols (1000BONKUSDT, 1000PEPEUSDT, ADAUSDT, AKEUSDT, ARBUSDT, BEATUSDT, BTCUSDT, DOGEUSDT, ENAUSDT, ETHUSDT, FARTCOINUSDT, HBARUSDT, INJUSDT, KORUUSDT, LABUSDT, NEARUSDT, ONDOUSDT, OPUSDT, PENGUUSDT, SKHYNIXUSDT, SNDKUSDT, SOLUSDT, SOXLUSDT, SPCXUSDT, SUIUSDT, TRXUSDT, WLDUSDT, XLMUSDT, XRPUSDT, ZECUSDT, HYPEUSDT, BCHUSDT, UNIUSDT, MUBARAKUSDT, CLUSDT, XAUUSDT, AVAXUSDT, TAOUSDT, LTCUSDT, AAVEUSDT, LINKUSDT, PUMPFUNUSDT, USELESSUSDT, ZROUSDT, XAGUSDT, SKHYUSDT, WIFUSDT, BNBUSDT, MUUSDT, XPLUSDT, TRUMPUSDT, AAPLUSDT, NILUSDT, CRCLUSDT, MSTRUSDT, TIAUSDT, XAUTUSDT, APTUSDT, LITUSDT, XMRUSDT, DASHUSDT); days=180; trades=216; window 4h→192×15m, 1h→96×15m; entry per ENTRY_MODEL (below); T1=0.75R partial 50%, BE after T1, +0.3R trail after 1R MFE; costs per config (taker 0.055% + slip 0.03% per side; maker 0.020%). **Entry model: limit_open** (limit at next open ∓ 0.0×ATR, wait 2 bars; 216/219 signals filled, 3 unfilled dropped).

Metric: **profitable%** = net-of-cost blended R > 0. Bar: SHIP ≥70% & net>0 & n≥30 on TEST; CANDIDATE ≥60%.

Skipped: PONSUSDT (23d 4h, 2210 15m bars), MARSCOINUSDT (22d 4h, 2109 15m bars)

## (a) Per signal × tf — default config

| signal | tf | tier | ALL | TRAIN (60%) | TEST (40%) |
|---|---|---|---|---|---|
| range_reversion_short | 4h | watch | n=216 prof=64.8% [58.2–70.9] net=+0.085 gross=+0.134 PF=1.24 stop=33.8% mfe=0.95 | n=129 prof=69.8% [61.4–77.0] net=+0.216 gross=+0.263 PF=1.73 stop=27.9% mfe=1.05 | n=87 prof=57.5% [47.0–67.3] net=-0.110 gross=-0.058 PF=0.76 stop=42.5% mfe=0.81 |

Total filter cuts tested across signals: 32.

### range_reversion_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-04 | 39 | 82.1 | +0.558 |
| 2026-05 | 29 | 69.0 | +0.311 |
| 2026-06 | 32 | 65.6 | +0.036 |
| 2026-07 | 35 | 57.1 | -0.152 |
| 2026-08 | 43 | 65.1 | +0.011 |
| 2026-09 | 38 | 50.0 | -0.231 |

**Filter study** (32 cuts tested — expect ~1.6 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=106 prof=70.8% [61.5–78.6] net=+0.256 gross=+0.304 PF=1.90 stop=26.4% mfe=1.08 | n=46 prof=56.5% [42.2–69.8] net=-0.108 gross=-0.057 PF=0.77 stop=43.5% mfe=0.80 |  |
| btc_aligned | yes | n=23 prof=65.2% [44.9–81.2] net=+0.035 gross=+0.073 PF=1.10 stop=34.8% mfe=0.92 | n=41 prof=58.5% [43.4–72.2] net=-0.112 gross=-0.060 PF=0.74 stop=41.5% mfe=0.82 |  |
| confluence3 | 0-1 | n=93 prof=73.1% [63.3–81.1] net=+0.294 gross=+0.336 PF=2.12 stop=24.7% mfe=1.10 | n=67 prof=55.2% [43.4–66.5] net=-0.158 gross=-0.106 PF=0.67 stop=44.8% mfe=0.77 |  |
| confluence3 | 2-3 | n=36 prof=61.1% [44.9–75.2] net=+0.016 gross=+0.076 PF=1.04 stop=36.1% mfe=0.91 | n=20 prof=65.0% [43.3–81.9] net=+0.050 gross=+0.104 PF=1.13 stop=35.0% mfe=0.94 | CANDIDATE |
| risk_pct | 2-4% | n=41 prof=70.7% [55.5–82.4] net=+0.183 gross=+0.214 PF=1.60 stop=29.3% mfe=0.99 | n=26 prof=53.8% [35.5–71.2] net=-0.126 gross=-0.092 PF=0.74 stop=46.2% mfe=0.83 |  |
| risk_pct | 4-8% | n=5 prof=60.0% [23.1–88.2] net=-0.014 gross=+0.005 PF=0.97 stop=40.0% mfe=0.99 | n=4 prof=75.0% [30.1–95.4] net=+0.429 gross=+0.444 PF=2.67 stop=25.0% mfe=1.08 |  |
| risk_pct | <2% | n=80 prof=72.5% [61.9–81.1] net=+0.256 gross=+0.315 PF=1.86 stop=27.5% mfe=1.12 | n=57 prof=57.9% [45.0–69.8] net=-0.141 gross=-0.078 PF=0.69 stop=42.1% mfe=0.78 |  |
| risk_pct | >8% | n=3 prof=0.0% [0.0–56.2] net=-0.010 gross=-0.009 PF=0.00 stop=0.0% mfe=0.01 | n=0 |  |
| hour | 00-08 | n=35 prof=74.3% [57.9–85.8] net=+0.212 gross=+0.274 PF=1.75 stop=25.7% mfe=1.09 | n=18 prof=66.7% [43.7–83.7] net=-0.072 gross=-0.017 PF=0.80 stop=33.3% mfe=0.88 |  |
| hour | 08-16 | n=39 prof=53.8% [38.6–68.4] net=-0.023 gross=+0.018 PF=0.95 stop=41.0% mfe=0.85 | n=17 prof=58.8% [36.0–78.4] net=-0.025 gross=+0.021 PF=0.94 stop=41.2% mfe=0.91 |  |
| hour | 16-24 | n=55 prof=78.2% [65.6–87.1] net=+0.389 gross=+0.430 PF=2.82 stop=20.0% mfe=1.16 | n=52 prof=53.8% [40.5–66.7] net=-0.151 gross=-0.098 PF=0.69 stop=46.2% mfe=0.75 |  |
| weekend | weekday | n=117 prof=70.9% [62.2–78.4] net=+0.230 gross=+0.277 PF=1.81 stop=26.5% mfe=1.05 | n=71 prof=53.5% [42.0–64.6] net=-0.187 gross=-0.133 PF=0.62 stop=46.5% mfe=0.77 |  |
| weekend | weekend | n=12 prof=58.3% [32.0–80.7] net=+0.088 gross=+0.127 PF=1.20 stop=41.7% mfe=1.05 | n=16 prof=75.0% [50.5–89.8] net=+0.230 gross=+0.275 PF=1.86 stop=25.0% mfe=1.01 |  |
| adx | 20-30 | n=62 prof=71.0% [58.7–80.8] net=+0.279 gross=+0.320 PF=1.97 stop=27.4% mfe=1.10 | n=39 prof=53.8% [38.6–68.4] net=-0.149 gross=-0.102 PF=0.69 stop=46.2% mfe=0.78 |  |
| adx | <20 | n=67 prof=68.7% [56.8–78.5] net=+0.158 gross=+0.211 PF=1.52 stop=28.4% mfe=1.00 | n=48 prof=60.4% [46.3–73.0] net=-0.078 gross=-0.022 PF=0.82 stop=39.6% mfe=0.83 |  |
| vol_spike | >=1.5 | n=129 prof=69.8% [61.4–77.0] net=+0.216 gross=+0.263 PF=1.73 stop=27.9% mfe=1.05 | n=87 prof=57.5% [47.0–67.3] net=-0.110 gross=-0.058 PF=0.76 stop=42.5% mfe=0.81 |  |
| ema50_dist_atr | -0.5..0.5 | n=2 prof=50.0% [9.5–90.5] net=-0.285 gross=-0.237 PF=0.45 stop=50.0% mfe=0.83 | n=0 |  |
| ema50_dist_atr | -2..-0.5 | n=1 prof=100.0% [20.7–100.0] net=+0.480 gross=+0.525 PF=inf stop=0.0% mfe=1.14 | n=0 |  |
| ema50_dist_atr | 0.5..2 | n=31 prof=71.0% [53.4–83.9] net=+0.255 gross=+0.295 PF=1.84 stop=29.0% mfe=1.09 | n=21 prof=66.7% [45.4–82.8] net=-0.015 gross=+0.038 PF=0.96 stop=33.3% mfe=0.87 |  |
| ema50_dist_atr | >2 | n=95 prof=69.5% [59.6–77.8] net=+0.212 gross=+0.261 PF=1.72 stop=27.4% mfe=1.04 | n=66 prof=54.5% [42.6–66.0] net=-0.140 gross=-0.089 PF=0.71 stop=45.5% mfe=0.79 |  |
| symbol_group | major | n=42 prof=85.7% [72.2–93.3] net=+0.497 gross=+0.543 PF=4.23 stop=14.3% mfe=1.24 | n=24 prof=58.3% [38.8–75.5] net=-0.191 gross=-0.135 PF=0.57 stop=41.7% mfe=0.71 |  |
| symbol_group | other | n=87 prof=62.1% [51.6–71.5] net=+0.081 gross=+0.128 PF=1.22 stop=34.5% mfe=0.96 | n=63 prof=57.1% [44.9–68.6] net=-0.079 gross=-0.029 PF=0.83 stop=42.9% mfe=0.85 |  |
| funding | na | n=129 prof=69.8% [61.4–77.0] net=+0.216 gross=+0.263 PF=1.73 stop=27.9% mfe=1.05 | n=87 prof=57.5% [47.0–67.3] net=-0.110 gross=-0.058 PF=0.76 stop=42.5% mfe=0.81 |  |
| funding_side | neutral | n=129 prof=69.8% [61.4–77.0] net=+0.216 gross=+0.263 PF=1.73 stop=27.9% mfe=1.05 | n=87 prof=57.5% [47.0–67.3] net=-0.110 gross=-0.058 PF=0.76 stop=42.5% mfe=0.81 |  |
| funding_z | na | n=129 prof=69.8% [61.4–77.0] net=+0.216 gross=+0.263 PF=1.73 stop=27.9% mfe=1.05 | n=87 prof=57.5% [47.0–67.3] net=-0.110 gross=-0.058 PF=0.76 stop=42.5% mfe=0.81 |  |
| oi_divergence | na | n=129 prof=69.8% [61.4–77.0] net=+0.216 gross=+0.263 PF=1.73 stop=27.9% mfe=1.05 | n=87 prof=57.5% [47.0–67.3] net=-0.110 gross=-0.058 PF=0.76 stop=42.5% mfe=0.81 |  |
| oi_chg_24h | na | n=129 prof=69.8% [61.4–77.0] net=+0.216 gross=+0.263 PF=1.73 stop=27.9% mfe=1.05 | n=87 prof=57.5% [47.0–67.3] net=-0.110 gross=-0.058 PF=0.76 stop=42.5% mfe=0.81 |  |
| settlement_bar | other | n=54 prof=68.5% [55.3–79.3] net=+0.221 gross=+0.263 PF=1.70 stop=29.6% mfe=1.10 | n=43 prof=58.1% [43.3–71.6] net=-0.089 gross=-0.037 PF=0.80 stop=41.9% mfe=0.85 |  |
| settlement_bar | settlement | n=75 prof=70.7% [59.6–79.8] net=+0.213 gross=+0.263 PF=1.74 stop=26.7% mfe=1.01 | n=44 prof=56.8% [42.2–70.3] net=-0.131 gross=-0.079 PF=0.71 stop=43.2% mfe=0.77 |  |
| session | 03-04 | n=13 prof=69.2% [42.4–87.3] net=+0.178 gross=+0.229 PF=1.54 stop=30.8% mfe=1.14 | n=14 prof=64.3% [38.8–83.7] net=-0.107 gross=-0.052 PF=0.72 stop=35.7% mfe=0.91 |  |
| session | 08-16 | n=39 prof=53.8% [38.6–68.4] net=-0.023 gross=+0.018 PF=0.95 stop=41.0% mfe=0.85 | n=17 prof=58.8% [36.0–78.4] net=-0.025 gross=+0.021 PF=0.94 stop=41.2% mfe=0.91 |  |
| session | other | n=77 prof=77.9% [67.5–85.7] net=+0.344 gross=+0.393 PF=2.53 stop=20.8% mfe=1.14 | n=56 prof=55.4% [42.4–67.6] net=-0.137 gross=-0.084 PF=0.71 stop=44.6% mfe=0.76 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- chosen: T1=0.5R, stop×0.75, T2=2.0R, trail=on
- TRAIN chosen: n=129 prof=79.8% [72.1–85.9] net=+0.239 gross=+0.299 PF=2.23 stop=17.8% mfe=1.12
- TEST chosen: n=87 prof=62.1% [51.6–71.5] net=-0.170 gross=-0.102 PF=0.59 stop=37.9% mfe=0.84
- TEST default: n=87 prof=57.5% [47.0–67.3] net=-0.110 gross=-0.058 PF=0.76 stop=42.5% mfe=0.81

## (f) Fill model — passive (maker) entry vs market (taker)

Limit rests at the next 15m open improved by offset×ATR; fills only when price trades THROUGH it within `wait` bars (touch ≠ fill); maker fee 0.020% on entry + take-profits, stops still taker+slippage. 'market same subset' re-costs the identical filled trades at taker fees, so (limit − market same subset) = pure fee effect and (market same subset − baseline) = selection effect of waiting for a fill. Unfilled signals are lost opportunities, not losses.


### range_reversion_short (4h) — market baseline: n=216 prof=64.8% [58.2–70.9] net=+0.028 gross=+0.134 PF=1.08 stop=33.8% mfe=0.95

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=216 prof=64.8% [58.2–70.9] net=+0.085 gross=+0.134 PF=1.24 stop=33.8% mfe=0.95 | n=216 prof=64.8% [58.2–70.9] net=+0.028 gross=+0.134 PF=1.08 stop=33.8% mfe=0.95 |
| 0.0 | 4 | 100% | n=216 prof=64.8% [58.2–70.9] net=+0.085 gross=+0.134 PF=1.24 stop=33.8% mfe=0.95 | n=216 prof=64.8% [58.2–70.9] net=+0.028 gross=+0.134 PF=1.08 stop=33.8% mfe=0.95 |
| 0.0 | 8 | 100% | n=216 prof=64.8% [58.2–70.9] net=+0.085 gross=+0.134 PF=1.24 stop=33.8% mfe=0.95 | n=216 prof=64.8% [58.2–70.9] net=+0.028 gross=+0.134 PF=1.08 stop=33.8% mfe=0.95 |
| 0.15 | 2 | 61% | n=132 prof=64.4% [55.9–72.0] net=+0.067 gross=+0.126 PF=1.17 stop=35.6% mfe=0.99 | n=132 prof=63.6% [55.2–71.3] net=-0.003 gross=+0.126 PF=0.99 stop=35.6% mfe=0.99 |
| 0.15 | 4 | 69% | n=149 prof=67.1% [59.2–74.1] net=+0.123 gross=+0.179 PF=1.36 stop=31.5% mfe=1.00 | n=149 prof=66.4% [58.5–73.5] net=+0.056 gross=+0.179 PF=1.16 stop=31.5% mfe=1.00 |
| 0.15 | 8 | 76% | n=165 prof=66.7% [59.2–73.4] net=+0.136 gross=+0.191 PF=1.40 stop=31.5% mfe=1.01 | n=165 prof=66.1% [58.5–72.8] net=+0.069 gross=+0.191 PF=1.19 stop=31.5% mfe=1.01 |
| 0.3 | 2 | 31% | n=68 prof=63.2% [51.4–73.7] net=+0.040 gross=+0.112 PF=1.10 stop=36.8% mfe=1.08 | n=68 prof=61.8% [49.9–72.4] net=-0.052 gross=+0.112 PF=0.88 stop=36.8% mfe=1.08 |
| 0.3 | 4 | 41% | n=89 prof=65.2% [54.8–74.3] net=+0.044 gross=+0.117 PF=1.11 stop=34.8% mfe=1.06 | n=89 prof=64.0% [53.7–73.2] net=-0.045 gross=+0.117 PF=0.89 stop=34.8% mfe=1.06 |
| 0.3 | 8 | 54% | n=117 prof=65.8% [56.8–73.8] net=+0.097 gross=+0.165 PF=1.28 stop=31.6% mfe=1.07 | n=117 prof=65.0% [56.0–73.0] net=+0.012 gross=+0.165 PF=1.03 stop=31.6% mfe=1.07 |

## (d) What would ship (TEST numbers; filter + management selected on TRAIN)

| signal | tf | default TEST | mgmt-only TEST | best filter+mgmt | best TEST | verdict |
|---|---|---|---|---|---|---|
| range_reversion_short | 4h | n=87 prof=57.5% [47.0–67.3] net=-0.110 gross=-0.058 PF=0.76 stop=42.5% mfe=0.81 | n=87 prof=62.1% [51.6–71.5] net=-0.170 gross=-0.102 PF=0.59 stop=37.9% mfe=0.84 | symbol_group=major + T1=0.5 stop×0.75 T2=2.0 trail=on | n=24 prof=62.5% [42.7–78.8] net=-0.244 gross=-0.175 PF=0.39 stop=37.5% mfe=0.66 | **NO (default NO; train-selected NO)** |

Runtime: 12s. Config knobs (getattr defaults): UB_DEDUP_DAYS, UB_MIN_HISTORY_DAYS, UB_DEFAULT_T1_R, UB_SHIP_PROFITABLE_PCT, UB_CANDIDATE_PROFITABLE_PCT, UB_MIN_TEST_N, UB_SHIP_MIN_N.