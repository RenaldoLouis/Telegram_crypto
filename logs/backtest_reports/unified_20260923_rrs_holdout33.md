# Unified backtest — 20260923

Universe: 33 symbols (BTCUSDT, ZECUSDT, HYPEUSDT, BCHUSDT, UNIUSDT, MUBARAKUSDT, CLUSDT, XAUUSDT, AVAXUSDT, TAOUSDT, LTCUSDT, AAVEUSDT, LINKUSDT, PUMPFUNUSDT, USELESSUSDT, ZROUSDT, XAGUSDT, SKHYUSDT, WIFUSDT, BNBUSDT, MUUSDT, XPLUSDT, TRUMPUSDT, AAPLUSDT, NILUSDT, CRCLUSDT, MSTRUSDT, TIAUSDT, XAUTUSDT, APTUSDT, LITUSDT, XMRUSDT, DASHUSDT); days=180; trades=120; window 4h→192×15m, 1h→96×15m; entry per ENTRY_MODEL (below); T1=0.75R partial 50%, BE after T1, +0.3R trail after 1R MFE; costs per config (taker 0.055% + slip 0.03% per side; maker 0.020%). **Entry model: limit_open** (limit at next open ∓ 0.0×ATR, wait 2 bars; 120/121 signals filled, 1 unfilled dropped).

Metric: **profitable%** = net-of-cost blended R > 0. Bar: SHIP ≥70% & net>0 & n≥30 on TEST; CANDIDATE ≥60%.

Skipped: PONSUSDT (23d 4h, 2210 15m bars), MARSCOINUSDT (22d 4h, 2109 15m bars)

## (a) Per signal × tf — default config

| signal | tf | tier | ALL | TRAIN (60%) | TEST (40%) |
|---|---|---|---|---|---|
| range_reversion_short | 4h | watch | n=120 prof=57.5% [48.6–66.0] net=-0.018 gross=+0.035 PF=0.96 stop=40.0% mfe=0.90 | n=72 prof=62.5% [51.0–72.8] net=+0.110 gross=+0.160 PF=1.31 stop=33.3% mfe=0.97 | n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78 |

Total filter cuts tested across signals: 32.

### range_reversion_short (4h)

**Walk-forward by month (default config):**

| month | n | profitable% | net exp |
|---|---|---|---|
| 2026-04 | 24 | 75.0 | +0.522 |
| 2026-05 | 17 | 52.9 | -0.037 |
| 2026-06 | 21 | 61.9 | -0.073 |
| 2026-07 | 16 | 43.8 | -0.323 |
| 2026-08 | 23 | 52.2 | -0.204 |
| 2026-09 | 19 | 52.6 | -0.138 |

**Filter study** (32 cuts tested — expect ~1.6 false positives at 5%):

