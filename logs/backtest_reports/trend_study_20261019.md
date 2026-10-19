# Single-coin trend-following study — 2026-10-19

Pre-registration: `logs/backtest_reports/prereg_trend_study_20261019.md`. 15 symbols (ADAUSDT, XRPUSDT, SOLUSDT, BTCUSDT, ETHUSDT, DOGEUSDT, SUIUSDT, XLMUSDT, ENAUSDT, HBARUSDT, TRXUSDT, NEARUSDT, OPUSDT, ARBUSDT, INJUSDT); 2023-10-21 → 2026-10-19; TRAIN = entries before 2025-08-07, TEST after. Breakout on the daily close, entry next open (taker 0.055% + slippage 0.03% per side), stop 3.0 × ATR(20) trailed after every daily close, checked on 4h bars, max hold 60 d, actual funding. R = initial stop distance; all figures net. [a..b] = bootstrap 95% CI of the mean.

## Verdict

| book | TRAIN | TEST | verdict |
|---|---|---|---|
| N=20 | n=334 exp=+0.063R [-0.03..+0.16] total=+21.1R PF=1.20 win=42% avgW=+0.89 avgL=-0.53 maxDD=26.6R streak=16 hold=11.0d | n=210 exp=+0.064R [-0.07..+0.20] total=+13.4R PF=1.19 win=43% avgW=+0.91 avgL=-0.57 maxDD=16.3R streak=11 hold=13.0d | **CANDIDATE** — TEST PF 1.19 < 1.3; max DD 26.6R > 20R |
| N=55 | n=183 exp=-0.050R [-0.18..+0.10] total=-9.1R PF=0.87 win=36% avgW=+0.91 avgL=-0.58 maxDD=25.4R streak=13 hold=9.5d | n=117 exp=+0.080R [-0.09..+0.27] total=+9.4R PF=1.26 win=44% avgW=+0.86 avgL=-0.54 maxDD=6.7R streak=7 hold=14.7d | **CANDIDATE** — TEST PF 1.26 < 1.3; TRAIN net ≤ 0; max DD 25.4R > 20R |
| baseline | n=358 exp=+0.011R [-0.07..+0.10] total=+3.9R PF=1.03 win=41% avgW=+0.80 avgL=-0.53 maxDD=34.5R streak=14 hold=14.0d | n=231 exp=+0.131R [-0.00..+0.27] total=+30.4R PF=1.49 win=41% avgW=+0.98 avgL=-0.45 maxDD=12.0R streak=15 hold=15.3d | **reference** — random entry, same exit |

## N=20

- ALL: n=544 exp=+0.063R [-0.01..+0.14] total=+34.4R PF=1.20 win=42% avgW=+0.90 avgL=-0.54 maxDD=26.6R streak=16 hold=11.5d
- costs per trade: fees 0.011R, funding -0.015R (+ = received); 3.5 trades/week on 15 coins; max 15 open at once
- portfolio at 0.5% risk per trade: +17.2% over 3.0 y (+5.7%/y, simple), max drawdown 13.3% (closed trades)
- exits: stop 533, open_at_end 6, max_hold 5

| slice | result |
|---|---|
| long — TRAIN | n=187 exp=+0.193R [+0.03..+0.35] total=+36.1R PF=1.59 win=44% avgW=+1.17 avgL=-0.58 maxDD=23.5R streak=13 hold=10.5d |
| long — TEST | n=105 exp=+0.018R [-0.19..+0.25] total=+1.9R PF=1.05 win=34% avgW=+1.19 avgL=-0.59 maxDD=18.3R streak=9 hold=7.7d |
| short — TRAIN | n=147 exp=-0.102R [-0.19..-0.01] total=-15.0R PF=0.64 win=38% avgW=+0.48 avgL=-0.46 maxDD=19.6R streak=11 hold=11.7d |
| short — TEST | n=105 exp=+0.109R [-0.04..+0.26] total=+11.5R PF=1.41 win=51% avgW=+0.73 avgL=-0.54 maxDD=8.4R streak=13 hold=17.5d |
| entries 2023 | n=23 exp=+0.214R [-0.11..+0.56] total=+4.9R PF=1.89 win=52% avgW=+0.87 avgL=-0.50 maxDD=2.4R streak=3 hold=9.8d |
| entries 2024 | n=201 exp=+0.035R [-0.10..+0.17] total=+7.0R PF=1.10 win=36% avgW=+1.02 avgL=-0.53 maxDD=26.6R streak=16 hold=10.7d |
| entries 2025 | n=170 exp=+0.005R [-0.12..+0.13] total=+0.8R PF=1.02 win=48% avgW=+0.64 avgL=-0.57 maxDD=19.9R streak=11 hold=12.5d |
| entries 2026 | n=150 exp=+0.145R [-0.03..+0.33] total=+21.7R PF=1.45 win=42% avgW=+1.10 avgL=-0.55 maxDD=9.8R streak=11 hold=12.5d |

Per coin (total net R, n): DOGEUSDT +7.2 (35), HBARUSDT +6.8 (36), NEARUSDT +6.6 (40), XLMUSDT +6.2 (37), ENAUSDT +5.2 (29), ETHUSDT +4.0 (34), SUIUSDT +3.3 (37), TRXUSDT +2.9 (33), BTCUSDT +1.3 (37), ARBUSDT +1.0 (40), XRPUSDT +0.3 (36), OPUSDT -1.2 (36), SOLUSDT -1.5 (38), ADAUSDT -2.2 (38), INJUSDT -5.3 (38)

## N=55

