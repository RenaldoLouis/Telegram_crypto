# Performance Summary
_Last updated: 2026-05-04 00:50 UTC_
_Total runs evaluated: 8_

## Overall Stats
- Total setups: 35
- Triggered: 29 (83%)
- Not triggered: 6
- **Win rate: 10.3%** (3W / 26L)  (**↓ -0.4%** from previous eval: 10.7%) ⚠️ REGRESSION
- Avg actual R:R: -0.64
- Avg winning R:R: 1.87
- Avg losing R:R: -0.93

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
| 2026-04-28 | 2 | 0 | 2 | 0% | 11.1% |
| 2026-04-29 | 2 | 0 | 2 | 0% | 10.3% |

**⚠️ Win rate is NOT improving across recent runs. Review what changed and whether the feedback loop is being followed.**

## By Setup Type
| Setup Type | Trades | Wins | Losses | Win Rate | Avg R:R |
|---|---|---|---|---|---|
| trend_pullback | 26 | 3 | 23 | 12% | -0.61 |
| failed_breakout | 2 | 0 | 2 | 0% | -1.00 |
| range_breakout | 1 | 0 | 1 | 0% | -0.50 |

## By Confidence Level
| Confidence | Trades | Wins | Losses | Win Rate |
|---|---|---|---|---|
| high | 9 | 2 | 7 | 22% |
| medium | 15 | 0 | 15 | 0% |
| low | 5 | 1 | 4 | 20% |

## By Rank Position
| Rank | Trades | Win Rate |
|---|---|---|
| #1 | 6 | 0% |
| #2 | 6 | 17% |
| #3 | 6 | 17% |
| #4 | 6 | 17% |
| #5 | 5 | 0% |

## By Model
| Model | Trades | Wins | Losses | Win Rate | Avg R:R |
|---|---|---|---|---|---|
| claude-haiku-4-5 | 8 | 1 | 7 | 12% | -0.25 |
| claude-sonnet-4-6 | 17 | 1 | 16 | 6% | -0.82 |
| unknown | 4 | 1 | 3 | 25% | -0.61 |

## Your Predictions vs Reality (LEARN FROM EACH ONE)
Each row is a setup YOU recommended. Study the gap between predicted and actual R:R.

| Date | Symbol | Dir | TF | Conf | TF-Conf | Pred R:R | Actual R:R | Exit | MFE |
|---|---|---|---|---|---|---|---|---|---|
| 2026-04-29 | XRPUSDT | L | intra | hig | 3/4 | 2.5 | -1.0 | stop_loss | 0.25R |
| 2026-04-29 | BTCUSDT | L | intra | hig | 3/4 | 2.7 | -1.0 | stop_loss | 0.23R |
| 2026-04-28 | 1000PEPE | L | intra | med | 3/4 | 2.2 | -1.0 | stop_loss | 0.77R |
| 2026-04-28 | XCNUSDT | S | scalp | low | 2/4 | 2.1 | -1.0 | stop_loss | 1.33R |
| 2026-04-26 | SOLUSDT | L | swing | med | 3/4 | 2.2 | -1.0 | stop_loss | 0.0R |
| 2026-04-26 | ALGOUSDT | L | intra | low | 3/4 | 2.1 | 1.04 | target_1 | 1.27R |
| 2026-04-26 | XRPUSDT | L | intra | low | 2/4 | 2.1 | -0.67 | expired | 0.48R |
| 2026-04-25 | HYPERUSD | S | intra | med | 4/4 | 2.2 | -1.0 | stop_loss | 0.34R |
| 2026-04-25 | OPUSDT | L | intra | med | 3/4 | 2.2 | -1.0 | stop_loss | 0.13R |
| 2026-04-25 | GALAUSDT | L | intra | med | 3/4 | 2.0 | -1.0 | stop_loss | 0.28R |
| 2026-04-25 | ADAUSDT | L | intra | med | 3/4 | 2.4 | -1.0 | stop_loss | 1.0R |
| 2026-04-25 | SOLUSDT | L | swing | low | 3/4 | 2.0 | -1.0 | stop_loss | 0.0R |
| 2026-04-25 | BTCUSDT | L | swing | hig | 4/4 | 1.6 | -1.0 | stop_loss | 0.0R |
| 2026-04-25 | SOLUSDT | L | swing | med | 3/4 | 1.3 | -1.0 | stop_loss | 0.0R |
| 2026-04-25 | ENJUSDT | L | intra | hig | 4/4 | 2.0 | -1.0 | stop_loss | 0.16R |
| 2026-04-25 | ARBUSDT | L | intra | med | 4/4 | 1.4 | -1.0 | stop_loss | 0.08R |
| 2026-04-25 | DOGEUSDT | L | intra | med | 4/4 | 1.5 | -0.5 | expired | 1.62R |
| 2026-04-23 | SPKUSDT | L | swing | hig | 4/4 | 1.44 | -1.0 | stop_loss | 0.0R |
| 2026-04-23 | BIOUSDT | L | swing | hig | 4/4 | 2.75 | 4.5 | target_2 | 4.71R |
| 2026-04-23 | ARBUSDT | L | intra | med | 4/4 | 2.27 | -1.0 | stop_loss | 0.05R |

**Prediction gap: avg predicted R:R = 2.1, avg actual = -0.64 (gap of 2.7R)**
**Direction accuracy: 8/29 (28%) reached 0.5R+ favorable. Avg MFE: 0.55R**
**DIAGNOSIS: Direction calls are wrong most of the time. Be far more selective — only trade when multi-TF confluence is 4/4.**

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
- CRITICAL: Win rate is 10% — nearly all setups lose. REDUCE quantity: only recommend setups with 4/4 TF confluence or high confidence. 1-2 high-quality setups is better than 5 mediocre ones.
- TARGET ISSUE: Only 2/29 setups hit T1. Targets are set too far. Use closer, more realistic T1 levels.
- STOP LOSS ISSUE: 22/29 setups hit stop loss. Stops may be too tight or entries too imprecise. Widen SL or wait for better entries.
- R:R ISSUE: Average actual R:R is -0.64. Losses are large relative to wins. Tighten targets and/or widen stops.
- Best setup type: **trend_pullback** (3/26 wins)
- MEDIUM CONFIDENCE FAILING: 0/15 wins (0%). Stop recommending medium-confidence setups unless R:R >= 3:1.
- RANK #4-5 FAILING: 1/11 wins (9%). These are filler setups. Recommend fewer, better setups instead of padding to 5.
- Best performing model: **unknown** (25% win rate, -0.61 avg R:R)
- claude-haiku-4-5: 12% win rate, -0.25 avg R:R over 8 trades
- claude-sonnet-4-6: 6% win rate, -0.82 avg R:R over 17 trades