| filter | bucket | TRAIN | TEST | flag |
|---|---|---|---|---|
| btc_aligned | no | n=58 prof=65.5% [52.7–76.4] net=+0.196 gross=+0.248 PF=1.62 stop=29.3% mfe=1.03 | n=28 prof=53.6% [35.8–70.5] net=-0.133 gross=-0.081 PF=0.73 stop=46.4% mfe=0.83 |  |
| btc_aligned | yes | n=14 prof=50.0% [26.8–73.2] net=-0.247 gross=-0.205 PF=0.53 stop=50.0% mfe=0.74 | n=20 prof=45.0% [25.8–65.8] net=-0.313 gross=-0.254 PF=0.46 stop=55.0% mfe=0.72 |  |
| confluence3 | 0-1 | n=50 prof=68.0% [54.2–79.2] net=+0.232 gross=+0.276 PF=1.78 stop=28.0% mfe=1.04 | n=41 prof=51.2% [36.5–65.7] net=-0.189 gross=-0.135 PF=0.64 stop=48.8% mfe=0.80 |  |
| confluence3 | 2-3 | n=22 prof=50.0% [30.7–69.3] net=-0.169 gross=-0.104 PF=0.66 stop=45.5% mfe=0.81 | n=7 prof=42.9% [15.8–75.0] net=-0.319 gross=-0.261 PF=0.48 stop=57.1% mfe=0.70 |  |
| risk_pct | 2-4% | n=22 prof=63.6% [43.0–80.3] net=+0.083 gross=+0.114 PF=1.22 stop=36.4% mfe=0.98 | n=14 prof=50.0% [26.8–73.2] net=-0.140 gross=-0.109 PF=0.73 stop=50.0% mfe=0.84 |  |
| risk_pct | 4-8% | n=1 prof=0.0% [0.0–79.3] net=-1.026 gross=-1.000 PF=0.00 stop=100.0% mfe=0.00 | n=2 prof=100.0% [34.2–100.0] net=+0.812 gross=+0.825 PF=inf stop=0.0% mfe=1.34 |  |
| risk_pct | <2% | n=46 prof=67.4% [53.0–79.1] net=+0.154 gross=+0.218 PF=1.44 stop=32.6% mfe=1.05 | n=32 prof=46.9% [30.9–63.6] net=-0.302 gross=-0.234 PF=0.47 stop=53.1% mfe=0.72 |  |
| risk_pct | >8% | n=3 prof=0.0% [0.0–56.2] net=-0.010 gross=-0.009 PF=0.00 stop=0.0% mfe=0.01 | n=0 |  |
| hour | 00-08 | n=22 prof=68.2% [47.3–83.6] net=+0.050 gross=+0.122 PF=1.14 stop=31.8% mfe=0.98 | n=8 prof=50.0% [21.5–78.5] net=-0.336 gross=-0.275 PF=0.37 stop=50.0% mfe=0.66 |  |
| hour | 08-16 | n=20 prof=40.0% [21.9–61.3] net=-0.225 gross=-0.186 PF=0.57 stop=50.0% mfe=0.64 | n=12 prof=58.3% [32.0–80.7] net=-0.021 gross=+0.027 PF=0.95 stop=41.7% mfe=0.98 |  |
| hour | 16-24 | n=30 prof=73.3% [55.6–85.8] net=+0.377 gross=+0.419 PF=2.52 stop=23.3% mfe=1.19 | n=28 prof=46.4% [29.5–64.2] net=-0.252 gross=-0.196 PF=0.56 stop=53.6% mfe=0.73 |  |
| weekend | weekday | n=66 prof=63.6% [51.6–74.2] net=+0.127 gross=+0.178 PF=1.37 stop=31.8% mfe=0.97 | n=39 prof=43.6% [29.3–59.0] net=-0.317 gross=-0.258 PF=0.47 stop=56.4% mfe=0.73 |  |
| weekend | weekend | n=6 prof=50.0% [18.8–81.2] net=-0.082 gross=-0.037 PF=0.84 stop=50.0% mfe=1.00 | n=9 prof=77.8% [45.3–93.7] net=+0.264 gross=+0.303 PF=2.12 stop=22.2% mfe=1.01 |  |
| adx | 20-30 | n=31 prof=61.3% [43.8–76.3] net=+0.142 gross=+0.187 PF=1.38 stop=35.5% mfe=1.03 | n=24 prof=45.8% [27.9–64.9] net=-0.282 gross=-0.232 PF=0.51 stop=54.2% mfe=0.74 |  |
| adx | <20 | n=41 prof=63.4% [48.1–76.4] net=+0.085 gross=+0.140 PF=1.25 stop=31.7% mfe=0.93 | n=24 prof=54.2% [35.1–72.1] net=-0.134 gross=-0.074 PF=0.73 stop=45.8% mfe=0.82 |  |
| vol_spike | >=1.5 | n=72 prof=62.5% [51.0–72.8] net=+0.110 gross=+0.160 PF=1.31 stop=33.3% mfe=0.97 | n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78 |  |
| ema50_dist_atr | -0.5..0.5 | n=2 prof=50.0% [9.5–90.5] net=-0.285 gross=-0.237 PF=0.45 stop=50.0% mfe=0.83 | n=0 |  |
| ema50_dist_atr | -2..-0.5 | n=1 prof=100.0% [20.7–100.0] net=+0.480 gross=+0.525 PF=inf stop=0.0% mfe=1.14 | n=0 |  |
| ema50_dist_atr | 0.5..2 | n=17 prof=64.7% [41.3–82.7] net=+0.139 gross=+0.181 PF=1.37 stop=35.3% mfe=1.09 | n=10 prof=50.0% [23.7–76.3] net=-0.256 gross=-0.207 PF=0.51 stop=50.0% mfe=0.75 |  |
| ema50_dist_atr | >2 | n=52 prof=61.5% [48.0–73.5] net=+0.108 gross=+0.161 PF=1.31 stop=32.7% mfe=0.94 | n=38 prof=50.0% [34.8–65.2] net=-0.196 gross=-0.139 PF=0.63 stop=50.0% mfe=0.79 |  |
| symbol_group | major | n=3 prof=100.0% [43.8–100.0] net=+0.809 gross=+0.875 PF=inf stop=0.0% mfe=1.35 | n=0 |  |
| symbol_group | other | n=69 prof=60.9% [49.1–71.5] net=+0.079 gross=+0.129 PF=1.21 stop=34.8% mfe=0.96 | n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78 |  |
| funding | na | n=72 prof=62.5% [51.0–72.8] net=+0.110 gross=+0.160 PF=1.31 stop=33.3% mfe=0.97 | n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78 |  |
| funding_side | neutral | n=72 prof=62.5% [51.0–72.8] net=+0.110 gross=+0.160 PF=1.31 stop=33.3% mfe=0.97 | n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78 |  |
| funding_z | na | n=72 prof=62.5% [51.0–72.8] net=+0.110 gross=+0.160 PF=1.31 stop=33.3% mfe=0.97 | n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78 |  |
| oi_divergence | na | n=72 prof=62.5% [51.0–72.8] net=+0.110 gross=+0.160 PF=1.31 stop=33.3% mfe=0.97 | n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78 |  |
| oi_chg_24h | na | n=72 prof=62.5% [51.0–72.8] net=+0.110 gross=+0.160 PF=1.31 stop=33.3% mfe=0.97 | n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78 |  |
| settlement_bar | other | n=30 prof=60.0% [42.3–75.4] net=+0.078 gross=+0.123 PF=1.20 stop=36.7% mfe=1.01 | n=26 prof=50.0% [32.1–67.9] net=-0.224 gross=-0.168 PF=0.58 stop=50.0% mfe=0.79 |  |
| settlement_bar | settlement | n=42 prof=64.3% [49.2–77.0] net=+0.132 gross=+0.186 PF=1.40 stop=31.0% mfe=0.94 | n=22 prof=50.0% [30.7–69.3] net=-0.189 gross=-0.135 PF=0.64 stop=50.0% mfe=0.77 |  |
| session | 03-04 | n=8 prof=50.0% [21.5–78.5] net=-0.220 gross=-0.163 PF=0.59 stop=50.0% mfe=0.84 | n=6 prof=50.0% [18.8–81.2] net=-0.346 gross=-0.287 PF=0.35 stop=50.0% mfe=0.67 |  |
| session | 08-16 | n=20 prof=40.0% [21.9–61.3] net=-0.225 gross=-0.186 PF=0.57 stop=50.0% mfe=0.64 | n=12 prof=58.3% [32.0–80.7] net=-0.021 gross=+0.027 PF=0.95 stop=41.7% mfe=0.98 |  |
| session | other | n=44 prof=75.0% [60.6–85.4] net=+0.322 gross=+0.376 PF=2.30 stop=22.7% mfe=1.15 | n=30 prof=46.7% [30.2–63.9] net=-0.256 gross=-0.198 PF=0.55 stop=53.3% mfe=0.72 |  |

