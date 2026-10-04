# Cross-sectional momentum v2 + funding-carry — Bybit USDT perps — 20261004

## Pre-registered bars (written before the run)

**Momentum (unchanged from v1):** SHIP-CANDIDATE if, net of costs, annualized Sharpe >= 1.0 AND max drawdown <= 25% AND >= 55% of weeks positive, holding on BOTH chronological halves AND for at least two adjacent lookbacks. CANDIDATE if net Sharpe >= 0.5 on both halves. Otherwise NO. Costs and the survivorship caveat are part of the result, not footnotes.

**Funding carry (new):** Weekly long-only basket of the N=10 symbols with the most negative trailing-7-day average funding rate (shorts pay longs), eligible if listed >= 30d and trailing-7d mean turnover >= $10M, equal weight, hedged 1:1 notional with a BTCUSDT short (so it is a carry trade, not a beta bet). SHIP-CANDIDATE if net Sharpe >= 1.0 AND max drawdown <= 20% AND >= 55% weeks positive on BOTH chrono halves; CANDIDATE if net Sharpe >= 0.5 on both halves; else NO.

Definition fixed before running: "trailing-7-day average funding rate" is measured as the cumulative funding over the 7 days ending at the rebalance close (sum of all settlements, so 1h/4h/8h-interval symbols are comparable; ranking by sum is identical to ranking by average daily rate). Most negative = shorts paid longs the most last week.

## Verdicts (mechanical)

| study | verdict | detail |
|---|---|---|
| Momentum L/S, pit30, nocap | **CANDIDATE** | SHIP pairs none; CANDIDATE lookbacks ['28', '56', '91'] |
| Momentum L/S, pit30, cap10 | **CANDIDATE** | SHIP pairs none; CANDIDATE lookbacks ['14', '28', '56', '91', '28s7'] |
| Momentum L/S, pit90, cap10 | **CANDIDATE** | SHIP pairs none; CANDIDATE lookbacks ['28', '56', '91', '28s7'] |
| Momentum L/S, pit30, cap10, carry basket EXCLUDED (k=56,91 only, as pre-specified) | **SHIP-CANDIDATE** | CANDIDATE lookbacks ['56', '91']; SHIP both k: ['56', '91'] |
| Momentum L/S, pit30, cap10, carry EXCLUDED, full ladder (context) | **SHIP-CANDIDATE** | CANDIDATE lookbacks ['14', '28', '56', '91']; SHIP pairs [('56', '91')] |
| Funding carry N=10 hedged | **NO** | H1 Sharpe 0.87 / MDD 30.5% / %+ 48%; H2 Sharpe -2.66 / MDD 74.7% / %+ 26% |

## 1. Point-in-time universe

- Listing age from `instruments-info.launchTime` (0 symbols lacked it → first cached bar used). A symbol is eligible at a rebalance only if listed ≥30d (`pit30`) / ≥90d (`pit90`) before that Monday 00:00 UTC, plus ≥ lookback+2 bars and trailing-7d turnover ≥ $10M.
- Names per leg (decile = floor(eligible/10)):

| universe | k | avg names/leg | min | max | avg eligible | min | max |
|---|---|---|---|---|---|---|---|
| pit30 | 7 | 8.3 | 5 | 13 | 87 | 58 | 135 |
| pit30 | 14 | 8.3 | 5 | 13 | 87 | 58 | 135 |
| pit30 | 28 | 8.3 | 5 | 13 | 87 | 58 | 135 |
| pit30 | 56 | 7.9 | 5 | 12 | 83 | 54 | 127 |
| pit30 | 91 | 7.5 | 4 | 12 | 80 | 49 | 122 |
| pit30 | 28s7 | 8.3 | 5 | 13 | 87 | 58 | 135 |
| pit90 | 7 | 7.5 | 4 | 12 | 80 | 49 | 122 |
| pit90 | 14 | 7.5 | 4 | 12 | 80 | 49 | 122 |
| pit90 | 28 | 7.5 | 4 | 12 | 80 | 49 | 122 |
| pit90 | 56 | 7.5 | 4 | 12 | 80 | 49 | 122 |
| pit90 | 91 | 7.5 | 4 | 12 | 80 | 49 | 122 |
| pit90 | 28s7 | 7.5 | 4 | 12 | 80 | 49 | 122 |

