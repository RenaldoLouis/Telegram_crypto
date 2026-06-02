# Strategic Rules (derived from 156 evaluated trades — solid sample)
_Last updated: 2026-06-01 09:12 UTC_

1. **MODERATE SELECTIVITY**: Win rate is 31%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 2/9 (22% WR) but 'Medium' is 39/122 (32% WR). ACTION: Only label a setup 'high confidence' if it has 4/4 TF confluence + volume confirmed + clean structure. If unsure, label 'medium' — it actually performs better.
3. **SHORT NEEDS DATA**: 0/6 short trades won, but sample is too small (6 trades, need 15+). ACTION: Include short setups when the market regime supports it and structure is clear. Do NOT avoid short based on this small sample.
4. **DIRECTIONAL BLIND SPOT**: Only 6 short trades vs 150 long trades in history. ACTION: When the market regime is RISK_OFF, actively consider short setups to build data. Do not default to longs in a declining market.
5. **'failed_breakout' STRUGGLING** (6 trades): 0% WR, -1.00 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
6. **BEST TYPE: 'trend_pullback'**: 33% WR over 141 trades. ACTION: Prioritize this setup type. At least 2 of your top setups should be this type if available.
7. **RANK #1 UNDERPERFORMS #2**: Rank #1 is 10/41 (24% WR) but Rank #2 is 14/39 (36% WR). ACTION: Your top-ranked setup may be the most 'obvious' one, not the best one. Re-evaluate ranking — prioritize setup quality and structural clarity over headline appeal.
8. **TARGETS TOO FAR**: Predicted avg 2.0R but actual is -0.18R (gap: 2.2R). Average MFE is 1.0R, so set T1 at max 0.8R from entry. Backtest: T1 at 0.75R would hit 54% of trades, T1 at 1.0R would hit 42% (vs current T1 hit rate of 46/156 = 29%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
9. **T1 HIT RATE LOW**: Only 46/156 (29%) setups hit T1. ACTION: T1 must be at the nearest real structural level (prior S/R, EMA cluster, order block). Not a projected move. If nearest structure gives R:R < 1.5:1, skip the setup.
10. **IMPROVING**: 2026-04 was 16% → 2026-05 is 34%. Current approach is working — maintain it.
11. **BEST MODEL**: claude-sonnet-4-6 (32% WR, -0.17 avg R:R). Consider using this model for production runs.
