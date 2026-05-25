# Strategic Rules (derived from 129 evaluated trades — solid sample)
_Last updated: 2026-05-25 04:36 UTC_

1. **MODERATE SELECTIVITY**: Win rate is 36%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 2/9 (22% WR) but 'Medium' is 38/100 (38% WR). ACTION: Only label a setup 'high confidence' if it has 4/4 TF confluence + volume confirmed + clean structure. If unsure, label 'medium' — it actually performs better.
3. **SHORT NEEDS DATA**: 0/3 short trades won, but sample is too small (3 trades, need 15+). ACTION: Include short setups when the market regime supports it and structure is clear. Do NOT avoid short based on this small sample.
4. **DIRECTIONAL BLIND SPOT**: Only 3 short trades vs 126 long trades in history. ACTION: When the market regime is RISK_OFF, actively consider short setups to build data. Do not default to longs in a declining market.
5. **BEST TYPE: 'trend_pullback'**: 37% WR over 120 trades. ACTION: Prioritize this setup type. At least 2 of your top setups should be this type if available.
6. **RANK #1 UNDERPERFORMS #2**: Rank #1 is 9/33 (27% WR) but Rank #2 is 14/31 (45% WR). ACTION: Your top-ranked setup may be the most 'obvious' one, not the best one. Re-evaluate ranking — prioritize setup quality and structural clarity over headline appeal.
7. **TARGETS TOO FAR**: Predicted avg 2.0R but actual is -0.09R (gap: 2.1R). Average MFE is 1.1R, so set T1 at max 0.8R from entry. Backtest: T1 at 0.75R would hit 63% of trades, T1 at 1.0R would hit 47% (vs current T1 hit rate of 40/129 = 31%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
8. **IMPROVING**: 2026-04 was 16% → 2026-05 is 42%. Current approach is working — maintain it.
9. **BEST MODEL**: claude-sonnet-4-6 (38% WR, -0.07 avg R:R). Consider using this model for production runs.