- **Survivorship is NOT fixed.** `instruments-info` lists only symbols trading today; coins delisted inside the window are absent and this endpoint cannot recover them. Direction of the bias: (i) delisted perps are overwhelmingly coins that collapsed → they would have sat in the bottom decile (SHORT leg) on the way down, so their absence UNDERSTATES short-leg profit; (ii) but many also pumped first (and carried extreme negative funding while squeezed) before collapsing → their absence OVERSTATES the long leg and OVERSTATES the funding-carry basket, whose selection is literally 'the most squeezed coins' — the ones most likely to be delisted after the squeeze unwinds. Net: the carry product and the long leg are biased UP; the L/S momentum book is ambiguous but more likely biased up because its P&L here comes from the long leg. 16% of carry-basket names were listed < 90 days at selection.

## 2. Momentum L/S — point-in-time universe, with / without the 10%-of-leg cap

Cap = no name > 10% of its leg (= 5% of equity). With decile legs of < 10 names an equal-weight leg already exceeds 10%/name, so the cap BINDS structurally: there is nothing to redistribute to, the residual stays in cash and the leg is under-invested (reported as `leg invested`). Net = gross − fees/slippage − actual funding.

### pit30, uncapped (avg leg invested 100%)

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | H1 Sharpe | H2 Sharpe | H1 MDD | H2 MDD | ex-funding Sharpe | turnover/wk | names/leg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | -31.4% | 3.8% | 0.38 | 71.1% | 48% | 3.03 | -1.67 | 10.8% | 71.1% | -0.42 | 1.76 | 8.3 |
| k=14 | 62 | -13.0% | 49.5% | 0.91 | 51.0% | 50% | 1.52 | 0.36 | 38.2% | 51.0% | 0.07 | 1.41 | 8.3 |
| k=28 | 62 | 49.7% | 213.0% | 1.96 | 43.3% | 58% | 2.83 | 1.20 | 25.5% | 43.3% | 0.85 | 1.21 | 8.3 |
| k=56 | 62 | 65.8% | 246.0% | 2.32 | 29.8% | 61% | 2.31 | 2.33 | 15.3% | 29.8% | 1.05 | 1.11 | 7.9 |
| k=91 | 62 | 114.9% | 278.8% | 2.25 | 43.1% | 65% | 2.59 | 2.20 | 14.0% | 43.1% | 1.37 | 0.99 | 7.5 |
| k=28s7 | 62 | 70.6% | 166.3% | 1.79 | 25.7% | 61% | 0.39 | 3.22 | 25.7% | 15.7% | 1.05 | 1.38 | 8.3 |

### pit30, 10% cap (avg leg invested 79%)

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | H1 Sharpe | H2 Sharpe | H1 MDD | H2 MDD | ex-funding Sharpe | turnover/wk | names/leg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | -8.9% | 26.5% | 0.71 | 55.4% | 48% | 2.90 | -1.45 | 10.8% | 55.4% | -0.08 | 1.42 | 8.3 |
| k=14 | 62 | 11.5% | 73.2% | 1.24 | 36.2% | 52% | 1.91 | 0.52 | 26.2% | 36.2% | 0.37 | 1.13 | 8.3 |
| k=28 | 62 | 65.5% | 191.6% | 2.22 | 31.1% | 58% | 3.10 | 1.30 | 17.8% | 31.1% | 1.13 | 0.96 | 8.3 |
| k=56 | 62 | 63.5% | 180.6% | 2.45 | 18.2% | 61% | 2.44 | 2.41 | 11.9% | 18.2% | 1.22 | 0.84 | 7.9 |
| k=91 | 62 | 88.3% | 183.3% | 2.44 | 28.1% | 63% | 2.68 | 2.27 | 11.7% | 28.1% | 1.50 | 0.72 | 7.5 |
| k=28s7 | 62 | 63.6% | 124.2% | 1.79 | 22.0% | 61% | 0.55 | 3.31 | 22.0% | 10.3% | 1.13 | 1.10 | 8.3 |