**Management sweep** (chosen on TRAIN: max profitable% s.t. net>0; T2 floor 1.5R):

- chosen: T1=0.5R, stop×0.75, T2=1.5R, trail=off
- TRAIN chosen: n=72 prof=73.6% [62.4–82.4] net=+0.181 gross=+0.242 PF=1.74 stop=22.2% mfe=1.00
- TEST chosen: n=48 prof=56.2% [42.3–69.3] net=-0.191 gross=-0.125 PF=0.60 stop=43.8% mfe=0.76
- TEST default: n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78

## (f) Fill model — passive (maker) entry vs market (taker)

Limit rests at the next 15m open improved by offset×ATR; fills only when price trades THROUGH it within `wait` bars (touch ≠ fill); maker fee 0.020% on entry + take-profits, stops still taker+slippage. 'market same subset' re-costs the identical filled trades at taker fees, so (limit − market same subset) = pure fee effect and (market same subset − baseline) = selection effect of waiting for a fill. Unfilled signals are lost opportunities, not losses.


### range_reversion_short (4h) — market baseline: n=120 prof=57.5% [48.6–66.0] net=-0.074 gross=+0.035 PF=0.83 stop=40.0% mfe=0.90

| offset×ATR | wait bars | fill rate | LIMIT (maker) filled | market, same subset |
|---|---|---|---|---|
| 0.0 | 2 | 100% | n=120 prof=57.5% [48.6–66.0] net=-0.018 gross=+0.035 PF=0.96 stop=40.0% mfe=0.90 | n=120 prof=57.5% [48.6–66.0] net=-0.074 gross=+0.035 PF=0.83 stop=40.0% mfe=0.90 |
| 0.0 | 4 | 100% | n=120 prof=57.5% [48.6–66.0] net=-0.018 gross=+0.035 PF=0.96 stop=40.0% mfe=0.90 | n=120 prof=57.5% [48.6–66.0] net=-0.074 gross=+0.035 PF=0.83 stop=40.0% mfe=0.90 |
| 0.0 | 8 | 100% | n=120 prof=57.5% [48.6–66.0] net=-0.018 gross=+0.035 PF=0.96 stop=40.0% mfe=0.90 | n=120 prof=57.5% [48.6–66.0] net=-0.074 gross=+0.035 PF=0.83 stop=40.0% mfe=0.90 |
| 0.15 | 2 | 62% | n=75 prof=54.7% [43.4–65.4] net=-0.085 gross=-0.022 PF=0.83 stop=45.3% mfe=0.90 | n=75 prof=53.3% [42.2–64.2] net=-0.154 gross=-0.022 PF=0.70 stop=45.3% mfe=0.90 |
| 0.15 | 4 | 74% | n=89 prof=59.6% [49.2–69.1] net=+0.022 gross=+0.081 PF=1.05 stop=38.2% mfe=0.94 | n=89 prof=58.4% [48.0–68.1] net=-0.044 gross=+0.081 PF=0.90 stop=38.2% mfe=0.94 |
| 0.15 | 8 | 80% | n=96 prof=60.4% [50.4–69.6] net=+0.066 gross=+0.123 PF=1.17 stop=36.5% mfe=0.96 | n=96 prof=59.4% [49.4–68.7] net=-0.000 gross=+0.123 PF=1.00 stop=36.5% mfe=0.96 |
| 0.3 | 2 | 28% | n=34 prof=47.1% [31.5–63.3] net=-0.296 gross=-0.207 PF=0.49 stop=52.9% mfe=0.92 | n=34 prof=44.1% [28.9–60.5] net=-0.386 gross=-0.207 PF=0.38 stop=52.9% mfe=0.92 |
| 0.3 | 4 | 39% | n=47 prof=48.9% [35.3–62.8] net=-0.304 gross=-0.215 PF=0.46 stop=51.1% mfe=0.88 | n=47 prof=46.8% [33.3–60.8] net=-0.391 gross=-0.215 PF=0.35 stop=51.1% mfe=0.88 |
| 0.3 | 8 | 52% | n=63 prof=52.4% [40.3–64.2] net=-0.147 gross=-0.070 PF=0.69 stop=42.9% mfe=0.92 | n=63 prof=50.8% [38.8–62.7] net=-0.227 gross=-0.070 PF=0.55 stop=42.9% mfe=0.92 |

## (d) What would ship (TEST numbers; filter + management selected on TRAIN)

| signal | tf | default TEST | mgmt-only TEST | best filter+mgmt | best TEST | verdict |
|---|---|---|---|---|---|---|
| range_reversion_short | 4h | n=48 prof=50.0% [36.4–63.6] net=-0.208 gross=-0.153 PF=0.61 stop=50.0% mfe=0.78 | n=48 prof=56.2% [42.3–69.3] net=-0.191 gross=-0.125 PF=0.60 stop=43.8% mfe=0.76 | session=other + T1=0.5 stop×0.75 T2=1.5 trail=off | n=30 prof=43.3% [27.4–60.8] net=-0.302 gross=-0.233 PF=0.51 stop=56.7% mfe=0.79 | **NO (default NO; train-selected NO)** |

Runtime: 178s. Config knobs (getattr defaults): UB_DEDUP_DAYS, UB_MIN_HISTORY_DAYS, UB_DEFAULT_T1_R, UB_SHIP_PROFITABLE_PCT, UB_CANDIDATE_PROFITABLE_PCT, UB_MIN_TEST_N, UB_SHIP_MIN_N.