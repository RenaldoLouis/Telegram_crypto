# Weekly cross-sectional momentum L/S — Bybit USDT perps — 20261004

## Pre-registered success bar (written before the run)

> SHIP-CANDIDATE if, net of costs, annualized Sharpe >= 1.0 AND max drawdown <= 25% AND >= 55% of weeks positive, holding on BOTH chronological halves AND for at least two adjacent lookbacks. CANDIDATE if net Sharpe >= 0.5 on both halves. Otherwise NO. Costs and the survivorship caveat are part of the result, not footnotes.

## Verdict (mechanical application of the bar, full universe, dollar-neutral L/S)

**CANDIDATE**

| lookback | full Sharpe | full MDD | full %+ | H1 Sharpe | H2 Sharpe | SHIP conditions (full+H1+H2) | CANDIDATE (Sharpe≥0.5 both halves) |
|---|---|---|---|---|---|---|---|
| 7 | 0.04 | 71.9% | 47% | 2.63 | -2.35 | fail | fail |
| 14 | 0.86 | 53.7% | 48% | 1.58 | 0.22 | fail | fail |
| 28 | 1.95 | 43.3% | 58% | 2.83 | 1.20 | fail | PASS |
| 56 | 2.32 | 29.8% | 61% | 2.31 | 2.33 | fail | PASS |
| 91 | 2.25 | 43.1% | 65% | 2.59 | 2.20 | fail | PASS |
| 28s7 | 1.76 | 27.6% | 61% | 0.31 | 3.22 | fail | fail |

### Funding sensitivity — the headline verdict depends on funding RECEIVED

Net = gross − fees/slippage − funding. `actual` is the pre-registered treatment (actual settlements, credits and debits). `ex-funding` ignores funding entirely. `pay-only` charges every funding payment but credits NOTHING received — the conservative bound if the squeezed-short funding windfalls prove uncapturable.

| lookback | actual: net ann / Sharpe / H1 / H2 | ex-funding: net ann / Sharpe / H1 / H2 | pay-only: net ann / Sharpe / H1 / H2 |
|---|---|---|---|
| 7 | -15.3% / 0.04 / 2.63 / -2.35 | -50.0% / -0.87 / 1.93 / -3.50 | -71.8% / -1.81 / 0.92 / -4.49 |
| 14 | 44.8% / 0.86 / 1.58 / 0.22 | -26.0% / -0.06 / 0.84 / -0.83 | -57.2% / -0.78 / -0.00 / -1.50 |
| 28 | 212.8% / 1.95 / 2.83 / 1.20 | 42.0% / 0.85 / 2.05 / -0.14 | -2.0% / 0.31 / 1.36 / -0.59 |
| 56 | 246.0% / 2.32 / 2.31 / 2.33 | 57.9% / 1.05 / 1.32 / 0.85 | 14.9% / 0.52 / 0.72 / 0.37 |
| 91 | 278.8% / 2.25 / 2.59 / 2.20 | 105.8% / 1.37 / 1.85 / 1.18 | 55.2% / 0.96 / 1.28 / 0.84 |
| 28s7 | 160.2% / 1.76 / 0.31 / 3.22 | 57.0% / 1.01 / -0.05 / 2.02 | 2.6% / 0.35 / -0.80 / 1.49 |

Bar applied under each treatment (full universe): actual → **CANDIDATE**; ex-funding → **CANDIDATE** (CANDIDATE lookbacks ['56', '91']); pay-only → **CANDIDATE** (CANDIDATE lookbacks ['91']).

k=56 funding attribution: total funding received over 62 weeks = 133.1% of equity, of which the LONG leg received 94% and the 10 largest symbol-weeks alone account for 36%. Largest: DEXEUSDT 2026-07-19 (8.2% of equity, w=+0.083); HUSDT 2026-06-07 (5.6% of equity, w=+0.062); RAVEUSDT 2026-04-12 (5.3% of equity, w=+0.071); LYNUSDT 2026-03-08 (4.8% of equity, w=+0.071); LABUSDT 2026-05-31 (4.8% of equity, w=+0.071).
These are squeezed shorts on hourly-funded small caps printing funding near the −2%/hour cap — the long leg is being paid to hold the pumping coin. That is a real transfer on Bybit, but it is (a) concentrated in a handful of names and weeks, (b) specific to recent listings (the ≥365-day universe loses it), and (c) a crowded-squeeze artefact, not a price-momentum premium. The ex-funding and pay-only rows are the honest read of the PRICE edge.

≥365-day-listed universe verdict: **NO** (SHIP pairs: none; CANDIDATE lookbacks: none)