### pit90, 10% cap (avg leg invested 75%)

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | H1 Sharpe | H2 Sharpe | H1 MDD | H2 MDD | ex-funding Sharpe | turnover/wk | names/leg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | -40.0% | -25.6% | -0.53 | 52.2% | 48% | 1.24 | -2.01 | 12.2% | 52.2% | -1.24 | 1.32 | 7.5 |
| k=14 | 62 | 5.0% | 39.8% | 0.98 | 32.3% | 48% | 1.68 | 0.50 | 14.5% | 32.3% | 0.21 | 1.04 | 7.5 |
| k=28 | 62 | 10.2% | 85.5% | 1.62 | 31.3% | 55% | 2.77 | 0.76 | 15.5% | 31.3% | 0.34 | 0.87 | 7.5 |
| k=56 | 62 | 42.3% | 128.0% | 2.16 | 18.0% | 65% | 1.65 | 2.59 | 14.5% | 18.0% | 0.97 | 0.80 | 7.5 |
| k=91 | 62 | 88.3% | 183.3% | 2.44 | 28.1% | 63% | 2.68 | 2.27 | 11.7% | 28.1% | 1.50 | 0.72 | 7.5 |
| k=28s7 | 62 | 59.2% | 131.1% | 2.20 | 16.2% | 60% | 1.33 | 2.90 | 16.2% | 16.0% | 1.21 | 1.00 | 7.5 |

## 3. Funding carry as its own product

Long the N most-negative-trailing-funding names (equal weight, 100% notional), short BTCUSDT 100% notional when hedged. Costs 0.055% + 0.03% per unit turnover (both legs, drift-adjusted); funding = actual settlements inside the holding week on both legs (longs receive negative funding; the BTC short pays when BTC funding is negative, receives when positive). N=10 hedged is the pre-registered product; the rest are robustness only.

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | H1 Sharpe | H2 Sharpe | H1 MDD | H2 MDD | ex-funding Sharpe | turnover/wk | names/leg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| N=5 hedged | 62 | -98.6% | -33.8% | 0.14 | 79.3% | 35% | 1.70 | -2.96 | 29.9% | 78.5% | -3.07 | 1.64 | 5.0 |
| N=5 UNHEDGED | 62 | -99.0% | -50.0% | -0.05 | 82.2% | 40% | 1.06 | -1.92 | 40.9% | 77.2% | -3.07 | 1.46 | 5.0 |
| N=10 hedged | 62 | -96.5% | -53.2% | -0.64 | 78.1% | 37% | 0.87 | -2.66 | 30.5% | 74.7% | -4.14 | 1.53 | 10.0 |
| N=10 UNHEDGED | 62 | -97.4% | -65.3% | -0.83 | 82.3% | 47% | -0.18 | -1.51 | 38.4% | 72.9% | -3.79 | 1.40 | 10.0 |
| N=20 hedged | 62 | -81.7% | -9.2% | 0.10 | 53.9% | 44% | 1.30 | -1.39 | 24.9% | 52.1% | -2.87 | 1.36 | 20.0 |
| N=20 UNHEDGED | 62 | -86.4% | -33.4% | -0.24 | 62.0% | 47% | -0.14 | -0.36 | 36.9% | 47.1% | -2.50 | 1.27 | 20.0 |

### Decomposition, N=10 hedged (cumulative sum of weekly contributions, % of equity)

| period | weeks | alts price P&L | BTC hedge price P&L | funding received on alts | funding on BTC short | fees+slippage | NET |
|---|---|---|---|---|---|---|---|
| full | 62 | -377.1% | +22.4% | +300.5% | +4.3% | -8.0% | -58.0% |
| H1 | 31 | -160.1% | +50.8% | +154.1% | +2.9% | -3.7% | +43.9% |
| H2 | 31 | -217.0% | -28.4% | +146.4% | +1.4% | -4.3% | -101.9% |

Average trailing-7d funding of the selected basket at selection: -10.1% per week (shorts paying longs). Avg eligible names for the carry signal: 86.
Funding actually RECEIVED by the basket the following week: mean 4.85%/wk, median 5.18%/wk, negative (basket paid) in 0% of weeks — i.e. 48% of last week's funding persisted.

## 4. Momentum ex-funding-carry (pit30, 10% cap, that week's N=10 carry basket removed from the eligible set)

