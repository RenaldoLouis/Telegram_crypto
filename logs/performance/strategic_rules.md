# Strategic Rules (derived from 248 evaluated trades — solid sample)
_Last updated: 2026-07-15 09:46 UTC_

0. **v11.3 VALIDATING (11/20 forward trades)**: so far 45% WR / +0.19R exp vs baseline 30.4% / -0.144R. ACTION: too early to conclude — keep monitoring.

1. **MODERATE SELECTIVITY**: Win rate is 31%. ACTION: Output 2-4 setups per run. Prefer fewer, higher-conviction setups over padding to 5.
2. **CONFIDENCE MISCALIBRATED**: 'High' confidence is 2/9 (22% WR) but 'Medium' is 62/196 (32% WR). ACTION: Reserve 'high confidence' for setups with 3/4 TF confluence + volume confirmed + clean structure. Do NOT equate 4/4 confluence with high confidence (see confluence rule below). If unsure, label 'medium' — it actually performs better.
3. **3/4 CONFLUENCE BEATS 4/4**: 3/4 TF is 62/159 (39% WR, +0.02 avg R:R) but 4/4 TF is 12/64 (19% WR, -0.31 avg R:R). 4/4 alignment = exhausted/late move, not higher probability. ACTION: Treat 3/4 confluence as the sweet spot. When all 4 TFs already agree, the move is likely mature — demand a fresh pullback/retest entry or SKIP; never rank a 4/4 setup #1 just because it is 4/4.
4. **'failed_breakout' STRUGGLING** (6 trades): 0% WR, -1.00 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
5. **'funding_squeeze' STRUGGLING** (7 trades): 14% WR, -0.55 avg R:R. ACTION: Apply extra scrutiny — check entries and stops.
6. **TARGETS TOO FAR**: Predicted avg 1.8R but actual is -0.13R (gap: 1.9R). Average MFE is 1.0R, so set T1 at max 0.8R from entry. Backtest: T1 at 0.75R would hit 54% of trades, T1 at 1.0R would hit 42% (vs current T1 hit rate of 80/248 = 32%). ACTION: Place T1 at the nearest REAL structural level. Use ATR: T1 should be 1.5-2× ATR from entry, NOT 3×+.
7. **WINNING SYMBOLS**: KORUUSDT (2/3). ACTION: Give these symbols slight priority when they appear in the scan.
8. **LOSING SYMBOLS**: ONDOUSDT (0/3), ZECUSDT (0/3), WLDUSDT (0/3), HYPEUSDT (0/3). ACTION: Require 3/4+ TF confluence + volume confirmed for these symbols. Do not include as filler.
9. **IMPROVING**: 2026-06 was 20% → 2026-07 is 42%. Current approach is working — maintain it.
10. **PARTIAL PROFIT HELPS**: With 50% close at T1 + BE stop, blended WR is 40% (vs raw 31%), avg blended R:R -0.15. ACTION: Always recommend taking 50% profit at T1 and moving stop to breakeven.
11. **BEST MODEL**: claude-sonnet-4-6 (32% WR, -0.12 avg R:R). Consider using this model for production runs.
12. **CAUTIOUS REGIME STRONG**: 10/23 (43% WR, +0.11 avg R:R over 23 trades). ACTION: During cautious, maintain current approach — it's working.
13. **RISK_ON REGIME WEAK (NEEDS DATA)**: 2/10 (20% WR, -0.47 avg R:R, only 10 trades). ACTION: In risk_on, stay selective (max 2 setups) but do NOT hard-block — sample too small to be sure.
14. **EFFECTIVE RULES**: regime_cautious (11/23=48%, +0.21R), short_bias (19/41=46%, +0.12R). ACTION: Continue applying these rules — they correlate with positive expectancy.