## Data & method

- Universe: 782 currently-listed `Trading` LinearPerpetual USDT symbols from `/v5/market/instruments-info`; 679 with ≥60 closed daily bars used, 103 skipped.
- Daily klines (`interval=D`), 540 days requested; panel 2025-04-12 → 2026-10-03 (540 days). The in-progress daily bar is dropped. 324 symbols span the full window; 417 have been listed ≥365 days.
- **SURVIVORSHIP BIAS:** only symbols listed TODAY are in the panel. Coins delisted during the window (typically the worst losers — exactly the short leg's targets, and the long leg's blow-ups) are absent. This biases the bottom-decile short leg's realised returns and the long-leg's tail risk. Results are an UPPER bound until a point-in-time universe is available. The ≥365-day-listed repeat below removes recent listings but does NOT fix delisting survivorship.
- Rebalance: every Monday 00:00 UTC at the daily close (= the Sunday daily bar's close). 62 weeks, 2025-07-20 → 2026-09-20, aligned so every lookback starts on the same week (first rebalance needs 93 bars). H1 = 2025-07-20 → 2026-02-15, H2 = 2026-02-22 → 2026-09-20.
- Eligible: ≥ lookback+2 contiguous daily closes AND trailing-7-day mean daily turnover ≥ $10M (kline turnover column, as of the rebalance bar — no look-ahead).
- Signal: trailing k-day close-to-close return, k ∈ {7,14,28,56,91}; plus `28s7` = return from t−28 to t−7 (skip the last week).
- Portfolio: long top decile, short bottom decile (decile = floor(n/10) names), equal weight within leg, 50/50 dollar-neutral, hold one week, weekly return = Σ wᵢ·(close_{t+7}/close_t − 1). `rev` = reversed sign (short winners / long losers). `long` / `short` = single leg at 100% gross.
- Costs: turnover = Σ|w_t − drifted w_{t−1}| (first week = full open), charged 0.055% taker + 0.03% slippage per unit of turnover. Funding: ACTUAL 8h/4h/1h settlement history fetched for all 405 held symbols. Funding is charged to longs / credited to shorts on the held weights using settlements inside the holding week.
- Multiple testing: **48 portfolio variants** were evaluated (6 lookbacks × 4 leg modes × 2 universes), each read under 3 funding treatments (144 readouts), plus one decile table; with ~62 weekly observations each, the chance that at least one variant shows net Sharpe ≥ 1.0 by luck alone is material (one-sided p for Sharpe 1.0 over 62 weeks ≈ 0.137 per variant). The pre-registered bar demands BOTH halves AND adjacent lookbacks precisely to blunt this; no parameter was tuned after seeing results.

## Results — full universe (679 symbols)

### Long/short (dollar-neutral)

**Full period**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | -45.9% | -15.3% | 0.04 | 71.9% | 47% | 1.77 | 8.7 | -53.6% |
| k=14 | 62 | -21.1% | 44.8% | 0.86 | 53.7% | 48% | 1.42 | 8.5 | -68.9% |
| k=28 | 62 | 49.9% | 212.8% | 1.95 | 43.3% | 58% | 1.21 | 8.3 | -81.6% |
| k=56 | 62 | 65.8% | 246.0% | 2.32 | 29.8% | 61% | 1.11 | 7.9 | -80.4% |
| k=91 | 62 | 114.9% | 278.8% | 2.25 | 43.1% | 65% | 0.99 | 7.5 | -61.8% |
| k=28s7 | 62 | 66.7% | 160.2% | 1.76 | 27.6% | 61% | 1.38 | 8.3 | -52.9% |

**First half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | 160.3% | 276.8% | 2.63 | 15.8% | 61% | 1.70 | 10.4 | -47.0% |
| k=14 | 31 | 50.6% | 138.9% | 1.58 | 29.3% | 55% | 1.36 | 10.1 | -56.6% |
| k=28 | 31 | 208.3% | 412.8% | 2.83 | 25.5% | 61% | 1.15 | 9.7 | -59.5% |
| k=56 | 31 | 82.0% | 199.5% | 2.31 | 15.3% | 61% | 1.07 | 9.1 | -56.4% |
| k=91 | 31 | 124.4% | 201.9% | 2.59 | 14.0% | 68% | 0.91 | 8.8 | -34.1% |
| k=28s7 | 31 | -14.2% | -0.1% | 0.31 | 27.6% | 55% | 1.32 | 9.7 | -23.4% |

**Second half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -88.8% | -80.9% | -2.35 | 71.9% | 32% | 1.84 | 7.1 | -60.3% |
| k=14 | 31 | -58.6% | -12.2% | 0.22 | 53.7% | 42% | 1.48 | 7.0 | -81.3% |
| k=28 | 31 | -27.2% | 90.8% | 1.20 | 43.3% | 55% | 1.28 | 6.9 | -103.6% |
| k=56 | 31 | 51.0% | 299.7% | 2.33 | 29.8% | 61% | 1.14 | 6.6 | -104.3% |
| k=91 | 31 | 105.9% | 375.4% | 2.20 | 43.1% | 61% | 1.08 | 6.3 | -89.5% |
| k=28s7 | 31 | 224.0% | 577.8% | 3.22 | 15.7% | 68% | 1.43 | 6.9 | -82.4% |

**2026 only**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 38 | -76.6% | -59.7% | -1.13 | 71.9% | 42% | 1.82 | 7.4 | -62.5% |
| k=14 | 38 | -40.5% | 26.4% | 0.68 | 53.7% | 45% | 1.46 | 7.3 | -82.0% |
| k=28 | 38 | 11.2% | 194.3% | 1.78 | 43.3% | 58% | 1.28 | 7.2 | -105.3% |
| k=56 | 38 | 87.1% | 416.0% | 2.79 | 29.8% | 63% | 1.15 | 6.9 | -109.4% |
| k=91 | 38 | 92.0% | 308.7% | 2.15 | 43.1% | 68% | 1.08 | 6.6 | -81.3% |
| k=28s7 | 38 | 208.0% | 494.2% | 2.97 | 17.3% | 63% | 1.44 | 7.2 | -74.6% |

### REVERSED sign — sanity check

**Full period**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | 29.9% | -31.2% | -0.29 | 75.7% | 52% | 1.76 | 8.7 | 53.6% |
| k=14 | 62 | -24.2% | -65.5% | -1.03 | 76.7% | 50% | 1.43 | 8.5 | 68.9% |
| k=28 | 62 | -58.6% | -83.5% | -2.11 | 90.9% | 42% | 1.24 | 8.3 | 81.6% |
| k=56 | 62 | -58.3% | -82.9% | -2.48 | 86.9% | 35% | 1.13 | 7.9 | 80.4% |
| k=91 | 62 | -72.0% | -86.0% | -2.37 | 91.5% | 35% | 1.03 | 7.5 | 61.8% |
| k=28s7 | 62 | -60.3% | -78.9% | -1.95 | 85.9% | 35% | 1.40 | 8.3 | 52.9% |

**First half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -71.4% | -84.1% | -2.90 | 67.6% | 39% | 1.73 | 10.4 | 47.0% |
| k=14 | 31 | -56.9% | -78.0% | -1.75 | 51.6% | 45% | 1.38 | 10.1 | 56.6% |
| k=28 | 31 | -78.5% | -89.3% | -2.98 | 68.7% | 39% | 1.18 | 9.7 | 59.5% |
| k=56 | 31 | -57.8% | -77.9% | -2.49 | 52.7% | 35% | 1.09 | 9.1 | 56.4% |
| k=91 | 31 | -64.8% | -76.2% | -2.77 | 59.1% | 32% | 0.93 | 8.8 | 34.1% |
| k=28s7 | 31 | -19.1% | -41.1% | -0.49 | 30.6% | 42% | 1.30 | 9.7 | 23.4% |

**Second half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | 490.5% | 198.3% | 2.09 | 21.2% | 65% | 1.79 | 7.1 | 60.3% |
| k=14 | 31 | 33.3% | -45.8% | -0.38 | 41.2% | 55% | 1.47 | 7.0 | 81.3% |
| k=28 | 31 | -20.4% | -74.5% | -1.35 | 63.5% | 45% | 1.30 | 6.9 | 103.6% |
| k=56 | 31 | -58.7% | -86.8% | -2.48 | 70.3% | 35% | 1.18 | 6.6 | 104.3% |
| k=91 | 31 | -77.7% | -91.8% | -2.31 | 74.6% | 39% | 1.12 | 6.3 | 89.5% |
| k=28s7 | 31 | -80.5% | -92.4% | -3.42 | 79.9% | 29% | 1.49 | 6.9 | 82.4% |

**2026 only**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 38 | 192.1% | 43.1% | 0.87 | 47.1% | 55% | 1.79 | 7.4 | 62.5% |
| k=14 | 38 | -1.7% | -60.5% | -0.85 | 63.4% | 53% | 1.45 | 7.3 | 82.0% |
| k=28 | 38 | -48.3% | -83.9% | -1.92 | 81.9% | 42% | 1.29 | 7.2 | 105.3% |
| k=56 | 38 | -65.4% | -89.6% | -2.95 | 81.1% | 32% | 1.18 | 6.9 | 109.4% |
| k=91 | 38 | -72.5% | -88.9% | -2.28 | 80.8% | 32% | 1.11 | 6.6 | 81.3% |
| k=28s7 | 38 | -79.7% | -91.5% | -3.15 | 84.6% | 34% | 1.48 | 7.2 | 74.6% |

### Long-only top decile

**Full period**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | -95.8% | -73.3% | -0.48 | 92.3% | 47% | 1.76 | 8.7 | -187.7% |
| k=14 | 62 | -80.6% | 47.4% | 0.90 | 77.2% | 47% | 1.38 | 8.5 | -209.5% |
| k=28 | 62 | -37.4% | 335.6% | 1.76 | 47.1% | 55% | 1.12 | 8.3 | -202.9% |
| k=56 | 62 | -29.2% | 366.4% | 1.86 | 47.3% | 61% | 0.99 | 7.9 | -195.2% |
| k=91 | 62 | -37.5% | 181.0% | 1.37 | 67.9% | 52% | 0.90 | 7.5 | -150.9% |
| k=28s7 | 62 | -51.8% | 116.6% | 1.22 | 55.0% | 50% | 1.29 | 8.3 | -156.1% |

**First half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -79.1% | 17.3% | 0.67 | 40.6% | 55% | 1.72 | 10.4 | -179.2% |
| k=14 | 31 | -52.1% | 224.3% | 1.56 | 47.3% | 48% | 1.29 | 10.1 | -201.3% |
| k=28 | 31 | -25.2% | 313.9% | 1.71 | 36.2% | 58% | 1.04 | 9.7 | -176.8% |
| k=56 | 31 | -32.7% | 204.9% | 1.55 | 35.7% | 58% | 0.96 | 9.1 | -156.0% |
| k=91 | 31 | -63.7% | 5.0% | 0.48 | 36.8% | 45% | 0.85 | 8.8 | -104.3% |
| k=28s7 | 31 | -81.1% | -36.5% | -0.04 | 55.0% | 45% | 1.20 | 9.7 | -124.3% |

**Second half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -99.2% | -93.9% | -1.49 | 92.3% | 39% | 1.80 | 7.1 | -196.3% |
| k=14 | 31 | -92.1% | -33.0% | 0.40 | 77.2% | 45% | 1.47 | 7.0 | -217.7% |
| k=28 | 31 | -47.6% | 358.5% | 1.79 | 47.1% | 52% | 1.21 | 6.9 | -228.9% |
| k=56 | 31 | -25.5% | 613.3% | 2.10 | 47.3% | 65% | 1.02 | 6.6 | -234.4% |
| k=91 | 31 | 7.6% | 652.1% | 1.97 | 67.9% | 58% | 0.95 | 6.3 | -197.4% |
| k=28s7 | 31 | 23.0% | 638.9% | 2.36 | 31.5% | 55% | 1.38 | 6.9 | -187.8% |

**2026 only**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 38 | -98.4% | -86.3% | -0.97 | 92.3% | 45% | 1.79 | 7.4 | -212.0% |
| k=14 | 38 | -89.8% | 4.5% | 0.66 | 77.2% | 47% | 1.44 | 7.3 | -236.5% |
| k=28 | 38 | -44.3% | 459.1% | 1.97 | 47.1% | 55% | 1.21 | 7.2 | -240.9% |
| k=56 | 38 | -22.8% | 781.8% | 2.35 | 47.3% | 66% | 1.04 | 6.9 | -253.3% |
| k=91 | 38 | -48.9% | 240.9% | 1.48 | 67.9% | 53% | 0.97 | 6.6 | -191.3% |
| k=28s7 | 38 | 4.4% | 573.9% | 2.27 | 31.5% | 55% | 1.40 | 7.2 | -194.3% |

### Short-only bottom decile

**Full period**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | 214.8% | 32.7% | 0.76 | 57.6% | 53% | 1.81 | 8.7 | 80.4% |
| k=14 | 62 | 58.0% | -30.8% | 0.12 | 63.7% | 52% | 1.48 | 8.5 | 71.6% |
| k=28 | 62 | 97.1% | 24.4% | 0.70 | 50.5% | 56% | 1.33 | 8.3 | 39.7% |
| k=56 | 62 | 121.3% | 48.6% | 0.91 | 40.0% | 58% | 1.24 | 7.9 | 34.4% |
| k=91 | 62 | 238.8% | 147.7% | 1.50 | 49.1% | 61% | 1.11 | 7.5 | 27.3% |
| k=28s7 | 62 | 236.8% | 83.6% | 1.15 | 44.9% | 60% | 1.47 | 8.3 | 50.4% |

**First half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | 1574.2% | 565.1% | 2.92 | 22.8% | 68% | 1.70 | 10.4 | 85.2% |
| k=14 | 31 | 155.4% | -13.1% | 0.44 | 58.0% | 58% | 1.46 | 10.1 | 88.1% |
| k=28 | 31 | 565.3% | 247.6% | 1.84 | 38.2% | 58% | 1.27 | 9.7 | 57.8% |
| k=56 | 31 | 206.8% | 87.8% | 1.24 | 28.6% | 65% | 1.19 | 9.1 | 43.1% |
| k=91 | 31 | 682.7% | 421.1% | 2.54 | 23.1% | 71% | 0.99 | 8.8 | 36.2% |
| k=28s7 | 31 | 109.9% | -16.0% | 0.42 | 44.9% | 61% | 1.45 | 9.7 | 77.6% |

**Second half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -40.8% | -73.5% | -1.11 | 57.6% | 39% | 1.91 | 7.1 | 75.7% |
| k=14 | 31 | -2.2% | -44.9% | -0.29 | 44.8% | 45% | 1.51 | 7.0 | 55.1% |
| k=28 | 31 | -41.6% | -55.5% | -0.50 | 50.5% | 55% | 1.38 | 6.9 | 21.6% |
| k=56 | 31 | 59.7% | 17.7% | 0.62 | 40.0% | 52% | 1.28 | 6.6 | 25.7% |
| k=91 | 31 | 46.7% | 17.8% | 0.65 | 49.1% | 52% | 1.23 | 6.3 | 18.4% |
| k=28s7 | 31 | 440.5% | 300.9% | 2.10 | 22.5% | 58% | 1.49 | 6.9 | 23.1% |

**2026 only**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 38 | 42.7% | -42.8% | -0.23 | 57.6% | 45% | 1.88 | 7.4 | 86.9% |
| k=14 | 38 | 73.1% | -18.0% | 0.15 | 44.8% | 50% | 1.50 | 7.3 | 72.6% |
| k=28 | 38 | 32.6% | -6.0% | 0.35 | 50.5% | 58% | 1.36 | 7.2 | 30.2% |
| k=56 | 38 | 153.8% | 72.7% | 1.09 | 40.0% | 58% | 1.28 | 6.9 | 34.5% |
| k=91 | 38 | 177.7% | 101.3% | 1.24 | 49.1% | 58% | 1.22 | 6.6 | 28.8% |
| k=28s7 | 38 | 476.6% | 248.8% | 1.99 | 22.5% | 61% | 1.49 | 7.2 | 45.2% |

## Decile monotonicity — k=28, gross next-week return

### Full universe

| decile (1 = biggest 28d losers … 10 = biggest winners) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| mean next-week return | -2.05% | -1.03% | -1.49% | -1.53% | -0.84% | -1.58% | -1.92% | -2.44% | -1.19% | -0.53% |
| % weeks positive | 44% | 42% | 37% | 40% | 44% | 44% | 40% | 39% | 31% | 42% |

D10 − D1 spread: mean 1.52%/week, positive in 52% of 62 weeks (gross, before costs/funding).

### ≥365-day-listed universe

| decile (1 = biggest 28d losers … 10 = biggest winners) | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|---|
| mean next-week return | -1.14% | -0.58% | -0.96% | -1.20% | -1.51% | -0.58% | -1.85% | -2.24% | 0.01% | -3.31% |
| % weeks positive | 42% | 39% | 37% | 40% | 45% | 39% | 40% | 35% | 40% | 34% |

D10 − D1 spread: mean -2.17%/week, positive in 45% of 62 weeks (gross, before costs/funding).

## Results — ≥365-day-listed universe (417 symbols)

### Long/short (dollar-neutral)

**Full period**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | -72.4% | -68.0% | -1.20 | 85.2% | 40% | 1.78 | 7.5 | -20.8% |
| k=14 | 62 | -52.1% | -32.5% | -0.07 | 73.2% | 39% | 1.40 | 7.5 | -40.1% |
| k=28 | 62 | -52.2% | -11.6% | 0.20 | 64.7% | 50% | 1.22 | 7.3 | -68.0% |
| k=56 | 62 | -22.8% | 23.6% | 0.64 | 50.9% | 53% | 1.11 | 7.2 | -54.1% |
| k=91 | 62 | 22.8% | 73.1% | 1.09 | 54.9% | 58% | 1.01 | 7.0 | -40.2% |
| k=28s7 | 62 | 12.8% | 64.8% | 1.12 | 28.4% | 61% | 1.39 | 7.3 | -45.0% |

**First half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | 64.2% | 97.2% | 1.46 | 24.1% | 45% | 1.70 | 9.8 | -28.6% |
| k=14 | 31 | 13.7% | 56.5% | 1.01 | 31.0% | 45% | 1.35 | 9.7 | -38.6% |
| k=28 | 31 | 59.9% | 145.4% | 1.86 | 29.9% | 55% | 1.14 | 9.4 | -49.2% |
| k=56 | 31 | 50.4% | 119.6% | 1.81 | 19.0% | 61% | 1.06 | 9.0 | -43.4% |
| k=91 | 31 | 201.7% | 279.9% | 3.06 | 14.0% | 68% | 0.91 | 8.7 | -27.4% |
| k=28s7 | 31 | -29.3% | -17.7% | -0.08 | 28.4% | 55% | 1.29 | 9.4 | -21.7% |

**Second half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -95.4% | -94.8% | -3.26 | 85.0% | 35% | 1.86 | 5.3 | -13.1% |
| k=14 | 31 | -79.8% | -70.9% | -0.72 | 73.2% | 32% | 1.45 | 5.3 | -41.6% |
| k=28 | 31 | -85.7% | -68.1% | -0.88 | 64.7% | 45% | 1.30 | 5.3 | -86.9% |
| k=56 | 31 | -60.4% | -30.5% | 0.03 | 50.9% | 45% | 1.16 | 5.3 | -64.9% |
| k=91 | 31 | -50.1% | -21.2% | 0.19 | 54.9% | 48% | 1.12 | 5.3 | -53.1% |
| k=28s7 | 31 | 79.9% | 230.0% | 2.14 | 19.3% | 68% | 1.49 | 5.3 | -68.3% |

**2026 only**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 38 | -91.7% | -90.9% | -2.78 | 85.0% | 37% | 1.84 | 5.7 | -12.4% |
| k=14 | 38 | -75.0% | -66.3% | -0.71 | 73.2% | 32% | 1.44 | 5.7 | -35.2% |
| k=28 | 38 | -80.8% | -58.7% | -0.69 | 64.7% | 45% | 1.29 | 5.7 | -82.9% |
| k=56 | 38 | -44.7% | -0.9% | 0.39 | 50.9% | 50% | 1.16 | 5.7 | -66.6% |
| k=91 | 38 | -23.0% | 13.8% | 0.55 | 54.9% | 58% | 1.11 | 5.7 | -46.1% |
| k=28s7 | 38 | 44.9% | 159.7% | 1.84 | 19.3% | 63% | 1.47 | 5.7 | -65.1% |

### REVERSED sign — sanity check

**Full period**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | 104.9% | 57.4% | 0.98 | 61.2% | 56% | 1.74 | 7.5 | 20.8% |
| k=14 | 62 | 3.3% | -35.9% | -0.08 | 66.2% | 61% | 1.40 | 7.5 | 40.1% |
| k=28 | 62 | 26.0% | -41.0% | -0.35 | 70.3% | 50% | 1.21 | 7.3 | 68.0% |
| k=56 | 62 | -19.9% | -57.3% | -0.78 | 67.7% | 47% | 1.12 | 7.2 | 54.1% |
| k=91 | 62 | -52.4% | -70.7% | -1.21 | 82.4% | 42% | 1.03 | 7.0 | 40.2% |
| k=28s7 | 62 | -38.0% | -63.4% | -1.33 | 73.4% | 37% | 1.40 | 7.3 | 45.0% |

**First half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -53.3% | -68.7% | -1.73 | 55.6% | 52% | 1.73 | 9.8 | 28.6% |
| k=14 | 31 | -38.6% | -61.3% | -1.21 | 46.6% | 55% | 1.36 | 9.7 | 38.6% |
| k=28 | 31 | -53.7% | -73.8% | -2.04 | 53.7% | 45% | 1.15 | 9.4 | 49.2% |
| k=56 | 31 | -47.9% | -68.3% | -2.00 | 41.3% | 39% | 1.08 | 9.0 | 43.4% |
| k=91 | 31 | -74.3% | -81.4% | -3.23 | 64.7% | 32% | 0.93 | 8.7 | 27.4% |
| k=28s7 | 31 | 7.2% | -19.0% | -0.12 | 22.5% | 42% | 1.27 | 9.4 | 21.7% |

**Second half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | 798.6% | 692.2% | 3.05 | 27.7% | 61% | 1.76 | 5.3 | 13.1% |
| k=14 | 31 | 73.7% | 6.1% | 0.59 | 50.5% | 68% | 1.44 | 5.3 | 41.6% |
| k=28 | 31 | 243.0% | 32.5% | 0.75 | 41.0% | 55% | 1.27 | 5.3 | 86.9% |
| k=56 | 31 | 23.1% | -42.4% | -0.14 | 41.4% | 55% | 1.17 | 5.3 | 64.9% |
| k=91 | 31 | -12.1% | -53.9% | -0.30 | 45.3% | 52% | 1.14 | 5.3 | 53.1% |
| k=28s7 | 31 | -64.2% | -83.5% | -2.35 | 65.0% | 32% | 1.53 | 5.3 | 68.3% |

**2026 only**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 38 | 478.0% | 404.0% | 2.57 | 30.8% | 61% | 1.75 | 5.7 | 12.4% |
| k=14 | 38 | 66.3% | 8.6% | 0.58 | 54.1% | 68% | 1.42 | 5.7 | 35.2% |
| k=28 | 38 | 180.3% | 13.3% | 0.55 | 53.0% | 55% | 1.26 | 5.7 | 82.9% |
| k=56 | 38 | -2.1% | -54.7% | -0.51 | 57.8% | 50% | 1.17 | 5.7 | 66.6% |
| k=91 | 38 | -34.7% | -62.9% | -0.67 | 60.6% | 42% | 1.12 | 5.7 | 46.1% |
| k=28s7 | 38 | -53.6% | -77.7% | -2.05 | 70.8% | 37% | 1.49 | 5.7 | 65.1% |

### Long-only top decile

**Full period**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | -98.6% | -93.5% | -1.66 | 97.5% | 35% | 1.77 | 7.5 | -153.4% |
| k=14 | 62 | -93.3% | -72.4% | -0.15 | 92.9% | 42% | 1.37 | 7.5 | -145.2% |
| k=28 | 62 | -90.0% | -45.5% | 0.13 | 80.7% | 48% | 1.15 | 7.3 | -176.3% |
| k=56 | 62 | -72.6% | 10.9% | 0.63 | 65.0% | 50% | 1.04 | 7.2 | -148.6% |
| k=91 | 62 | -66.2% | -0.9% | 0.58 | 78.9% | 48% | 0.94 | 7.0 | -111.7% |
| k=28s7 | 62 | -78.6% | -12.3% | 0.31 | 55.5% | 48% | 1.33 | 7.3 | -142.9% |

**First half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -83.3% | -39.6% | 0.11 | 62.5% | 39% | 1.70 | 9.8 | -136.7% |
| k=14 | 31 | -76.5% | -13.9% | 0.38 | 64.9% | 45% | 1.28 | 9.7 | -134.0% |
| k=28 | 31 | -62.5% | 50.5% | 0.86 | 43.8% | 52% | 1.04 | 9.4 | -143.7% |
| k=56 | 31 | -60.6% | 30.7% | 0.72 | 35.7% | 52% | 0.96 | 9.0 | -121.0% |
| k=91 | 31 | -42.3% | 40.9% | 0.79 | 32.2% | 48% | 0.85 | 8.7 | -89.3% |
| k=28s7 | 31 | -87.1% | -65.4% | -0.95 | 55.5% | 39% | 1.16 | 9.4 | -100.4% |

**Second half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -99.9% | -99.3% | -3.61 | 96.6% | 32% | 1.84 | 5.3 | -170.1% |
| k=14 | 31 | -98.1% | -91.1% | -0.48 | 92.9% | 39% | 1.45 | 5.3 | -156.3% |
| k=28 | 31 | -97.3% | -80.3% | -0.51 | 80.7% | 45% | 1.26 | 5.3 | -208.8% |
| k=56 | 31 | -81.0% | -5.9% | 0.59 | 65.0% | 48% | 1.11 | 5.3 | -176.1% |
| k=91 | 31 | -80.2% | -30.3% | 0.49 | 78.9% | 48% | 1.04 | 5.3 | -134.1% |
| k=28s7 | 31 | -64.2% | 122.4% | 1.26 | 40.3% | 58% | 1.49 | 5.3 | -185.3% |

**2026 only**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 38 | -99.8% | -98.9% | -3.31 | 96.6% | 32% | 1.83 | 5.7 | -158.8% |
| k=14 | 38 | -98.0% | -91.8% | -0.70 | 92.9% | 39% | 1.43 | 5.7 | -144.3% |
| k=28 | 38 | -97.8% | -85.4% | -0.87 | 80.7% | 45% | 1.27 | 5.7 | -196.5% |
| k=56 | 38 | -83.6% | -15.3% | 0.48 | 65.0% | 47% | 1.11 | 5.7 | -177.3% |
| k=91 | 38 | -81.2% | -37.8% | 0.35 | 78.9% | 47% | 1.04 | 5.7 | -127.4% |
| k=28s7 | 38 | -77.3% | 29.0% | 0.73 | 40.3% | 53% | 1.46 | 5.7 | -175.4% |

### Short-only bottom decile

**Full period**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | 135.1% | -28.9% | 0.24 | 71.7% | 55% | 1.82 | 7.5 | 111.7% |
| k=14 | 62 | 35.5% | -34.0% | 0.11 | 63.1% | 55% | 1.47 | 7.5 | 65.0% |
| k=28 | 62 | 13.4% | -29.4% | 0.14 | 65.1% | 53% | 1.31 | 7.3 | 40.2% |
| k=56 | 62 | 18.9% | -25.1% | 0.14 | 68.9% | 56% | 1.21 | 7.2 | 40.3% |
| k=91 | 62 | 119.2% | 53.8% | 0.95 | 62.0% | 61% | 1.10 | 7.0 | 31.2% |
| k=28s7 | 62 | 222.4% | 72.2% | 1.08 | 44.9% | 60% | 1.48 | 7.3 | 52.9% |

**First half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | 718.3% | 231.4% | 1.91 | 22.8% | 65% | 1.72 | 9.8 | 79.5% |
| k=14 | 31 | 180.3% | 46.0% | 0.86 | 40.8% | 55% | 1.44 | 9.7 | 56.8% |
| k=28 | 31 | 234.4% | 95.2% | 1.18 | 48.8% | 58% | 1.26 | 9.4 | 45.3% |
| k=56 | 31 | 231.9% | 118.9% | 1.41 | 32.0% | 65% | 1.19 | 9.0 | 34.3% |
| k=91 | 31 | 819.5% | 522.5% | 2.76 | 23.1% | 71% | 0.99 | 8.7 | 34.6% |
| k=28s7 | 31 | 105.0% | 0.0% | 0.61 | 44.9% | 65% | 1.45 | 9.4 | 57.0% |

**Second half**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 31 | -32.4% | -84.7% | -0.83 | 71.7% | 45% | 1.92 | 5.3 | 144.0% |
| k=14 | 31 | -34.5% | -70.2% | -0.57 | 62.6% | 55% | 1.50 | 5.3 | 73.1% |
| k=28 | 31 | -61.6% | -74.5% | -0.86 | 65.1% | 48% | 1.36 | 5.3 | 35.0% |
| k=56 | 31 | -57.4% | -74.3% | -0.88 | 68.9% | 48% | 1.23 | 5.3 | 46.3% |
| k=91 | 31 | -47.8% | -62.0% | -0.47 | 62.0% | 52% | 1.22 | 5.3 | 27.9% |
| k=28s7 | 31 | 407.1% | 196.5% | 1.66 | 24.8% | 55% | 1.52 | 5.3 | 48.8% |

**2026 only**

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | avg wkly turnover | avg names/leg | funding drag ann |
|---|---|---|---|---|---|---|---|---|---|
| k=7 | 38 | 29.1% | -68.0% | -0.33 | 71.7% | 47% | 1.89 | 5.7 | 134.1% |
| k=14 | 38 | 8.3% | -51.2% | -0.17 | 62.6% | 58% | 1.49 | 5.7 | 73.9% |
| k=28 | 38 | -13.9% | -40.1% | -0.02 | 65.1% | 55% | 1.33 | 5.7 | 30.7% |
| k=56 | 38 | -2.2% | -39.6% | -0.04 | 68.9% | 55% | 1.24 | 5.7 | 44.1% |
| k=91 | 38 | 36.4% | -7.5% | 0.43 | 62.0% | 58% | 1.20 | 5.7 | 35.2% |
| k=28s7 | 38 | 422.4% | 218.6% | 1.75 | 24.8% | 61% | 1.50 | 5.7 | 45.2% |

## Reading guide

- The `rev` block is the same book with the sign flipped: if momentum has no edge, `ls` and `rev` are mirror images around −(costs); if `rev` is the one that looks good, the cross-section is mean-reverting at the weekly horizon, not trending.
- Long-only / short-only are NOT market-neutral: their return is dominated by beta to the crypto market over this window; read them as attribution for the L/S book, not as standalone products.
- Every number above is subject to the survivorship caveat in Data & method.

_Generated by `xs_momentum_backtest.py` in 12s. Zero Claude tokens, zero order logic._