| variant | n wks | gross ann | net ann | net Sharpe | max DD | % wks + | H1 Sharpe | H2 Sharpe | H1 MDD | H2 MDD | ex-funding Sharpe | turnover/wk | names/leg |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| k=7 | 62 | 0.0% | 3.2% | 0.30 | 53.9% | 45% | 2.02 | -1.52 | 12.1% | 53.9% | 0.11 | 1.30 | 7.3 |
| k=14 | 62 | 32.0% | 43.0% | 0.95 | 37.8% | 52% | 0.88 | 1.01 | 35.4% | 37.8% | 0.71 | 1.06 | 7.3 |
| k=28 | 62 | 117.3% | 166.2% | 2.22 | 29.4% | 55% | 2.29 | 2.13 | 21.0% | 29.4% | 1.75 | 0.91 | 7.3 |
| k=56  ← pre-specified | 62 | 134.5% | 168.9% | 2.64 | 23.5% | 63% | 2.22 | 3.04 | 13.3% | 23.5% | 2.21 | 0.78 | 7.0 |
| k=91  ← pre-specified | 62 | 110.2% | 146.2% | 2.55 | 23.9% | 68% | 2.61 | 2.45 | 9.4% | 23.9% | 2.05 | 0.67 | 6.7 |
| k=28s7 | 62 | 84.4% | 103.0% | 1.69 | 32.7% | 60% | -0.29 | 4.40 | 32.7% | 7.7% | 1.43 | 1.01 | 7.3 |

| k | with carry names: net ann / Sharpe / H1 / H2 | carry names EXCLUDED: net ann / Sharpe / H1 / H2 | ex-funding Sharpe with → without |
|---|---|---|---|
| 56 | 180.6% / 2.45 / 2.44 / 2.41 | 168.9% / 2.64 / 2.22 / 3.04 | 1.22 → 2.21 |
| 91 | 183.3% / 2.44 / 2.68 / 2.27 | 146.2% / 2.55 / 2.61 / 2.45 | 1.50 → 2.05 |

### Leg attribution, ex-carry k=56 / k=91 (cumulative sum of weekly gross contributions, % of equity)

| k | period | long leg price | short leg price | funding (− = received) | fees+slippage | NET | worst week | max DD |
|---|---|---|---|---|---|---|---|---|
| 56 | full | +67.4% | +44.4% | -20.6% | -4.1% | +128.3% | -10.4% | 23.5% |
| 56 | H1 | +8.7% | +42.2% | -6.6% | -2.4% | +55.1% | -8.3% | 13.3% |
| 56 | H2 | +58.8% | +2.1% | -14.0% | -1.8% | +73.1% | -10.4% | 23.5% |
| 91 | full | +34.0% | +63.6% | -22.5% | -3.6% | +116.5% | -9.9% | 23.9% |
| 91 | H1 | +3.4% | +54.1% | -7.2% | -2.0% | +62.8% | -7.6% | 9.4% |
| 91 | H2 | +30.6% | +9.4% | -15.3% | -1.6% | +53.7% | -9.9% | 23.9% |

**Margin note on the ex-carry SHIP verdict:** the bar is applied mechanically, but the pass rests on full-period max drawdowns of 23.5% (k=56) and 23.9% (k=91) against a 25% cap — a thin margin on a 62-week sample with ~7 names per leg, in a survivorship-biased universe. One additional bad week would flip it. Treat SHIP-CANDIDATE as 'eligible for a pre-registered forward paper test', not as proof.

## Multiple testing

30 portfolio variants were evaluated in this file (momentum: 6 lookbacks × 3 universe/cap settings + 6 ex-carry; carry: 3 basket sizes × hedged/unhedged), each also read ex-funding, on top of the 48 variants in the v1 report. With 62 weekly observations, a zero-edge series shows annualized Sharpe ≥ 1.0 with p ≈ 0.137 and ≥ 0.5 with p ≈ 0.293 per variant; the both-halves requirement squares these roughly. No parameter in either bar was changed after seeing results; the carry bar was written before the carry code ran.

## Data

- 782 Trading LinearPerpetual USDT symbols; 679 with ≥60 closed daily bars; panel 2025-04-12 → 2026-10-03; funding history for 679 symbols (cached under `logs/backtest_cache/xs_funding_*.json`); 62 weekly rebalances 2025-07-20 → 2026-09-20 (Sunday daily bar close = Monday 00:00 UTC).

_Generated by `xs_momentum_v2.py` in 8s. Zero Claude tokens, zero order logic._
