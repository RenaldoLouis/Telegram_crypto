# Performance Summary
_Last updated: 2026-06-01 09:12 UTC_
_Total runs evaluated: 45_

## Overall Stats
- Total setups: 167
- Triggered: 156 (93%)
- Not triggered: 11
- **Win rate: 30.8%** (48W / 108L)  (**↓ -1.0%** from previous eval: 31.8%) ⚠️ REGRESSION
- Avg actual R:R: -0.18
- Avg winning R:R: 1.38
- Avg losing R:R: -0.88

### Partial Profit Model (50% at T1 + BE stop)
- **Blended win rate: 30.9%** (17W / 38L)
- Avg blended R:R: -0.37
- BE stops (T1 hit then reversed to entry): 7

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
| 2026-05-23 | 2 | 0 | 2 | 0% | 35.1% |
| 2026-05-24 | 5 | 0 | 5 | 0% | 33.8% |
| 2026-05-25 | 5 | 1 | 4 | 20% | 33.3% |
| 2026-05-25 | 4 | 0 | 4 | 0% | 32.4% |
| 2026-05-26 | 3 | 0 | 3 | 0% | 31.8% |
| 2026-05-28 | 2 | 1 | 1 | 50% | 32.0% |
| 2026-05-28 | 1 | 0 | 1 | 0% | 31.8% |
| 2026-05-28 | 2 | 0 | 2 | 0% | 31.4% |
| 2026-05-30 | 3 | 0 | 3 | 0% | 30.8% |

**⚠️ ALERT: Last 3 runs have 0% win rate. The current approach is NOT working. Major changes needed: tighter setup criteria, wider stops, closer targets, or fewer setups per run.**

## By Setup Type
| Setup Type | Trades | Wins | Losses | Win Rate | Avg R:R |
|---|---|---|---|---|---|
| trend_pullback | 141 | 46 | 95 | 33% | -0.15 |
| failed_breakout | 6 | 0 | 6 | 0% | -1.00 |
| post_liquidation | 3 | 0 | 3 | 0% | -1.00 |
| range_breakout | 2 | 1 | 1 | 50% | 0.48 |
| liquidity_sweep | 2 | 1 | 1 | 50% | 0.91 |
| funding_squeeze | 1 | 0 | 1 | 0% | -1.00 |
| other | 1 | 0 | 1 | 0% | -0.44 |

## By Confidence Level
| Confidence | Trades | Wins | Losses | Win Rate |
|---|---|---|---|---|
| high | 9 | 2 | 7 | 22% |
| medium | 122 | 39 | 83 | 32% |
| low | 25 | 7 | 18 | 28% |

## By Rank Position
| Rank | Trades | Win Rate |
|---|---|---|
| #1 | 41 | 24% |
| #2 | 39 | 36% |
| #3 | 32 | 31% |
| #4 | 25 | 32% |
| #5 | 19 | 32% |

## By Model
| Model | Trades | Wins | Losses | Win Rate | Avg R:R |
|---|---|---|---|---|---|
| claude-haiku-4-5 | 8 | 1 | 7 | 12% | -0.25 |
| claude-sonnet-4-6 | 144 | 46 | 98 | 32% | -0.17 |
| unknown | 4 | 1 | 3 | 25% | -0.61 |

## Your Predictions vs Reality (LEARN FROM EACH ONE)
Each row is a setup YOU recommended. Study the gap between predicted and actual R:R.

| Date | Symbol | Dir | TF | Conf | TF-Conf | Pred R:R | Actual R:R | Exit | MFE |
|---|---|---|---|---|---|---|---|---|---|
| 2026-05-30 | HBARUSDT | L | intra | med | 3/4 | 1.5 | -1.0 | stop_loss | 0.73R |
| 2026-05-30 | XRPUSDT | L | intra | low | 2/4 | 1.5 | -0.44 | expired | 0.45R |
| 2026-05-30 | INJUSDT | L | intra | med | 4/4 | 1.5 | 0.0 | be_stop | 1.43R |
| 2026-05-28 | XLMUSDT | S | intra | med | 3/4 | 1.5 | -1.0 | stop_loss | 0.46R |
| 2026-05-28 | BTCUSDT | S | intra | med | 4/4 | 1.5 | -1.0 | stop_loss | 0.67R |
| 2026-05-28 | XLMUSDT | S | intra | low | 2/4 | 1.5 | -1.0 | stop_loss | 0.33R |
| 2026-05-28 | XLMUSDT | L | intra | med | 3/4 | 1.5 | 1.9 | target_2 | 2.23R |
| 2026-05-28 | SEIUSDT | L | intra | med | 3/4 | 1.5 | -1.0 | stop_loss | 0.91R |
| 2026-05-26 | TRXUSDT | L | intra | med | 4/4 | 1.7 | -0.82 | expired | 1.13R |
| 2026-05-26 | ERAUSDT | L | intra | med | 3/4 | 1.9 | -1.0 | stop_loss | 0.39R |
| 2026-05-26 | XRPUSDT | L | intra | low | 2/4 | 1.5 | -1.0 | stop_loss | 1.32R |
| 2026-05-25 | XRPUSDT | L | intra | med | 3/4 | 1.7 | -1.0 | stop_loss | 0.2R |
| 2026-05-25 | SUIUSDT | L | intra | med | 3/4 | 1.7 | -1.0 | stop_loss | 0.2R |
| 2026-05-25 | ZECUSDT | L | intra | med | 4/4 | 1.7 | -1.0 | stop_loss | 0.21R |
| 2026-05-25 | DOGEUSDT | L | intra | low | 3/4 | 1.5 | -0.35 | expired | 0.17R |
| 2026-05-25 | ZECUSDT | L | intra | med | 3/4 | 1.6 | 0.0 | be_stop | 1.38R |
| 2026-05-25 | FIDAUSDT | L | intra | med | 4/4 | 1.6 | -1.0 | stop_loss | 0.42R |
| 2026-05-25 | ONDOUSDT | L | intra | med | 3/4 | 1.55 | -1.0 | stop_loss | 0.45R |
| 2026-05-25 | BTCUSDT | L | intra | med | 3/4 | 2.0 | -1.0 | stop_loss | 1.05R |
| 2026-05-25 | NEARUSDT | L | intra | low | 3/4 | 1.56 | 1.51 | target_2 | 1.67R |

**Prediction gap: avg predicted R:R = 2.0, avg actual = -0.18 (gap of 2.2R)**
**Direction accuracy: 97/156 (62%) reached 0.5R+ favorable. Avg MFE: 1.04R**

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
- WARNING: Win rate is 31% (below 40%). Apply stricter entry criteria — prefer fewer, higher-conviction setups.
- TARGET ISSUE: Only 46/156 setups hit T1. Targets are set too far. Use closer, more realistic T1 levels.
- Best setup type: **trend_pullback** (46/141 wins)
- Worst setup type: **failed_breakout** (0/6 wins, 0%) — deprioritize unless 4/4 TF confluence
- CALIBRATION ISSUE: 'High' confidence setups don't outperform 'Medium'. Recalibrate confidence scoring.
- Best performing model: **claude-sonnet-4-6** (32% win rate, -0.17 avg R:R)
- claude-sonnet-4-6: 32% win rate, -0.17 avg R:R over 144 trades
- claude-haiku-4-5: 12% win rate, -0.25 avg R:R over 8 trades
