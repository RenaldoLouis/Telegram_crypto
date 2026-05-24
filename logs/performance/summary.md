# Performance Summary
_Last updated: 2026-05-24 09:37 UTC_
_Total runs evaluated: 36_

## Overall Stats
- Total setups: 139
- Triggered: 129 (93%)
- Not triggered: 10
- **Win rate: 35.7%** (46W / 83L)  (**↓ -4.0%** from previous eval: 39.7%) ⚠️ REGRESSION
- Avg actual R:R: -0.09
- Avg winning R:R: 1.36
- Avg losing R:R: -0.90

### Partial Profit Model (50% at T1 + BE stop)
- **Blended win rate: 39.3%** (11W / 17L)
- Avg blended R:R: -0.20
- BE stops (T1 hit then reversed to entry): 3

## Win Rate Trend (per eval run)
This tracks whether recommendations are IMPROVING over time. If not trending up, something needs to change.

| Run Date | Setups | W | L | Run Win Rate | Cumulative Win Rate |
|---|---|---|---|---|---|
| 2026-04-22 | 4 | 1 | 3 | 25% | 25.0% |
| 2026-04-22 | 5 | 0 | 5 | 0% | 11.1% |
| 2026-04-23 | 3 | 1 | 2 | 33% | 16.7% |
| 2026-04-25 | 5 | 0 | 5 | 0% | 11.8% |
| 2026-04-25 | 5 | 0 | 5 | 0% | 9.1% |
| 2026-04-26 | 3 | 1 | 2 | 33% | 12.0% |
| 2026-04-28 | 4 | 2 | 2 | 50% | 17.2% |
| 2026-04-29 | 2 | 0 | 2 | 0% | 16.1% |
| 2026-05-03 | 1 | 0 | 1 | 0% | 15.6% |
| 2026-05-03 | 3 | 3 | 0 | 100% | 22.9% |
| 2026-05-04 | 2 | 2 | 0 | 100% | 27.0% |
| 2026-05-05 | 3 | 1 | 2 | 33% | 27.5% |
| 2026-05-06 | 3 | 0 | 3 | 0% | 25.6% |
| 2026-05-06 | 4 | 2 | 2 | 50% | 27.7% |
| 2026-05-07 | 4 | 3 | 1 | 75% | 31.4% |
| 2026-05-07 | 5 | 4 | 1 | 80% | 35.7% |
| 2026-05-09 | 4 | 4 | 0 | 100% | 40.0% |
| 2026-05-10 | 5 | 4 | 1 | 80% | 43.1% |
| 2026-05-11 | 5 | 0 | 5 | 0% | 40.0% |
| 2026-05-11 | 5 | 2 | 3 | 40% | 40.0% |
| 2026-05-12 | 5 | 1 | 4 | 20% | 38.8% |
| 2026-05-13 | 5 | 3 | 2 | 60% | 40.0% |
| 2026-05-13 | 5 | 2 | 3 | 40% | 40.0% |
| 2026-05-14 | 4 | 1 | 3 | 25% | 39.4% |
| 2026-05-14 | 2 | 1 | 1 | 50% | 39.6% |
| 2026-05-16 | 2 | 0 | 2 | 0% | 38.8% |
| 2026-05-17 | 3 | 0 | 3 | 0% | 37.6% |
| 2026-05-18 | 3 | 0 | 3 | 0% | 36.5% |
| 2026-05-19 | 2 | 1 | 1 | 50% | 36.8% |
| 2026-05-19 | 2 | 0 | 2 | 0% | 36.1% |
| 2026-05-20 | 5 | 5 | 0 | 100% | 38.9% |
| 2026-05-20 | 3 | 2 | 1 | 67% | 39.7% |
| 2026-05-21 | 5 | 0 | 5 | 0% | 38.0% |
| 2026-05-22 | 3 | 0 | 3 | 0% | 37.1% |
| 2026-05-22 | 5 | 0 | 5 | 0% | 35.7% |

**⚠️ ALERT: Last 3 runs have 0% win rate. The current approach is NOT working. Major changes needed: tighter setup criteria, wider stops, closer targets, or fewer setups per run.**

## By Setup Type
| Setup Type | Trades | Wins | Losses | Win Rate | Avg R:R |
|---|---|---|---|---|---|
| trend_pullback | 120 | 44 | 76 | 37% | -0.08 |
| failed_breakout | 3 | 0 | 3 | 0% | -1.00 |
| post_liquidation | 3 | 0 | 3 | 0% | -1.00 |
| range_breakout | 2 | 1 | 1 | 50% | 0.48 |
| liquidity_sweep | 1 | 1 | 0 | 100% | 2.82 |

## By Confidence Level
| Confidence | Trades | Wins | Losses | Win Rate |
|---|---|---|---|---|
| high | 9 | 2 | 7 | 22% |
| medium | 100 | 38 | 62 | 38% |
| low | 20 | 6 | 14 | 30% |

## By Rank Position
| Rank | Trades | Win Rate |
|---|---|---|
| #1 | 33 | 27% |
| #2 | 31 | 45% |
| #3 | 27 | 37% |
| #4 | 22 | 36% |
| #5 | 16 | 31% |

## By Model
| Model | Trades | Wins | Losses | Win Rate | Avg R:R |
|---|---|---|---|---|---|
| claude-haiku-4-5 | 8 | 1 | 7 | 12% | -0.25 |
| claude-sonnet-4-6 | 117 | 44 | 73 | 38% | -0.07 |
| unknown | 4 | 1 | 3 | 25% | -0.61 |

