# Strategic Rules (derived from 185 evaluated trades — solid sample)
_Last updated: 2026-06-27 08:29 UTC_

1. **MODERATE SELECTIVITY**: Win rate is 30%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 2/9 (22% WR) but 'Medium' is 44/146 (30% WR). ACTION: Only label a setup 'high confidence' if it has 4/4 TF confluence + volume confirmed + clean structure. If unsure, label 'medium' — it actually performs better.
3. **'failed_breakout' STRUGGLING** (6 trades): 0% WR, -1.00 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
4. **BEST TYPE: 'trend_pullback'**: 31% WR over 163 trades. ACTION: Prioritize this setup type. At least 2 of your top setups should be this type if available.
5. **RANK #1 UNDERPERFORMS #2**: Rank #1 is 13/57 (23% WR) but Rank #2 is 17/50 (34% WR). ACTION: Your top-ranked setup may be the most 'obvious' one, not the best one. Re-evaluate ranking — prioritize setup quality and structural clarity over headline appeal.
6. **TARGETS TOO FAR**: Predicted avg 1.9R but actual is -0.15R (gap: 2.0R). Average MFE is 1.1R, so set T1 at max 0.8R from entry. Backtest: T1 at 0.75R would hit 56% of trades, T1 at 1.0R would hit 44% (vs current T1 hit rate of 60/185 = 32%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
7. **DIRECTION RIGHT, EXECUTION WRONG**: 63% reach 0.5R+ favorable (avg MFE: 1.07R) but win rate is 30%. ACTION: Widen stops by 0.5× ATR and bring T1 closer. The direction is correct — fix the execution.
8. **LOSING SYMBOLS**: ONDOUSDT (0/3), ZECUSDT (0/3), WLDUSDT (0/3). ACTION: Require 4/4 TF confluence + volume confirmed for these symbols. Do not include as filler.
9. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 37% (vs raw 30%), avg blended R:R -0.21. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
10. **BEST MODEL**: claude-sonnet-4-6 (31% WR, -0.13 avg R:R). Consider using this model for production runs.
