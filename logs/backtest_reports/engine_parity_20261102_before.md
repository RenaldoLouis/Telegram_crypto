# Engine parity — 2026-11-02 06:10 UTC before

Live rows: 364 v2 evaluated with levels · rules failed_breakout_short, liquidity_sweep_long, observation, range_reversion_long, range_reversion_short, rsi_bounce_long, trend_pullback_short · engine entry model limit_open, scan lag 0 min.

- Matched 338/364 · agree within 0.05R: **51%**
- Mean net: live -0.051R · engine +0.026R · **gap (engine − live) +0.077R/trade** (median +0.002)
- Level gap, median in live-risk units: stop 0.000 · T1 0.113 · T2 0.096

| rule | tf | n | live | engine | gap | agree |
|---|---|---:|---:|---:|---:|---:|
| failed_breakout_short | 4h | 78 | +0.276 | +0.370 | +0.094 | 37% |
| liquidity_sweep_long | 1h | 95 | -0.289 | -0.133 | +0.156 | 45% |
| range_reversion_long | 4h | 7 | -0.944 | -0.770 | +0.174 | 71% |
| range_reversion_short | 4h | 6 | +0.374 | +0.775 | +0.401 | 33% |
| rsi_bounce_long | 4h | 57 | -0.128 | -0.105 | +0.023 | 60% |
| trend_pullback_short | 4h | 95 | +0.005 | -0.006 | -0.011 | 62% |

Unmatched: engine has no trade on this bar 15, engine: limit not filled 11