## Your Predictions vs Reality (LEARN FROM EACH ONE)
Each row is a setup YOU recommended. Study the gap between predicted and actual R:R.

| Date | Symbol | Dir | TF | Conf | TF-Conf | Pred R:R | Actual R:R | Exit | MFE |
|---|---|---|---|---|---|---|---|---|---|
| 2026-05-22 | ADAUSDT | L | intra | med | 3/4 | 2.0 | -1.0 | stop_loss | 0.83R |
| 2026-05-22 | DOGEUSDT | L | intra | med | 3/4 | 1.7 | -1.0 | stop_loss | 0.45R |
| 2026-05-22 | SOLUSDT | L | intra | med | 3/4 | 1.8 | -1.0 | stop_loss | 0.45R |
| 2026-05-22 | ENAUSDT | L | intra | med | 3/4 | 2.1 | -1.0 | stop_loss | 1.29R |
| 2026-05-22 | PENGUUSD | L | intra | med | 4/4 | 1.8 | -1.0 | stop_loss | 0.34R |
| 2026-05-22 | DOGEUSDT | L | intra | med | 3/4 | 1.8 | -1.0 | stop_loss | 0.45R |
| 2026-05-22 | XRPUSDT | L | intra | med | 3/4 | 1.9 | -1.0 | stop_loss | 0.16R |
| 2026-05-22 | ENAUSDT | L | intra | med | 3/4 | 1.5 | -1.0 | stop_loss | 0.99R |
| 2026-05-21 | SOLUSDT | L | intra | med | 3/4 | 1.9 | 0.0 | be_stop | 1.52R |
| 2026-05-21 | DOGEUSDT | L | intra | med | 3/4 | 1.8 | -1.0 | stop_loss | 1.36R |
| 2026-05-21 | XRPUSDT | L | intra | med | 3/4 | 1.7 | -1.0 | stop_loss | 0.54R |
| 2026-05-21 | SUIUSDT | L | intra | med | 3/4 | 1.9 | 0.0 | be_stop | 1.77R |
| 2026-05-21 | ADAUSDT | L | intra | low | 2/4 | 1.7 | 0.0 | be_stop | 0.96R |
| 2026-05-20 | XRPUSDT | L | intra | med | 3/4 | 1.7 | -0.34 | expired | 0.61R |
| 2026-05-20 | DOGEUSDT | L | intra | med | 3/4 | 1.7 | 0.47 | expired | 0.87R |
| 2026-05-20 | SOLUSDT | L | intra | med | 2/4 | 1.6 | 0.95 | target_1 | 1.53R |
| 2026-05-20 | XRPUSDT | L | intra | med | 3/4 | 1.6 | 1.68 | target_1 | 1.72R |
| 2026-05-20 | ADAUSDT | L | intra | med | 3/4 | 1.7 | 0.47 | expired | 1.09R |
| 2026-05-20 | PENGUUSD | L | intra | med | 3/4 | 2.5 | 2.66 | target_2 | 2.75R |
| 2026-05-20 | SOLUSDT | L | intra | med | 3/4 | 1.5 | 1.92 | target_2 | 2.04R |

**Prediction gap: avg predicted R:R = 2.0, avg actual = -0.09 (gap of 2.1R)**
**Direction accuracy: 83/129 (64%) reached 0.5R+ favorable. Avg MFE: 1.11R**

## Trader's Actual Trades (Manual Log)
- Closed trades: 1 (0W / 1L)
- Open trades: 1
- Win rate (closed): 0%

### Recurring Failure Patterns
- **target_too_far**: 1 occurrence(s)
- **sl_too_tight**: 1 occurrence(s)

### Trade-by-Trade Analysis (USE THESE TO IMPROVE FUTURE SETUPS)

**SPKUSDT** (2026-04-23) — LOSS
- Trader: entry 0.0501, SL 0.04655, exit 0.04655, reason: stop_loss
- Claude recommended: trend_pullback (swing), rank #1, confidence high, model claude-haiku-4-5
  Entry zone 0.051–0.052, SL 0.047, T1 0.058, T2 0.065, predicted R:R 1.44
- **Lesson**: Should have TP'd at 0.05255 — the screening target was too far. Next time consider taking partial profit at a closer level when the move stalls.
- **Failure category**: target_too_far

**ENJUSDT** (2026-04-25) — OPEN
- Trader: entry 0.0606, SL 0.0595, exit None, reason: None
- Claude recommended: trend_pullback (intraday), rank #3, confidence high, model claude-haiku-4-5
  Entry zone 0.0605–0.0608, SL 0.0595, T1 0.0625, T2 0.065, predicted R:R 2.0
- **Lesson**: SL too tight — only 1.8% from entry (0.0606 to 0.0595). Risk of getting stopped out by normal volatility before the move plays out.
- **Failure category**: sl_too_tight

## Key Insights for Future Briefs
- WARNING: Win rate is 36% (below 40%). Apply stricter entry criteria — prefer fewer, higher-conviction setups.
- Best setup type: **trend_pullback** (44/120 wins)
- Worst setup type: **failed_breakout** (0/3 wins, 0%) — deprioritize unless 4/4 TF confluence
- CALIBRATION ISSUE: 'High' confidence setups don't outperform 'Medium'. Recalibrate confidence scoring.
- Best performing model: **claude-sonnet-4-6** (38% win rate, -0.07 avg R:R)
- claude-sonnet-4-6: 38% win rate, -0.07 avg R:R over 117 trades
- claude-haiku-4-5: 12% win rate, -0.25 avg R:R over 8 trades
