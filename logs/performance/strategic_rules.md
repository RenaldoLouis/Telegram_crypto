# Strategic Rules (derived from 213 evaluated trades — solid sample)
_Last updated: 2026-07-07 15:34 UTC_

1. **MODERATE SELECTIVITY**: Win rate is 29%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 2/9 (22% WR) but 'Medium' is 48/166 (29% WR). ACTION: Only label a setup 'high confidence' if it has 4/4 TF confluence + volume confirmed + clean structure. If unsure, label 'medium' — it actually performs better.
3. **'failed_breakout' STRUGGLING** (6 trades): 0% WR, -1.00 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
4. **'funding_squeeze' STRUGGLING** (7 trades): 14% WR, -0.55 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **BEST TYPE: 'trend_pullback'**: 31% WR over 181 trades. ACTION: Prioritize this setup type. At least 2 of your top setups should be this type if available.
6. **TARGETS TOO FAR**: Predicted avg 1.8R but actual is -0.17R (gap: 2.0R). Average MFE is 1.0R, so set T1 at max 0.8R from entry. Backtest: T1 at 0.75R would hit 52% of trades, T1 at 1.0R would hit 41% (vs current T1 hit rate of 66/213 = 31%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
7. **DIRECTION RIGHT, EXECUTION WRONG**: 62% reach 0.5R+ favorable (avg MFE: 1.03R) but win rate is 29%. ACTION: Widen stops by 0.5× ATR and bring T1 closer. The direction is correct — fix the execution.
8. **LOSING SYMBOLS**: ONDOUSDT (0/3), ZECUSDT (0/3), WLDUSDT (0/3), HYPEUSDT (0/3). ACTION: Require 4/4 TF confluence + volume confirmed for these symbols. Do not include as filler.
9. **IMPROVING**: 2026-06 was 20% → 2026-07 is 40%. Current approach is working — maintain it.
10. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 36% (vs raw 29%), avg blended R:R -0.24. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
11. **BEST MODEL**: claude-sonnet-4-6 (30% WR, -0.16 avg R:R). Consider using this model for production runs.
12. **RISK_ON REGIME LOSING**: 0/7 (0% WR, -0.86 avg R:R). ACTION: During risk_on, reduce to max 1-2 setups and require 4/4 TF + volume.
13. **INEFFECTIVE RULES**: tight_t1 (1/9=11%). ACTION: Reconsider setups based on these rules — they correlate with losses.
