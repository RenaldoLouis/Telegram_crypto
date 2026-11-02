# Engine parity — 2026-11-02 06:13 UTC after

Live rows: 364 v2 evaluated with levels · rules failed_breakout_short, liquidity_sweep_long, observation, range_reversion_long, range_reversion_short, rsi_bounce_long, trend_pullback_short · engine entry model limit_open, scan lag 2 min.

- Matched 328/364 · agree within 0.05R: **66%**
- Mean net: live -0.064R · engine -0.039R · **gap (engine − live) +0.025R/trade** (median +0.000)
- Level gap, median in live-risk units: stop 0.000 · T1 0.072 · T2 0.095

| rule | tf | n | live | engine | gap | agree |
|---|---|---:|---:|---:|---:|---:|
| failed_breakout_short | 4h | 78 | +0.275 | +0.291 | +0.016 | 54% |
| liquidity_sweep_long | 1h | 89 | -0.336 | -0.288 | +0.048 | 57% |
| range_reversion_long | 4h | 7 | -0.944 | -0.952 | -0.008 | 86% |
| range_reversion_short | 4h | 5 | +0.318 | +0.489 | +0.171 | 0% |
| rsi_bounce_long | 4h | 59 | -0.127 | -0.088 | +0.039 | 83% |
| trend_pullback_short | 4h | 90 | -0.001 | -0.005 | -0.004 | 76% |

Unmatched: engine has no trade on this bar 19, engine: limit not filled 4, no data 13