- ALL: n=300 exp=+0.001R [-0.10..+0.11] total=+0.3R PF=1.00 win=39% avgW=+0.89 avgL=-0.57 maxDD=25.4R streak=13 hold=11.5d
- costs per trade: fees 0.011R, funding -0.018R (+ = received); 1.9 trades/week on 15 coins; max 15 open at once
- portfolio at 0.5% risk per trade: +0.1% over 3.0 y (+0.0%/y, simple), max drawdown 12.7% (closed trades)
- exits: stop 296, max_hold 2, open_at_end 2

| slice | result |
|---|---|
| long — TRAIN | n=111 exp=+0.085R [-0.12..+0.30] total=+9.4R PF=1.22 win=40% avgW=+1.19 avgL=-0.64 maxDD=15.8R streak=9 hold=7.5d |
| long — TEST | n=55 exp=+0.050R [-0.25..+0.41] total=+2.8R PF=1.12 win=40% avgW=+1.17 avgL=-0.70 maxDD=8.7R streak=5 hold=7.7d |
| short — TRAIN | n=72 exp=-0.257R [-0.36..-0.15] total=-18.5R PF=0.27 win=29% avgW=+0.32 avgL=-0.50 maxDD=18.5R streak=15 hold=13.3d |
| short — TEST | n=62 exp=+0.106R [-0.04..+0.26] total=+6.6R PF=1.53 win=48% avgW=+0.63 avgL=-0.39 maxDD=3.5R streak=7 hold=17.3d |
| entries 2023 | n=7 exp=+0.113R [-0.30..+0.55] total=+0.8R PF=1.52 win=43% avgW=+0.77 avgL=-0.38 maxDD=0.9R streak=2 hold=12.5d |
| entries 2024 | n=111 exp=-0.005R [-0.21..+0.21] total=-0.6R PF=0.99 win=33% avgW=+1.23 avgL=-0.62 maxDD=25.4R streak=13 hold=8.5d |
| entries 2025 | n=98 exp=-0.157R [-0.26..-0.04] total=-15.4R PF=0.51 win=39% avgW=+0.42 avgL=-0.53 maxDD=15.4R streak=7 hold=13.5d |
| entries 2026 | n=84 exp=+0.184R [-0.03..+0.42] total=+15.5R PF=1.63 win=46% avgW=+1.02 avgL=-0.54 maxDD=6.2R streak=5 hold=12.3d |

Per coin (total net R, n): NEARUSDT +6.1 (19), XLMUSDT +4.5 (17), HBARUSDT +4.0 (20), XRPUSDT +2.5 (17), ETHUSDT +2.0 (19), ENAUSDT +2.0 (20), BTCUSDT +1.6 (19), DOGEUSDT +0.1 (20), SOLUSDT -1.2 (20), ADAUSDT -1.9 (19), TRXUSDT -2.3 (21), SUIUSDT -3.7 (23), ARBUSDT -3.8 (23), OPUSDT -4.1 (21), INJUSDT -5.8 (22)

## baseline

- ALL: n=589 exp=+0.058R [-0.02..+0.13] total=+34.2R PF=1.20 win=41% avgW=+0.87 avgL=-0.50 maxDD=34.5R streak=19 hold=14.5d
- costs per trade: fees 0.010R, funding -0.006R (+ = received); 3.8 trades/week on 15 coins; max 15 open at once
- portfolio at 0.5% risk per trade: +17.1% over 3.0 y (+5.7%/y, simple), max drawdown 17.3% (closed trades)
- exits: stop 572, open_at_end 11, max_hold 6

| slice | result |
|---|---|
| long — TRAIN | n=180 exp=+0.132R [-0.01..+0.29] total=+23.8R PF=1.45 win=41% avgW=+1.03 avgL=-0.50 maxDD=21.1R streak=20 hold=14.0d |
| long — TEST | n=116 exp=+0.015R [-0.17..+0.25] total=+1.7R PF=1.05 win=29% avgW=+1.06 avgL=-0.42 maxDD=15.4R streak=19 hold=15.8d |
| short — TRAIN | n=178 exp=-0.112R [-0.21..-0.01] total=-19.9R PF=0.67 win=40% avgW=+0.55 avgL=-0.56 maxDD=23.0R streak=13 hold=14.2d |
| short — TEST | n=115 exp=+0.249R [+0.10..+0.41] total=+28.6R PF=2.06 win=52% avgW=+0.93 avgL=-0.49 maxDD=10.8R streak=15 hold=15.2d |
| entries 2023 | n=27 exp=+0.082R [-0.22..+0.42] total=+2.2R PF=1.29 win=52% avgW=+0.71 avgL=-0.59 maxDD=5.5R streak=6 hold=21.0d |
| entries 2024 | n=215 exp=-0.070R [-0.17..+0.04] total=-14.9R PF=0.80 win=34% avgW=+0.78 avgL=-0.52 maxDD=21.2R streak=9 hold=12.5d |
| entries 2025 | n=189 exp=+0.126R [+0.00..+0.25] total=+23.8R PF=1.48 win=48% avgW=+0.81 avgL=-0.50 maxDD=14.2R streak=19 hold=14.8d |
| entries 2026 | n=158 exp=+0.146R [-0.02..+0.35] total=+23.1R PF=1.53 win=39% avgW=+1.08 avgL=-0.46 maxDD=12.0R streak=15 hold=15.3d |

Per coin (total net R, n): NEARUSDT +11.9 (35), OPUSDT +9.0 (32), ADAUSDT +6.8 (38), TRXUSDT +6.4 (42), XLMUSDT +5.7 (40), DOGEUSDT +5.0 (42), ETHUSDT +0.8 (40), BTCUSDT +0.8 (40), SUIUSDT +0.8 (39), SOLUSDT -0.6 (42), ARBUSDT -0.6 (42), INJUSDT -0.9 (38), HBARUSDT -1.6 (40), XRPUSDT -2.0 (42), ENAUSDT -7.4 (37)