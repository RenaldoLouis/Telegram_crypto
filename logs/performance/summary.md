# Performance Summary
_Last updated: 2026-04-28 02:05 UTC_
_Total runs evaluated: 5_

## Overall Stats
- Total setups: 14
- Triggered: 13 (93%)
- Not triggered: 1
- **Win rate: 7.7%** (1W / 12L)
- Avg actual R:R: -0.79
- Avg winning R:R: 0.08
- Avg losing R:R: -0.87

## By Setup Type
| Setup Type | Trades | Wins | Losses | Win Rate | Avg R:R |
|---|---|---|---|---|---|
| trend_pullback | 11 | 1 | 10 | 9% | -0.80 |
| range_breakout | 1 | 0 | 1 | 0% | -0.50 |
| failed_breakout | 1 | 0 | 1 | 0% | -1.00 |

## By Confidence Level
| Confidence | Trades | Wins | Losses | Win Rate |
|---|---|---|---|---|
| high | 2 | 1 | 1 | 50% |
| medium | 10 | 0 | 10 | 0% |
| low | 1 | 0 | 1 | 0% |

## By Rank Position
| Rank | Trades | Win Rate |
|---|---|---|
| #1 | 1 | 0% |
| #2 | 1 | 0% |
| #3 | 4 | 25% |
| #4 | 4 | 0% |
| #5 | 3 | 0% |

## By Model
| Model | Trades | Wins | Losses | Win Rate | Avg R:R |
|---|---|---|---|---|---|
| claude-haiku-4-5 | 4 | 0 | 4 | 0% | -0.88 |
| claude-sonnet-4-6 | 7 | 0 | 7 | 0% | -0.91 |
| unknown | 2 | 1 | 1 | 50% | -0.23 |

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
- WARNING: Overall win rate below 40%. Consider stricter entry criteria.
- Best setup type: **trend_pullback** (1/11 wins)
- claude-sonnet-4-6: 0% win rate, -0.91 avg R:R over 7 trades
